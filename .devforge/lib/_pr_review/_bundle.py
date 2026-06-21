"""Bundle-context aggregator for pr_review_helper (PR-REVIEW Step 6).

`run(target, pr_number, devforge_dir)` is the Phase 4a entry point.

It reads state.json (written by Step 3 intake), assembles authoritative
project context from local filesystem sources, and REPLACES state.bundle
with the assembled dict.

## Bundle schema (helper-owns; LLM at Step 8 dispatch-review consumes it)

After bundle-context, state.bundle contains:

    {
        "constitution_md": "<absolute path>" | null,
        "constitution_md_content": "<file content>" | "",
        "constitute_json": {<parsed dict>} | null,
        "concern_docs": [
            {
                "concern": "<dir basename>",
                "overview_path": "<abs path>",
                "overview_content": "<file content>",
                "architecture_path": "<abs path>",
                "architecture_content": "<file content>"
            },
            ...
        ],
        "adrs": [
            {
                "path": "<absolute>",
                "filename": "<basename>",
                "content": "<file content>"
            },
            ...
        ],
        "plan_files": [
            {
                "path": "<absolute>",
                "name": "<basename>",
                "content": "<file content>"
            },
            ...
        ]
    }

research_handoffs is added separately by import-handoffs (Step 6b).

## Content caps

Per-file content is capped at _MAX_CONTENT_CHARS (50_000) characters.
Files that exceed the cap are truncated with "... [truncated]" appended.

File-read errors are handled with mixed semantics:
- If the file disappeared between listdir and read (OSError + file no longer
  exists), the entry is excluded from the output entirely (applies to ADR
  scanner only, which has an explicit race-detection guard).
- If the file exists but cannot be opened (permission error, encoding error,
  etc.), the entry is included with empty `content`. The LLM consuming the
  bundle will see the path but no content; downstream consumers should treat
  empty content as "unreadable rather than absent."

## Bounds

- concern_docs: capped at _MAX_CONCERN_DOCS = 30 (alphabetical by concern name)
- adrs:         capped at _MAX_ADRS = 100 (alphabetical by filename)
- plan_files:   capped at _MAX_PLANS = 50 (alphabetical by name)

## Re-invocation semantics (idempotency)

Running bundle-context REPLACES state.bundle (except the research_handoffs
key, which is written by import-handoffs and is preserved when present).
Re-running produces a clean bundle from current filesystem state.

## CBM constraint

This module does NOT call CBM / MCP tools. All data comes from the
local filesystem. CBM is invoked by the LLM orchestrator at Step 8.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import glob
import json
import os
import tempfile
from typing import Dict, List, Optional

from ._state import PRReviewState, state_path
from ._detect_tier import (
    _ADR_CANDIDATES,
    _DEVFORGE_INFRA_SUBDIRS,
    _find_constitution,
)


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

_MAX_CONCERN_DOCS = 30
_MAX_ADRS = 100
_MAX_PLANS = 50
_MAX_CONTENT_CHARS = 50_000
_TRUNCATION_MARKER = "... [truncated]"


# ---------------------------------------------------------------------------
# File read utility.
# ---------------------------------------------------------------------------


def _read_file_truncated(path: str, max_chars: int = _MAX_CONTENT_CHARS) -> str:
    """Read a file and return its content, truncated to max_chars if necessary.

    Appends _TRUNCATION_MARKER when the raw content exceeds max_chars.
    Returns empty string on any read error (fail-soft).

    Args:
        path:      Absolute path to the file to read.
        max_chars: Maximum number of characters to return (default: 50_000).

    Returns:
        File contents (possibly truncated), or "" on read failure.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(max_chars + 1)
    except OSError:
        return ""
    if len(content) > max_chars:
        return content[:max_chars] + _TRUNCATION_MARKER
    return content


# ---------------------------------------------------------------------------
# Constitution loader.
# ---------------------------------------------------------------------------


