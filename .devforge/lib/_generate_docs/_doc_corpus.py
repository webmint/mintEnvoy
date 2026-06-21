"""Shared corpus-extraction substrate for JUDGMENT-LAYER-PLAN.md Track A + Track B.

Five public functions consumed by both tracks:

  walk_doc_corpus       -- enumerate docs/**/*.md; return (rel_path, fm, body) list
  extract_term_occurrences -- regex PascalCase/camelCase/ALL_CAPS_SNAKE across corpus
  validate_cite_paths   -- check project-root-relative paths exist
  get_section_body_span -- compute (start+1, next_section_start-1) line span
  noise_filter          -- strip framework-name terms; optional override file

No CBM dependency. Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ._md_frontmatter import FrontmatterParseError, parse_frontmatter

# ── Regex patterns (module-level, compiled once) ─────────────────────────────

_PASCAL_CASE_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]+\b")
_CAMEL_CASE_RE = re.compile(r"\b[a-z]+[A-Z][a-zA-Z0-9]*\b")
# Requires at least one underscore — single ALL-CAPS words (e.g. XML) don't match.
_ALL_CAPS_SNAKE_RE = re.compile(r"\b[A-Z]+(?:_[A-Z]+)+\b")

# ── Noise baseline ────────────────────────────────────────────────────────────

_NOISE_BASELINE: frozenset = frozenset([
    "Vue", "Pinia", "GraphQL", "Promise", "React", "Angular", "TypeScript",
    "JavaScript", "Python", "Node", "JSON", "YAML", "HTML", "CSS", "URL",
    "URI", "HTTP", "HTTPS", "API", "XML", "JWT", "OAuth", "JSX", "TSX", "DOM",
])

# ── walk_doc_corpus ───────────────────────────────────────────────────────────


def walk_doc_corpus(docs_root: Path) -> List[Tuple[str, Dict, str]]:
    """Enumerate docs/**/*.md under docs_root.

    Returns a sorted list of (rel_path, frontmatter, body) tuples.
    rel_path is POSIX forward-slash relative to docs_root.
    On frontmatter parse failure: frontmatter is {} and body is whole file text.
    If docs_root does not exist or is not a directory: returns [].
    """
    if not docs_root.exists() or not docs_root.is_dir():
        return []

    results: List[Tuple[str, Dict, str]] = []

    for dirpath, _dirs, filenames in os.walk(str(docs_root)):
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            abs_path = Path(dirpath) / fname
            # Compute POSIX relative path.
            try:
                rel = abs_path.relative_to(docs_root)
            except ValueError:
                continue
            rel_str = rel.as_posix()
            try:
                text = abs_path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                fm, body = parse_frontmatter(text)
            except FrontmatterParseError:
                fm = {}
                body = text
            results.append((rel_str, fm, body))

    results.sort(key=lambda t: t[0])
    return results


# ── extract_term_occurrences ──────────────────────────────────────────────────


def _is_table_separator(line: str) -> bool:
    """Return True if line looks like a markdown table separator row."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    inner = stripped.strip("|").strip()
    # separator rows contain only dashes, colons, pipes, spaces
    return bool(re.match(r"^[-: |]+$", inner))


def _context_around(line_text: str, match_start: int, match_end: int) -> str:
    """Extract up to 2-sentence context around a match within line_text.

    Simple heuristic: split on sentence-boundary whitespace to get sentences.
    Take the sentence containing the match, plus up to one before and one after.
    Cap at 240 chars.
    """
    # Build list of (sentence_text, start_offset) using real separator positions.
    sentences = []
    prev_end = 0
    for m in re.finditer(r"(?<=[.!?])\s+", line_text):
        sentences.append((line_text[prev_end:m.start()], prev_end))
        prev_end = m.end()
    sentences.append((line_text[prev_end:], prev_end))  # final sentence

    # Find which sentence contains the match start.
    target_idx = 0
    for i, (sent, start_offset) in enumerate(sentences):
        if start_offset <= match_start <= start_offset + len(sent):
            target_idx = i
            break

    start_idx = max(0, target_idx - 1)
    end_idx = min(len(sentences), target_idx + 2)
    snippet = " ".join(s for s, _ in sentences[start_idx:end_idx])
    if len(snippet) > 240:
        snippet = snippet[:237] + "..."
    return snippet


