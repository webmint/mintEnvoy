"""Bullet / table / sub-section render helpers + JSON list decoder.

These functions transform structured entry lists (JSON-decoded by
`_decode_entry_list`) into markdown blocks (bullet lists, tables,
sub-sections). They are pure string-builders — no I/O, no state, no
argparse coupling. Consumed by handlers in `_cmds_package` and
`_cmds_project`.
"""

from __future__ import annotations

import json
import sys
from typing import Dict, List, Optional


# ── Bullet-list builders ───────────────────────────────────────────────────


def _render_concerns_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role[, cite]} → '- <name> — <role>; <cite>'."""
    lines: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        role = (e.get("role") or "").strip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        line = f"- {name}"
        if role:
            line += f" — {role}"
        if cite:
            line += f"; {cite}"
        lines.append(line)
    return "\n".join(lines)


def _render_layers_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role, cite} → '- <name> — <role>; <cite>'."""
    return _render_concerns_bullets(entries)


def _render_files_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role[, cite]} → '- <name> — <role>; <cite>'.

    Same shape as concerns; cite is the project-relative file path
    (e.g. <pkg>/src/<basename>) and is optional — basenames alone are
    self-locating since they live at the package's src/ root.
    """
    return _render_concerns_bullets(entries)


def _render_patterns_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, rule, cite} → '- <name> — <rule>; <cite>'."""
    lines: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        rule = (e.get("rule") or "").strip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        line = f"- {name}"
        if rule:
            line += f" — {rule}"
        if cite:
            line += f"; {cite}"
        lines.append(line)
    return "\n".join(lines)


def _render_subconcerns_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, purpose_summary, doc_path} →
    '- <name> — <purpose_summary> ([→](<doc_path>))'.

    Plan F 3a: parent concern doc lists each split sub_concern with a
    1-line summary + link to its child index.md. ALL THREE fields
    (name, purpose_summary, doc_path) are required — entries missing
    any of them are skipped silently. The 3a.5 validate-doc parser
    expects the full ``<name> — <summary> ([→](<path>))`` shape; partial
    bullets would fail that regex, so we don't emit them at all.
    """
    lines: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        summary = (e.get("purpose_summary") or "").strip()
        doc_path = (e.get("doc_path") or "").strip()
        if not (name and summary and doc_path):
            continue
        lines.append(f"- {name} — {summary} ([→]({doc_path}))")
    return "\n".join(lines)


# ── Track 4 Phase 1 — project-overview mechanical render helpers ───────────


def _render_tech_stack_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {layer, technology} → markdown table row."""
    lines = ["| Layer | Technology |", "|---|---|"]
    for e in entries:
        layer = (e.get("layer") or "").strip()
        tech = (e.get("technology") or "").strip()
        if not (layer and tech):
            continue
        lines.append(f"| {layer} | {tech} |")
    return "\n".join(lines)


def _render_key_commands_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {command, description} → markdown table row.

    Command cell wrapped in backticks for shell-style rendering. Description
    is empty-string-tolerant; absent description renders as empty cell.
    """
    lines = ["| Command | Description |", "|---|---|"]
    for e in entries:
        cmd = (e.get("command") or "").strip()
        desc = (e.get("description") or "").strip()
        if not cmd:
            continue
        lines.append(f"| `{cmd}` | {desc} |")
    return "\n".join(lines)


def _render_test_files_bullets(entries: List[Dict[str, str]]) -> str:
    """Each entry: {path[, description]} → '- `<path>` — <description>'."""
    lines: List[str] = []
    for e in entries:
        path = (e.get("path") or "").strip()
        desc = (e.get("description") or "").strip()
        if not path:
            continue
        line = f"- `{path}`"
        if desc:
            line += f" — {desc}"
        lines.append(line)
    return "\n".join(lines)


def _render_fenced_text(text: str, language: str = "text") -> str:
    """Wrap text in a fenced code block. Default language tag is `text`."""
    body = text.rstrip("\n")
    return f"```{language}\n{body}\n```"


# ── Track 4 Phase 2 — mixed mechanical+LLM render helpers ──────────────────


def _render_entry_points_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {label, path, purpose} → table row.

    Path cell wrapped in backticks. Skip rows missing label OR path; allow
    empty purpose (renders as empty cell).
    """
    lines = ["| Entry Point | Path | Purpose |", "|---|---|---|"]
    for e in entries:
        label = (e.get("label") or "").strip()
        path = (e.get("path") or "").strip()
        purpose = (e.get("purpose") or "").strip()
        if not (label and path):
            continue
        lines.append(f"| {label} | `{path}` | {purpose} |")
    return "\n".join(lines)


def _render_application_routes_table(entries: List[Dict[str, str]]) -> str:
    """Each entry: {path, component, description} → table row.

    Path + component cells in backticks. Skip rows missing path.
    """
    lines = ["| Route | Component | Description |", "|---|---|---|"]
    for e in entries:
        path = (e.get("path") or "").strip()
        component = (e.get("component") or "").strip()
        description = (e.get("description") or "").strip()
        if not path:
            continue
        component_cell = f"`{component}`" if component else ""
        lines.append(f"| `{path}` | {component_cell} | {description} |")
    return "\n".join(lines)