def _load_constitution(target: str) -> Dict:
    """Return constitution path and content dict.

    Checks src/constitution.md first, then constitution.md at root
    (mirrors _detect_tier._find_constitution).

    Returns:
        dict with keys "constitution_md" (str|None) and
        "constitution_md_content" (str).
    """
    path = _find_constitution(target)
    if path is None:
        return {"constitution_md": None, "constitution_md_content": ""}
    content = _read_file_truncated(path)
    return {"constitution_md": path, "constitution_md_content": content}


# ---------------------------------------------------------------------------
# constitute.json loader.
# ---------------------------------------------------------------------------


def _load_constitute_json(devforge_path: str) -> Optional[Dict]:
    """Parse .devforge/constitute.json and return the dict, or None.

    Returns None when the file is absent, unreadable, or not valid JSON.
    Failure is silent (fail-soft) — a missing/broken constitute.json does
    not abort bundle assembly.

    Args:
        devforge_path: Absolute path to the .devforge directory.

    Returns:
        Parsed dict, or None.
    """
    path = os.path.join(devforge_path, "constitute.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Concern docs scanner.
# ---------------------------------------------------------------------------


def _scan_concern_docs(devforge_path: str) -> List[Dict]:
    """Scan .devforge/ for concern doc directories and collect overview+architecture.

    Only directories directly under devforge_path that are NOT in
    _DEVFORGE_INFRA_SUBDIRS are treated as concern dirs (same filter as
    _detect_tier._find_concern_dirs).

    For each concern dir, reads overview.md and architecture.md.
    Files that exist but cannot be read (permission error, encoding error, etc.)
    have their entry included with empty content (""). Missing files are
    omitted from the entry (their path and content fields are left as "").

    Results are sorted alphabetically by concern name and capped at
    _MAX_CONCERN_DOCS entries.

    Args:
        devforge_path: Absolute path to the .devforge directory.

    Returns:
        List of concern-doc dicts (may be empty).
    """
    if not os.path.isdir(devforge_path):
        return []

    try:
        entries = os.listdir(devforge_path)
    except OSError:
        return []

    concern_dirs = []
    for name in entries:
        if name in _DEVFORGE_INFRA_SUBDIRS:
            continue
        full = os.path.join(devforge_path, name)
        if os.path.isdir(full):
            concern_dirs.append((name, full))

    concern_dirs.sort(key=lambda t: t[0])

    results = []
    for concern_name, concern_dir in concern_dirs[:_MAX_CONCERN_DOCS]:
        overview_path = os.path.join(concern_dir, "overview.md")
        arch_path = os.path.join(concern_dir, "architecture.md")

        overview_content = ""
        overview_abs = ""
        if os.path.isfile(overview_path):
            overview_abs = overview_path
            overview_content = _read_file_truncated(overview_path)

        arch_content = ""
        arch_abs = ""
        if os.path.isfile(arch_path):
            arch_abs = arch_path
            arch_content = _read_file_truncated(arch_path)

        results.append({
            "concern": concern_name,
            "overview_path": overview_abs,
            "overview_content": overview_content,
            "architecture_path": arch_abs,
            "architecture_content": arch_content,
        })

    return results


# ---------------------------------------------------------------------------
# ADR scanner.
# ---------------------------------------------------------------------------


def _scan_adrs(target: str) -> List[Dict]:
    """Scan well-known ADR directories for *.md files.

    Checks _ADR_CANDIDATES in priority order; uses the first existing dir.
    Collects all *.md files in that directory (non-recursive), sorts by
    filename, caps at _MAX_ADRS.

    File-read errors are handled with mixed semantics:
    - If a file disappeared between listdir and read (OSError + file no longer
      exists), the entry is excluded from the output entirely.
    - If the file exists but cannot be opened (permission error, etc.), the
      entry is included with empty `content`.

    Args:
        target: Absolute path to the repository root.

    Returns:
        List of ADR dicts with keys: path, filename, content.
    """
    adr_dir = None
    for candidate in _ADR_CANDIDATES:
        full = os.path.join(target, candidate)
        if os.path.isdir(full):
            adr_dir = full
            break

    if adr_dir is None:
        return []

    try:
        entries = os.listdir(adr_dir)
    except OSError:
        return []

    md_files = sorted(
        e for e in entries
        if e.lower().endswith(".md") and os.path.isfile(os.path.join(adr_dir, e))
    )

    results = []
    for filename in md_files[:_MAX_ADRS]:
        abs_path = os.path.join(adr_dir, filename)
        content = _read_file_truncated(abs_path)
        if content == "" and not os.path.isfile(abs_path):
            # File disappeared between listdir and read; skip.
            continue
        results.append({
            "path": abs_path,
            "filename": filename,
            "content": content,
        })

    return results


# ---------------------------------------------------------------------------
# Plan files scanner.
# ---------------------------------------------------------------------------


def _scan_plan_files(target: str) -> List[Dict]:
    """Scan repo root for *-PLAN.md files.

    Uses glob to find all *-PLAN.md at the top level of target.
    Sorts alphabetically by basename, caps at _MAX_PLANS.

    File-read errors: if a file exists but cannot be opened (permission error,
    etc.), the entry is included with empty `content`. Glob-returned paths that
    no longer exist (race) are skipped entirely.

    Args:
        target: Absolute path to the repository root.

    Returns:
        List of plan-file dicts with keys: path, name, content.
    """
    pattern = os.path.join(target, "*-PLAN.md")
    matches = glob.glob(pattern)

    # Sort by basename for determinism.
    matches.sort(key=os.path.basename)

    results = []
    for abs_path in matches[:_MAX_PLANS]:
        if not os.path.isfile(abs_path):
            continue
        content = _read_file_truncated(abs_path)
        results.append({
            "path": abs_path,
            "name": os.path.basename(abs_path),
            "content": content,
        })

    return results


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
        prefix="bundle-", suffix=".tmp.json", dir=target_dir
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
    """Aggregate filesystem context sources into state.bundle.

    Reads state.json (written by Step 3 intake), assembles:
      - constitution_md + constitution_md_content
      - constitute_json (parsed .devforge/constitute.json)
      - concern_docs (from .devforge/ subdirs, tier=full|partial)
      - adrs (from first existing well-known ADR dir)
      - plan_files (from *-PLAN.md at repo root)

    REPLACES state.bundle with the assembled dict. The research_handoffs
    key (written by import-handoffs) is preserved when already present.

    Re-running is idempotent: state.bundle is overwritten with current
    filesystem state each invocation.

    Args:
        target:       Path to the reviewer's local repo root.
        pr_number:    PR number (positive int). Used to locate state.json.
        devforge_dir: Name of the devforge directory under target.

    Returns:
        dict with keys:
            status           — "ok"
            state_path       — absolute path of the (updated) state.json
            pr_number        — int
            sources_gathered — summary dict of what was collected

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

    # Assemble bundle from filesystem sources.
    constitution_data = _load_constitution(abs_target)
    constitute_json = _load_constitute_json(abs_devforge)
    concern_docs = _scan_concern_docs(abs_devforge)
    adrs = _scan_adrs(abs_target)
    plan_files = _scan_plan_files(abs_target)

    # Preserve research_handoffs from any prior import-handoffs run.
    existing_research_handoffs = state.bundle.get("research_handoffs", None)

    new_bundle = {
        "constitution_md": constitution_data["constitution_md"],
        "constitution_md_content": constitution_data["constitution_md_content"],
        "constitute_json": constitute_json,
        "concern_docs": concern_docs,
        "adrs": adrs,
        "plan_files": plan_files,
    }

    if existing_research_handoffs is not None:
        new_bundle["research_handoffs"] = existing_research_handoffs

    state.bundle = new_bundle

    # Atomic write.
    _write_state(sp, state)

    sources_gathered = {
        "constitution_md": constitution_data["constitution_md"] is not None,
        "constitute_json": constitute_json is not None,
        "concern_docs_count": len(concern_docs),
        "adrs_count": len(adrs),
        "plan_files_count": len(plan_files),
    }

    return {
        "status": "ok",
        "state_path": sp,
        "pr_number": pr_number,
        "sources_gathered": sources_gathered,
    }
