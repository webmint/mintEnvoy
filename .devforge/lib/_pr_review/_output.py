"""findings.md renderer for pr_review_helper (PR-REVIEW Step 9 — finalize-output).

`run(target, pr_number, devforge_dir)` is the Phase 7 finalize-output entry
point.  It reads state.json (populated by Step 8 dispatch-review), renders a
Markdown findings report to
  <target>/<devforge_dir>/pr-reviews/<pr_number>/findings.md
and returns a summary dict.

## Responsibility boundary

This helper RENDERS the findings report from state.findings.  It does NOT
invoke any LLM, MCP tool, or git command.  The LLM (orchestrator) is
responsible for populating state.findings before calling this verb.

## findings.md structure (canonical)

  # PR Review Findings — PR #N
  **Repo**: <owner/repo>
  **PR title**: <title or "(not in state)">
  **PR URL**: <url or "(not in state)">
  **Generated**: <ISO timestamp>

  ## Summary
  - **Findings total**: N
  - **By severity**: ...
  - **By category**: ...
  - **Aggregate scores**:
    - Slop-score: N
    - Blast-risk-score: N
    - Drift-summary: ...

  ## Findings
  (sorted by severity then location; each rendered as an H3 block)

## Severity ordering

_SEVERITY_ORDER = ["high", "medium", "low", "nit"]

## Score constants

_SLOP_WEIGHTS = {"high": 30, "medium": 10, "low": 3, "nit": 1}

Slop-score = sum(weight * count) capped at 100.

Blast-risk-score is estimated from len(state.blast) plus the maximum
inbound-callers count from any filled probe spec.  Default 0 when unfilled.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
import os
import tempfile
from typing import Dict, List, Optional

from ._state import PRReviewState, state_path, _PR_REVIEWS_DIR


# ---------------------------------------------------------------------------
# Constants (helper-owned schema).
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = ["high", "medium", "low", "nit"]
_CATEGORY_DISPLAY_ORDER = [
    "smell",
    "blast",
    "drift",
    "convention",
    "hallucination",
    "missing-test",
    "other",
]
_SLOP_WEIGHTS: Dict[str, int] = {"high": 30, "medium": 10, "low": 3, "nit": 1}
_SLOP_CAP = 100
_FINDINGS_FILENAME = "findings.md"


# ---------------------------------------------------------------------------
# Computation helpers.
# ---------------------------------------------------------------------------


def _count_by_severity(findings: List[dict]) -> Dict[str, int]:
    """Return count per severity level for the ordered severity list.

    Counts are included for all four levels; unknown severities are
    collected under the rightmost level ("nit") to keep output stable.
    """
    counts: Dict[str, int] = {s: 0 for s in _SEVERITY_ORDER}
    for finding in findings:
        sev = finding.get("severity", "nit")
        if sev in counts:
            counts[sev] += 1
        else:
            counts["nit"] += 1
    return counts


def _count_by_category(findings: List[dict]) -> Dict[str, int]:
    """Return count per category, including only non-zero entries."""
    counts: Dict[str, int] = {}
    for finding in findings:
        cat = finding.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def _compute_slop_score(by_sev: Dict[str, int]) -> int:
    """Return slop score (0-100) from severity counts.

    Formula: sum(weight * count for weight in _SLOP_WEIGHTS), capped at 100.

    Args:
        by_sev: dict with keys from _SEVERITY_ORDER, values are counts.

    Returns:
        int in [0, 100].
    """
    raw = sum(_SLOP_WEIGHTS.get(sev, 0) * count for sev, count in by_sev.items())
    return min(raw, _SLOP_CAP)


def _compute_blast_risk_score(state: PRReviewState) -> int:
    """Estimate blast-risk score (0-100) from state.blast.

    Heuristic: 3 points per probe spec (symbol changed) + max inbound caller
    count among filled probes.  Capped at 100.

    Returns 0 when state.blast is empty.
    """
    blast = state.blast or []
    if not blast:
        return 0
    base = min(len(blast) * 3, 60)
    max_callers = 0
    for probe in blast:
        if probe.get("filled", False):
            callers = probe.get("callers") or []
            if len(callers) > max_callers:
                max_callers = len(callers)
    return min(base + max_callers * 2, _SLOP_CAP)


def _compute_drift_summary(state: PRReviewState) -> str:
    """Return a short drift-coverage summary string.

    Returns "drift not assessed" when no bullets are present.
    Returns "<covered>/<total> covered" when bullets exist (coverage_matrix
    entries with status == "satisfied" are counted as covered).
    """
    drift = state.drift or {}
    bullets = drift.get("bullets") or []
    if not bullets:
        return "drift not assessed"
    total = len(bullets)
    coverage_matrix = drift.get("coverage_matrix") or []
    satisfied = sum(
        1 for entry in coverage_matrix
        if entry.get("status") == "satisfied"
    )
    return "{covered}/{total} covered".format(covered=satisfied, total=total)


def _sort_findings(findings: List[dict]) -> List[dict]:
    """Sort findings by severity order then location (alphabetical).

    Findings with unknown severity sort to the end of the severity groups
    (after "nit").  Findings with no location sort before those with one (empty string < any path string lexicographically).
    """
    sev_index = {s: i for i, s in enumerate(_SEVERITY_ORDER)}
    unknown_sev_idx = len(_SEVERITY_ORDER)

    def sort_key(f: dict):
        sev = f.get("severity", "nit")
        idx = sev_index.get(sev, unknown_sev_idx)
        loc = f.get("location") or ""
        return (idx, loc)

    return sorted(findings, key=sort_key)


# ---------------------------------------------------------------------------
# Render helpers.
# ---------------------------------------------------------------------------


def _render_finding(finding: dict, idx: int) -> str:
    """Render one finding as a Markdown H3 block.

    Args:
        finding: dict with keys severity, location, category, evidence,
                 fix_hint, source_heuristic.
        idx:     1-based index (unused in output body; available for callers).

    Returns:
        Multi-line Markdown string ending with "---\\n".
    """
    severity = finding.get("severity") or "low"
    location = finding.get("location") or "(unknown)"
    category = finding.get("category") or "other"
    evidence = finding.get("evidence") or ""
    fix_hint = finding.get("fix_hint") or ""
    source_heuristic = finding.get("source_heuristic") or ""

    # Derive source display: prefer source_heuristic; fall back to category-default.
    source_display = source_heuristic if source_heuristic else "{0}-heuristic".format(category)

    lines = [
        "### [{sev}] `{loc}` ({cat})".format(sev=severity, loc=location, cat=category),
        "",
        "**Evidence**: {ev}".format(ev=evidence if evidence else "(none)"),
        "",
        "**Fix**: {fix}".format(fix=fix_hint if fix_hint else "(none)"),
        "",
        "**Source**: {src}".format(src=source_display),
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _render_summary(
    state: PRReviewState,
    by_sev: Dict[str, int],
    by_cat: Dict[str, int],
    slop: int,
    blast_risk: int,
    drift: str,
) -> str:
    """Render the ## Summary section.

    Zero-count categories are omitted from the category line.

    Args:
        state:      PRReviewState (used for PR metadata).
        by_sev:     severity counts dict.
        by_cat:     category counts dict.
        slop:       slop score (0-100).
        blast_risk: blast-risk score (0-100).
        drift:      drift summary string.

    Returns:
        Multi-line Markdown string.
    """
    # Build severity line.
    sev_parts = [
        "{s}={c}".format(s=s, c=by_sev.get(s, 0))
        for s in _SEVERITY_ORDER
    ]

    # Build category line — display-ordered, omit zeros.
    seen_cats = set(by_cat.keys())
    ordered_cats = [c for c in _CATEGORY_DISPLAY_ORDER if c in seen_cats]
    # Append any cats not in the display order (preserve insertion order).
    for c in by_cat:
        if c not in ordered_cats:
            ordered_cats.append(c)
    cat_parts = [
        "{c}={n}".format(c=c, n=by_cat[c])
        for c in ordered_cats
        if by_cat.get(c, 0) > 0
    ]

    lines = [
        "## Summary",
        "",
        "- **Findings total**: {n}".format(n=sum(by_sev.values())),
        "- **By severity**: {s}".format(s=" ".join(sev_parts)),
    ]
    if cat_parts:
        lines.append("- **By category**: {c}".format(c=" ".join(cat_parts)))
    else:
        lines.append("- **By category**: (none)")
    lines += [
        "- **Aggregate scores**:",
        "  - Slop-score: {score}".format(score=slop),
        "  - Blast-risk-score: {score}".format(score=blast_risk),
        "  - Drift-summary: {drift}".format(drift=drift),
        "",
    ]
    return "\n".join(lines)


def _render_findings_md(state: PRReviewState) -> str:
    """Render the full findings.md content from state.

    Args:
        state: PRReviewState with populated fields.

    Returns:
        Complete Markdown string.
    """
    now_ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Header metadata.
    repo = state.repo or "(not in state)"
    pr_number = state.pr_number
    if state.repo and state.pr_number:
        pr_url = "https://github.com/{repo}/pull/{num}".format(
            repo=state.repo, num=state.pr_number
        )
    else:
        pr_url = "(not in state)"

    pr_title = state.pr_title if state.pr_title else "(not in state)"
    header_lines = [
        "# PR Review Findings — PR #{n}".format(n=pr_number),
        "",
        "**Repo**: {repo}".format(repo=repo),
        "**PR title**: {title}".format(title=pr_title),
        "**PR URL**: {url}".format(url=pr_url),
        "**Generated**: {ts}".format(ts=now_ts),
        "",
    ]

    findings = state.findings or []
    by_sev = _count_by_severity(findings)
    by_cat = _count_by_category(findings)
    slop = _compute_slop_score(by_sev)
    blast_risk = _compute_blast_risk_score(state)
    drift = _compute_drift_summary(state)

    summary_block = _render_summary(state, by_sev, by_cat, slop, blast_risk, drift)

    findings_header = ["## Findings", ""]

    if not findings:
        findings_body = [
            "_No findings recorded. Either Step 8 dispatch-review was not run,"
            " or reviewer concluded PR is clean._",
            "",
        ]
        findings_section = "\n".join(findings_body)
    else:
        sorted_findings = _sort_findings(findings)
        parts = []
        for i, finding in enumerate(sorted_findings, start=1):
            parts.append(_render_finding(finding, i))
        findings_section = "\n".join(parts)

    return (
        "\n".join(header_lines)
        + "\n"
        + summary_block
        + "\n"
        + "\n".join(findings_header)
        + "\n"
        + findings_section
    )


# ---------------------------------------------------------------------------
# Atomic writer.
# ---------------------------------------------------------------------------


def _write_findings_md(findings_path: str, content: str) -> None:
    """Write findings Markdown to findings_path atomically.

    Uses tempfile.mkstemp in the same directory, then os.replace.
    On failure, unlinks the temp file before re-raising.

    Args:
        findings_path: Absolute path to the destination findings.md.
                       Parent directory must already exist.
        content:       Markdown string to write.

    Raises:
        OSError: if write or rename fails.
    """
    findings_dir = os.path.dirname(findings_path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="findings-", suffix=".tmp.md", dir=findings_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, findings_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(
    target: str,
    pr_number: int,
    devforge_dir: str = ".devforge",
) -> dict:
    """Read state, render findings.md, return summary dict.

    Args:
        target:       Absolute (or relative) path to the reviewer's local repo root.
        pr_number:    PR number (positive int).
        devforge_dir: Name of the devforge directory under target (default ".devforge").

    Returns:
        dict with keys: status, state_path, findings_path, findings_total,
        by_severity, by_category, slop_score, blast_risk_score, drift_summary.

    Raises:
        ValueError: if state.json does not exist or cannot be parsed.
        OSError:    if findings.md cannot be written.
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

    # Determine output path.
    pr_dir = os.path.join(abs_devforge, _PR_REVIEWS_DIR, str(pr_number))
    os.makedirs(pr_dir, exist_ok=True)
    findings_path = os.path.join(pr_dir, _FINDINGS_FILENAME)

    # Render and write.
    content = _render_findings_md(state)
    _write_findings_md(findings_path, content)

    # Build summary.
    findings = state.findings or []
    by_sev = _count_by_severity(findings)
    by_cat = _count_by_category(findings)
    slop = _compute_slop_score(by_sev)
    blast_risk = _compute_blast_risk_score(state)
    drift = _compute_drift_summary(state)

    return {
        "status": "ok",
        "state_path": sp,
        "findings_path": findings_path,
        "findings_total": len(findings),
        "by_severity": by_sev,
        "by_category": by_cat,
        "slop_score": slop,
        "blast_risk_score": blast_risk,
        "drift_summary": drift,
    }
