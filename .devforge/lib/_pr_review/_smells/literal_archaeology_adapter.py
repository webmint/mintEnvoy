"""Heuristic: literal_archaeology_adapter — fires per diff-introduced literal
whose git-blame archaeology shows ambiguous intent.

Severity: low (placeholder/forgotten), nit (generated)

Logic:
    1. Extract LITERALS from diff added lines using LITERAL_TOKEN_RE.
    2. For each literal occurrence (limited to _MAX_LITERALS_PER_PR):
       a. Find the file + line number within the diff (parse diff @@ hunks).
       b. Run `git blame -L <line>,<line> -- <file>` in the target directory.
       c. Parse blame output: SHA + commit subject (first line of log).
       d. Classify intent via _classify_intent().
    3. Emit findings only for intent == 'placeholder' or 'forgotten' (low) or
       'generated' (nit).  'migrated', 'deliberate', 'inherited-refactor' → no
       finding (low false-positive target).

Git operations: READ-ONLY.
    - `git blame -L <line>,<line> -- <file>` — reads blame for one line.
    - `git log -1 --format=%s <sha>` — reads commit subject for the blamed SHA.
    Both are purely query operations; no state-mutating git commands are used.
    Any subprocess error (binary not found, timeout, non-zero exit) → fail-soft:
    skip the literal silently (no crash, no finding).

Finding schema:
    {
        "name": "literal_archaeology_adapter",
        "severity": <"low"|"nit">,
        "location": "<file:line>",
        "evidence": "literal <literal> introduced by <sha7>: <commit_subject> [intent=<intent>]"
    }

Constants:
    _MAX_LITERALS_PER_PR  = 50
    _INTENT_PATTERNS      — dict mapping intent name → list of regex patterns (case-insensitive)
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from _shared.literal_call_shape import LITERAL_TOKEN_RE

_MAX_LITERALS_PER_PR = 50

# Intent classification patterns.  Evaluated in the order defined below;
# first match wins (the literal_archaeology spec defines 6 exclusive classes).
_INTENT_PATTERNS: Dict[str, List[str]] = {
    "placeholder": [
        r"TODO",
        r"TBD",
        r"placeholder",
        r"FIXME",
        r"WIP",
    ],
    "migrated": [
        r"migration",
        r"migrate",
        r"\bport(ing|ed)?\b",
    ],
    # 'forgotten' checked before 'deliberate' — forgotten patterns are anchored
    # at ^ (start of subject line) and would otherwise be shadowed by
    # 'deliberate' patterns like 'adjust' which match anywhere in the string.
    # Example: "fix(orderflow): adjust limit" must classify as 'forgotten',
    # not 'deliberate', because the commit type is 'fix'.
    "forgotten": [
        r"^fix[\(:]",     # 'fix:' or 'fix(scope):'
        r"^chore[\(:]",   # 'chore:' or 'chore(scope):'
        r"^fix$",
        r"^wip$",
    ],
    "deliberate": [
        r"change\s+\d+",
        r"set\s+to\s+\d+",
        r"adjust",
        r"update\s+\w+\s+to",
    ],
    "inherited-refactor": [
        r"refactor",
        r"cleanup",
        r"restructure",
        r"move",
    ],
    "generated": [
        r"generated",
        r"auto-",
        r"codegen",
        r"scaffold",
    ],
}

# Compiled intent patterns for efficient reuse.
_COMPILED_INTENT_PATTERNS: List[Tuple[str, List[Any]]] = [
    (
        intent,
        [re.compile(pat, re.IGNORECASE) for pat in pats],
    )
    for intent, pats in _INTENT_PATTERNS.items()
]

# Severities for actionable intents; others produce no finding.
_ACTIONABLE_INTENTS: Dict[str, str] = {
    "placeholder": "low",
    "forgotten": "low",
    "generated": "nit",
}

# Matches unified diff hunk header: @@ -<old> +<new>,<len> @@
_HUNK_HEADER_RE = re.compile(
    r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", re.MULTILINE
)

# Matches added content lines (not +++ headers).
_ADDED_LINE_RE = re.compile(r"^\+([^+\n].*)$", re.MULTILINE)

# Matches diff block header to identify the current file path.
_FILE_PATH_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)

# Matches `diff --git` to split per-file blocks.
_DIFF_SPLIT_RE = re.compile(r"^diff --git ", re.MULTILINE)


def _classify_intent(commit_msg: str, file_path: str, literal: str) -> str:
    """Classify the intent of a literal based on its introducing commit message.

    Applies _INTENT_PATTERNS in order; first match wins.  Falls back to
    'deliberate' when no pattern matches (conservative — no finding emitted
    for 'deliberate').

    Args:
        commit_msg: The one-line commit subject (from `git log -1 --format=%s`).
        file_path:  File path (reserved for future extension; unused now).
        literal:    The literal value (reserved for future extension; unused now).

    Returns:
        One of: 'placeholder', 'migrated', 'deliberate', 'forgotten',
                'inherited-refactor', 'generated'.
    """
    for intent, compiled_pats in _COMPILED_INTENT_PATTERNS:
        for cpat in compiled_pats:
            if cpat.search(commit_msg):
                return intent
    return "deliberate"


def _parse_blame_sha(blame_output: str) -> Optional[str]:
    """Extract the 40-char commit SHA from `git blame -p` output.

    Args:
        blame_output: stdout of `git blame --porcelain -L n,n -- file`.

    Returns:
        40-char SHA string, or None if output is empty or malformed.
    """
    if not blame_output:
        return None
    first_line = blame_output.split("\n")[0]
    parts = first_line.split()
    if parts and len(parts[0]) == 40:
        return parts[0]
    return None


def _git_blame_sha(file_path: str, line_number: int, target: str) -> Optional[str]:
    """Run git blame to get the SHA that introduced a specific line.

    Read-only git operation: `git blame --porcelain -L <line>,<line> -- <file>`.

    Args:
        file_path:   Path to the file, relative to target.
        line_number: 1-based line number within the file.
        target:      Repository root (cwd for subprocess).

    Returns:
        40-char SHA string, or None on any error.
    """
    try:
        result = subprocess.run(
            [
                "git", "blame", "--porcelain",
                "-L", "{n},{n}".format(n=line_number),
                "--", file_path,
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=target,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return _parse_blame_sha(result.stdout)


def _git_commit_subject(sha: str, target: str) -> Optional[str]:
    """Return the one-line subject of a commit.

    Read-only git operation: `git log -1 --format=%s <sha>`.

    Args:
        sha:    40-char commit SHA.
        target: Repository root (cwd for subprocess).

    Returns:
        Commit subject string, or None on any error.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s", sha],
            capture_output=True,
            text=True,
            check=False,
            cwd=target,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _extract_literals_with_locations(
    diff: str,
) -> List[Tuple[str, str, int]]:
    """Extract (literal, file_path, absolute_line_number) from diff added lines.

    Parses diff @@ hunk headers to compute the absolute line number in the
    target file for each added line.

    Args:
        diff: Raw unified diff string.

    Returns:
        List of (literal_value, file_path, 1-based_line_number) tuples.
        Capped at _MAX_LITERALS_PER_PR entries total.
    """
    results: List[Tuple[str, str, int]] = []

    # Split into per-file blocks.
    positions = [m.start() for m in _DIFF_SPLIT_RE.finditer(diff)]
    if not positions:
        return results

    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(diff)
        block = diff[start:end]

        path_match = _FILE_PATH_RE.search(block)
        if not path_match:
            continue
        file_path = path_match.group(1).strip()

        # Walk lines within this block, tracking current file line number.
        current_file_line = 0
        lines = block.split("\n")
        for raw_line in lines:
            hunk_match = _HUNK_HEADER_RE.match(raw_line)
            if hunk_match:
                current_file_line = int(hunk_match.group(1))
                continue

            if raw_line.startswith("+++") or raw_line.startswith("---"):
                continue

            if raw_line.startswith("+"):
                content = raw_line[1:]
                for lit_match in LITERAL_TOKEN_RE.finditer(content):
                    literal = lit_match.group(0)
                    results.append((literal, file_path, current_file_line))
                    if len(results) >= _MAX_LITERALS_PER_PR:
                        return results
                current_file_line += 1
            elif raw_line.startswith("-"):
                # Removed lines don't advance the new-file line counter.
                pass
            else:
                # Context line.
                if current_file_line > 0:
                    current_file_line += 1

    return results