def extract_term_occurrences(
    corpus: List[Tuple[str, Dict, str]]
) -> Dict[str, List[Tuple[str, int, str]]]:
    """Extract PascalCase, camelCase, ALL_CAPS_SNAKE terms from corpus bodies.

    Skips: fenced code blocks (``` ... ```), markdown table header+separator rows.
    Returns: {term: [(rel_path, line_1indexed, context_snippet), ...]}
    Same term may appear multiple times; all occurrences preserved in order.
    """
    result: Dict[str, List[Tuple[str, int, str]]] = {}

    for rel_path, _fm, body in corpus:
        lines = body.split("\n")
        in_code_block = False

        for lineno_0, line in enumerate(lines):
            line_1 = lineno_0 + 1

            # Track fenced code block state.
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Detect table header + separator: skip both rows.
            # A table header row starts with |; separator follows immediately.
            if _is_table_separator(line):
                # This line is a separator — skip it.
                continue

            # Check if this is a table header row (starts with |, next might be sep).
            # We peek ahead: if this line starts with | and next line is a separator,
            # skip this line.
            is_table_row = stripped.startswith("|")
            next_is_sep = False
            if is_table_row and lineno_0 + 1 < len(lines):
                next_is_sep = _is_table_separator(lines[lineno_0 + 1])
            if is_table_row and next_is_sep:
                continue  # skip header row

            # Extract terms from this line.
            for pattern in (_PASCAL_CASE_RE, _CAMEL_CASE_RE, _ALL_CAPS_SNAKE_RE):
                for m in pattern.finditer(line):
                    term = m.group(0)
                    context = _context_around(line, m.start(), m.end())
                    if term not in result:
                        result[term] = []
                    result[term].append((rel_path, line_1, context))

    return result


# ── validate_cite_paths ───────────────────────────────────────────────────────


def validate_cite_paths(
    paths: Iterable[str], project_root: Path
) -> Tuple[bool, List[str]]:
    """Check whether each path exists relative to project_root.

    Returns (all_ok, missing_list).
    Empty input -> (True, []).
    """
    missing: List[str] = []
    for p in paths:
        full = project_root / p
        if not os.path.exists(str(full)):
            missing.append(p)
    return (len(missing) == 0, missing)


# ── get_section_body_span ─────────────────────────────────────────────────────


def get_section_body_span(file_path: Path, section_start_line: int) -> Tuple[int, int]:
    """Return (body_start, body_end) line numbers (1-indexed) for a ## section.

    body_start = section_start_line + 1
    body_end   = next ## heading line - 1, or total_lines if last section.

    Raises ValueError if section_start_line is not a ## heading line.
    Raises OSError if file cannot be read (let propagate).
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    total_lines = len(lines)

    # Collect all ## heading line numbers (1-indexed).
    h2_lines: List[int] = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            h2_lines.append(i + 1)  # 1-indexed

    if section_start_line not in h2_lines:
        raise ValueError(
            "Line {0} is not a '## ' heading in {1}".format(section_start_line, file_path)
        )

    idx = h2_lines.index(section_start_line)
    body_start = section_start_line + 1

    if idx + 1 < len(h2_lines):
        body_end = h2_lines[idx + 1] - 1
    else:
        body_end = total_lines

    return (body_start, body_end)


# ── noise_filter ──────────────────────────────────────────────────────────────


def noise_filter(
    terms: Iterable[str], override_path: Optional[Path] = None
) -> List[str]:
    """Filter framework-noise terms from input, returning deduplicated list.

    Baseline strip-set: _NOISE_BASELINE.
    If override_path exists: read newline-separated terms (skip blank + # lines)
    and add to strip-set for this call.
    First-occurrence wins for deduplication. Order preserved.
    """
    strip_set = set(_NOISE_BASELINE)

    if override_path is not None and override_path.is_file():
        try:
            text = override_path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                strip_set.add(stripped)

    seen: set = set()
    out: List[str] = []
    for term in terms:
        if term in strip_set:
            continue
        if term in seen:
            continue
        seen.add(term)
        out.append(term)

    return out
