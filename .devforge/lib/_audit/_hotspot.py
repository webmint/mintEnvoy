"""Hotspot risk-scoring engine for audit_helper --top N (Phase 1).

Implements the risk formula:
    risk(file) = w_c * churn_norm + w_k * callers_norm + w_s * size_norm

where *_norm = min-max normalised within the candidate set.  When max == min
for a metric, all norms for that metric are 0.0 (no division by zero).

CBM constraint (plan Decision 8):
    This module does NOT call CBM / MCP tools.  Caller counts are supplied by
    the LLM orchestrator as a JSON payload (``--callers <path>`` in the CLI).
    If the payload is absent, the CLI layer exits 2 immediately.

Subprocess calls:
    ``compute_churn``  — ``git log --oneline``  (workspace-relative counts)
    ``enumerate_candidates`` — ``git ls-files``  (workspace-relative paths)

Stdlib only.  Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import os
import subprocess
from typing import Dict, List, Optional

from .hotspot_schema import FileScore, HotspotResult, SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: Dict[str, float] = {"c": 0.5, "k": 0.4, "s": 0.1}

_SOURCE_EXTS = frozenset((
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue",
    ".go", ".rs", ".java", ".rb", ".php", ".cs",
    ".swift", ".kt", ".scala", ".c", ".cc", ".cpp",
    ".h", ".hpp",
))

# ---------------------------------------------------------------------------
# parse_weights
# ---------------------------------------------------------------------------


def parse_weights(weights_dict_or_none):
    # type: (Optional[Dict]) -> Dict[str, float]
    """Validate and return a weights dict.

    Args:
        weights_dict_or_none: None → return defaults; dict → validate and
            return.  Must have exactly keys {"c", "k", "s"}, each a float in
            [0, 1], and the sum must equal 1.0 within 1e-6.

    Returns:
        dict with keys "c", "k", "s".

    Raises:
        ValueError: if the dict is malformed.
    """
    if weights_dict_or_none is None:
        return dict(_DEFAULT_WEIGHTS)

    w = weights_dict_or_none
    expected_keys = {"c", "k", "s"}

    if not isinstance(w, dict):
        raise ValueError(
            "weights must be a dict, got {0}".format(type(w).__name__)
        )

    got_keys = set(w.keys())
    missing = expected_keys - got_keys
    if missing:
        raise ValueError(
            "weights is missing keys: {0}".format(sorted(missing))
        )
    extra = got_keys - expected_keys
    if extra:
        raise ValueError(
            "weights has unexpected keys: {0}".format(sorted(extra))
        )

    for key in ("c", "k", "s"):
        val = w[key]
        if isinstance(val, bool):
            raise ValueError(
                "weights[{0!r}] must be a float, got bool".format(key)
            )
        if not isinstance(val, (int, float)):
            raise ValueError(
                "weights[{0!r}] must be a float, got {1}".format(
                    key, type(val).__name__
                )
            )
        fv = float(val)
        if not (0.0 <= fv <= 1.0):
            raise ValueError(
                "weights[{0!r}] must be in [0, 1], got {1}".format(key, fv)
            )

    total = float(w["c"]) + float(w["k"]) + float(w["s"])
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            "weights must sum to 1.0 (got {0:.8f})".format(total)
        )

    return {"c": float(w["c"]), "k": float(w["k"]), "s": float(w["s"])}


# ---------------------------------------------------------------------------
# compute_churn
# ---------------------------------------------------------------------------


def compute_churn(file_paths, repo_root, since):
    # type: (List[str], str, str) -> Dict[str, int]
    """Return {file: commit_count} for files in file_paths.

    Runs ``git -C <repo_root> log --since=<since> --oneline -- <file>`` for
    each file and counts output lines.  Files with no commits → 0.

    Args:
        file_paths: workspace-relative file paths.
        repo_root:  absolute (or relative) path to the git repo root.
        since:      git --since string (e.g. ``"90.days.ago"`` or ISO date).

    Returns:
        dict mapping each path in file_paths to its commit count.  Always
        contains every path in file_paths (missing → 0).
    """
    result: Dict[str, int] = {}

    for fp in file_paths:
        cmd = [
            "git", "-C", repo_root,
            "log", "--since={0}".format(since), "--oneline", "--", fp,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if proc.returncode == 0:
                lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
                result[fp] = len(lines)
            else:
                result[fp] = 0
        except FileNotFoundError:
            # git not on PATH
            result[fp] = 0
        except subprocess.TimeoutExpired:
            result[fp] = 0

    return result


# ---------------------------------------------------------------------------
# compute_loc
# ---------------------------------------------------------------------------


def compute_loc(file_paths, repo_root):
    # type: (List[str], str) -> Dict[str, int]
    """Return {file: non_blank_line_count} for files in file_paths.

    LOC = count of non-blank lines (lines that are non-empty after strip()).
    Unreadable or binary files → 0 (error caught and continues).

    Args:
        file_paths: workspace-relative file paths.
        repo_root:  repo root directory (used to resolve relative paths).

    Returns:
        dict mapping each path to its LOC.
    """
    result: Dict[str, int] = {}

    for fp in file_paths:
        abs_path = os.path.join(repo_root, fp)
        try:
            count = 0
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        count += 1
            result[fp] = count
        except (OSError, UnicodeDecodeError):
            result[fp] = 0

    return result


# ---------------------------------------------------------------------------
# load_callers
# ---------------------------------------------------------------------------


def load_callers(callers_payload):
    # type: (dict) -> Dict[str, int]
    """Normalise an orchestrator CBM payload to {file: int}.

    Accepts per-entry values in two forms:
    - strict int (not bool): used directly as the inbound-edge count (negatives
      clamped to 0). bool values degrade to 0 (a JSON `true`/`false` is a
      malformed count, not 1/0).
    - list of caller qualified-names: deduped length used as the count.
    Any other value type degrades to 0 rather than crashing the run.

    Args:
        callers_payload: dict from the JSON file written by the orchestrator.

    Returns:
        dict {file_path: caller_count}.  Only contains entries present in the
        payload.  Missing files must be handled at the merge step (→ 0).

    Raises:
        ValueError: if callers_payload is not a dict.
    """
    if not isinstance(callers_payload, dict):
        raise ValueError(
            "callers payload must be a dict, got {0}".format(
                type(callers_payload).__name__
            )
        )

    result: Dict[str, int] = {}
    for key, val in callers_payload.items():
        if isinstance(val, int) and not isinstance(val, bool):
            result[key] = max(0, val)
        elif isinstance(val, list):
            result[key] = len(set(val))
        else:
            # Unexpected shape — treat as 0 rather than crashing the whole run.
            result[key] = 0
    return result


# ---------------------------------------------------------------------------
# score_files
# ---------------------------------------------------------------------------


def score_files(metrics, weights, top_n):
    # type: (List[Dict], Dict[str, float], int) -> HotspotResult
    """Compute normalised scores, rank files, and return a HotspotResult.

    PURE function — no I/O, no subprocess.

    Normalisation:
        churn_norm, callers_norm, size_norm = min-max within the candidate set.
        When max == min for a metric, ALL norms for that metric are 0.0.

    Tie-break:
        Primary: score descending.
        Secondary: churn descending.
        Tertiary: file path ascending (deterministic).

    Args:
        metrics: list of dicts {"file", "churn", "callers", "size_loc"}.
        weights: validated weights dict {"c", "k", "s"}.
        top_n:   how many files go into HotspotResult.top; the next 10
                 positions go into next_candidates.

    Returns:
        HotspotResult (frozen dataclass).
    """
    if not metrics:
        return HotspotResult(
            schema_version=SCHEMA_VERSION,
            weights=weights,
            top=[],
            next_candidates=[],
            total_files_scored=0,
        )

    # Extract raw metric vectors.
    churns = [float(m["churn"]) for m in metrics]
    callers_list = [float(m["callers"]) for m in metrics]
    sizes = [float(m["size_loc"]) for m in metrics]

    def _norm_vec(values):
        # type: (List[float]) -> List[float]
        mn = min(values)
        mx = max(values)
        if mx == mn:
            return [0.0] * len(values)
        rng = mx - mn
        return [(v - mn) / rng for v in values]

    churn_norms = _norm_vec(churns)
    caller_norms = _norm_vec(callers_list)
    size_norms = _norm_vec(sizes)

    wc = weights["c"]
    wk = weights["k"]
    ws = weights["s"]

    scored = []
    for i, m in enumerate(metrics):
        sc = wc * churn_norms[i] + wk * caller_norms[i] + ws * size_norms[i]
        # Clamp to [0,1]: parse_weights tolerates a sum of 1±1e-6, so a file
        # maxing all three norms can yield e.g. 1.0000009 and trip
        # FileScore.__post_init__'s range check. Clamp before constructing.
        sc = min(1.0, max(0.0, sc))
        scored.append((
            m["file"],
            int(m["churn"]),
            int(m["callers"]),
            int(m["size_loc"]),
            churn_norms[i],
            caller_norms[i],
            size_norms[i],
            sc,
        ))

    # Sort: score DESC, churn DESC, file ASC
    scored.sort(key=lambda x: (-x[7], -x[1], x[0]))

    file_scores = []
    for rank, item in enumerate(scored, start=1):
        (fp, churn, callers, size_loc, cn, kn, sn, sc) = item
        file_scores.append(FileScore(
            file=fp,
            churn=churn,
            callers=callers,
            size_loc=size_loc,
            churn_norm=round(cn, 10),
            callers_norm=round(kn, 10),
            size_norm=round(sn, 10),
            score=round(sc, 10),
            rank=rank,
        ))

    top = file_scores[:top_n]
    next_candidates = file_scores[top_n: top_n + 10]

    return HotspotResult(
        schema_version=SCHEMA_VERSION,
        weights=weights,
        top=top,
        next_candidates=next_candidates,
        total_files_scored=len(metrics),
    )


# ---------------------------------------------------------------------------
# enumerate_candidates
# ---------------------------------------------------------------------------


def enumerate_candidates(repo_root):
    # type: (str) -> List[str]
    """Return workspace-relative source file paths from ``git ls-files``.

    Filters by _SOURCE_EXTS.  Returns sorted list.

    Args:
        repo_root: repo root (passed as -C to git).

    Returns:
        Sorted list of workspace-relative paths.

    Raises:
        FileNotFoundError: if git is not on PATH (propagated to caller).
        ValueError: if git exits non-zero.
    """
    cmd = ["git", "-C", repo_root, "ls-files"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except FileNotFoundError:
        raise

    if proc.returncode != 0:
        raise ValueError(
            "git ls-files exited {0}: {1}".format(
                proc.returncode, proc.stderr.strip()
            )
        )

    result = []
    for line in proc.stdout.splitlines():
        fp = line.strip()
        if not fp:
            continue
        _, ext = os.path.splitext(fp)
        if ext.lower() in _SOURCE_EXTS:
            result.append(fp)

    result.sort()
    return result


# ---------------------------------------------------------------------------
# run_compute_hotspots
# ---------------------------------------------------------------------------


def run_compute_hotspots(repo_root, callers_payload, top_n, weights, since):
    # type: (str, dict, int, Optional[Dict], str) -> dict
    """Orchestration function: enumerate → churn → loc → merge → score.

    Args:
        repo_root:       Path to the git repo root.
        callers_payload: Raw dict from the CBM JSON payload (may be empty).
        top_n:           How many files go into the top list.
        weights:         None → use defaults; dict → validated via parse_weights.
        since:           git --since string (e.g. ``"90.days.ago"``).

    Returns:
        Plain dict (``dataclasses.asdict(hotspot_result)``) for JSON output.
    """
    validated_weights = parse_weights(weights)
    caller_map = load_callers(callers_payload)

    candidates = enumerate_candidates(repo_root)

    churn_map = compute_churn(candidates, repo_root, since)
    loc_map = compute_loc(candidates, repo_root)

    metrics = []
    for fp in candidates:
        metrics.append({
            "file": fp,
            "churn": churn_map.get(fp, 0),
            "callers": caller_map.get(fp, 0),
            "size_loc": loc_map.get(fp, 0),
        })

    result = score_files(metrics, validated_weights, top_n)
    return dataclasses.asdict(result)
