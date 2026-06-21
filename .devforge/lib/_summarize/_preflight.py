"""Pure preflight function for summarize_helper.

preflight_context — read and validate the 4-command setup chain artefacts,
                    check the target spec **Status**: Complete, and report
                    Source-Root / wrapper-mode from CLAUDE.md.

The function returns a plain dict; the CLI handler (cmd_preflight in _cli.py)
decides whether to stop on missing artefacts or a non-Complete spec (exit 2)
or pass.

Setup-chain artefacts checked (same as /audit's, /review's, and /verify's
preflight — all four helpers enforce the same gate on the same markers):
  1. constitution.md present
  2. CLAUDE.md present
  3. .devforge/project-config.json present  (/configure output)
  4. .devforge/index.json present           (/generate-docs output)

NOTE: this module intentionally OMITS the constitution-populated sentinel guard
(_UNPOPULATED_SENTINELS) that /verify and /review carry.  /summarize runs AFTER
/verify has already approved the feature — the spec **Status**: Complete gate is
a strictly stronger precondition than a populated constitution at this pipeline
stage.  The setup-chain EXISTENCE check still includes constitution.md (artefact
#1 above), ensuring the command was run.

NOTE: this module reads .devforge/memory.md — the live path per
src/CLAUDE.md References block ("Memory: .devforge/memory.md").
Do NOT change the memory path without verifying the current convention in
src/CLAUDE.md.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Setup-chain artefacts that must exist for /summarize to run.
# Parallel to /audit's, /review's, and /verify's preflight — same four-command
# chain.  Must stay in sync with those preflights.
_SETUP_CHAIN_ARTEFACTS = [
    # (relative_path, label) — label shown in missing_artefacts list
    ("constitution.md",                      "/constitute"),
    ("CLAUDE.md",                            "/init-forge"),
    (".devforge/project-config.json",        "/configure"),
    (".devforge/index.json",                 "/generate-docs"),
]

# The only valid status value that allows /summarize to proceed.
# Value from _specify/_schema.py SPEC_STATUS_ENUM: ("Draft", "Approved", "In Progress", "Complete")
_REQUIRED_SPEC_STATUS = "Complete"

# Regex to parse **Status**: <value> from spec.md.
# The spec renders this as a bare bold line, e.g.: **Status**: Draft
#
# IMPORTANT: uses [ \t]* (horizontal whitespace only), NOT \s*, and does NOT
# use re.DOTALL.  This is intentional — the status value MUST appear on the
# same line as the **Status**: marker.  Using \s* would allow the match to
# bleed across blank lines and capture a value from a subsequent line in a
# malformed spec (e.g. "**Status**:\n\nComplete\n" would wrongly pass the gate).
_STATUS_RE = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# preflight_context
# ---------------------------------------------------------------------------

def preflight_context(workspace_root, spec_path=None):
    # type: (str, Optional[str]) -> Dict
    """Check setup-chain artefacts, spec Complete gate, and CLAUDE.md context.

    Never raises on a missing file — returns sane defaults.

    Parameters
    ----------
    workspace_root : str
        The directory to scan for setup-chain artefacts and CLAUDE.md.
        In wrapper mode this is the wrapper root, not the project sub-directory.
    spec_path : str or None
        Explicit path to a spec.md to check.  When None, the spec gate
        is skipped (spec_status will be "" and spec_complete will be False).

    Returns a dict with keys always present:

      setup_chain_ok            bool  — all 4 artefacts present
      missing_artefacts         list  — labels of missing artefacts (empty = ok)
      spec_path                 str   — the resolved spec path (or "" if not given)
      spec_status               str   — the parsed **Status**: value (or "")
      spec_complete             bool  — True when spec_status == "Complete"
      source_root               str   — value from CLAUDE.md Project Root / Source Root
      wrapper_mode              bool  — True when CLAUDE.md contains a wrapper-mode marker
      project_type              str   — value of **Type**: line in CLAUDE.md
      framework                 str   — value of **Frameworks**: line in CLAUDE.md
      language                  str   — value of **Languages**: line in CLAUDE.md
      claude_md_present         bool  — CLAUDE.md exists
      memory_present            bool  — .devforge/memory.md exists
      memory_excerpt            str   — first 40 lines of memory.md (empty if absent)
    """
    result = {
        "setup_chain_ok": False,
        "missing_artefacts": [],
        "spec_path": spec_path or "",
        "spec_status": "",
        "spec_complete": False,
        "source_root": ".",
        "wrapper_mode": False,
        "project_type": "",
        "framework": "",
        "language": "",
        "claude_md_present": False,
        "memory_present": False,
        "memory_excerpt": "",
    }  # type: Dict

    # --- Check all setup-chain artefacts ---
    missing = []  # type: List[str]
    for rel_path, label in _SETUP_CHAIN_ARTEFACTS:
        full = os.path.join(workspace_root, rel_path)
        if not os.path.isfile(full):
            missing.append(label)
    result["missing_artefacts"] = missing
    result["setup_chain_ok"] = len(missing) == 0

    # --- Spec **Status**: Complete gate ---
    if spec_path:
        try:
            with open(spec_path, "r", encoding="utf-8") as fh:
                spec_text = fh.read()
            m = _STATUS_RE.search(spec_text)
            if m:
                status_value = m.group(1).strip()
                result["spec_status"] = status_value
                result["spec_complete"] = (status_value == _REQUIRED_SPEC_STATUS)
        except OSError:
            pass

    # --- CLAUDE.md ---
    claude_path = os.path.join(workspace_root, "CLAUDE.md")
    try:
        with open(claude_path, "r", encoding="utf-8") as fh:
            claude_lines = fh.readlines()
        result["claude_md_present"] = True
        for line in claude_lines:
            stripped = line.strip()
            lower = stripped.lower()

            # Wrapper-mode detection: look for the WRAPPER_MODE_SECTION marker
            # or a "Source Root:" / "Wrapper root:" line.  The /init-forge wizard
            # writes a {{WRAPPER_MODE_SECTION}} block that expands to contain
            # the phrase "wrapper mode" when wrapper mode is active.
            if "wrapper mode" in lower or "wrapper root" in lower:
                result["wrapper_mode"] = True

            # Source Root / Project Root extraction.
            # Mirrors _verify/_preflight.py's logic exactly.
            # Known limitation (shared with _audit/_preflight and
            # _review/_preflight): a path value containing a colon — e.g. a
            # Windows drive letter like C:\Users\me — is truncated to the part
            # after the last colon (\Users\me). Forge installs on Windows are
            # uncommon; accepted.
            if result["source_root"] == "." and (
                "source root" in lower or "project root" in lower
            ):
                if ":" in stripped:
                    val = stripped.rsplit(":", 1)[-1].strip()
                    val = val.strip("*`")
                    if val:
                        result["source_root"] = val

            # Bold-key extraction (anchored to "**Key**:" lines).
            if "**" in stripped and "type" in lower and ":" in stripped:
                if not result["project_type"]:
                    val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                    if val:
                        result["project_type"] = val

            if "**" in stripped and "framework" in lower and ":" in stripped:
                if not result["framework"]:
                    val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                    if val:
                        result["framework"] = val

            if "**" in stripped and "language" in lower and ":" in stripped:
                if not result["language"]:
                    val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                    if val:
                        result["language"] = val
    except OSError:
        pass

    # --- .devforge/memory.md ---
    # Reads .devforge/memory.md — the live path per src/CLAUDE.md
    # References block ("Memory: .devforge/memory.md").
    memory_path = os.path.join(workspace_root, ".devforge", "memory.md")
    try:
        with open(memory_path, "r", encoding="utf-8") as fh:
            mem_lines = fh.readlines()
        result["memory_present"] = True
        result["memory_excerpt"] = "".join(mem_lines[:40])
    except OSError:
        pass

    return result
