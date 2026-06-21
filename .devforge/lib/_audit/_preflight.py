"""Pure preflight functions for audit_helper.

Three pure functions that return plain dicts for the CLI to JSON-encode.
No filesystem writes; no subprocess calls.

resolve_mode  — parse raw $ARGUMENTS string into mode + knobs
check_agents  — check which audit-capable agent .md files are present
preflight_context — best-effort read of constitution.md, CLAUDE.md, MEMORY.md
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUDIT_AGENTS: List[str] = [
    "architect",
    "code-reviewer",
    "qa-reviewer",
    "security-reviewer",
]

# Sentinels that indicate constitution.md has NOT been populated by /constitute.
_UNPOPULATED_SENTINELS = (
    "{{CONSTITUTION_BODY}}",
    "Run `/constitute`",
    "Run /constitute to populate",
)

# Default passes by mode when --passes is not explicitly given.
_MODE_DEFAULT_PASSES = {"broad": 2, "hotspot": 2, "narrow": 1}


# ---------------------------------------------------------------------------
# resolve_mode
# ---------------------------------------------------------------------------

def _empty_result() -> Dict:
    """Return the canonical empty result dict for resolve_mode."""
    return {
        "mode": None,
        "scope_arg": None,
        "uncommitted": False,
        "top_n": None,
        "weights": None,
        "scope_limit": 200,
        "line_range": None,
        "passes": 1,
        "passes_clamp_note": "",
        "error": None,
    }


def resolve_mode(arguments: str) -> Dict:
    """Parse the raw $ARGUMENTS string into mode + knobs.

    Argument grammar:
      empty / whitespace-only, OR --full  → mode="broad"
      --uncommitted                        → mode="narrow", uncommitted=True
      --top N                              → mode="hotspot", top_n=N
      --top N --weights c=0.5,k=0.4,s=0.1 → top_n + weights dict
      single positional path               → mode="narrow", scope_arg=<path>
        optional :start-end suffix         → stripped into line_range
      --scope-limit N (any mode)           → scope_limit=N
      --passes N (any mode)                → passes=clamp(N,1,3); non-int → error
      two+ positional paths                → error
      unknown flag                         → error

    Returns a dict with keys always present:
      mode, scope_arg, uncommitted, top_n, weights, scope_limit, line_range,
      passes, passes_clamp_note, error

    When --passes is NOT given, passes defaults by mode:
      broad   → 2
      hotspot → 2
      narrow  → 1
      (any other/None mode → 1 as a defensive fallback)

    When --passes N IS given explicitly: N is clamped into [1,3]; a non-empty
    passes_clamp_note is set when the value was clamped. The mode-conditional
    default does NOT apply when --passes is explicit.
    """
    result = _empty_result()
    passes_explicit = False  # tracks whether --passes was given on the command line

    tokens = arguments.split() if arguments else []

    # Walk tokens manually to handle positional vs flag arguments.
    positionals: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok == "--full":
            if result["mode"] is not None:
                result["error"] = "Conflicting mode flags: --full may not be combined with other mode flags."
                result["mode"] = None
                return result
            result["mode"] = "broad"
            i += 1

        elif tok == "--uncommitted":
            if result["mode"] is not None:
                result["error"] = "Conflicting mode flags: --uncommitted may not be combined with other mode flags."
                result["mode"] = None
                return result
            result["mode"] = "narrow"
            result["uncommitted"] = True
            i += 1

        elif tok == "--top":
            if result["mode"] is not None:
                result["error"] = "Conflicting mode flags: --top may not be combined with other mode flags."
                result["mode"] = None
                return result
            i += 1
            if i >= len(tokens):
                result["error"] = "Usage: --top N (positive integer required after --top)."
                result["mode"] = None
                return result
            try:
                n = int(tokens[i])
                if n <= 0:
                    raise ValueError("must be positive")
            except ValueError:
                result["error"] = (
                    "Usage: --top N (N must be a positive integer, got {!r}).".format(tokens[i])
                )
                result["mode"] = None
                return result
            result["mode"] = "hotspot"
            result["top_n"] = n
            i += 1

        elif tok == "--weights":
            i += 1
            if i >= len(tokens):
                result["error"] = "Usage: --weights c=0.5,k=0.4,s=0.1 (value required after --weights)."
                result["mode"] = None
                return result
            weights_str = tokens[i]
            parsed_weights: Dict[str, float] = {}
            try:
                for part in weights_str.split(","):
                    k, v = part.split("=", 1)
                    fv = float(v)
                    if not (0.0 <= fv <= 1.0):
                        raise ValueError("weight {!r} out of range [0,1]".format(fv))
                    parsed_weights[k.strip()] = fv
            except ValueError as exc:
                result["error"] = (
                    "Usage: --weights c=0.5,k=0.4,s=0.1 — parse error: {}.".format(exc)
                )
                result["mode"] = None
                return result
            result["weights"] = parsed_weights
            i += 1

        elif tok == "--scope-limit":
            i += 1
            if i >= len(tokens):
                result["error"] = "Usage: --scope-limit N (positive integer required)."
                result["mode"] = None
                return result
            try:
                sl = int(tokens[i])
                if sl <= 0:
                    raise ValueError("must be positive")
            except ValueError:
                result["error"] = (
                    "Usage: --scope-limit N (N must be a positive integer, got {!r}).".format(tokens[i])
                )
                result["mode"] = None
                return result
            result["scope_limit"] = sl
            i += 1

        elif tok == "--passes":
            i += 1
            if i >= len(tokens):
                result["error"] = "Usage: --passes N (integer in [1,3] required after --passes)."
                result["mode"] = None
                return result
            try:
                p = int(tokens[i])
            except (ValueError, TypeError):
                result["error"] = (
                    "Usage: --passes N (N must be an integer, got {!r}).".format(tokens[i])
                )
                result["mode"] = None
                return result
            # Clamp into [1, 3]; record note so caller can emit a stderr note.
            clamped = max(1, min(3, p))
            if clamped != p:
                result["passes_clamp_note"] = (
                    "--passes {0} out of range [1,3]; clamped to {1}.".format(p, clamped)
                )
            result["passes"] = clamped
            passes_explicit = True
            i += 1

        elif tok.startswith("-"):
            result["error"] = "Unknown flag {!r}. Supported: --full, --uncommitted, --top N, --weights ..., --scope-limit N, or a single path.".format(tok)
            result["mode"] = None
            return result

        else:
            # Positional argument (path or path:range).
            positionals.append(tok)
            i += 1

    # Validate positional count.
    if len(positionals) > 1:
        result["error"] = (
            "Provide at most one path argument; got {}: {}.".format(
                len(positionals), ", ".join(repr(p) for p in positionals)
            )
        )
        result["mode"] = None
        return result

    if positionals:
        if result["mode"] is not None:
            result["error"] = "Conflicting mode flags: a path argument may not be combined with --full, --uncommitted, or --top."
            result["mode"] = None
            return result
        raw_path = positionals[0]
        # Strip optional :start-end suffix.
        # Only strip the suffix when the last component looks like "digits-digits"
        # to avoid splitting paths that happen to contain a colon for other reasons.
        scope_arg = raw_path
        line_range: Optional[str] = None
        colon_pos = raw_path.rfind(":")
        if colon_pos > 0:
            suffix = raw_path[colon_pos + 1:]
            # Accept suffix matching digits-digits (e.g. 42-87).
            if re.fullmatch(r"\d+-\d+", suffix):
                scope_arg = raw_path[:colon_pos]
                line_range = suffix
        result["mode"] = "narrow"
        result["scope_arg"] = scope_arg
        result["line_range"] = line_range

    # --weights is only meaningful with --top (hotspot mode). Reject a
    # weights value that did not land on a hotspot result (e.g. --weights
    # passed without --top) rather than silently discarding user intent.
    if result["weights"] is not None and result["mode"] != "hotspot":
        result["error"] = "--weights requires --top N."
        result["mode"] = None
        return result

    # Default to broad when nothing specified.
    if result["mode"] is None and result["error"] is None:
        result["mode"] = "broad"

    # Apply mode-conditional default for passes when not explicitly given.
    if not passes_explicit:
        result["passes"] = _MODE_DEFAULT_PASSES.get(result["mode"], 1)  # type: ignore[arg-type]

    return result


# ---------------------------------------------------------------------------
# check_agents
# ---------------------------------------------------------------------------

def check_agents(agents_dir: str) -> Dict:
    """Check which audit-capable agent .md files exist in agents_dir.

    The four agents are: architect, code-reviewer, qa-reviewer, security-reviewer.
    Returns {"present": [...sorted...], "missing": [...sorted...], "all_missing": bool}.
    Pure filesystem check; if agents_dir doesn't exist, all four are missing.
    """
    present: List[str] = []
    missing: List[str] = []

    for agent in _AUDIT_AGENTS:
        candidate = os.path.join(agents_dir, agent + ".md")
        if os.path.isfile(candidate):
            present.append(agent)
        else:
            missing.append(agent)

    return {
        "present": sorted(present),
        "missing": sorted(missing),
        "all_missing": len(present) == 0,
    }


# ---------------------------------------------------------------------------
# preflight_context
# ---------------------------------------------------------------------------

def preflight_context(workspace_root: str) -> Dict:
    """Best-effort read of constitution.md, CLAUDE.md, and .claude/memory/MEMORY.md.

    Never raises on a missing file — returns sane defaults for absent files.
    Returns a dict with keys always present:
      constitution_present, constitution_populated, source_root, project_type,
      framework, language, claude_md_present, memory_present, memory_excerpt
    """
    result = {
        "constitution_present": False,
        "constitution_populated": False,
        "source_root": ".",
        "project_type": "",
        "framework": "",
        "language": "",
        "claude_md_present": False,
        "memory_present": False,
        "memory_excerpt": "",
    }

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
            # Source Root / Project Root line: "- **Project Root**: value"
            if result["source_root"] == "." and ("source root" in lower or "project root" in lower):
                # Extract value after the last ":" on the line.
                if ":" in stripped:
                    val = stripped.rsplit(":", 1)[-1].strip()
                    # Strip markdown bold markers and backticks.
                    val = val.strip("*`")
                    if val:
                        result["source_root"] = val
            # Anchor field extraction to bold markdown keys ("- **Type**: ...")
            # so prose lines that merely contain the word are not captured.
            if (not result["project_type"] and "**" in stripped
                    and "type" in lower and ":" in stripped):
                val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                if val:
                    result["project_type"] = val
            if (not result["framework"] and "**" in stripped
                    and "framework" in lower and ":" in stripped):
                val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                if val:
                    result["framework"] = val
            if (not result["language"] and "**" in stripped
                    and "language" in lower and ":" in stripped):
                val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                if val:
                    result["language"] = val
    except OSError:
        pass

    # --- .claude/memory/MEMORY.md ---
    memory_path = os.path.join(workspace_root, ".claude", "memory", "MEMORY.md")
    try:
        with open(memory_path, "r", encoding="utf-8") as fh:
            mem_lines = fh.readlines()
        result["memory_present"] = True
        excerpt_lines = mem_lines[:40]
        result["memory_excerpt"] = "".join(excerpt_lines)
    except OSError:
        pass

    return result
