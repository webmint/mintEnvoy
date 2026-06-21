"""Read handlers: read-init / read-configure / read-docs / read-glossary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import configure_helper  # type: ignore  # noqa: E402
import init_helper  # type: ignore  # noqa: E402

from ._md_parsers import _parse_glossary_md
from ._validators import _die


def cmd_read_init(args: argparse.Namespace) -> int:
    """Read .devforge/init.yaml and emit JSON to stdout.

    Uses init_helper.parse_yaml so the real producer is the inverse.
    Exit 1 if file is missing or unreadable. Exit 2 if malformed yaml.
    """
    init_yaml_path = Path(args.devforge_dir) / init_helper.OUTPUT_FILE_NAME
    if not init_yaml_path.exists():
        return _die(
            "read-init: init.yaml not found at {0}".format(init_yaml_path)
        )
    try:
        text = init_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die("read-init: cannot read {0}: {1}".format(init_yaml_path, err))
    try:
        state = init_helper.parse_yaml(text)
    except init_helper.YamlParseError as err:
        return _die(
            "read-init: cannot parse {0}: {1}".format(init_yaml_path, err),
            code=2,
        )
    sys.stdout.write(json.dumps(state, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_read_configure(args: argparse.Namespace) -> int:
    """Read .devforge/configure.yaml and emit JSON to stdout.

    Uses configure_helper.parse_yaml so the real producer is the inverse.
    Exit 1 if file is missing or unreadable. Exit 2 if malformed yaml.
    """
    configure_yaml_path = Path(args.devforge_dir) / configure_helper.OUTPUT_FILE_NAME
    if not configure_yaml_path.exists():
        return _die(
            "read-configure: configure.yaml not found at {0}".format(
                configure_yaml_path
            )
        )
    try:
        text = configure_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-configure: cannot read {0}: {1}".format(configure_yaml_path, err)
        )
    try:
        state = configure_helper.parse_yaml(text)
    except configure_helper.YamlParseError as err:
        return _die(
            "read-configure: cannot parse {0}: {1}".format(configure_yaml_path, err),
            code=2,
        )
    sys.stdout.write(json.dumps(state, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_read_docs(args: argparse.Namespace) -> int:
    """Parse docs/overview.md + docs/architecture.md and emit JSON.

    Reuses configure_helper's section parsers (_parse_overview_md,
    _parse_architecture_md, _extract_section). Missing sections emit
    empty values (graceful). Exit 1 if either file is missing.
    """
    install_root = Path(args.install_root)
    overview_path = install_root / "docs" / "overview.md"
    arch_path = install_root / "docs" / "architecture.md"

    if not overview_path.exists():
        return _die(
            "read-docs: docs/overview.md not found at {0}".format(overview_path)
        )
    if not arch_path.exists():
        return _die(
            "read-docs: docs/architecture.md not found at {0}".format(arch_path)
        )

    try:
        overview_text = overview_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-docs: cannot read {0}: {1}".format(overview_path, err)
        )
    try:
        arch_text = arch_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-docs: cannot read {0}: {1}".format(arch_path, err)
        )

    try:
        overview_parsed = configure_helper._parse_overview_md(overview_text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            "constitute_helper read-docs: warning — overview parse error: {0}\n".format(exc)
        )
        overview_parsed = {}

    try:
        arch_parsed = configure_helper._parse_architecture_md(arch_text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            "constitute_helper read-docs: warning — architecture parse error: {0}\n".format(exc)
        )
        arch_parsed = {}

    output = {
        "overview": overview_parsed,
        "architecture": arch_parsed,
    }
    sys.stdout.write(json.dumps(output, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_read_glossary(args: argparse.Namespace) -> int:
    """Read docs/glossary.md and emit JSON list of term records.

    Each record: {term, definition, used_in, related}.
    Exit 1 if file is missing or unreadable. Exit 0 for empty file (empty list).
    """
    install_root = Path(args.install_root)
    glossary_path = install_root / "docs" / "glossary.md"

    if not glossary_path.exists():
        return _die(
            "read-glossary: docs/glossary.md not found at {0}".format(glossary_path)
        )
    try:
        text = glossary_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-glossary: cannot read {0}: {1}".format(glossary_path, err)
        )

    terms = _parse_glossary_md(text)
    sys.stdout.write(json.dumps(terms, indent=2))
    sys.stdout.write("\n")
    return 0