def _render_navigation_guards_list(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, role} → numbered list item.

    Format: `1. **<name>** — <role>`. The `**bold**` matches reference bar
    convention. Numbering reflects guard chain order from input.
    """
    lines: List[str] = []
    for i, e in enumerate(entries, start=1):
        name = (e.get("name") or "").strip()
        role = (e.get("role") or "").strip()
        if not name:
            continue
        line = f"{i}. **{name}**"
        if role:
            line += f" — {role}"
        lines.append(line)
    return "\n".join(lines)


def _render_module_map_sections(entries: Dict[str, List[Dict[str, str]]]) -> str:
    """Three sub-sections (Infrastructure / Core / Domain), each a Package table.

    Input dict: {"infrastructure": [...], "core": [...], "domain": [...]}.
    Each list entry: {name, purpose}. Sub-sections with empty lists are
    omitted entirely (cleaner render than empty headers).

    Sub-headings emit as `### Infrastructure Packages` etc., matching
    reference bar literal style.
    """
    section_order = (
        ("infrastructure", "Infrastructure Packages"),
        ("core", "Core Package"),
        ("domain", "Domain Packages"),
    )
    blocks: List[str] = []
    for key, heading in section_order:
        items = entries.get(key) or []
        if not items:
            continue
        block_lines = [f"### {heading}", "", "| Package | Purpose |", "|---|---|"]
        for item in items:
            name = (item.get("name") or "").strip()
            purpose = (item.get("purpose") or "").strip()
            if not name:
                continue
            block_lines.append(f"| `{name}` | {purpose} |")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


# ── Track 4 Phase 3 — architecture-tier render helpers ──────────────────────


def _render_arch_patterns_subsections(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, applies_in, rule, language, code_snippet, cite} →
    `### <name>` heading + applies-in line + rule prose + cite-back HTML
    comment + fenced code block.

    Skip entries missing `name`; allow any other field empty (renders that
    part as absent rather than failing). The cite-back HTML comment uses
    the format `<!-- <cite> -->` mirroring concern + package tier convention.
    """
    blocks: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        applies_in = (e.get("applies_in") or "").strip()
        rule = (e.get("rule") or "").strip()
        language = (e.get("language") or "").strip()
        snippet = (e.get("code_snippet") or "").rstrip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        block_lines = [f"### {name}"]
        if applies_in:
            block_lines.append("")
            block_lines.append(f"**Applies in**: {applies_in}")
        if rule:
            block_lines.append("")
            block_lines.append(rule)
        if snippet:
            block_lines.append("")
            if cite:
                block_lines.append(f"<!-- {cite} -->")
            fence_lang = language or "text"
            block_lines.append(f"```{fence_lang}")
            block_lines.append(snippet)
            block_lines.append("```")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_conventions_subsections(entries: Dict[str, List[str]]) -> str:
    """Render up to 6 sub-sections: Naming, File Organization, Import Style,
    Error Handling, Styling, State Management.

    Input dict: each key maps to list of bullet-point strings. Sub-sections
    with empty lists are omitted. Sub-headings use `**bold**` paragraph form
    (reference bar literal style: `**Naming**\\n- bullet\\n...`).
    """
    section_order = (
        ("naming", "Naming"),
        ("file_organization", "File Organization"),
        ("import_style", "Import Style"),
        ("error_handling", "Error Handling"),
        ("styling", "Styling"),
        ("state_management", "State Management"),
    )
    blocks: List[str] = []
    for key, heading in section_order:
        items = entries.get(key) or []
        if not items:
            continue
        block_lines = [f"**{heading}**"]
        for item in items:
            text = str(item).strip()
            if not text:
                continue
            block_lines.append(f"- {text}")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_cross_cuts_detailed_subsections(entries: List[Dict[str, str]]) -> str:
    """Each entry: {name, description, language, code_snippet, cite} →
    `### <name>` heading + description prose + cite-back HTML comment +
    fenced code block.

    Phase 3 enriched shape supersedes Phase 0 Cross-Cuts bullet list when
    the orchestrator wants per-cross-cut code samples + cite-backs. Skip
    entries missing `name`.
    """
    blocks: List[str] = []
    for e in entries:
        name = (e.get("name") or "").strip()
        description = (e.get("description") or "").strip()
        language = (e.get("language") or "").strip()
        snippet = (e.get("code_snippet") or "").rstrip()
        cite = (e.get("cite") or "").strip()
        if not name:
            continue
        block_lines = [f"### {name}"]
        if description:
            block_lines.append("")
            block_lines.append(description)
        if snippet:
            block_lines.append("")
            if cite:
                block_lines.append(f"<!-- {cite} -->")
            fence_lang = language or "text"
            block_lines.append(f"```{fence_lang}")
            block_lines.append(snippet)
            block_lines.append("```")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_dep_direction_rules_bullets(entries: List[str]) -> str:
    """Each entry is a bullet-point rule string. Skip empty strings."""
    lines: List[str] = []
    for entry in entries:
        text = str(entry).strip()
        if not text:
            continue
        lines.append(f"- {text}")
    return "\n".join(lines)


def _decode_entry_list(arg_value: str, name: str) -> Optional[List[Dict[str, str]]]:
    """Decode a JSON list-of-objects argument; return None on parse failure (caller exits)."""
    try:
        decoded = json.loads(arg_value)
    except json.JSONDecodeError as exc:
        print(f"--{name} must be valid JSON: {exc}", file=sys.stderr)
        return None
    if not isinstance(decoded, list):
        print(f"--{name} must decode to a JSON array", file=sys.stderr)
        return None
    out: List[Dict[str, str]] = []
    for entry in decoded:
        if isinstance(entry, dict):
            out.append({k: str(v) for k, v in entry.items()})
    return out
