"""Pure preflight function for grill_helper.

preflight_context — read and validate the 4-command setup chain artefacts,
                    report Source-Root / wrapper-mode from CLAUDE.md, and
                    check that the target feature has both a spec.md and an
                    approved plan.md (required preconditions for /grill, which
                    runs between /plan and /breakdown).

The function returns a plain dict; the CLI handler (cmd_preflight in _cli.py)
decides whether to stop on missing/unpopulated artefacts (exit 2) or pass.

Sentinel set is intentionally identical to _audit/_preflight.py and
_review/_preflight.py so all three helpers enforce the same gate on the same
markers.

Setup-chain artefacts checked (same as /audit and /review preflights):
  1. constitution.md present + populated (no unpopulated sentinels)
  2. CLAUDE.md present
  3. .devforge/project-config.json present  (/configure output)
  4. .devforge/index.json present           (/generate-docs output)

Feature-level artefacts checked (specific to /grill):
  5. <feature_dir>/spec.md present         (/specify output)
  6. <feature_dir>/plan.md present         (/plan output)
"""

import os
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants (identical to _audit/_preflight.py and _review/_preflight.py —
# must stay in sync with both)
# ---------------------------------------------------------------------------

# Sentinels that indicate constitution.md has NOT been populated by /constitute.
# These are the exact strings checked by _audit/_preflight.py and
# _review/_preflight.py; any change here must be reflected there (and vice
# versa) to keep parity.
_UNPOPULATED_SENTINELS = (
    "{{CONSTITUTION_BODY}}",
    "Run `/constitute`",
    "Run /constitute to populate",
)

# Setup-chain artefacts that must exist for /grill to run.
# Parallel to /audit and /review preflights — same four-command chain.
_SETUP_CHAIN_ARTEFACTS = [
    # (relative_path, label) — label shown in missing_artefacts list
    ("constitution.md",                      "/constitute"),
    ("CLAUDE.md",                            "/init-forge"),
    (".devforge/project-config.json",        "/configure"),
    (".devforge/index.json",                 "/generate-docs"),
]


# ---------------------------------------------------------------------------
# preflight_context
# ---------------------------------------------------------------------------

def preflight_context(
    workspace_root: str,
    feature_dir: Optional[str] = None,
) -> Dict:
    """Check setup-chain artefacts, constitution, memory, and feature plan.

    Never raises on a missing file — returns sane defaults.
    Returns a dict with keys always present:

      constitution_present      bool  — constitution.md exists
      constitution_populated    bool  — no unpopulated sentinel found
      setup_chain_ok            bool  — all 4 artefacts present
      missing_artefacts         list  — labels of missing artefacts (empty = ok)
      source_root               str   — value from CLAUDE.md Project Root / Source Root
      wrapper_mode              bool  — True when CLAUDE.md contains a wrapper-mode marker
      project_type              str   — value of **Type**: line in CLAUDE.md
      framework                 str   — value of **Frameworks**: line in CLAUDE.md
      language                  str   — value of **Languages**: line in CLAUDE.md
      claude_md_present         bool  — CLAUDE.md exists
      memory_present            bool  — .devforge/memory.md exists
      memory_excerpt            str   — first 40 lines of memory.md (empty if absent)
      spec_present              bool  — <feature_dir>/spec.md exists
      plan_present              bool  — <feature_dir>/plan.md exists
      feature_gate_ok           bool  — both spec.md and plan.md exist
      missing_feature_artefacts list  — labels of missing feature artefacts
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
        "spec_present": False,
        "plan_present": False,
        "feature_gate_ok": False,
        "missing_feature_artefacts": [],
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
            # Mirrors _audit/_preflight.py and _review/_preflight.py exactly.
            # Known limitation (shared with _audit and _review preflight): a
            # path value containing a colon — e.g. a Windows drive letter like
            # C:\Users\me — is truncated to the part after the last colon
            # (\Users\me). Forge installs on Windows are uncommon; accepted.
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
    # NOTE: the correct forge memory path is .devforge/memory.md.
    # _review/_preflight.py carries a bug where it checks .claude/memory/MEMORY.md
    # instead; this implementation uses the correct path.
    memory_path = os.path.join(workspace_root, ".devforge", "memory.md")
    try:
        with open(memory_path, "r", encoding="utf-8") as fh:
            mem_lines = fh.readlines()
        result["memory_present"] = True
        result["memory_excerpt"] = "".join(mem_lines[:40])
    except OSError:
        pass

    # --- Feature-level gate: spec.md + plan.md ---
    # /grill runs between /plan and /breakdown; both spec.md (/specify output)
    # and plan.md (/plan output) must exist in the feature directory.
    missing_feature = []  # type: List[str]
    if feature_dir is not None:
        spec_path = os.path.join(feature_dir, "spec.md")
        plan_path = os.path.join(feature_dir, "plan.md")
        if os.path.isfile(spec_path):
            result["spec_present"] = True
        else:
            missing_feature.append("spec.md")
        if os.path.isfile(plan_path):
            result["plan_present"] = True
        else:
            missing_feature.append("plan.md")
    # When feature_dir is None the feature gate is treated as not-applicable
    # (setup-chain-only mode); both artefacts remain False and the gate is
    # considered not satisfied.
    result["missing_feature_artefacts"] = missing_feature
    result["feature_gate_ok"] = (
        feature_dir is not None and len(missing_feature) == 0
    )

    return result
