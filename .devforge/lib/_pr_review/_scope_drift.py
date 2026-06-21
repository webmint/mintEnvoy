r"""Ticket-bullet extractor + drift-matrix scaffold for pr_review_helper (PR-REVIEW Step 7).

`run(target, pr_number, devforge_dir)` is the Phase 5 entry point.

It reads state.json (written by Step 3 intake), extracts requirement bullets
from state.ticket_text (primary) and state.pr_body (secondary) using five
deterministic regex-based strategies, and writes a drift scaffold to state.drift.

## Drift schema (helper-owns; LLM fills coverage fields at Step 8)

state.drift after Step 7:
    {
        "bullets": [
            {
                "id":            "B1",
                "text":          "...",
                "source":        "ticket_text|pr_body|ticket_text_sentence",
                "extracted_via": "markdown_bullet|numbered_list|ac_marker|gwt|sentence_fallback"
            },
            ...
        ],
        "coverage_matrix": [],     # LLM fills at Step 8 (dispatch-review)
        "scope_creep_files": [],   # LLM fills at Step 8
        "filled": False            # LLM flips True when populated at Step 8
    }

coverage_matrix entry shape (LLM-filled at Step 8, documented here for consumers):
    {
        "bullet_id":  "B1",
        "status":     "satisfied|partial|missing|unknown",
        "evidence":   "<file:line or summary>",
        "confidence": 0.0-1.0
    }

## Extraction strategies (applied in order)

1. markdown_bullet  — `^\s*[-*+]\s+(.+?)$`
2. numbered_list    — `^\s*\d+[.)]\s+(.+?)$`
3. ac_marker        — `^\s*AC[-_]?\d+[:.]?\s*(.+?)$` (case-insensitive)
4. gwt              — `^\s*(?:GIVEN|WHEN|THEN|AND)\s+(.+?)$` (case-insensitive)
5. sentence_fallback — splits on sentence boundaries; 20-300 chars; ONLY when
                       strategies 1-4 yield 0 bullets for the current text.

Bullets from ticket_text are interleaved before bullets from pr_body.
Dedup is by normalised (lowercased, stripped) text; first occurrence wins.
Total bullets are capped at _MAX_BULLETS = 50.

## Re-invocation semantics (idempotency)

Running check-scope-drift REPLACES state.drift entirely (not append).
Re-running with the same state produces the same deterministic output.

## LLM constraint

This module does NOT call LLM / MCP tools.  Bullet extraction is fully
deterministic regex + string splitting.  LLM fills coverage_matrix and
scope_creep_files at Step 8 (dispatch-review).

Stdlib only.  Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import tempfile
from typing import Dict, List, Tuple

from ._state import PRReviewState, state_path


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

_MAX_BULLETS = 50
_MIN_SENTENCE_CHARS = 20
_MAX_SENTENCE_CHARS = 300

# ---------------------------------------------------------------------------
# Regex constants per extraction strategy.
# ---------------------------------------------------------------------------

_RE_MARKDOWN_BULLET = re.compile(r"^\s*[-*+]\s+(.+?)$", re.MULTILINE)
_RE_NUMBERED_LIST = re.compile(r"^\s*\d+[.)]\s+(.+?)$", re.MULTILINE)
_RE_AC_MARKER = re.compile(r"^\s*AC[-_]?\d+[:.]?\s*(.+?)$", re.MULTILINE | re.IGNORECASE)
_RE_GWT = re.compile(
    r"^\s*(?:GIVEN|WHEN|THEN|AND)\s+(.+?)$", re.MULTILINE | re.IGNORECASE
)
_RE_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Individual extractor helpers.
# ---------------------------------------------------------------------------


def _extract_via_markdown_bullets(text: str) -> List[Tuple[str, str]]:
    """Return (matched_text, "markdown_bullet") tuples from text.

    Matches lines that begin with an optional indent followed by -, *, or +
    and a space.  Captures the rest of the line.

    Args:
        text: Raw ticket or PR body text (may be empty).

    Returns:
        List of (bullet_text, "markdown_bullet") tuples, preserving
        appearance order.
    """
    results = []
    for m in _RE_MARKDOWN_BULLET.finditer(text):
        stripped = m.group(1).strip()
        if stripped:
            results.append((stripped, "markdown_bullet"))
    return results


def _extract_via_numbered_list(text: str) -> List[Tuple[str, str]]:
    """Return (matched_text, "numbered_list") tuples from text.

    Matches lines like "1. foo", "2) bar", "10. baz".

    Args:
        text: Raw ticket or PR body text (may be empty).

    Returns:
        List of (bullet_text, "numbered_list") tuples.
    """
    results = []
    for m in _RE_NUMBERED_LIST.finditer(text):
        stripped = m.group(1).strip()
        if stripped:
            results.append((stripped, "numbered_list"))
    return results


def _extract_via_ac_marker(text: str) -> List[Tuple[str, str]]:
    """Return (matched_text, "ac_marker") tuples from text.

    Matches lines like "AC-1: foo", "AC1 bar", "ac_2: baz" (case-insensitive).
    The captured group is the text AFTER the AC identifier.

    Args:
        text: Raw ticket or PR body text (may be empty).

    Returns:
        List of (bullet_text, "ac_marker") tuples.
    """
    results = []
    for m in _RE_AC_MARKER.finditer(text):
        stripped = m.group(1).strip()
        if stripped:
            results.append((stripped, "ac_marker"))
    return results


def _extract_via_gwt(text: str) -> List[Tuple[str, str]]:
    """Return (matched_text, "gwt") tuples from text.

    Matches lines beginning with GIVEN, WHEN, THEN, or AND (case-insensitive).

    Args:
        text: Raw ticket or PR body text (may be empty).

    Returns:
        List of (bullet_text, "gwt") tuples.
    """
    results = []
    for m in _RE_GWT.finditer(text):
        stripped = m.group(1).strip()
        if stripped:
            results.append((stripped, "gwt"))
    return results


def _extract_via_sentence_fallback(text: str) -> List[Tuple[str, str]]:
    """Return (sentence, "sentence_fallback") tuples from text.

    Splits text on sentence boundaries (after . ! ?) and keeps sentences
    whose stripped length is between _MIN_SENTENCE_CHARS and
    _MAX_SENTENCE_CHARS (inclusive).

    This strategy is ONLY called when all four structured strategies
    (markdown_bullet, numbered_list, ac_marker, gwt) returned 0 results
    for the same text.  Callers are responsible for enforcing this guard.

    Args:
        text: Raw ticket text (may be empty).

    Returns:
        List of (sentence_text, "sentence_fallback") tuples.
    """
    if not text:
        return []
    sentences = _RE_SENTENCE_SPLIT.split(text)
    results = []
    for sentence in sentences:
        stripped = sentence.strip()
        if _MIN_SENTENCE_CHARS <= len(stripped) <= _MAX_SENTENCE_CHARS:
            results.append((stripped, "sentence_fallback"))
    return results


# ---------------------------------------------------------------------------
# Multi-strategy extractor.
# ---------------------------------------------------------------------------


def _extract_bullets(text: str, source: str) -> List[Dict]:
    """Apply all five extraction strategies to text and return bullet dicts.

    Strategies are applied in order: markdown_bullet, numbered_list,
    ac_marker, gwt.  If ALL four structured strategies return 0 results,
    sentence_fallback is applied as a last resort.

    IDs are NOT assigned here — the caller assigns them via
    _dedupe_and_assign_ids after merging bullets from multiple sources.

    Args:
        text:   Raw text to extract from (may be empty).
        source: Source label — one of "ticket_text", "pr_body",
                "ticket_text_sentence".  Used as the `source` field in
                returned dicts.  Pass "ticket_text" for primary; this
                function detects whether the fallback was used and
                adjusts source to "ticket_text_sentence" automatically
                when source == "ticket_text".

    Returns:
        List of dicts with keys: text, source, extracted_via.
        (No `id` key — assigned by _dedupe_and_assign_ids.)
    """
    if not text:
        return []

    # Apply four structured strategies.
    structured: List[Tuple[str, str]] = []
    structured.extend(_extract_via_markdown_bullets(text))
    structured.extend(_extract_via_numbered_list(text))
    structured.extend(_extract_via_ac_marker(text))
    structured.extend(_extract_via_gwt(text))

    if structured:
        return [
            {"text": t, "source": source, "extracted_via": via}
            for t, via in structured
        ]

    # Fallback: sentence splitting.  Only reachable when all four above = 0.
    # Adjust source label to distinguish fallback bullets from structured ones.
    fallback_source = "ticket_text_sentence" if source == "ticket_text" else source
    fallback = _extract_via_sentence_fallback(text)
    return [
        {"text": t, "source": fallback_source, "extracted_via": "sentence_fallback"}
        for t, _ in fallback
    ]


# ---------------------------------------------------------------------------
# Dedup + ID assignment.
# ---------------------------------------------------------------------------


def _dedupe_and_assign_ids(bullets: List[Dict]) -> List[Dict]:
    """Deduplicate bullets by normalised text and assign B1/B2/... IDs.

    Normalisation: lowercase + strip.  First occurrence wins on duplicate.
    Input order is preserved (ticket_text bullets before pr_body bullets).

    Args:
        bullets: List of bullet dicts from _extract_bullets (no `id` key).

    Returns:
        List of bullet dicts with `id` added; duplicates removed.
    """
    seen: set = set()
    unique: List[Dict] = []
    for bullet in bullets:
        key = bullet["text"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(bullet)

    # Assign 1-indexed IDs.
    result = []
    for idx, bullet in enumerate(unique, start=1):
        entry = {"id": "B{0}".format(idx)}
        entry.update(bullet)
        result.append(entry)

    return result


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
        prefix="drift-", suffix=".tmp.json", dir=target_dir
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
    """Extract ticket bullets from state and write drift scaffold to state.drift.

    Reads state.json (written by Step 3 intake), applies all extraction
    strategies to state.ticket_text (primary) and state.pr_body (secondary),
    deduplicates, assigns IDs, and REPLACES state.drift with the scaffold.

    The coverage_matrix, scope_creep_files, and filled fields in state.drift
    are set to their empty defaults — LLM fills them at Step 8 (dispatch-review).

    Re-running check-scope-drift is idempotent: state.drift is overwritten
    each time from the current state.ticket_text and state.pr_body.

    LLM / MCP tools are NOT called here.  This module is deterministic.

    Args:
        target:       Path to the reviewer's local repo root.
        pr_number:    PR number (positive int). Used to locate state.json.
        devforge_dir: Name of the devforge directory under target.

    Returns:
        dict with keys:
            status           — "ok"
            state_path       — absolute path of the (updated) state.json
            pr_number        — int
            bullets_extracted — int
            by_source        — dict mapping source label -> count
            by_extracted_via — dict mapping strategy label -> count
            capped           — bool (True if _MAX_BULLETS was reached)
            next_action      — reminder string for the LLM

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

    # Extract bullets from primary (ticket_text) then secondary (pr_body).
    raw_bullets: List[Dict] = []
    raw_bullets.extend(_extract_bullets(state.ticket_text, source="ticket_text"))
    raw_bullets.extend(_extract_bullets(state.pr_body, source="pr_body"))

    # Deduplicate and assign IDs (preserves ticket_text-first order).
    all_bullets = _dedupe_and_assign_ids(raw_bullets)

    # Cap at _MAX_BULLETS.
    capped = len(all_bullets) > _MAX_BULLETS
    if capped:
        all_bullets = all_bullets[:_MAX_BULLETS]

    # Build the drift scaffold.
    drift = {
        "bullets": all_bullets,
        "coverage_matrix": [],
        "scope_creep_files": [],
        "filled": False,
    }

    # Replace state.drift entirely.
    state.drift = drift

    # Atomic write.
    _write_state(sp, state)

    # Build summary counts.
    by_source: Dict[str, int] = {
        "ticket_text": 0,
        "pr_body": 0,
        "ticket_text_sentence": 0,
    }
    by_extracted_via: Dict[str, int] = {
        "markdown_bullet": 0,
        "numbered_list": 0,
        "ac_marker": 0,
        "gwt": 0,
        "sentence_fallback": 0,
    }
    for bullet in all_bullets:
        src = bullet.get("source", "")
        via = bullet.get("extracted_via", "")
        by_source[src] = by_source.get(src, 0) + 1
        by_extracted_via[via] = by_extracted_via.get(via, 0) + 1

    return {
        "status": "ok",
        "state_path": sp,
        "pr_number": pr_number,
        "bullets_extracted": len(all_bullets),
        "by_source": by_source,
        "by_extracted_via": by_extracted_via,
        "capped": capped,
        "next_action": (
            "dispatch-review (Step 8) populates coverage_matrix + scope_creep_files via LLM"
        ),
    }
