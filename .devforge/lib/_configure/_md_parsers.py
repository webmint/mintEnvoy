"""Markdown parsing helpers for read-docs + agent frontmatter."""

from __future__ import annotations

import re
from typing import Dict, List, Optional


def _extract_section(md_text: str, heading: str) -> str:
    """Return body of '## <heading>' section from md_text.

    Body = lines AFTER the '## <heading>' line, UP TO (not including)
    the next '## ' heading or EOF. Preserves whitespace and fenced code
    blocks; a '## ' line INSIDE a fenced code block does NOT terminate
    the section (fence-aware). Returns empty string if heading not found.
    """
    target = "## {0}".format(heading)
    lines = md_text.splitlines(keepends=True)
    in_section = False
    in_fence = False
    body_lines = []
    for line in lines:
        rstripped = line.rstrip()
        if in_section:
            if rstripped.startswith("```"):
                in_fence = not in_fence
            if not in_fence and rstripped.startswith("## "):
                break
            body_lines.append(line)
        elif rstripped == target:
            in_section = True
    body = "".join(body_lines)
    # Strip leading/trailing blank lines but preserve internal structure.
    return body.strip()


def _parse_md_table(text: str) -> List[Dict[str, str]]:
    """Parse the first GitHub-style markdown table found in text.

    Returns a list of dicts keyed by header column names (lowercased,
    spaces replaced with underscores). Skips the alignment row (|---|---|).
    Returns [] if no table is found.
    """
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:]:
            # Check if the next line is an alignment row.
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if re.match(r"^\|[-| :]+\|$", next_stripped):
                    header_idx = i
                    break
    if header_idx is None:
        return []

    # Parse header.
    header_line = lines[header_idx].strip()
    headers = [
        col.strip().lower().replace(" ", "_")
        for col in header_line.strip("|").split("|")
    ]

    # Skip alignment row and parse data rows.
    records = []
    for i in range(header_idx + 2, len(lines)):
        row = lines[i].strip()
        if not row.startswith("|"):
            break
        cols = [col.strip() for col in row.strip("|").split("|")]
        # Pad or trim to match header count.
        while len(cols) < len(headers):
            cols.append("")
        record = {headers[j]: cols[j] for j in range(len(headers))}
        records.append(record)

    return records


def _parse_md_bullets(text: str) -> List[str]:
    """Parse bullet and numbered list items from text.

    Accepts '- ' prefix or '1. ' / 'N. ' numbered list. Returns flat list
    of stripped item texts. Returns [] if no list items found.
    """
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif re.match(r"^\d+\.\s", stripped):
            items.append(re.sub(r"^\d+\.\s+", "", stripped))
    return items


def _parse_module_map(text: str) -> dict:
    """Parse ### Infrastructure Packages / ### Core Package / ### Domain Packages sub-sections.

    Each sub-section contains a markdown table. Returns a dict with keys
    'infrastructure', 'core', 'domain' — only includes keys whose sub-sections
    are present and parse to non-empty tables.
    """
    result = {}
    buckets = {
        "infrastructure": "Infrastructure Packages",
        "core": "Core Package",
        "domain": "Domain Packages",
    }
    for key, heading in buckets.items():
        target = "### {0}".format(heading)
        lines = text.splitlines(keepends=True)
        in_sub = False
        sub_lines = []
        for line in lines:
            if in_sub:
                if line.startswith("### ") or line.startswith("## "):
                    break
                sub_lines.append(line)
            elif line.rstrip() == target:
                in_sub = True
        if sub_lines:
            sub_text = "".join(sub_lines)
            rows = _parse_md_table(sub_text)
            if rows:
                result[key] = rows
    return result


