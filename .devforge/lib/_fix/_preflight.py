"""Preflight gate for fix_helper.

preflight_context — read and validate the 4-command setup chain artefacts
                    and report source_root / wrapper_mode from CLAUDE.md.

Mirrors _verify/_preflight.py exactly in structure and setup-chain contract.
Reads .devforge/ paths ONLY — does NOT read .claude/memory/MEMORY.md (the
stale path that plan-22 "finding F" flagged as a bug in _review/_preflight.py;
that path is never reproduced here).

Setup-chain artefacts checked (same 4 as /verify's and /review's preflight):
  1. constitution.md present + populated (no unpopulated sentinels)
  2. CLAUDE.md present
  3. .devforge/project-config.json present  (/configure output)
  4. .devforge/index.json present           (/generate-docs output)

The result dict has the same keys as _verify._preflight.preflight_context
so callers of both helpers can use the same JSON consumer.

Stdlib only.  Python 3.8+.  No side effects except file reads.
"""

from __future__ import annotations

import os
from typing import Dict, List

# ---------------------------------------------------------------------------
# Constants — identical to _verify/_preflight.py (must stay in sync)
# ---------------------------------------------------------------------------

# Sentinels indicating constitution.md has NOT been populated by /constitute.
_UNPOPULATED_SENTINELS = (
    "{{CONSTITUTION_BODY}}",
    "Run `/constitute`",
    "Run /constitute to populate",
)

# Setup-chain artefacts that must exist for /fix to run.
_SETUP_CHAIN_ARTEFACTS = [
    # (relative_path, label) — label shown in missing_artefacts list
    ("constitution.md",               "/constitute"),
    ("CLAUDE.md",                     "/init-forge"),
    (".devforge/project-config.json", "/configure"),
    (".devforge/index.json",          "/generate-docs"),
]


# ---------------------------------------------------------------------------
# preflight_context
# ---------------------------------------------------------------------------


def preflight_context(workspace_root):
    # type: (str) -> Dict
    """Check setup-chain artefacts and read key context from workspace_root.

    Never raises on a missing file — returns sane defaults.
    Reads .devforge/ paths ONLY (NOT .claude/ — plan-22 finding F not copied).

    Returns a dict with keys always present:

      constitution_present      bool  — constitution.md exists
      constitution_populated    bool  — no unpopulated sentinel found
      setup_chain_ok            bool  — all 4 artefacts present
      missing_artefacts         list  — labels of missing artefacts (empty = ok)
      source_root               str   — value from CLAUDE.md Project Root / Source Root
      wrapper_mode              bool  — True when CLAUDE.md contains wrapper-mode marker
      project_type              str   — value of **Type**: line in CLAUDE.md
      framework                 str   — value of **Frameworks**: line in CLAUDE.md
      language                  str   — value of **Languages**: line in CLAUDE.md
      claude_md_present         bool  — CLAUDE.md exists
      memory_present            bool  — .devforge/memory.md exists
      memory_excerpt            str   — first 40 lines of .devforge/memory.md (empty if absent)
    """
    result = {
        "constitution_present": False,
        "constitution_populated": False,
        "setup_chain_ok": False,
        "missing_artefacts": [],
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

    # --- constitution.md ---
    const_path = os.path.join(workspace_root, "constitution.md")
    try:
        with open(const_path, "r", encoding="utf-8") as fh:
            const_text = fh.read()
        result["constitution_present"] = True
        populated = True
        for sentinel in _UNPOPULATED_SENTINELS:
            if sentinel in const_text:
                populated = False
                break
        result["constitution_populated"] = populated
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
            # or a "Source Root:" / "Wrapper root:" line. The /init-forge wizard
            # writes a {{WRAPPER_MODE_SECTION}} block that expands to contain
            # the phrase "wrapper mode" when wrapper mode is active.
            if "wrapper mode" in lower or "wrapper root" in lower:
                result["wrapper_mode"] = True

            # Source Root / Project Root extraction.
            # Mirrors _verify/_preflight.py's logic exactly.
            # Known limitation (shared with _audit/_preflight and
            # _verify/_preflight): a path value containing a colon (e.g.
            # Windows drive letter C:\Users\me) is truncated to the part after
            # the last colon. Forge installs on Windows are uncommon; accepted.
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
    # Reads .devforge/memory.md — the live path per src/CLAUDE.md References
    # block ("Memory: .devforge/memory.md").
    # DO NOT change to .claude/memory/MEMORY.md (plan-22 finding F).
    memory_path = os.path.join(workspace_root, ".devforge", "memory.md")
    try:
        with open(memory_path, "r", encoding="utf-8") as fh:
            mem_lines = fh.readlines()
        result["memory_present"] = True
        result["memory_excerpt"] = "".join(mem_lines[:40])
    except OSError:
        pass

    return result
