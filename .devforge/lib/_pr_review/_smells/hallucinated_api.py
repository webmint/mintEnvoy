"""Heuristic: hallucinated_api — fires when an import in diff additions references
a module that doesn't appear elsewhere in the target codebase.

Severity: low

Scope (v1): only checks IMPORT statements.  Broader symbol-presence checks are
too noisy; import-site is the clearest signal.

Language support:
    Python:  `import <module>` and `from <module> import <symbol>`
    TS/JS:   `import { Name } from '<module>'` and `import Name from '<module>'`
    Vue:     same as TS/JS (inside <script> blocks — script tag not parsed; same
             regex applies when the diff includes the script section)

Logic:
    1. Extract added lines from state.diff.
    2. For each added line, try each language's import pattern to identify the
       imported module name.
    3. If the module is in the stdlib allowlist for its language → skip (no finding).
    4. Run `grep -r --include="*.py" ...` (or *.ts, *.js, etc.) over the target
       repo to check whether the module appears outside this PR's diff.
    5. If grep finds ZERO other occurrences → emit finding.
    6. Cap at _MAX_IMPORTS_PER_PR import sites total.

Git operations: NONE.  Uses read-only grep subprocess over the filesystem.

Subprocess pattern:
    grep -rl --include="*.py" <module_name> <target>
    (--files-with-matches for efficiency; stop after finding one match)

Fail-soft: if grep is not in PATH or a subprocess error occurs → skip the
finding for that import (no crash, no finding).  `_grep_for_module` returns
None for tool-unavailable, False for absent, True for found.  The caller in
run() treats None as "skip" (not as "not found").

Finding schema:
    {
        "name": "hallucinated_api",
        "severity": "low",
        "location": "diff:line+<N>",   # 0-based index in added-lines list
        "evidence": "import <module> not found elsewhere in codebase"
    }

Constants:
    _MAX_IMPORTS_PER_PR = 30
    _PYTHON_STDLIB     — frozenset of common Python stdlib module names
    _IMPORT_PATTERNS   — compiled per-language import regexes
"""

from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, List, Optional

_MAX_IMPORTS_PER_PR = 30

# ---------------------------------------------------------------------------
# Python standard-library allowlist.
# Modules here are never flagged regardless of grep result.
# ---------------------------------------------------------------------------
_PYTHON_STDLIB: frozenset = frozenset([
    # Built-ins / builtins.
    "__future__", "builtins",
    # Data types / structures.
    "abc", "collections", "contextlib", "copy", "dataclasses", "datetime",
    "decimal", "enum", "fractions", "functools", "gc", "heapq", "io",
    "itertools", "numbers", "operator", "queue", "struct", "typing",
    "types", "weakref",
    # I/O + filesystem.
    "csv", "filecmp", "glob", "io", "os", "os.path", "pathlib", "pickle",
    "shelve", "shutil", "stat", "tempfile", "zipfile", "tarfile",
    # Text processing.
    "codecs", "difflib", "gettext", "readline", "re", "string", "textwrap",
    "unicodedata",
    # Math + numbers.
    "cmath", "math", "random", "statistics",
    # Networking + URLs.
    "email", "ftplib", "http", "http.client", "http.server", "ipaddress",
    "smtplib", "socket", "ssl", "urllib", "urllib.parse", "urllib.request",
    "uuid",
    # System / process.
    "argparse", "ast", "atexit", "cmd", "code", "compileall", "configparser",
    "dis", "getopt", "getpass", "inspect", "keyword", "logging", "multiprocessing",
    "platform", "pprint", "profile", "pstats", "pty", "pwd", "resource",
    "runpy", "signal", "site", "subprocess", "sys", "sysconfig", "traceback",
    "tracemalloc", "warnings",
    # Serialization.
    "base64", "binascii", "hashlib", "hmac", "html", "html.parser", "json",
    "marshal", "mimetypes", "quopri", "secrets", "sqlite3", "xml", "xml.etree",
    "xml.etree.ElementTree", "xmlrpc",
    # Testing.
    "doctest", "mock", "unittest", "unittest.mock",
    # Concurrency.
    "asyncio", "concurrent", "concurrent.futures", "threading",
    # Misc.
    "calendar", "cProfile", "gzip", "importlib", "linecache", "locale",
    "lzma", "mmap", "pdb", "pkgutil", "posixpath", "sched", "time", "timeit",
    "token", "tokenize", "trace", "tty", "uu", "wave", "zlib",
])