def _parse_patterns(text: str) -> List[dict]:
    """Parse ### <name> sub-sections from text.

    Each sub-section may contain:
    - **Applies in**: <text>
    - Prose paragraphs
    - Fenced code blocks (``` ... ```)

    Returns one record per pattern with keys:
      name, applies_in, snippet_lang, snippet (empty string if no code block).
    """
    patterns = []
    lines = text.splitlines(keepends=True)
    current_name = None
    current_lines = []

    def _flush():
        if current_name is None:
            return
        body = "".join(current_lines).strip()
        applies_in = ""
        m = re.search(r"\*\*Applies in\*\*:\s*(.+)", body)
        if m:
            applies_in = m.group(1).strip()
        snippet_lang = ""
        snippet = ""
        fence_m = re.search(r"```(\w*)\n(.*?)```", body, re.DOTALL)
        if fence_m:
            snippet_lang = fence_m.group(1).strip()
            snippet = fence_m.group(2).rstrip()
        patterns.append({
            "name": current_name,
            "applies_in": applies_in,
            "snippet_lang": snippet_lang,
            "snippet": snippet,
        })

    for line in lines:
        if line.startswith("### "):
            _flush()
            current_name = line[4:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    _flush()
    return patterns


def _parse_overview_md(md_text: str) -> dict:
    """Parse docs/overview.md into a structured dict.

    Extracts all Plan F sections. Missing sections emit empty values.
    """
    purpose = _extract_section(md_text, "Purpose")
    tech_stack_body = _extract_section(md_text, "Tech Stack")
    tech_stack = _parse_md_table(tech_stack_body)
    project_structure = _extract_section(md_text, "Project Structure")
    entry_points_body = _extract_section(md_text, "Entry Points")
    entry_points = _parse_md_table(entry_points_body)
    key_commands_body = _extract_section(md_text, "Key Commands")
    key_commands = _parse_md_table(key_commands_body)
    module_map_body = _extract_section(md_text, "Module Map")
    module_map = _parse_module_map(module_map_body)
    cross_module_dependencies = _extract_section(md_text, "Cross-Module Dependencies")
    app_routes_body = _extract_section(md_text, "Application Routes")
    application_routes = _parse_md_table(app_routes_body)
    nav_guards_body = _extract_section(md_text, "Navigation Guards")
    navigation_guards = _parse_md_bullets(nav_guards_body)
    test_files_body = _extract_section(md_text, "Test Files")
    test_files = _parse_md_bullets(test_files_body)
    packages_body = _extract_section(md_text, "Packages")
    packages = _parse_md_bullets(packages_body)

    return {
        "purpose": purpose,
        "tech_stack": tech_stack,
        "project_structure": project_structure,
        "entry_points": entry_points,
        "key_commands": key_commands,
        "module_map": module_map,
        "cross_module_dependencies": cross_module_dependencies,
        "application_routes": application_routes,
        "navigation_guards": navigation_guards,
        "test_files": test_files,
        "packages": packages,
    }


def _parse_architecture_md(md_text: str) -> dict:
    """Parse docs/architecture.md into a structured dict.

    Extracts all Plan F sections. Missing sections emit empty values.
    """
    architecture_overview = _extract_section(md_text, "Architecture Overview")
    module_structure = _extract_section(md_text, "Module / Package Structure")
    if not module_structure:
        module_structure = _extract_section(md_text, "Module Structure")
    patterns_body = _extract_section(md_text, "Patterns")
    patterns = _parse_patterns(patterns_body)
    conventions = _extract_section(md_text, "Conventions")
    layers_body = _extract_section(md_text, "Layers")
    layers = _parse_md_bullets(layers_body)
    cross_cuts_body = _extract_section(md_text, "Cross-Cuts")
    cross_cuts = _parse_md_bullets(cross_cuts_body)
    dep_rules_body = _extract_section(md_text, "Dependency Direction Rules")
    dependency_direction_rules = _parse_md_bullets(dep_rules_body)
    dependency_overview = _extract_section(md_text, "Dependency Overview")

    return {
        "architecture_overview": architecture_overview,
        "module_structure": module_structure,
        "patterns": patterns,
        "conventions": conventions,
        "layers": layers,
        "cross_cuts": cross_cuts,
        "dependency_direction_rules": dependency_direction_rules,
        "dependency_overview": dependency_overview,
    }


def _parse_agent_frontmatter(text: str) -> Optional[List[str]]:
    """Parse the applies_to field from an agent file's YAML frontmatter.

    Two frontmatter forms are tolerated (parser tries both):

    1. SOURCE form (`src/agents/*.md`) — fenced YAML block:

           ```yaml
           name: foo
           applies_to: ["web", "backend"]
           ```

    2. INSTALLED form (`<install_root>/.claude/agents/*.md`) — Claude
       Code native triple-dash delimited:

           ---
           name: foo
           applies_to: ["web", "backend"]
           ---

    The installed form is what prune-agents actually walks at runtime
    (helper consumes the deployed agent files, not the source). Both
    forms must parse identically; a future refactor that moves source
    to triple-dash form would not require a parser change.

    Returns the list of applies_to strings, or None if frontmatter is
    absent or applies_to cannot be parsed. Caller interprets None as
    "missing frontmatter → KEEP (conservative default)".

    Parser only supports the bracketed list form ["a", "b"] (as emitted
    by the agent template generator). Does NOT support YAML block sequences
    since no current agent file uses that form.
    """
    lines = text.splitlines()

    # Find opening fence — either ```yaml/```yml OR --- (Claude native form).
    # Allow blank lines before the opener.
    fence_start = None
    fence_kind = None  # "yaml" → close on ```; "dash" → close on ---
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "":
            continue
        if stripped in ("```yaml", "```yml"):
            fence_start = i
            fence_kind = "yaml"
            break
        if stripped == "---":
            fence_start = i
            fence_kind = "dash"
            break
        # First non-blank line that is NOT an opening fence → no frontmatter.
        break

    if fence_start is None:
        return None

    # Collect lines until closing fence.
    closer = "```" if fence_kind == "yaml" else "---"
    fence_end = None
    for i in range(fence_start + 1, len(lines)):
        if lines[i].strip() == closer:
            fence_end = i
            break

    if fence_end is None:
        # Unclosed fence → treat as missing frontmatter.
        return None

    # Parse key: value pairs within the fence for applies_to.
    applies_to = None
    for line in lines[fence_start + 1:fence_end]:
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, _, rest = stripped.partition(":")
        key = key.strip()
        if key != "applies_to":
            continue
        rest = rest.strip()
        # Expected form: ["a", "b"] or ['a', 'b'] or ["all"]
        # Strip outer brackets.
        if not (rest.startswith("[") and rest.endswith("]")):
            # Cannot parse → return None to trigger KEEP (conservative).
            return None
        inner = rest[1:-1].strip()
        if inner == "":
            applies_to = []
        else:
            items = []
            for token in inner.split(","):
                token = token.strip()
                # Strip surrounding quotes (double or single).
                if len(token) >= 2 and token[0] in ('"', "'") and token[-1] == token[0]:
                    token = token[1:-1]
                if token:
                    items.append(token)
            applies_to = items
        break

    return applies_to
