"""Replay-corpus writer for pr_review_helper (PR-REVIEW Step 9 — append-to-replay-corpus).

`run(target, pr_number, devforge_dir)` is the Phase 7 append-to-replay-corpus
entry point.  It:
  1. Reads state.json.
  2. Writes a full state snapshot to
       <target>/<devforge_dir>/pr-reviews/<pr_number>/pr-review-bundle.json
  3. Upserts an entry in the corpus-wide index at
       <target>/<devforge_dir>/pr-reviews/_corpus_index.json

Both files are written atomically (temp+os.replace).

## pr-review-bundle.json schema (helper-owned)

    {
        "schema_version": "1",
        "generated_at": "<ISO timestamp>",
        "pr_number": <N>,
        "repo": "<owner/repo>",
        "state": <full state.json contents>
    }

## _corpus_index.json schema (helper-owned)

    {
        "schema_version": "1",
        "entries": [
            {
                "pr_number": <N>,
                "repo": "<owner/repo>",
                "bundle_path": "<absolute path to bundle json>",
                "first_reviewed_at": "<ISO>",
                "last_reviewed_at": "<ISO>",
                "review_count": <int>,
                "findings_count": <int>,
                "smells_count": <int>,
                "blast_probes_count": <int>,
                "drift_bullets_count": <int>
            },
            ...
        ]
    }

## Idempotency / upsert semantics

- Reads existing index (creates empty default when absent or malformed).
- Finds entry with matching pr_number AND repo (same PR# but different repo
  is a distinct entry — not a collision).
- If found: updates last_reviewed_at + increments review_count + refreshes
  counts; first_reviewed_at is preserved.
- If not found: appends new entry with first_reviewed_at = last_reviewed_at = now,
  review_count = 1.
- Index is written atomically after upsert.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
import os
import tempfile
from typing import List, Optional

from ._state import PRReviewState, state_path, _PR_REVIEWS_DIR


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

_BUNDLE_FILENAME = "pr-review-bundle.json"
_CORPUS_INDEX_FILENAME = "_corpus_index.json"
_SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _corpus_index_path(target_devforge: str) -> str:
    """Return absolute path to the corpus-wide index file.

    Path: <target_devforge>/pr-reviews/_corpus_index.json
    """
    return os.path.join(target_devforge, _PR_REVIEWS_DIR, _CORPUS_INDEX_FILENAME)


def _load_corpus_index(path: str) -> dict:
    """Load corpus index from path; return empty default on absence or malformed JSON.

    Fail-soft: any I/O or parse error returns the canonical empty index rather
    than propagating the error.  The caller writes back a fresh index, so
    data loss is limited to the malformed/missing prior state.

    Args:
        path: Absolute path to the index JSON file.

    Returns:
        dict with keys "schema_version" and "entries" (list).
    """
    empty: dict = {"schema_version": _SCHEMA_VERSION, "entries": []}
    if not os.path.exists(path):
        return empty
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(data, dict):
        return empty
    if not isinstance(data.get("entries"), list):
        return empty
    return data


def _upsert_corpus_entry(
    index: dict,
    pr_number: int,
    repo: str,
    bundle_path: str,
    findings_count: int,
    smells_count: int,
    blast_count: int,
    drift_count: int,
    now_ts: str,
) -> str:
    """Upsert a corpus entry in-place; return "created" or "updated".

    Matches by (pr_number, repo).  Same PR# with different repo is a separate
    entry.

    Args:
        index:          Corpus index dict (mutated in-place).
        pr_number:      PR number (int).
        repo:           Owner/repo string.
        bundle_path:    Absolute path to the bundle JSON.
        findings_count: Count of state.findings.
        smells_count:   Count of state.smells.
        blast_count:    Count of state.blast.
        drift_count:    Count of state.drift["bullets"] (0 when absent).
        now_ts:         ISO timestamp string for this invocation.

    Returns:
        "created" or "updated".
    """
    entries: List[dict] = index.get("entries", [])
    for entry in entries:
        if entry.get("pr_number") == pr_number and entry.get("repo") == repo:
            # Update existing entry; preserve first_reviewed_at.
            entry["last_reviewed_at"] = now_ts
            entry["review_count"] = entry.get("review_count", 0) + 1
            entry["findings_count"] = findings_count
            entry["smells_count"] = smells_count
            entry["blast_probes_count"] = blast_count
            entry["drift_bullets_count"] = drift_count
            entry["bundle_path"] = bundle_path
            return "updated"

    # New entry.
    entries.append({
        "pr_number": pr_number,
        "repo": repo,
        "bundle_path": bundle_path,
        "first_reviewed_at": now_ts,
        "last_reviewed_at": now_ts,
        "review_count": 1,
        "findings_count": findings_count,
        "smells_count": smells_count,
        "blast_probes_count": blast_count,
        "drift_bullets_count": drift_count,
    })
    index["entries"] = entries
    return "created"


def _write_corpus_index(path: str, index: dict) -> None:
    """Write corpus index to path atomically.

    Uses tempfile.mkstemp in the same directory, then os.replace.
    On failure, unlinks the temp file before re-raising.

    Args:
        path:  Absolute path to the destination index JSON.
               Parent directory must already exist.
        index: Dict to serialize.

    Raises:
        OSError: if write or rename fails.
    """
    index_dir = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="corpus-index-", suffix=".tmp.json", dir=index_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _write_bundle(
    target_devforge: str,
    pr_number: int,
    state_dict: dict,
    repo: str,
    now_ts: str,
) -> str:
    """Write pr-review-bundle.json snapshot and return its absolute path.

    Bundle schema: schema_version, generated_at, pr_number, repo, state.

    Args:
        target_devforge: Absolute path to <target>/<devforge_dir>.
        pr_number:       PR number.
        state_dict:      Raw state dict (as loaded from state.json).
        repo:            Owner/repo string from state.
        now_ts:          ISO timestamp string.

    Returns:
        Absolute path to the written bundle file.

    Raises:
        OSError: if write fails.
    """
    pr_dir = os.path.join(target_devforge, _PR_REVIEWS_DIR, str(pr_number))
    os.makedirs(pr_dir, exist_ok=True)
    bundle_path = os.path.join(pr_dir, _BUNDLE_FILENAME)

    bundle = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": now_ts,
        "pr_number": pr_number,
        "repo": repo,
        "state": state_dict,
    }

    fd, tmp_path = tempfile.mkstemp(
        prefix="bundle-", suffix=".tmp.json", dir=pr_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, bundle_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return bundle_path


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(
    target: str,
    pr_number: int,
    devforge_dir: str = ".devforge",
) -> dict:
    """Read state, write bundle + upsert corpus index, return summary dict.

    Args:
        target:       Absolute (or relative) path to the reviewer's local repo root.
        pr_number:    PR number (positive int).
        devforge_dir: Name of the devforge directory under target (default ".devforge").

    Returns:
        dict with keys: status, bundle_path, corpus_index_path,
        entry_action, review_count, findings_count.

    Raises:
        ValueError: if state.json does not exist or cannot be parsed.
        OSError:    if bundle or index cannot be written.
    """
    abs_target = os.path.abspath(target)
    abs_devforge = os.path.join(abs_target, devforge_dir)
    sp = state_path(abs_devforge, pr_number)

    if not os.path.exists(sp):
        raise ValueError(
            "no state.json at {path}; run `intake` first".format(path=sp)
        )

    try:
        with open(sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            "cannot read state.json at {path}: {exc}".format(path=sp, exc=exc)
        ) from exc

    try:
        state = PRReviewState(**state_dict)
    except TypeError as exc:
        raise ValueError(
            "state schema error in {path}: {exc}".format(path=sp, exc=exc)
        ) from exc

    now_ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo = state.repo or ""

    # Write bundle snapshot.
    bundle_path = _write_bundle(
        target_devforge=abs_devforge,
        pr_number=pr_number,
        state_dict=state_dict,
        repo=repo,
        now_ts=now_ts,
    )

    # Compute counts for index.
    findings_count = len(state.findings or [])
    smells_count = len(state.smells or [])
    blast_count = len(state.blast or [])
    drift = state.drift or {}
    drift_count = len(drift.get("bullets") or [])

    # Ensure the pr-reviews dir exists for index write.
    pr_reviews_dir = os.path.join(abs_devforge, _PR_REVIEWS_DIR)
    os.makedirs(pr_reviews_dir, exist_ok=True)

    # Load / upsert / write corpus index.
    idx_path = _corpus_index_path(abs_devforge)
    index = _load_corpus_index(idx_path)
    action = _upsert_corpus_entry(
        index=index,
        pr_number=pr_number,
        repo=repo,
        bundle_path=bundle_path,
        findings_count=findings_count,
        smells_count=smells_count,
        blast_count=blast_count,
        drift_count=drift_count,
        now_ts=now_ts,
    )
    _write_corpus_index(idx_path, index)

    # Find updated review_count from index.
    review_count = 1
    for entry in index.get("entries", []):
        if entry.get("pr_number") == pr_number and entry.get("repo") == repo:
            review_count = entry.get("review_count", 1)
            break

    return {
        "status": "ok",
        "bundle_path": bundle_path,
        "corpus_index_path": idx_path,
        "entry_action": action,
        "review_count": review_count,
        "findings_count": findings_count,
    }
