"""Render handlers: render-config + substitute-templates + substitute-file + prune-agents."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import init_helper  # type: ignore  # noqa: E402

from ._md_parsers import _parse_agent_frontmatter
from ._render import (
    _build_project_config,
    _build_substitution_map,
    _decide_agent,
    _read_agent_list,
    _substitute_placeholders,
    _write_file_atomic,
    _write_json,
)
from ._state import _load
from ._yaml import YamlParseError


def cmd_render_config(args: argparse.Namespace) -> int:
    """Read configure.yaml + init.yaml; derive AGENT_LIST; write project-config.json.

    Output: <devforge_dir>/project-config.json with 37 keys (29 from
    configure.yaml + 5 from init.yaml + 3 derived). Atomic write via
    _write_json (mkstemp + fsync + os.replace).

    Exits 1 if init.yaml is missing or unreadable. Exits 1 if configure.yaml
    is unreadable (missing configure.yaml is fine — uses defaults).
    """
    devforge_dir = Path(args.devforge_dir)

    # Load init.yaml (required — it carries PROJECT_ROOT + WORKSPACE_MODE).
    init_yaml_path = devforge_dir / init_helper.OUTPUT_FILE_NAME
    if not init_yaml_path.exists():
        sys.stderr.write(
            "configure_helper render-config: init.yaml not found at {0}\n".format(
                init_yaml_path
            )
        )
        return 1
    try:
        init_text = init_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper render-config: cannot read {0}: {1}\n".format(
                init_yaml_path, err
            )
        )
        return 1
    try:
        init_state = init_helper.parse_yaml(init_text)
    except init_helper.YamlParseError as err:
        sys.stderr.write(
            "configure_helper render-config: cannot parse {0}: {1}\n".format(
                init_yaml_path, err
            )
        )
        return 1

    # Load configure.yaml (defaults if absent).
    try:
        cfg_state = _load(args.devforge_dir)
    except (OSError, YamlParseError) as err:
        sys.stderr.write(
            "configure_helper render-config: cannot load configure.yaml: {0}\n".format(err)
        )
        return 1

    # Derive AGENT_LIST from .claude/agents/*.md.
    install_root = Path(args.install_root)
    agent_list_str = _read_agent_list(install_root)

    # Build the config dict and write atomically.
    config = _build_project_config(cfg_state, init_state, agent_list_str)
    target = devforge_dir / "project-config.json"
    try:
        _write_json(config, target)
    except OSError as err:
        sys.stderr.write(
            "configure_helper render-config: cannot write {0}: {1}\n".format(target, err)
        )
        return 1
    return 0


def cmd_substitute_templates(args: argparse.Namespace) -> int:
    """Substitute {{KEY}} placeholders across CLAUDE.md, .claude/agents/*.md,
    and (when present) docs/overview.md + docs/architecture.md.

    Reads project-config.json from <devforge_dir>; reads init.yaml for
    packages_detected; builds substitution map; walks template list;
    substitutes per-file; writes atomically.  docs/ files are processed
    only when they exist on disk; their absence is not an error.

    Exit 0 = all templates substituted; no {{KEY}} markers remain.
    Exit 1 = project-config.json missing or malformed; init.yaml missing.
    Exit 2 = at least one template has unknown placeholder; stderr lists
            them per file. Failed files are NOT modified (atomic per-file).
    """
    devforge_dir = Path(args.devforge_dir)
    install_root = Path(args.install_root)

    # --- Load project-config.json ---
    config_path = devforge_dir / "project-config.json"
    if not config_path.exists():
        sys.stderr.write(
            "configure_helper substitute-templates: project-config.json not found at "
            "{0}\n".format(config_path)
        )
        return 1
    try:
        config_text = config_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper substitute-templates: cannot read {0}: {1}\n".format(
                config_path, err
            )
        )
        return 1
    try:
        project_config = json.loads(config_text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper substitute-templates: malformed project-config.json: "
            "{0}\n".format(err)
        )
        return 1

    # --- Load packages_detected from init.yaml ---
    init_yaml_path = devforge_dir / init_helper.OUTPUT_FILE_NAME
    packages_detected = []  # type: List[dict]
    if init_yaml_path.exists():
        try:
            init_text = init_yaml_path.read_text(encoding="utf-8")
            init_state = init_helper.parse_yaml(init_text)
            packages_detected = init_state.get("packages_detected") or []
        except (OSError, init_helper.YamlParseError):
            # init.yaml unreadable: PROJECT_PATHS falls back to empty.
            packages_detected = []

    # --- Build substitution map ---
    sub_map = _build_substitution_map(project_config, packages_detected)

    # --- Discover template list ---
    claude_md = install_root / "CLAUDE.md"
    if not claude_md.exists():
        sys.stderr.write(
            "configure_helper substitute-templates: CLAUDE.md not found at "
            "{0}\n".format(claude_md)
        )
        return 1

    agents_dir = install_root / ".claude" / "agents"
    agent_templates = []  # type: List[Path]
    if agents_dir.is_dir():
        try:
            agent_templates = sorted(
                p for p in agents_dir.iterdir()
                if p.is_file() and p.suffix == ".md"
            )
        except OSError:
            agent_templates = []
    else:
        sys.stderr.write(
            "configure_helper substitute-templates: .claude/agents/ not found at "
            "{0} — no agent templates to substitute\n".format(agents_dir)
        )

    docs_templates = []  # type: List[Path]
    for docs_name in ("overview.md", "architecture.md"):
        docs_file = install_root / "docs" / docs_name
        if docs_file.is_file():
            docs_templates.append(docs_file)

    templates = [claude_md] + agent_templates + docs_templates

    # --- Substitute per-file ---
    all_missing = {}  # type: Dict[str, List[str]]  # path → missing keys
    for tmpl in templates:
        try:
            original = tmpl.read_text(encoding="utf-8")
        except OSError as err:
            sys.stderr.write(
                "configure_helper substitute-templates: cannot read {0}: {1}\n".format(
                    tmpl, err
                )
            )
            return 1

        new_text, missing = _substitute_placeholders(original, sub_map)

        if missing:
            all_missing[str(tmpl)] = missing
            # Leave the file unchanged (atomic write skipped for this file).
            continue

        # Write atomically only when there are no unknown placeholders.
        try:
            _write_file_atomic(tmpl, new_text)
        except OSError as err:
            sys.stderr.write(
                "configure_helper substitute-templates: cannot write {0}: {1}\n".format(
                    tmpl, err
                )
            )
            return 1

    if all_missing:
        for path_str, keys in sorted(all_missing.items()):
            sys.stderr.write(
                "configure_helper substitute-templates: unknown placeholders in "
                "{0}: {1}\n".format(path_str, ", ".join(keys))
            )
        return 2

    return 0


def cmd_substitute_file(args: argparse.Namespace) -> int:
    """Substitute {{KEY}} placeholders in a single arbitrary file in place.

    Reads project-config.json from <devforge_dir>; reads init.yaml for
    packages_detected; builds substitution map; reads --file; substitutes;
    writes atomically.

    Exit 0 = file substituted (or had no placeholders).
    Exit 1 = project-config.json missing or malformed; --file unreadable.
    Exit 2 = file has unknown placeholder(s); file is NOT modified.
    """
    devforge_dir = Path(args.devforge_dir)

    # --- Load project-config.json ---
    config_path = devforge_dir / "project-config.json"
    if not config_path.exists():
        sys.stderr.write(
            "configure_helper substitute-file: project-config.json not found at "
            "{0}\n".format(config_path)
        )
        return 1
    try:
        config_text = config_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper substitute-file: cannot read {0}: {1}\n".format(
                config_path, err
            )
        )
        return 1
    try:
        project_config = json.loads(config_text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper substitute-file: malformed project-config.json: "
            "{0}\n".format(err)
        )
        return 1

    # --- Load packages_detected from init.yaml ---
    init_yaml_path = devforge_dir / init_helper.OUTPUT_FILE_NAME
    packages_detected = []  # type: List[dict]
    if init_yaml_path.exists():
        try:
            init_text = init_yaml_path.read_text(encoding="utf-8")
            init_state = init_helper.parse_yaml(init_text)
            packages_detected = init_state.get("packages_detected") or []
        except (OSError, init_helper.YamlParseError):
            packages_detected = []

    # --- Build substitution map ---
    sub_map = _build_substitution_map(project_config, packages_detected)

    # --- Read the target file ---
    target_path = Path(args.file)
    if not target_path.exists():
        sys.stderr.write(
            "configure_helper substitute-file: not found at {0}\n".format(target_path)
        )
        return 1
    if not target_path.is_file():
        sys.stderr.write(
            "configure_helper substitute-file: not a file: {0}\n".format(target_path)
        )
        return 1
    try:
        original = target_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper substitute-file: cannot read {0}: {1}\n".format(
                target_path, err
            )
        )
        return 1

    # --- Substitute placeholders ---
    new_text, missing = _substitute_placeholders(original, sub_map)

    if missing:
        sys.stderr.write(
            "configure_helper substitute-file: unknown placeholders in "
            "{0}: {1}\n".format(target_path, ", ".join(missing))
        )
        return 2

    # --- Write atomically ---
    try:
        _write_file_atomic(target_path, new_text)
    except OSError as err:
        sys.stderr.write(
            "configure_helper substitute-file: cannot write {0}: {1}\n".format(
                target_path, err
            )
        )
        return 1

    return 0


def cmd_prune_agents(args: argparse.Namespace) -> int:
    """Prune agent files whose applies_to doesn't overlap project_natures.

    Reads configure.yaml for project_natures. Walks .claude/agents/*.md.
    Parses applies_to frontmatter per file. Emits JSON decision report to
    stdout. With --apply, deletes 'dropped' files.

    Exit 0 = report emitted (with or without --apply).
    Exit 2 = project_natures unset in configure.yaml.

    JSON output shape:
        {
          "kept":  ["agent-a", "agent-b"],
          "dropped": ["agent-c"],
          "decisions": [
            {"name": "agent-a", "applies_to": ["all"], "status": "keep"},
            ...
          ]
        }
    """
    # Load configure.yaml and check project_natures.
    try:
        state = _load(args.devforge_dir)
    except (OSError, YamlParseError) as err:
        sys.stderr.write(
            "configure_helper prune-agents: cannot load configure.yaml: {0}\n".format(err)
        )
        return 1

    project_natures = state.get("project_natures") or []
    if not project_natures:
        sys.stderr.write(
            "configure_helper prune-agents: project_natures unset; "
            "complete /configure Phase 2 first\n"
        )
        return 2

    # Walk .claude/agents/*.md
    install_root = Path(args.install_root)
    agents_dir = install_root / ".claude" / "agents"

    kept = []    # type: List[str]
    dropped = [] # type: List[str]
    decisions = []  # type: List[dict]

    if agents_dir.is_dir():
        try:
            agent_files = sorted(
                p for p in agents_dir.iterdir()
                if p.is_file() and p.suffix == ".md"
            )
        except OSError as err:
            sys.stderr.write(
                "configure_helper prune-agents: cannot list {0}: {1}\n".format(
                    agents_dir, err
                )
            )
            return 1

        for agent_path in agent_files:
            name = agent_path.stem
            try:
                text = agent_path.read_text(encoding="utf-8")
            except OSError as err:
                sys.stderr.write(
                    "configure_helper prune-agents: cannot read {0}: {1}; keeping\n".format(
                        agent_path, err
                    )
                )
                kept.append(name)
                decisions.append({
                    "name": name,
                    "applies_to": None,
                    "status": "keep",
                })
                continue

            applies_to = _parse_agent_frontmatter(text)

            if applies_to is None:
                sys.stderr.write(
                    "configure_helper prune-agents: warning: {0} has missing or "
                    "unparseable applies_to frontmatter; keeping\n".format(agent_path.name)
                )

            status = _decide_agent(applies_to, project_natures, name)

            if status == "keep":
                kept.append(name)
            else:
                dropped.append(name)

            decisions.append({
                "name": name,
                "applies_to": applies_to,
                "status": status,
            })

    # With --apply, delete dropped files.
    if args.apply:
        for agent_path in (agents_dir / "{0}.md".format(n) for n in dropped):
            try:
                os.unlink(str(agent_path))
            except OSError as err:
                sys.stderr.write(
                    "configure_helper prune-agents: cannot delete {0}: {1}\n".format(
                        agent_path, err
                    )
                )
                return 1

    report = {
        "kept": kept,
        "dropped": dropped,
        "decisions": decisions,
    }
    sys.stdout.write(json.dumps(report, indent=2))
    sys.stdout.write("\n")
    return 0
