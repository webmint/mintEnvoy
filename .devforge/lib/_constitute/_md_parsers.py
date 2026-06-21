"""Glossary markdown parser helpers."""

from __future__ import annotations

import re
from typing import List


def _parse_used_in_line(line: str) -> List[str]:
    """Parse '- **Used in**: a, b, c (and N others)' → [a, b, c].

    Strips the ' (and N others)' suffix. Returns [] if the line doesn't
    match the pattern.
    """
    m = re.match(r"^-\s+\*\*Used in\*\*:\s*(.+)$", line.strip())
    if not m:
        return []
    raw = m.group(1).strip()
    raw = re.sub(r"\s*\(and \d+ others?\)\s*$", "", raw)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_related_line(line: str) -> List[str]:
    """Parse '- **Related**: a, b, c' → [a, b, c].

    Returns [] if the line doesn't match the pattern.
    """
    m = re.match(r"^-\s+\*\*Related\*\*:\s*(.+)$", line.strip())
    if not m:
        return []
    return [item.strip() for item in m.group(1).split(",") if item.strip()]


def _parse_glossary_md(text: str) -> List[dict]:
    """Parse a glossary.md file into a list of term records.

    Each term block:
      ## <term>
      <definition paragraph(s)>
      - **Used in**: ...
      - **Related**: ...

    Returns list of {"term": str, "definition": str, "used_in": [str], "related": [str]}.
    Empty file → []. Terms with no definition/used_in/related emit empty
    strings / lists for those subfields (graceful).
    """
    lines = text.splitlines()
    terms = []

    current_term = None
    current_body_lines = []  # type: List[str]

    def _flush_term():
        if current_term is None:
            return
        definition_lines = []
        used_in = []
        related = []
        for body_line in current_body_lines:
            stripped = body_line.strip()
            if stripped.startswith("- **Used in**:"):
                parsed = _parse_used_in_line(stripped)
                if parsed:
                    used_in = parsed
            elif stripped.startswith("- **Related**:"):
                parsed = _parse_related_line(stripped)
                if parsed:
                    related = parsed
            elif re.match(r"^---\s*$", stripped):
                # Skip horizontal-rule / stray frontmatter delimiter lines.
                # Match exactly `---` (with optional trailing whitespace) — a
                # broader startswith("---") would silently swallow definition
                # text that begins with `---` (e.g., CLI flags like `---verbose`).
                pass
            else:
                definition_lines.append(body_line)
        definition = "\n".join(definition_lines).strip()
        terms.append(
            {
                "term": current_term,
                "definition": definition,
                "used_in": used_in,
                "related": related,
            }
        )

    in_frontmatter = False
    frontmatter_done = False
    frontmatter_start_seen = False

    for line in lines:
        stripped = line.strip()

        if not frontmatter_done:
            if stripped == "---" and not frontmatter_start_seen:
                frontmatter_start_seen = True
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                    frontmatter_done = True
                continue
            frontmatter_done = True

        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue

        if stripped.startswith("## "):
            _flush_term()
            current_term = stripped[3:].strip()
            current_body_lines = []
            continue

        if current_term is not None:
            current_body_lines.append(line)

    _flush_term()
    return terms