def run(state: Any) -> List[Dict[str, Any]]:
    """Scan diff-introduced literals with git blame archaeology for intent.

    Args:
        state: PRReviewState instance.  Reads state.diff and state.target.

    Returns:
        List of findings — one per literal with an actionable intent.
        Empty if no smells detected or git is unavailable.
    """
    diff = state.diff or ""
    if not diff:
        return []

    target = state.target or ""
    if not target:
        return []

    literal_locations = _extract_literals_with_locations(diff)
    findings: List[Dict[str, Any]] = []

    for literal, file_path, line_number in literal_locations:
        sha = _git_blame_sha(file_path, line_number, target)
        if sha is None:
            continue

        commit_subject = _git_commit_subject(sha, target)
        if commit_subject is None:
            continue

        intent = _classify_intent(commit_subject, file_path, literal)
        severity = _ACTIONABLE_INTENTS.get(intent)
        if severity is None:
            continue

        findings.append({
            "name": "literal_archaeology_adapter",
            "severity": severity,
            "location": "{file}:{line}".format(file=file_path, line=line_number),
            "evidence": (
                "literal {lit} introduced by {sha7}: {subject} [intent={intent}]".format(
                    lit=literal,
                    sha7=sha[:7],
                    subject=commit_subject,
                    intent=intent,
                )
            ),
        })

    return findings
