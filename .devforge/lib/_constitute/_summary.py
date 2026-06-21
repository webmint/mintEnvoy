"""Deterministic constitute-helper summary renderer."""

from __future__ import annotations

from ._state import _empty_patterns_section


def _render_constitute_summary(state: dict) -> str:
    """Build the deterministic constitute summary string from state.

    Format:
        ## Constitute Helper Summary

        Project Name:        <value or '(unset)'>
        Generated:           <value or '(unset)'>
        Last Updated:        <value or '(unset)'>
        Mode:                <value or '(unset)'>

        Project Identity:
          Name:              <value or '(unset)'>
          ...

        Architecture Rules:  <N sections>
          ...

        ...

    Stable across re-runs (deterministic). Returns string ending in one newline.
    """
    def _val(v: object) -> str:
        if v is None:
            return "(unset)"
        return str(v)

    def _section_line(section: dict) -> str:
        num = section.get("number", "?")
        title = section.get("title", "(untitled)")
        r = len(section.get("rules", []))
        t = len(section.get("tables", []))
        c = len(section.get("code_examples", []))
        return "  {0} {1}: {2} rules, {3} tables, {4} code examples\n".format(
            num, title, r, t, c
        )

    lines = []
    lines.append("## Constitute Helper Summary\n")
    lines.append("\n")
    lines.append("Project Name:        {0}\n".format(_val(state.get("project_name"))))
    lines.append("Generated:           {0}\n".format(_val(state.get("generated_date"))))
    lines.append("Last Updated:        {0}\n".format(_val(state.get("last_updated"))))
    lines.append("Mode:                {0}\n".format(_val(state.get("mode"))))
    lines.append("\n")

    identity = state.get("project_identity")
    lines.append("Project Identity:\n")
    if identity is None:
        lines.append("  Name:              (unset)\n")
        lines.append("  Type:              (unset)\n")
        lines.append("  Domain:            (unset)\n")
        lines.append("  Stack:             (unset)\n")
    else:
        lines.append("  Name:              {0}\n".format(_val(identity.get("name"))))
        lines.append("  Type:              {0}\n".format(_val(identity.get("type"))))
        lines.append("  Domain:            {0}\n".format(_val(identity.get("domain"))))
        lines.append("  Stack:             {0}\n".format(_val(identity.get("stack"))))
    lines.append("\n")

    arch = state.get("architecture_rules", [])
    lines.append("Architecture Rules:  {0} sections\n".format(len(arch)))
    for section in arch:
        lines.append(_section_line(section))

    cqs = state.get("code_quality_standards", [])
    lines.append("Code Quality Standards:  {0} sections\n".format(len(cqs)))
    for section in cqs:
        lines.append(_section_line(section))

    pat = state.get("patterns_and_antipatterns", _empty_patterns_section())
    lines.append("Patterns & Anti-Patterns:\n")
    lines.append("  Always (Universal):         {0} rules\n".format(
        len(pat.get("always_universal", []))
    ))
    lines.append("  Always (Project-Specific):  {0} rules\n".format(
        len(pat.get("always_project_specific", []))
    ))
    lines.append("  Never (Universal):          {0} rules\n".format(
        len(pat.get("never_universal", []))
    ))
    lines.append("  Never (Project-Specific):   {0} rules\n".format(
        len(pat.get("never_project_specific", []))
    ))
    lines.append("  Prefer (Universal):         {0} rules\n".format(
        len(pat.get("prefer_universal", []))
    ))
    lines.append("  Prefer (Project-Specific):  {0} rules\n".format(
        len(pat.get("prefer_project_specific", []))
    ))
    lines.append("\n")

    domain = state.get("domain_rules", [])
    lines.append("Domain Rules:        {0} sections\n".format(len(domain)))
    for section in domain:
        lines.append(_section_line(section))

    workflow = state.get("workflow_rules", [])
    lines.append("Workflow Rules:      {0} sections\n".format(len(workflow)))
    for section in workflow:
        lines.append(_section_line(section))
    lines.append("\n")

    scaffolding = state.get("scaffolding_guide")
    if scaffolding is None:
        lines.append("Scaffolding Guide:   unset\n")
    else:
        lines.append("Scaffolding Guide:   set\n")
        starter_dirs = scaffolding.get("starter_directories", [])
        sample_files = scaffolding.get("sample_files", [])
        lines.append("  Starter Dirs:      {0}\n".format(len(starter_dirs)))
        lines.append("  Sample Files:      {0}\n".format(len(sample_files)))

    return "".join(lines)
