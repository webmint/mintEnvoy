"""Research handoff importer for pr_review_helper (PR-REVIEW Step 6).

`run(target, pr_number, devforge_dir)` is the Phase 4b entry point.

It reads state.json (written by Step 3 intake), scans <target>/research/
for date-slug subdirectories containing handoff.json files, filters by
relevance to state.ticket_text or PR title, and APPENDS/REPLACES the
`research_handoffs` key in state.bundle.

## research_handoffs schema (helper-owns; LLM at Step 8 consumes it)

After import-handoffs, state.bundle["research_handoffs"] contains:

    [
        {
            "path": "<absolute path to handoff.json>",
            "date": "YYYY-MM-DD",
            "slug": "<topic slug>",
            "verdict": "<handoff['verdict'] if present, else handoff['mode'] if present, else ''>",
            "mode": "<from handoff.json or ''>",
            "matched_via": "ticket_text_substring" | "title_substring" | "all",
            "content_excerpt": "<first 5000 chars of handoff.json>"
        },
        ...
    ]

`matched_via` values:
  "ticket_text_substring" — the research dir slug or handoff mode/verdict
                            contains a substring of state.ticket_text.
  "title_substring"       — the research dir slug contains a substring
                            of the PR title (from state.pr_body header
                            or state.repo field).
  "all"                   — no filter criteria available (ticket_text and
                            pr_title both empty); all handoffs returned.

## Filtering

Substring matching is case-insensitive. The filter checks whether
`topic_slug` (extracted from the research dir name) contains any word
from ticket_text or PR title (split on whitespace, minimum 3 chars).

If both ticket_text and a derivable PR title are empty, the filter is
skipped and all handoffs are returned with matched_via="all".

## Bounds

- Handoffs are sorted most-recent-first by date (extracted from dir name).
- Capped at _MAX_HANDOFFS = 20 after filtering.

## Re-invocation semantics

Running import-handoffs REPLACES state.bundle["research_handoffs"] on
each invocation. Prior values are discarded.

## CBM constraint

This module does NOT call CBM / MCP tools. All data comes from the
local filesystem. Does NOT invoke `gh` or any subprocess.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from typing import Dict, List, Optional

from ._state import PRReviewState, state_path


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

_MAX_HANDOFFS = 20
_EXCERPT_CHARS = 5000
_MIN_FILTER_TOKEN_LEN = 3   # tokens shorter than this are ignored in filter


# ---------------------------------------------------------------------------
# Research directory scanner.
# ---------------------------------------------------------------------------


def _scan_research_dir(target: str) -> List[str]:
    """Return sorted list of handoff.json paths under <target>/research/.

    Scans for date-slug subdirectories of the form YYYY-MM-DD-*.
    Returns only paths where handoff.json actually exists and is a file.

    Args:
        target: Absolute path to the repository root.

    Returns:
        List of absolute paths to handoff.json files (may be empty).
    """
    research_dir = os.path.join(target, "research")
    if not os.path.isdir(research_dir):
        return []

    try:
        entries = os.listdir(research_dir)
    except OSError:
        return []

    paths = []
    for name in entries:
        subdir = os.path.join(research_dir, name)
        if not os.path.isdir(subdir):
            continue
        hf_path = os.path.join(subdir, "handoff.json")
        if os.path.isfile(hf_path):
            paths.append(hf_path)

    paths.sort()
    return paths


# ---------------------------------------------------------------------------
# Handoff parser.
# ---------------------------------------------------------------------------


def _parse_handoff(path: str) -> Optional[Dict]:
    """Parse a handoff.json file and extract key metadata.

    Returns a dict with keys: path, date, slug, verdict, mode.
    Returns None on any parse error (fail-soft).

    The dir name is expected to be YYYY-MM-DD-<slug>. If the name does
    not match the expected pattern, date defaults to "" and slug defaults
    to the dir basename.

    The `verdict` output field uses a fallback chain:
      handoff['verdict'] > handoff['mode'] > ""
    This handles older handoff.json shapes that don't have an explicit
    `verdict` field but do have a `mode` classifier.

    Args:
        path: Absolute path to the handoff.json file.

    Returns:
        Metadata dict, or None on failure.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    # Extract date and slug from the parent directory name.
    dir_name = os.path.basename(os.path.dirname(path))
    # Expected format: YYYY-MM-DD-<slug>
    date = ""
    slug = dir_name
    if len(dir_name) >= 10 and dir_name[4] == "-" and dir_name[7] == "-":
        date = dir_name[:10]
        slug = dir_name[11:] if len(dir_name) > 11 else ""

    verdict = ""
    mode = ""
    if isinstance(data, dict):
        verdict = str(data.get("verdict", data.get("mode", "")))
        mode = str(data.get("mode", ""))

    # content_excerpt: first _EXCERPT_CHARS characters of the raw JSON text.
    excerpt = _excerpt_handoff(raw)

    return {
        "path": path,
        "date": date,
        "slug": slug,
        "verdict": verdict,
        "mode": mode,
        "content_excerpt": excerpt,
    }


# ---------------------------------------------------------------------------
# Filter helper.
# ---------------------------------------------------------------------------


