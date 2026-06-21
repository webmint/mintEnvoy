"""Blast-radius probe-spec generator for pr_review_helper (PR-REVIEW Step 5).

`run(target, pr_number, devforge_dir)` is the Phase 3 entry point.

It reads state.json (written by Step 3 intake), parses state.diff to identify
NEW or MODIFIED symbols (functions, classes, methods, components, exported
types), and writes one probe-spec entry per symbol into state.blast.

## Probe-spec schema (helper-owns; LLM fills caller/callee fields at Step 8)

Each entry in state.blast after Step 5:
    {
        "symbol":        "<extracted identifier>",
        "file":          "<path/to/file as it appears in the diff header>",
        "kind":          "component|function|class|method|export|interface|type|struct|enum|trait",
        "language":      "vue|python|typescript|javascript|go|java|ruby|rust",
        "diff_line_hint":"diff:line+<0-based-N>",   # 0-based index within added_lines
        "mcp_hints": {
            "trace_path_in":  "<symbol_name>",      # CBM trace_path direction=inbound
            "trace_path_out": "<symbol_name>",      # CBM trace_path direction=outbound
            "data_flow":      "<symbol_name>",      # CBM mode=data_flow
        },
        "callers":             [],   # LLM fills via CBM trace_path at Step 8
        "callees":             [],   # LLM fills via CBM trace_path at Step 8
        "data_flow_targets":   [],   # LLM fills via CBM mode=data_flow at Step 8
        "tests_referencing":   [],   # LLM fills via CBM search_graph or grep at Step 8
        "filled":              False # LLM sets True when populated at Step 8
    }

## Re-invocation semantics (idempotency)

Running compute-blast-radius REPLACES state.blast entirely (not append).
Re-running with a fresh diff or changed state produces a clean probe-spec list.
Downstream Step 8 always processes the current state.blast from scratch.

## CBM constraint

This module does NOT call CBM / MCP tools. Those are invoked by the LLM
orchestrator at Step 8 (dispatch-review). The mcp_hints field provides the
symbol name the LLM should pass to CBM trace_path; this helper only populates
the probe-spec shape.

## Language coverage

Python (.py), TypeScript (.ts/.tsx), JavaScript (.js/.jsx/.mjs),
Vue (.vue), Go (.go), Java (.java), Ruby (.rb), Rust (.rs).
Files with other/no extensions are skipped (no probe spec emitted).

## Symbol extraction bounds

- _MAX_SYMBOLS_PER_PR = 100: hard cap on total probe specs per invocation.
- Dedup by (symbol, file) tuple — same symbol at multiple locations in the
  same file emits only one entry.
- Final list sorted by (file, symbol) for deterministic output.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import tempfile
from typing import Dict, List, Optional, Tuple

from ._state import PRReviewState, state_path


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

_MAX_SYMBOLS_PER_PR = 100

# Mapping from file extension (without leading dot) to language string.
_EXT_LANGUAGE: Dict[str, str] = {
    "py": "python",
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "vue": "vue",
    "go": "go",
    "java": "java",
    "rb": "ruby",
    "rs": "rust",
}


# ---------------------------------------------------------------------------
# Per-language regex constants.
# Each tuple is (compiled_regex, kind_string).
# Regexes match against individual added lines (lines that start with '+').
# ---------------------------------------------------------------------------

_PY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^\+\s*def\s+([a-zA-Z_]\w*)\s*\("), "function"),
    (re.compile(r"^\+\s*async\s+def\s+([a-zA-Z_]\w*)\s*\("), "function"),
    (re.compile(r"^\+\s*class\s+([a-zA-Z_]\w*)\s*[(:)]"), "class"),
]

_TS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$]\w*)\s*\("
        ),
        "function",
    ),
    (
        re.compile(r"^\+\s*(?:export\s+)?class\s+([a-zA-Z_$]\w*)\s*[<{]"),
        "class",
    ),
    (
        re.compile(r"^\+\s*(?:export\s+)?interface\s+([a-zA-Z_$]\w*)\s*[<{]"),
        "interface",
    ),
    (
        re.compile(r"^\+\s*(?:export\s+)?type\s+([a-zA-Z_$]\w*)\s*="),
        "type",
    ),
    (
        re.compile(
            r"^\+\s*(?:export\s+)?const\s+([a-zA-Z_$]\w*)\s*[:=]"
        ),
        "export",
    ),
]

# Regex to detect if a const RHS looks like a function expression.
# Only emit an export probe spec if the line's RHS (after an optional type
# annotation between the name and =) starts with function / async / arrow-
# function indicators.
# Examples matched:
#   const foo = () => {                      (untyped arrow)
#   const handleClick: EventHandler = (e) => {  (typed arrow — React/TS handler idiom)
#   export const validate: Validator = (input) => {
#   const myFn = function() {}
#   const process = async (x) => {}
_TS_CONST_FUNCTION_RHS_RE = re.compile(
    r"^\+\s*(?:export\s+)?const\s+[a-zA-Z_$][\w$]*"
    r"(?:\s*:[^=]+)?"            # optional: SomeType annotation before =
    r"\s*=\s*"
    r"(?:function|async\s+function|async\s*\(|\()"
)

# JavaScript uses the same patterns as TypeScript.
_JS_PATTERNS = _TS_PATTERNS

_GO_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"^\+\s*func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)\s*\("),
        "function",
    ),
    (
        re.compile(r"^\+\s*type\s+([A-Za-z_]\w*)\s+(?:struct|interface)"),
        "type",
    ),
]

_JAVA_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"^\+\s*(?:public|protected|private|static|\s)+"
            r"(?:[\w<>\[\]]+\s+)+([a-zA-Z_]\w*)\s*\("
        ),
        "method",
    ),
    (
        re.compile(
            r"^\+\s*(?:public|protected|private|static)?\s*class\s+([A-Za-z_]\w*)"
        ),
        "class",
    ),
]

_RUBY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^\+\s*def\s+([a-zA-Z_]\w*[?!]?)"), "method"),
    (re.compile(r"^\+\s*class\s+([A-Z]\w*)"), "class"),
]

_RUST_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"^\+\s*(?:pub\s+)?fn\s+([a-zA-Z_]\w*)\s*[(<]"), "function"),
    (re.compile(r"^\+\s*(?:pub\s+)?struct\s+([A-Z]\w*)"), "struct"),
    (re.compile(r"^\+\s*(?:pub\s+)?enum\s+([A-Z]\w*)"), "enum"),
    (re.compile(r"^\+\s*(?:pub\s+)?trait\s+([A-Z]\w*)"), "trait"),
]

_LANGUAGE_PATTERNS: Dict[str, List[Tuple[re.Pattern, str]]] = {
    "python": _PY_PATTERNS,
    "typescript": _TS_PATTERNS,
    "javascript": _JS_PATTERNS,
    "vue": _TS_PATTERNS,  # Vue script blocks are TS/JS; applied to all + lines
    "go": _GO_PATTERNS,
    "java": _JAVA_PATTERNS,
    "ruby": _RUBY_PATTERNS,
    "rust": _RUST_PATTERNS,
}


# ---------------------------------------------------------------------------
# Language detection.
# ---------------------------------------------------------------------------


def _detect_language(file_path: str) -> Optional[str]:
    """Return the language string for a file path based on its extension.

    Returns None for files with unsupported or no extension.

    Args:
        file_path: Relative or absolute path to the file (as it appears in
                   the diff header, e.g. "apps/app/src/foo.vue").

    Returns:
        Language string ("python", "typescript", "javascript", "vue", "go",
        "java", "ruby", "rust") or None.
    """
    _, ext = os.path.splitext(file_path)
    if not ext:
        return None
    ext_lower = ext.lstrip(".").lower()
    return _EXT_LANGUAGE.get(ext_lower)


# ---------------------------------------------------------------------------
# Diff parser.
# ---------------------------------------------------------------------------


def _parse_diff(diff_text: str) -> List[Dict]:
    """Parse a unified diff into per-file records.

    Returns a list of dicts, one per changed file:
        {"file": "<path>", "added_lines": ["<raw diff line>", ...]}

    Only lines starting with "+" (but NOT "+++") are included in added_lines.
    The raw line (including the leading "+") is preserved so that per-language
    regexes can match against it directly.

    A "diff --git" or "--- a/" header starts a new file section.
    Lines inside hunk headers (@@ ... @@) are ignored.

    Args:
        diff_text: Raw unified diff string (may be empty).

    Returns:
        List of per-file dicts (may be empty).
    """
    if not diff_text:
        return []

    results: List[Dict] = []
    current_file: Optional[str] = None
    current_added: List[str] = []

    for line in diff_text.splitlines():
        # "diff --git a/<path> b/<path>" — start of a new file block.
        if line.startswith("diff --git "):
            if current_file is not None:
                results.append({"file": current_file, "added_lines": current_added})
            # Extract b/<path> from the header.
            parts = line.split(" b/", 1)
            current_file = parts[1] if len(parts) == 2 else None
            current_added = []
            continue

        # "+++ b/<path>" — alternative file header style; update current_file.
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        # Skip "---", "+++" lines (file headers) and "@@ ... @@" hunk headers.
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue

        # Collect added lines (but skip empty-add guard "+" alone).
        if line.startswith("+") and len(line) > 1:
            current_added.append(line)

    # Flush last file.
    if current_file is not None:
        results.append({"file": current_file, "added_lines": current_added})

    return results


# ---------------------------------------------------------------------------
# Probe spec builder.
# ---------------------------------------------------------------------------


def _build_probe_spec(
    symbol: str,
    file: str,
    kind: str,
    language: str,
    diff_line_hint: str,
) -> Dict:
    """Construct and return a canonical probe-spec dict.

    callers, callees, data_flow_targets, tests_referencing are all empty lists
    and filled=False. The LLM fills these fields at Step 8 via CBM trace_path.

    Args:
        symbol:         Extracted identifier name.
        file:           File path as it appears in the diff header.
        kind:           Symbol kind (function, class, method, etc.).
        language:       Language string.
        diff_line_hint: "diff:line+<0-based-N>" index string.

    Returns:
        Probe-spec dict with all required keys.
    """
    return {
        "symbol": symbol,
        "file": file,
        "kind": kind,
        "language": language,
        "diff_line_hint": diff_line_hint,
        "mcp_hints": {
            "trace_path_in": symbol,
            "trace_path_out": symbol,
            "data_flow": symbol,
        },
        "callers": [],
        "callees": [],
        "data_flow_targets": [],
        "tests_referencing": [],
        "filled": False,
    }


# ---------------------------------------------------------------------------
# Per-file symbol extraction.
# ---------------------------------------------------------------------------


def _extract_symbols_for_file(
    file_path: str,
    added_lines: List[str],
    language: str,
) -> List[Dict]:
    """Apply language-specific regex patterns to added_lines and return probe specs.

    For "export" kind (TypeScript/JavaScript const), only emits a probe spec
    when the line's RHS looks like a function expression (function keyword,
    async function, or arrow function) — plain const assignments are skipped
    to avoid noise.

    For "vue" language, emits one implicit "component" probe spec for the file
    basename (without extension), in addition to any script-block symbols.

    Uses 0-based indexing for diff_line_hint within the added_lines list.

    Args:
        file_path:    File path from the diff header.
        added_lines:  List of raw diff lines starting with "+".
        language:     Language string (from _detect_language).

    Returns:
        List of probe-spec dicts (may be empty; duplicates not yet filtered).
    """
    results: List[Dict] = []
    patterns = _LANGUAGE_PATTERNS.get(language, [])

    for idx, line in enumerate(added_lines):
        hint = "diff:line+{0}".format(idx)
        for pattern, kind in patterns:
            match = pattern.match(line)
            if not match:
                continue
            symbol = match.group(1)

            # For "export" kind: only emit if the const RHS is a function expression.
            if kind == "export":
                if not _TS_CONST_FUNCTION_RHS_RE.match(line):
                    break  # not a function expression; skip this line entirely
                           # (break, not continue — moves to next diff line)

            results.append(_build_probe_spec(symbol, file_path, kind, language, hint))
            # Each line can match at most one pattern; first match wins.
            break

    # Vue: add implicit component probe spec (file basename without extension).
    if language == "vue" and added_lines:
        basename = os.path.basename(file_path)
        component_name, _ = os.path.splitext(basename)
        if component_name:
            results.append(
                _build_probe_spec(
                    symbol=component_name,
                    file=file_path,
                    kind="component",
                    language="vue",
                    diff_line_hint="diff:line+0",
                )
            )

    return results


# ---------------------------------------------------------------------------
# Dedup + sort + cap helpers.
# ---------------------------------------------------------------------------


def _dedup_sort_cap(
    probe_specs: List[Dict],
) -> Tuple[List[Dict], bool]:
    """Dedup by (symbol, file), sort by (file, symbol), cap at _MAX_SYMBOLS_PER_PR.

    Returns:
        (deduplicated_sorted_capped_list, capped_bool)
        capped_bool is True if the original list (after dedup) exceeded the cap.
    """
    seen: set = set()
    unique: List[Dict] = []
    for spec in probe_specs:
        key = (spec["symbol"], spec["file"])
        if key not in seen:
            seen.add(key)
            unique.append(spec)

    unique.sort(key=lambda s: (s["file"], s["symbol"]))

    capped = len(unique) > _MAX_SYMBOLS_PER_PR
    if capped:
        unique = unique[:_MAX_SYMBOLS_PER_PR]

    return unique, capped


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
        prefix="blast-", suffix=".tmp.json", dir=target_dir
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
    """Parse diff from state.json, build probe-spec list, write to state.blast.

    Reads state.json (written by Step 3 intake), extracts changed symbols from
    state.diff, and REPLACES state.blast with one probe-spec entry per symbol.

    Re-running compute-blast-radius is idempotent: state.blast is overwritten
    with the result of the current diff — no prior entries are preserved.

    CBM is NOT called here. The mcp_hints field in each probe spec carries the
    symbol name for the LLM to pass to CBM trace_path at Step 8.

    Args:
        target:       Path to the reviewer's local repo root.
        pr_number:    PR number (positive int). Used to locate state.json.
        devforge_dir: Name of the devforge directory under target.

    Returns:
        dict with keys:
            status           — "ok"
            state_path       — absolute path of the (updated) state.json
            pr_number        — int
            symbols_extracted — int
            by_language      — dict mapping language -> count
            by_kind          — dict mapping kind -> count
            next_action      — reminder string for the LLM
            capped           — bool (True if _MAX_SYMBOLS_PER_PR was reached)

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

    # Parse diff into per-file blocks.
    file_blocks = _parse_diff(state.diff)

    # Extract symbols from each file block.
    all_specs: List[Dict] = []
    for block in file_blocks:
        file_path = block["file"]
        added_lines = block["added_lines"]
        language = _detect_language(file_path)
        if language is None:
            continue
        specs = _extract_symbols_for_file(file_path, added_lines, language)
        all_specs.extend(specs)

    # Dedup, sort, cap.
    probe_specs, capped = _dedup_sort_cap(all_specs)

    # Replace state.blast entirely.
    state.blast = probe_specs

    # Atomic write.
    _write_state(sp, state)

    # Build summary counts.
    by_language: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    for spec in probe_specs:
        lang = spec["language"]
        kind = spec["kind"]
        by_language[lang] = by_language.get(lang, 0) + 1
        by_kind[kind] = by_kind.get(kind, 0) + 1

    return {
        "status": "ok",
        "state_path": sp,
        "pr_number": pr_number,
        "symbols_extracted": len(probe_specs),
        "by_language": by_language,
        "by_kind": by_kind,
        "next_action": (
            "dispatch-review (Step 8) populates callers/callees via CBM trace_path"
        ),
        "capped": capped,
    }
