"""_hygiene.py — scope-creep + leftover-artifact flags for /verify.

Public surface
--------------
  check_hygiene(changed_files, scope_baseline, source_root) -> dict
      Flag (a) scope-creep — files in ``changed_files`` but not in the
      declared scope baseline — and (b) leftover artifacts across the changed
      files: debug prints, bare TODOs/FIXMEs, and obvious commented-out blocks.

      Parameters
      ----------
      changed_files : list[str]
          File paths that changed during implementation (relative or absolute;
          relative paths are resolved against ``source_root``).  Typically the
          ``files_for_finders`` array from ``resolve-feature-scope``.
      scope_baseline : list[str] or None
          The declared planned file set — the union of ``touched_files`` across
          all tasks in ``breakdown-handoff.json``.  Pass ``None`` or ``[]`` to
          skip scope-creep checking (only leftover artifacts are reported).
      source_root : str
          Absolute path to the source tree.  Changed files are read from
          here.

      Returns
      -------
      dict with:
        "scope_creep" : list[str]
            Files in ``changed_files`` not found in ``scope_baseline`` (after
            normalisation).  Empty list when scope-creep check is skipped.
            Non-code files (prose artifacts, forge-managed dirs) are never
            reported as scope-creep regardless of baseline contents.
        "leftover_artifacts" : list[dict]
            One dict per flagged line:
              "file"    : str  — path as given in ``changed_files``
              "line"    : int  — 1-based line number
              "kind"    : str  — one of "debug_print" | "debug_statement" |
                                 "bare_todo" | "bare_fixme" |
                                 "commented_code_block"
              "snippet" : str  — the flagged line, stripped
        "scope_creep_checked" : bool
            True when a scope baseline was supplied and the check ran.
        "files_checked" : int
            Number of changed files that were successfully read and scanned
            for artifacts.  Non-code files are not counted here.
        "files_unreadable" : list[str]
            Files that could not be read (missing, binary, permission error).
        "files_skipped" : int
            Number of changed files that were skipped by the file-type gate
            (non-code prose/data files).  Additive and back-compatible key.

File-type gate (_is_code_file)
--------------------------------
The artifact scanner and scope-creep check operate only on source-code files.
Pipeline prose artifacts (specs/, docs/, design/, audits/, research/, etc.)
and data/lock files (.json, .yaml, .lock, etc.) are excluded via a DENYLIST
approach — we exclude KNOWN prose/data, rather than allowlisting code languages.
Reason: this codebase targets polyglot consumers; hardcoding code-file extensions
would be language-specific and would break on new stacks.  False negatives (a
prose file slips through) are preferable to false positives (a legitimate source
file in an unlisted language gets skipped).

Design notes — conservative posture
-------------------------------------
The hygiene check PREFERS false negatives over false positives; trust is
eroded faster by spurious flags than by occasional misses.

Scope-creep
~~~~~~~~~~~
Comparison is done on normalised paths (both sides stripped) after stripping
leading "./" from relative paths.  If either ``changed_files`` or
``scope_baseline`` uses absolute paths, they are made relative to
``source_root`` before comparison.  Comparison is CASE-SENSITIVE — lowercasing
was removed because it produces false negatives on case-sensitive filesystems
(e.g. Linux, where ``src/Components/MyButton.tsx`` and
``src/components/mybutton.tsx`` are distinct files).

Leftover-artifact patterns (conservative)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. ``debug_print``:
   - ``console.log(`` — JS/TS/Vue debug log.
   - ``print(`` — Python debug print.  Matched with a negative lookbehind
     ``(?<![.\\w])`` so that method calls like ``self.print(``, ``rich.print(``,
     and ``obj.print(`` are NOT flagged — only bare ``print(`` and ``(print(``
     (or other non-identifier, non-dot prefixes) trigger the rule.
     False-positive risk: legitimate bare ``print()`` in scripts/CLIs.  We flag
     it anyway because the caller reviews the snippet.  The kind makes it clear.
   - ``console.error(`` / ``console.warn(`` are NOT flagged — those are often
     legitimate error-boundary logging.
   NOTE: ``print(`` is matched on any matching line, including inside string
   literals or docstrings — the scanner does not track open-quote state.  The
   caller reviews the snippet to confirm intent.

2. ``debug_statement``:
   - ``debugger`` on its own line (JavaScript ``debugger;`` statement).
     Matched as a whole-line token to avoid false positives in comments/strings.
   - ``pdb.set_trace()`` — Python interactive debugger.
   - ``breakpoint()`` — Python 3.7+ built-in breakpoint.  Flagged only when
     it appears as a standalone call (not as a method or in a comment).

3. ``bare_todo`` / ``bare_fixme``:
   - ``TODO`` or ``FIXME`` (case-insensitive) on a line that does NOT contain
     a ticket/issue reference.  A ticket reference is anything matching
     ``#NNN`` (hash + digits), ``PROJ-NNN`` (JIRA-style), or a URL (``http``).
     ``TODO(name):`` with no ticket is still flagged.
     This is intentionally strict — a bare "TODO: do X" without a reference is
     a leftover.

4. ``commented_code_block``:
   A line is flagged ONLY when it is a comment-only line (``#`` or ``//``
   prefix after stripping) AND the de-commented body triggers one of four
   conservative rules:

   Rule A — assignment-call: body contains ``<ident> = <something>(`` (the
   ``=`` + ``(`` together are a reliable code signal, e.g. "const x = getConfig();").

   Rule B — bare call ending ``;``: body ends with ``;`` AND contains ``(``
   (catches "// oldFunc();" and "// doSomething(a, b);" without a keyword).

   Rule C — structure + terminator (dual signal):
     (a) Body starts with a narrow code-structure pattern:
           ``def ``  ``async def ``  ``function ``  ``async function ``
           ``if (``  ``for (``  ``while (``  ``foreach (``  ``module.exports``
         Bare tokens ``return ``, ``from ``, ``import ``, ``class ``, ``const ``,
         ``let ``, ``var ``, ``export `` are EXCLUDED — all common in English prose.
     (b) Body ends with one of: ``:``  ``{``  ``}``  ``)``  ``;``

   Rule D — call-expression ending ``)``: body ends with ``)`` AND contains an
   ident-call pattern ``<ident>(`` (catches "// return compute(x)" and
   "// fetchData(url)" but NOT parenthetical prose like "// the result (lazy)").

   Multi-line blocks are not tracked — each qualifying line is flagged
   independently.  The multi-rule requirement prevents prose comments like
   "// from the spec", "// return type is X", or "// class is immutable" from
   firing.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# File-type gate — polyglot denylist (not a code-extension allowlist)
# ---------------------------------------------------------------------------
# We exclude KNOWN prose/data path segments and extensions rather than
# enumerating source-code languages.  This avoids false negatives on
# unlisted language extensions (Go, Rust, Kotlin, …) at the cost of
# occasionally letting a prose file slip through — which is the correct
# trade-off for a framework that targets polyglot consumer projects.
#
# Skip-dirs: matched against every SEGMENT of the normalised path so that
# both top-level "specs/foo.md" and wrapper-prefixed "subdir/specs/foo.md"
# are caught.  The check is case-insensitive to handle macOS/Windows paths.
_SKIP_PATH_SEGMENTS = frozenset([
    "specs", "docs", "design", "audits",
    "research", "discover", "bugs", ".devforge",
])

# Skip-extensions: matched case-insensitively against the file's suffix.
_SKIP_EXTENSIONS = frozenset([
    ".md", ".html", ".htm", ".txt",
    ".json", ".yaml", ".yml",
    ".csv", ".svg", ".lock",
])


def _is_code_file(path):
    # type: (str) -> bool
    """Return True when path should be treated as a source-code file.

    Returns False (skip) for:
      - Files whose normalised path contains a known forge-artifact directory
        segment (``specs``, ``docs``, ``design``, ``audits``, ``research``,
        ``discover``, ``bugs``, ``.devforge``).  Matching is done on every
        individual path segment so that wrapper-mode prefixes (e.g.
        ``subproject/specs/…``) are also excluded.
      - Files with known prose/data extensions (``.md``, ``.html``, etc.).

    Returns True for everything else (prefer false negatives over false
    positives — an unrecognised code extension passes through rather than
    being silently skipped).

    Note on dotfiles: ``.env``, ``.gitignore``, and similar dotfiles have an
    empty string as their extension under ``os.path.splitext`` (the leading dot
    is part of the name, not a suffix separator).  An empty extension is not in
    ``_SKIP_EXTENSIONS``, so dotfiles pass through and are scanned — consistent
    with the denylist design.
    """
    # Strip leading "./" and normalise separators, matching _normalise_path.
    if path.startswith("./"):
        path = path[2:]
    path = path.replace("\\", "/")

    # Check extension (case-insensitive).
    _, ext = os.path.splitext(path)
    if ext.lower() in _SKIP_EXTENSIONS:
        return False

    # Check every path segment against the known forge-artifact directories.
    segments = path.split("/")
    for seg in segments[:-1]:  # exclude the filename itself
        if seg.lower() in _SKIP_PATH_SEGMENTS:
            return False

    return True


# ---------------------------------------------------------------------------
# Leftover-artifact regex patterns
# ---------------------------------------------------------------------------

# debug_print: console.log( or bare print(
# The negative lookbehind (?<![.\w]) on print ensures that .print( (method
# calls like self.print(), rich.print(), obj.print()) are NOT matched.
# \w covers [a-zA-Z0-9_], so any identifier or dot before print is excluded.
# console.log( is already qualified so the lookbehind there is harmless.
_DEBUG_PRINT_RE = re.compile(r"\bconsole\.log\s*\(|(?<![.\w])print\s*\(")

# debug_statement: debugger (whole-word), pdb.set_trace(), breakpoint()
_DEBUG_STMT_DEBUGGER_RE = re.compile(r"\bdebugger\b")
_DEBUG_STMT_PDB_RE = re.compile(r"\bpdb\.set_trace\s*\(")
_DEBUG_STMT_BREAKPOINT_RE = re.compile(r"\bbreakpoint\s*\(\s*\)")

# bare_todo / bare_fixme: TODO or FIXME not followed by a ticket reference.
# A "ticket reference" is: #digits, JIRA-style (LETTERS-digits), or http URL.
_TODO_RE = re.compile(r"\bTODO\b", re.IGNORECASE)
_FIXME_RE = re.compile(r"\bFIXME\b", re.IGNORECASE)
_TICKET_REF_RE = re.compile(
    r"#\d+|[A-Z]{2,}-\d+|https?://",
    re.IGNORECASE,
)

# commented_code_block: comment-only line whose body carries a dual code signal.
# Python comment: # (stripped)
# JS/TS/Vue comment: // (stripped)
_COMMENT_PREFIX_RE = re.compile(r"^(//|#)\s*(.*)")

# Structure patterns that — combined with a terminator — signal commented code.
# These are deliberately NARROW: only forms unlikely to appear in English prose.
# Excluded: return/from/import/class/const/let/var/export — all common in English.
_STRUCTURE_START_RE = re.compile(
    r"^(def |async def |function |async function |if \(|for \(|while \(|foreach \(|module\.exports)",
    re.IGNORECASE,
)

# Assignment-call pattern: <ident> = <something>( — the = and ( together signal code.
# Matches "x = foo(" or "self.x = Bar(" etc.
_ASSIGN_CALL_RE = re.compile(r"\w[\w.]*\s*=\s*\S+\s*\(")

# Code terminators that — after a structure match — confirm a code statement.
# Ends with : { } ) or ;
_CODE_TERMINATOR_RE = re.compile(r"[:{})]$|;$")

# Call-expression pattern: an identifier immediately followed by ( — signals a real
# function call (e.g. compute(, fetchData(, doSomething() — NOT a parenthetical note).
_IDENT_CALL_RE = re.compile(r"\w\s*\(")


def _is_commented_code(line_stripped):
    # type: (str) -> bool
    """Return True when line_stripped is a comment-only line with a dual code signal.

    Rules (any one match fires):

    Rule A — assignment-call pattern:
      The body contains ``<ident> = <something>(`` — the ``=`` and ``(`` together
      signal a commented-out assignment to a function call, regardless of leading
      keyword.  Catches "// const x = getConfig();" even without a code terminator.

    Rule B — bare call-statement ending with ``;`` and containing ``(``:
      e.g. "// oldFunc();" "// doSomething(a, b);"  The ``;`` is a strong
      code-statement signal.

    Rule C — structure-pattern + code-terminator (dual signal):
      (a) Body starts with a narrow code-structure pattern:
            ``def ``         ``async def ``   — Python function definition
            ``function ``    ``async function `` — JS/TS function definition
            ``if (``         ``for (``   ``while (``   ``foreach (`` — control flow with paren
            ``module.exports``                          — CommonJS export
      (b) Body ends with a code terminator: ``:`` ``{`` ``}`` ``)`` or ``;``.
      Note: bare tokens like ``return ``, ``from ``, ``import ``, ``class ``,
      ``const ``, ``let ``, ``var ``, and ``export `` are EXCLUDED from (a) because
      they match common English prose ("// from the spec", "// class is immutable").

    Rule D — call-expression ending with ``)``:
      Body ends with ``)`` AND contains ``(``.  This catches return/assignment
      patterns whose body IS a call expression, e.g. "# return compute(x)" or
      "// fetchData(url)".  English prose like "// return type is X" does not end
      with ``)`` so it is safe.

    English prose comments like "// from the spec", "// return type is X",
    "// class is immutable", "// let me explain" do NOT fire under any rule.
    """
    m = _COMMENT_PREFIX_RE.match(line_stripped)
    if m is None:
        return False
    body = m.group(2).strip()
    if not body:
        return False

    body_lower = body.lower()

    # Rule A: assignment-call pattern (ident = func_call() — regardless of prefix)
    if _ASSIGN_CALL_RE.search(body):
        return True

    # Rule B: bare call-statement ending with ; that contains (
    # e.g. "oldFunc();" "doSomething(a, b);"
    if body.endswith(";") and "(" in body:
        return True

    # Rule C: structure-pattern + code-terminator (dual signal)
    if _STRUCTURE_START_RE.match(body_lower):
        # Terminators: : { } ) or ;
        if re.search(r"[:{})]\s*$|;\s*$", body):
            return True

    # Rule D: call-expression ending with ) that contains an ident-call pattern.
    # Catches "return compute(x)", "fetchData(url)" but NOT "the result (lazy)".
    # Requires <ident>( somewhere in the body so parenthetical prose doesn't fire.
    if body.endswith(")") and _IDENT_CALL_RE.search(body):
        return True

    return False


def _has_ticket_ref(line):
    # type: (str) -> bool
    """Return True when the line contains a ticket/issue reference."""
    return bool(_TICKET_REF_RE.search(line))


def _normalise_path(path, source_root):
    # type: (str, str) -> str
    """Normalise a file path to a source-root-relative form.

    Absolute paths inside source_root are made relative.  Leading "./" is
    stripped.  Path separators are normalised to "/".  Case is preserved —
    lowercasing is NOT applied because it produces false negatives on
    case-sensitive filesystems (Linux) where ``src/Components/MyButton.tsx``
    and ``src/components/mybutton.tsx`` are distinct files.
    """
    # Strip leading "./"
    if path.startswith("./"):
        path = path[2:]

    # If absolute and under source_root, make relative.
    if os.path.isabs(path) and source_root:
        rel = os.path.relpath(path, source_root)
        if not rel.startswith(".."):
            path = rel

    # Normalise separators only (no case change).
    return path.replace("\\", "/")


def _check_file_artifacts(filepath, file_lines):
    # type: (str, List[str]) -> List[Dict]
    """Scan file_lines for leftover artifacts.  Returns list of finding dicts."""
    findings = []  # type: List[Dict]

    for lineno, raw_line in enumerate(file_lines, start=1):
        stripped = raw_line.rstrip("\n\r").strip()
        if not stripped:
            continue

        # --- debug_print ---
        if _DEBUG_PRINT_RE.search(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "debug_print",
                "snippet": stripped[:200],
            })
            continue  # one finding per line

        # --- debug_statement ---
        if (
            _DEBUG_STMT_DEBUGGER_RE.search(stripped)
            or _DEBUG_STMT_PDB_RE.search(stripped)
            or _DEBUG_STMT_BREAKPOINT_RE.search(stripped)
        ):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "debug_statement",
                "snippet": stripped[:200],
            })
            continue

        # --- bare_todo / bare_fixme ---
        if _TODO_RE.search(stripped) and not _has_ticket_ref(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "bare_todo",
                "snippet": stripped[:200],
            })
            continue
        if _FIXME_RE.search(stripped) and not _has_ticket_ref(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "bare_fixme",
                "snippet": stripped[:200],
            })
            continue

        # --- commented_code_block ---
        if _is_commented_code(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "commented_code_block",
                "snippet": stripped[:200],
            })
            continue

    return findings


def check_hygiene(changed_files, scope_baseline, source_root):
    # type: (List[str], Optional[List[str]], str) -> Dict
    """Flag scope-creep and leftover artifacts across the changed files.

    Parameters
    ----------
    changed_files : list[str]
        File paths changed during implementation.
    scope_baseline : list[str] or None
        Planned file set (``touched_files`` union from breakdown-handoff.json).
        ``None`` or ``[]`` skips scope-creep checking.
    source_root : str
        Absolute path to the source tree; relative paths in ``changed_files``
        are resolved against this.

    Returns
    -------
    dict with keys:
        scope_creep : list[str]
            Files in ``changed_files`` not in ``scope_baseline``, after
            normalisation.  Non-code files are never reported here.
        leftover_artifacts : list[dict]
            See module docstring for the per-finding shape.
        scope_creep_checked : bool
        files_checked : int
            Count of code files actually read and scanned.
        files_unreadable : list[str]
            Code files that could not be read.
        files_skipped : int
            Count of files bypassed by the file-type gate (prose/data files).
            Additive key — callers that only check the pre-existing keys are
            not affected.
    """
    source_root = source_root or os.getcwd()

    # --- Scope-creep check ---
    # Non-code files are excluded from scope-creep reporting: they live in
    # forge-managed directories (specs/, docs/, …) that are never declared in
    # the breakdown-handoff scope baseline, so they would always appear as
    # "creep" without the gate.
    scope_creep_checked = scope_baseline is not None and len(scope_baseline) > 0
    scope_creep = []  # type: List[str]

    if scope_creep_checked:
        baseline_set = {
            _normalise_path(p, source_root) for p in scope_baseline
        }
        for cf in changed_files:
            if not _is_code_file(cf):
                continue  # prose/data file — never scope-creep
            norm = _normalise_path(cf, source_root)
            if norm not in baseline_set:
                scope_creep.append(cf)

    # --- Leftover-artifact check ---
    leftover_artifacts = []  # type: List[Dict]
    files_unreadable = []  # type: List[str]
    files_checked = 0
    files_skipped = 0

    for cf in changed_files:
        # Gate: skip prose/data files — artifact patterns are meaningless there
        # and produce false positives (e.g. HTML comment blocks matching
        # _DEBUG_PRINT_RE, spec headings matching commented-code rules).
        if not _is_code_file(cf):
            files_skipped += 1
            continue

        # Resolve the path to read.
        if os.path.isabs(cf):
            full_path = cf
        else:
            full_path = os.path.join(source_root, cf)

        try:
            with open(full_path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            files_unreadable.append(cf)
            continue

        files_checked += 1
        findings = _check_file_artifacts(cf, lines)
        leftover_artifacts.extend(findings)

    return {
        "scope_creep": scope_creep,
        "leftover_artifacts": leftover_artifacts,
        "scope_creep_checked": scope_creep_checked,
        "files_checked": files_checked,
        "files_unreadable": files_unreadable,
        "files_skipped": files_skipped,
    }
