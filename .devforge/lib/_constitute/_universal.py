"""Universal-section parsers for forge-internal:verify-universal-defaults."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from ._schema import _PATTERNS_BUCKET_TO_SECTION, _UNIVERSAL_SECTIONS


def _parse_universal_blocks(constitution_md_path: "Path") -> "Dict[str, Dict]":
    """Parse universal sections from a constitution.md file.

    Reads the markdown file at `constitution_md_path` and returns a dict
    keyed by §-prefixed section number (e.g. "§3.5") for each section in
    _UNIVERSAL_SECTIONS.

    Return shape per section::

        {
            "heading": "<exact heading text after the section number>",
            "rules": [
                {"tag_or_label": "<label>", "body": "<rule body text>"},
                ...
            ],
        }

    Section-specific splitting:
    - §3.6: splits the SOLID block into individual sub-rules (one entry per
      ``- **Name**`` bullet) plus DRY and KISS as additional entries.
      Single Responsibility is included when present.
    - §4.1, §4.2, §4.3: splits on ``- **Label.**`` / ``- **Label**`` bullets
      (each top-level bullet becomes one rule entry).
    - All other sections: emits a single rule entry with tag_or_label equal to
      the section heading and body equal to the full section body text.

    Missing file: raises ``FileNotFoundError`` (caller decides how to handle).
    Section absent from file: that section key is absent from the returned dict.
    """
    text = Path(constitution_md_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    # --- Step 1: locate each heading and extract the body slice. ---
    heading_re = re.compile(r"^(#{2,})\s+([\d]+\.[\d]+(?:\.[\d]+)*)\s+(.*)")
    heading_positions = []  # type: List[tuple]
    for idx, line in enumerate(lines):
        m = heading_re.match(line)
        if m:
            level = len(m.group(1))
            number = m.group(2)
            title_raw = m.group(3).strip()
            heading_positions.append((idx, level, number, title_raw))

    # Build a map: number_str -> (title_raw, body_lines).
    section_map = {}  # type: Dict[str, tuple]
    for i, (idx, level, number, title_raw) in enumerate(heading_positions):
        body_start = idx + 1
        body_end = len(lines)
        for j in range(i + 1, len(heading_positions)):
            nxt_idx, nxt_level, _, _ = heading_positions[j]
            if nxt_level <= level:
                body_end = nxt_idx
                break
        body_lines = lines[body_start:body_end]
        section_map[number] = (title_raw, body_lines)

    # --- Step 2: build the result dict for universal sections. ---
    result = {}  # type: Dict[str, Dict]
    for sect_key in _UNIVERSAL_SECTIONS:
        number = sect_key[1:]  # strip leading §
        if number not in section_map:
            continue
        title_raw, body_lines = section_map[number]
        heading = re.sub(r"\s*\[.*?\]\s*$", "", title_raw).strip()
        body_text = "\n".join(body_lines).strip()

        if sect_key == "§3.6":
            rules = _split_design_principles(body_text)
        elif sect_key in ("§4.1", "§4.2", "§4.3"):
            rules = _split_bullet_rules(heading, body_text)
        else:
            rules = [{"tag_or_label": heading, "body": body_text}]

        result[sect_key] = {"heading": heading, "rules": rules}

    return result


def _split_design_principles(body_text: str) -> "List[Dict]":
    """Split §3.6 body into individual design-principle rule entries.

    Recognises two block shapes:
    - SOLID sub-rules: ``- **Name** — ...`` top-level bullets within the
      ``**SOLID:**`` block.  Each becomes a separate rule with the principle
      name as tag_or_label.
    - Top-level bold-header blocks (DRY, KISS): ``**Name (...):**`` paragraphs.
      Each becomes a rule with the short name as tag_or_label and the full
      paragraph text (including its sub-bullets) as body.

    Returns a list of rule dicts in document order.
    """
    rules = []  # type: List[Dict]

    block_header_re = re.compile(r"^\*\*([^*]+):\*\*\s*$")

    lines = body_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        bm = block_header_re.match(line.strip())
        if bm:
            block_name = bm.group(1).strip()
            block_lines = []
            i += 1
            while i < len(lines):
                peek = lines[i]
                if block_header_re.match(peek.strip()):
                    break
                block_lines.append(peek)
                i += 1
            block_body = "\n".join(block_lines).strip()

            if block_name == "SOLID":
                rules.extend(_split_solid_sub_rules(block_body))
            else:
                short_name = re.split(r"\s*[\(\s]", block_name)[0].strip()
                rules.append({"tag_or_label": short_name, "body": block_body})
        else:
            i += 1

    return rules


def _split_solid_sub_rules(solid_body: str) -> "List[Dict]":
    """Split the SOLID block body into one entry per principle.

    Each principle starts with ``- **Name** — ...`` at the top indent level.
    Lines that are continuations (indented or blank) belong to the previous
    principle.  Returns list of dicts with tag_or_label and body.
    """
    bullet_re = re.compile(r"^- \*\*([^*]+)\*\*")
    lines = solid_body.splitlines()
    entries = []   # type: List[tuple]
    current_name = None
    current_lines = []  # type: List[str]

    for line in lines:
        m = bullet_re.match(line)
        if m:
            if current_name is not None:
                entries.append((current_name, current_lines))
            current_name = m.group(1).strip()
            rest = line[m.end():].strip()
            rest = re.sub(r"^\s*—\s*", "", rest)
            current_lines = [rest] if rest else []
        else:
            if current_name is not None:
                current_lines.append(line)

    if current_name is not None:
        entries.append((current_name, current_lines))

    result = []
    for name, body_lines in entries:
        body = "\n".join(body_lines).strip()
        result.append({"tag_or_label": name, "body": body})
    return result


def _split_bullet_rules(heading: str, body_text: str) -> "List[Dict]":
    """Split §4.1 / §4.2 / §4.3 body into per-bullet rule entries.

    Each top-level bullet ``- **Label.** ...`` or ``- **Label** ...``
    becomes a rule entry.  Continuation lines (indented or blank) belong to
    the previous bullet.

    If no bullets are found, falls back to a single rule entry with
    ``tag_or_label = heading`` and ``body = body_text``.
    """
    bullet_re = re.compile(r"^- \*\*([^*]+?)[.\*]*\*\*")
    lines = body_text.splitlines()
    entries = []   # type: List[tuple]
    current_label = None
    current_lines = []  # type: List[str]

    for line in lines:
        m = bullet_re.match(line)
        if m:
            if current_label is not None:
                entries.append((current_label, current_lines))
            raw_label = m.group(1).strip().rstrip(".")
            current_label = raw_label
            rest = line[m.end():].strip().lstrip("* ")
            rest = re.sub(r"^\.?\s*", "", rest)
            current_lines = [rest] if rest else []
        else:
            if current_label is not None:
                current_lines.append(line)

    if current_label is not None:
        entries.append((current_label, current_lines))

    if not entries:
        return [{"tag_or_label": heading, "body": body_text}]

    result = []
    for label, body_lines in entries:
        body = "\n".join(body_lines).strip()
        result.append({"tag_or_label": label, "body": body})
    return result


def _extract_universal_rules_from_state(
    constitute_json_path: "Path",
) -> "Dict[str, Dict]":
    """Extract universal-section rules from a .devforge/constitute.json file.

    Reads the JSON state file at `constitute_json_path` and returns a dict
    keyed by §-prefixed section number for each universal section that has
    rules populated in the state.

    Return shape matches ``_parse_universal_blocks``::

        {
            "§3.5": {
                "heading": "<section title from state>",
                "rules": [
                    {"tag_or_label": "<rule tag>", "body": "<rule text>"},
                    ...
                ],
            },
            ...
        }

    Sources:
    - ``code_quality_standards``, ``workflow_rules``: sections with
      ``tag == "universal"``, keyed by ``§<section.number>``.  Only sections
      whose number matches ``_UNIVERSAL_SECTIONS`` (stripped of §) are included.
    - ``patterns_and_antipatterns``: ``always_universal`` → §4.1,
      ``never_universal`` → §4.2, ``prefer_universal`` → §4.3.  Rules in
      each bucket are included regardless of the rule's own ``tag`` field.

    Rule mapping: each ``{"tag": t, "text": txt}`` record maps to
    ``{"tag_or_label": t, "body": txt}``.

    Returns ``{}`` if the state file has no universal sections populated.
    Raises ``FileNotFoundError`` if the path does not exist.
    Raises ``json.JSONDecodeError`` if the file is malformed JSON.
    """
    text = Path(constitute_json_path).read_text(encoding="utf-8")
    state = json.loads(text)

    result = {}  # type: Dict[str, Dict]

    universal_numbers = {s[1:] for s in _UNIVERSAL_SECTIONS}

    for bucket_key in ("code_quality_standards", "workflow_rules"):
        for section in state.get(bucket_key, []):
            if section.get("tag") != "universal":
                continue
            number = section.get("number")
            if number is None or number not in universal_numbers:
                continue
            sect_key = "§{0}".format(number)
            title = section.get("title") or ""
            rules_raw = section.get("rules", [])
            rules = [
                {"tag_or_label": r.get("tag", ""), "body": r.get("text", "")}
                for r in rules_raw
            ]
            result[sect_key] = {"heading": title, "rules": rules}

    patterns = state.get("patterns_and_antipatterns", {})
    for bucket_name, sect_key in _PATTERNS_BUCKET_TO_SECTION.items():
        bucket_rules = patterns.get(bucket_name, [])
        if not bucket_rules:
            continue
        rules = [
            {"tag_or_label": r.get("tag", ""), "body": r.get("text", "")}
            for r in bucket_rules
        ]
        result[sect_key] = {"heading": bucket_name, "rules": rules}

    return result
