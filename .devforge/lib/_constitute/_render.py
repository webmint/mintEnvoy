"""Constitution.md renderer + atomic write + round-trip parser."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from ._state import _empty_patterns_section


_MODE_PRETTY = {
    "existing-codebase": "Existing Codebase",
    "greenfield": "Greenfield",
}

# Required top-level scalars for render (fields whose absence → exit 2).
_RENDER_REQUIRED_SCALARS = (
    "project_name",
    "generated_date",
    "last_updated",
    "mode",
)

# project_identity subfields required for render.
_IDENTITY_REQUIRED_SUBFIELDS = ("name", "type", "domain", "stack")


def _render_table(table: dict) -> str:
    """Render a table record as a GFM markdown table string.

    table shape: {columns: [str, ...], rows: [[str, ...], ...]}
    Returns a string ending in a newline. If columns is empty, returns "".
    """
    columns = table.get("columns", [])
    rows = table.get("rows", [])
    if not columns:
        return ""

    header = "| " + " | ".join(columns) + " |\n"
    sep = "|" + "|".join("-" * (len(c) + 2) if len(c) >= 3 else "----"
                         for c in columns) + "|\n"
    data_lines = []
    for row in rows:
        data_lines.append("| " + " | ".join(str(cell) for cell in row) + " |\n")
    return header + sep + "".join(data_lines)


def _render_code_example(ex: dict) -> str:
    """Render a code example record as a labelled fenced block.

    ex shape: {label, language, code, annotation}
    Format:
        **<label>** — <annotation>   (annotation only if non-null/non-empty)

        ```<language>
        <code>
        ```
    Returns a string. The fenced block is followed by a blank line.
    """
    label = ex.get("label", "EXAMPLE")
    language = ex.get("language", "")
    code = ex.get("code", "")
    annotation = ex.get("annotation")

    parts = []
    if annotation:
        parts.append("**{0}** — {1}\n".format(label, annotation))
    else:
        parts.append("**{0}**\n".format(label))
    parts.append("\n```{0}\n".format(language))
    code_body = code.rstrip("\n")
    parts.append(code_body + "\n")
    parts.append("```\n")
    return "".join(parts)


def _render_section_body(section: dict, include_tag_suffix: bool) -> str:
    """Render a single section record into markdown.

    Produces:
        ### <number> <title> [<tag>]      (tag suffix only when include_tag_suffix=True and tag non-null)
        [<description paragraph>]
        [<table(s)>]
        - [<rule.tag>] <rule.text>
        [<code_example(s)>]

    Returns a string. Always ends without a trailing newline (caller adds spacing).
    """
    number = section.get("number", "")
    title = section.get("title", "")
    tag = section.get("tag")
    description = section.get("description")
    rules = section.get("rules", [])
    tables = section.get("tables", [])
    code_examples = section.get("code_examples", [])

    lines = []
    if include_tag_suffix and tag:
        lines.append("### {0} {1} [{2}]\n".format(number, title, tag))
    else:
        lines.append("### {0} {1}\n".format(number, title))

    if description:
        lines.append("\n{0}\n".format(description))

    for table in tables:
        lines.append("\n")
        lines.append(_render_table(table))

    for rule in rules:
        rule_tag = rule.get("tag", "")
        rule_text = rule.get("text", "")
        lines.append("- [{0}] {1}\n".format(rule_tag, rule_text))

    for ex in code_examples:
        lines.append("\n")
        lines.append(_render_code_example(ex))

    return "".join(lines)


def _render_section_array(
    sections: List[dict],
    h2_title: str,
    intro_text: Optional[str],
    include_tag_suffix: bool,
) -> str:
    """Render a whole section_array bucket as a markdown H2 block.

    If sections is empty, renders:
        ## <h2_title>
        _(no rules defined)_

    intro_text (if non-None) is rendered as a paragraph between the H2 heading
    and the first section. Returns a string; caller adds surrounding --- separators.
    """
    lines = []
    lines.append("## {0}\n".format(h2_title))
    if intro_text:
        lines.append("\n{0}\n".format(intro_text))
    if not sections:
        lines.append("\n_(no rules defined)_\n")
    else:
        for section in sections:
            lines.append("\n")
            lines.append(_render_section_body(section, include_tag_suffix))
    return "".join(lines)


def _render_pattern_bucket(
    patterns_state: dict,
    bucket_key: str,
    heading: str,
) -> str:
    """Render one patterns_and_antipatterns bucket as a ### sub-section.

    Returns a string (heading + bullet list). If empty, renders heading +
    _(no rules defined)_ marker.
    """
    rules = patterns_state.get(bucket_key, [])
    lines = []
    lines.append("### {0}\n".format(heading))
    if not rules:
        lines.append("_(no rules defined)_\n")
    else:
        for rule in rules:
            rule_tag = rule.get("tag", "")
            rule_text = rule.get("text", "")
            lines.append("- [{0}] {1}\n".format(rule_tag, rule_text))
    return "".join(lines)


def _render_constitution(state: dict) -> str:
    """Render state dict into a constitution.md string.

    Returns the full file text. Raises ValueError with a message enumerating
    missing required fields if project_name, generated_date, last_updated,
    mode, or project_identity (with all 4 subfields) are None.
    """
    # --- Required field validation ---
    missing = []
    for field in _RENDER_REQUIRED_SCALARS:
        if state.get(field) is None:
            missing.append(field)
    identity = state.get("project_identity")
    if identity is None:
        missing.append("project_identity")
    else:
        for sub in _IDENTITY_REQUIRED_SUBFIELDS:
            if identity.get(sub) is None:
                missing.append("project_identity.{0}".format(sub))
    if missing:
        raise ValueError(
            "render: missing required fields: {0}".format(", ".join(missing))
        )

    mode = state["mode"]
    mode_pretty = _MODE_PRETTY.get(mode, mode)
    parts = []  # type: List[str]

    # --- Header ---
    parts.append("# Project Constitution — {0}\n".format(state["project_name"]))
    parts.append("\n")
    parts.append("Generated: {0}\n".format(state["generated_date"]))
    parts.append("Last updated: {0}\n".format(state["last_updated"]))
    parts.append("Mode: {0}\n".format(mode_pretty))
    parts.append("\n")
    parts.append(
        "> Sections marked `[universal]` are pre-populated with rules that apply"
        " to ALL projects.\n"
    )
    parts.append(
        "> Sections marked `[project-specific]` are populated by `/constitute`"
        " based on your codebase or interview answers.\n"
    )
    parts.append("\n---\n\n")

    # --- Section 1: Project Identity ---
    parts.append("## 1. Project Identity\n")
    parts.append("\n")
    parts.append("**Name**: {0}\n".format(identity["name"]))
    parts.append("**Type**: {0}\n".format(identity["type"]))
    parts.append("**Domain**: {0}\n".format(identity["domain"]))
    parts.append("**Stack**: {0}\n".format(identity["stack"]))
    parts.append("\n---\n\n")

    # --- Section 2: Architecture Rules ---
    arch_intro = (
        "These rules MUST be followed in every code change. Violating these"
        " rules requires explicit user approval."
    )
    parts.append(_render_section_array(
        state.get("architecture_rules", []),
        "2. Architecture Rules (NON-NEGOTIABLE)",
        arch_intro,
        include_tag_suffix=False,
    ))
    parts.append("\n---\n\n")

    # --- Section 3: Code Quality Standards ---
    parts.append(_render_section_array(
        state.get("code_quality_standards", []),
        "3. Code Quality Standards",
        None,
        include_tag_suffix=True,
    ))
    parts.append("\n---\n\n")

    # --- Section 4: Patterns & Anti-Patterns ---
    pat = state.get("patterns_and_antipatterns", _empty_patterns_section())
    parts.append("## 4. Patterns & Anti-Patterns\n")
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "always_universal", "Always Do (Universal)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "always_project_specific", "Always Do (Project-Specific)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "never_universal", "Never Do (Universal)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "never_project_specific", "Never Do (Project-Specific)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "prefer_universal", "Prefer (Universal)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "prefer_project_specific", "Prefer (Project-Specific)"))
    parts.append("\n---\n\n")

    # --- Section 5: Domain Rules ---
    parts.append(_render_section_array(
        state.get("domain_rules", []),
        "5. Domain Rules",
        None,
        include_tag_suffix=False,
    ))
    parts.append("\n---\n\n")

    # --- Section 6: Workflow Rules ---
    parts.append(_render_section_array(
        state.get("workflow_rules", []),
        "6. Workflow Rules",
        None,
        include_tag_suffix=False,
    ))

    # --- Section 7: Scaffolding Guide (greenfield only) ---
    scaffolding = state.get("scaffolding_guide")
    if mode == "greenfield" and scaffolding is not None:
        parts.append("\n---\n\n")
        parts.append("## 7. Scaffolding Guide [greenfield-only]\n")
        starter_dirs = scaffolding.get("starter_directories", [])
        if starter_dirs:
            parts.append("\n**Starter Directories**:\n")
            for d in starter_dirs:
                parts.append("- {0}\n".format(d))
        sample_files = scaffolding.get("sample_files", [])
        if sample_files:
            parts.append("\n**Sample Files**:\n")
            for sf in sample_files:
                sf_path = sf.get("path", "")
                sf_lang = sf.get("language", "")
                sf_content = sf.get("content", "")
                parts.append("\n#### {0}\n".format(sf_path))
                parts.append("```{0}\n".format(sf_lang))
                content_body = sf_content.rstrip("\n")
                parts.append(content_body + "\n")
                parts.append("```\n")

    # Ensure exactly one trailing newline.
    result = "".join(parts)
    return result.rstrip("\n") + "\n"


def _write_constitution_atomic(text: str, install_root: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write text to <install_root>/constitution.md.

    Uses tempfile.mkstemp in the same directory. flush + fsync + os.replace
    for durability. On failure, unlinks temp file and re-raises.
    """
    target = Path(install_root) / "constitution.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="constitution-",
        suffix=".md.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _parse_rendered_constitution(text: str) -> dict:
    """Minimal parser for round-trip identity check in verify.

    Extracts project_name and the number of top-level ## sections
    (H2 headings). Returns {"project_name": str | None, "section_count": int}.
    """
    project_name = None
    section_count = 0

    name_match = re.search(r"^# Project Constitution — (.+)$", text, re.MULTILINE)
    if name_match:
        project_name = name_match.group(1).strip()

    section_count = len(re.findall(r"^## ", text, re.MULTILINE))

    return {"project_name": project_name, "section_count": section_count}


def _expected_section_count(state: dict) -> int:
    """Return the expected number of H2 sections for round-trip identity.

    Sections 1-6 are always present. Section 7 (Scaffolding Guide) is
    present when mode==greenfield AND scaffolding_guide is non-null.
    """
    count = 6
    if state.get("mode") == "greenfield" and state.get("scaffolding_guide") is not None:
        count = 7
    return count