def _filter_by_ticket_text(
    handoffs: List[Dict],
    ticket_text: str,
    pr_title: str,
) -> List[Dict]:
    """Filter handoffs by relevance to ticket_text or PR title.

    Splitting on whitespace, extracts tokens of >= _MIN_FILTER_TOKEN_LEN
    chars from ticket_text and pr_title. A handoff matches if its `slug`
    contains any of those tokens (case-insensitive substring match).

    When both ticket_text and pr_title are empty (no filter criteria),
    returns all handoffs with matched_via="all".

    Args:
        handoffs:    List of handoff metadata dicts from _parse_handoff.
        ticket_text: From state.ticket_text (may be empty).
        pr_title:    PR title string (may be empty).

    Returns:
        Filtered list with matched_via field added to each entry.
    """
    # Build filter tokens from both sources.
    def _tokens(text: str) -> List[str]:
        return [
            t.lower() for t in text.split()
            if len(t) >= _MIN_FILTER_TOKEN_LEN
        ]

    ticket_tokens = _tokens(ticket_text)
    title_tokens = _tokens(pr_title)

    if not ticket_tokens and not title_tokens:
        # No filter criteria: return all with matched_via="all".
        return [dict(h, matched_via="all") for h in handoffs]

    results = []
    for h in handoffs:
        slug_lower = h["slug"].lower()
        matched_via = None

        # Check ticket_text tokens first.
        if ticket_tokens:
            for tok in ticket_tokens:
                if tok in slug_lower:
                    matched_via = "ticket_text_substring"
                    break

        # If no ticket match, try title tokens.
        if matched_via is None and title_tokens:
            for tok in title_tokens:
                if tok in slug_lower:
                    matched_via = "title_substring"
                    break

        if matched_via is not None:
            results.append(dict(h, matched_via=matched_via))

    return results


# ---------------------------------------------------------------------------
# Excerpt helper (exposed for testing; called by _parse_handoff).
# ---------------------------------------------------------------------------


def _excerpt_handoff(raw_content: str, max_chars: int = _EXCERPT_CHARS) -> str:
    """Return up to max_chars characters of raw_content with truncation marker.

    Called by _parse_handoff (single canonical truncation impl).

    Args:
        raw_content: Raw string to excerpt.
        max_chars:   Character cap (default: _EXCERPT_CHARS = 5000).

    Returns:
        Truncated string (with "... [truncated]" suffix if over cap),
        or the original string if under cap.
    """
    if len(raw_content) <= max_chars:
        return raw_content
    return raw_content[:max_chars] + "... [truncated]"


# ---------------------------------------------------------------------------
# Atomic state writer.
# ---------------------------------------------------------------------------


# TODO(Step 7+): consolidate _write_state across _intake.py / _blast.py /
# _bundle.py / _handoff_import.py / _scope_drift.py (5 copies). Extract to
# _state.py.write_state when next verb would otherwise create a 6th copy.
def _write_state(target_path: str, state: PRReviewState) -> None:
    """Write PRReviewState as JSON to target_path atomically.

    Uses tempfile.mkstemp in the same directory as target_path then os.replace.
    On failure, unlinks the temp file and re-raises.

    Args:
        target_path: Absolute path to the destination state.json.
                     Parent directory must already exist.
        state:       PRReviewState instance to serialise.

    Raises:
        OSError: if the write or rename fails.
    """
    target_dir = os.path.dirname(target_path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="handoff-import-", suffix=".tmp.json", dir=target_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(state), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, target_path)
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
    """Scan research/ for relevant handoffs and write to state.bundle.research_handoffs.

    Reads state.json (written by Step 3 intake), discovers handoff.json
    files under <target>/research/*/handoff.json, filters by relevance to
    state.ticket_text and PR title, and REPLACES state.bundle["research_handoffs"]
    with the filtered set (capped at _MAX_HANDOFFS, most-recent-first).

    Other keys in state.bundle (from bundle-context) are preserved.

    Args:
        target:       Path to the reviewer's local repo root.
        pr_number:    PR number (positive int). Used to locate state.json.
        devforge_dir: Name of the devforge directory under target.

    Returns:
        dict with keys:
            status               — "ok"
            state_path           — absolute path of the (updated) state.json
            pr_number            — int
            handoffs_found       — int (total discovered)
            handoffs_matched     — int (after filter + cap)
            filter_applied       — bool (False when no filter criteria)

    Raises:
        ValueError: if state.json is missing or cannot be parsed.
        OSError:    if the atomic write fails.
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
            "cannot read state: {exc}".format(exc=exc)
        ) from exc

    try:
        state = PRReviewState(**state_dict)
    except TypeError as exc:
        raise ValueError(
            "state schema error: {exc}".format(exc=exc)
        ) from exc

    # Scan for handoff.json files.
    handoff_paths = _scan_research_dir(abs_target)

    # Parse each handoff; fail-soft on broken files.
    parsed = []
    for hf_path in handoff_paths:
        result = _parse_handoff(hf_path)
        if result is not None:
            parsed.append(result)

    handoffs_found = len(parsed)

    # Sort most-recent-first by date string (ISO dates sort lexicographically).
    parsed.sort(key=lambda h: h["date"], reverse=True)

    # Derive PR title for filter — use state.pr_body first line or empty.
    pr_title = ""
    if state.pr_body:
        pr_title = state.pr_body.strip().splitlines()[0].strip()

    # Filter by relevance.
    filtered = _filter_by_ticket_text(parsed, state.ticket_text, pr_title)
    filter_applied = bool(state.ticket_text.strip() or pr_title.strip())

    # Cap.
    capped = filtered[:_MAX_HANDOFFS]

    # Replace state.bundle["research_handoffs"]; preserve other bundle keys.
    bundle = dict(state.bundle)
    bundle["research_handoffs"] = capped
    state.bundle = bundle

    # Atomic write.
    _write_state(sp, state)

    return {
        "status": "ok",
        "state_path": sp,
        "pr_number": pr_number,
        "handoffs_found": handoffs_found,
        "handoffs_matched": len(capped),
        "filter_applied": filter_applied,
    }