# ---------------------------------------------------------------------------
# Import patterns: (language_tag, compiled_re, group_index_for_module)
#   group 1 = module name in Python; group 2 = module path in TS/JS
# ---------------------------------------------------------------------------
_IMPORT_PATTERNS: List = [
    # Python: `import foo` or `import foo.bar`
    (
        "py",
        re.compile(r"^\s*import\s+([\w.]+)"),
        1,
        [".py"],
    ),
    # Python: `from foo.bar import baz`
    (
        "py",
        re.compile(r"^\s*from\s+([\w.]+)\s+import\s+"),
        1,
        [".py"],
    ),
    # TS/JS: `import { X } from 'some-module'` or `import X from "some-module"`
    (
        "ts",
        re.compile(r"""^\s*import\s+.*\bfrom\s+['"]([^'"]+)['"]"""),
        1,
        [".ts", ".tsx", ".js", ".jsx", ".vue"],
    ),
]

# Glob patterns passed to grep --include for each language tag.
_LANG_GLOBS: Dict = {
    "py": ["--include=*.py"],
    "ts": ["--include=*.ts", "--include=*.tsx", "--include=*.js",
           "--include=*.jsx", "--include=*.vue"],
}

# Matched added content lines (not +++ headers or bare additions).
_ADDED_LINE_RE = re.compile(r"^\+([^+\n].*)$", re.MULTILINE)


def _is_stdlib_python(module: str) -> bool:
    """Return True if module is in the Python stdlib allowlist.

    Checks both the full dotted name and the top-level package.
    """
    if module in _PYTHON_STDLIB:
        return True
    top = module.split(".")[0]
    return top in _PYTHON_STDLIB


def _grep_for_module(module: str, lang: str, target: str) -> Optional[bool]:
    """Return True/False/None for module presence check.

    Uses grep -rl (files-with-matches) to stop after the first file found.
    Bounded: --max-count=1 per grep invocation.

    Return values:
        True   — grep ran and found at least one occurrence.
        False  — grep ran and found nothing (module is absent from codebase).
        None   — grep binary unavailable or subprocess error; caller should
                 skip the finding (fail-soft per spec: "grep binary missing → no findings").

    Args:
        module: The module name / path to search for.
        lang:   Language tag ("py" or "ts") — controls --include globs.
        target: Repository root directory.
    """
    globs = _LANG_GLOBS.get(lang, [])
    cmd = ["grep", "-rl", "--max-count=1"] + globs + [module, target]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return result.returncode == 0 and bool(result.stdout.strip())


def run(state: Any) -> List[Dict[str, Any]]:
    """Scan diff additions for imports of modules absent from the codebase.

    Args:
        state: PRReviewState instance.  Reads state.diff and state.target.

    Returns:
        List of findings — one per import of an unrecognised module.
        Empty if no smells detected or grep is unavailable.
    """
    diff = state.diff or ""
    if not diff:
        return []

    target = state.target or ""
    if not target:
        return []

    # Extract added lines with their 0-based index.
    added_lines = [m.group(1) for m in _ADDED_LINE_RE.finditer(diff)]

    findings: List[Dict[str, Any]] = []
    imports_seen = 0

    for idx, line in enumerate(added_lines):
        if imports_seen >= _MAX_IMPORTS_PER_PR:
            break

        for lang, pattern, group, _exts in _IMPORT_PATTERNS:
            m = pattern.match(line)
            if not m:
                continue

            module = m.group(group).strip()
            if not module:
                continue

            imports_seen += 1

            # Python stdlib allowlist.
            if lang == "py" and _is_stdlib_python(module):
                break

            # Relative imports (start with '.') are always local — skip.
            if module.startswith("."):
                break

            # Check grep across codebase.
            # _grep_for_module returns True=found, False=absent, None=tool unavailable.
            found = _grep_for_module(module, lang, target)
            if found is None:
                # grep unavailable → fail-soft: skip this import, no finding.
                break
            if found is False:
                findings.append({
                    "name": "hallucinated_api",
                    "severity": "low",
                    "location": "diff:line+{n}".format(n=idx),
                    "evidence": "import {module} not found elsewhere in codebase".format(
                        module=module
                    ),
                })
            break  # Only one pattern match per line.

    return findings
