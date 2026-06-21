"""Read handlers: read-init / read-docs / read-manifests / read-configs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import init_helper  # type: ignore  # noqa: E402

from ._hints import _derive_build_tool_hint, _derive_framework_hint
from ._md_parsers import _parse_architecture_md, _parse_overview_md


def cmd_read_init(args: argparse.Namespace) -> int:
    """Read .devforge/init.yaml and emit JSON to stdout.

    Uses init_helper.parse_yaml so the parser is the real producer.
    Exits 1 with a stderr message if init.yaml is missing or malformed.
    """
    init_yaml_path = Path(args.devforge_dir) / init_helper.OUTPUT_FILE_NAME
    if not init_yaml_path.exists():
        sys.stderr.write(
            "configure_helper read-init: init.yaml not found at {0}\n".format(
                init_yaml_path
            )
        )
        return 1
    try:
        text = init_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-init: cannot read {0}: {1}\n".format(
                init_yaml_path, err
            )
        )
        return 1
    try:
        state = init_helper.parse_yaml(text)
    except init_helper.YamlParseError as err:
        sys.stderr.write(
            "configure_helper read-init: cannot parse {0}: {1}\n".format(
                init_yaml_path, err
            )
        )
        return 1
    sys.stdout.write(json.dumps(state, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_read_docs(args: argparse.Namespace) -> int:
    """Parse Plan F sections from docs/overview.md + docs/architecture.md.

    Emits structured JSON to stdout. Exits 1 if either file is missing.
    Uses --install-root (default: parent of --devforge-dir).
    """
    install_root = Path(args.install_root)
    overview_path = install_root / "docs" / "overview.md"
    arch_path = install_root / "docs" / "architecture.md"

    if not overview_path.exists():
        sys.stderr.write(
            "configure_helper read-docs: docs/overview.md not found at {0}\n".format(
                overview_path
            )
        )
        return 1
    if not arch_path.exists():
        sys.stderr.write(
            "configure_helper read-docs: docs/architecture.md not found at {0}\n".format(
                arch_path
            )
        )
        return 1

    try:
        overview_text = overview_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-docs: cannot read {0}: {1}\n".format(
                overview_path, err
            )
        )
        return 1
    try:
        arch_text = arch_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-docs: cannot read {0}: {1}\n".format(
                arch_path, err
            )
        )
        return 1

    output = {
        "overview": _parse_overview_md(overview_text),
        "architecture": _parse_architecture_md(arch_text),
    }
    sys.stdout.write(json.dumps(output, indent=2))
    sys.stdout.write("\n")
    return 0


def cmd_read_manifests(args: argparse.Namespace) -> int:
    """Read .devforge/index.json and emit per-package script tables as JSON.

    Exits 1 if index.json is missing or unreadable.
    """
    index_path = Path(args.devforge_dir) / "index.json"
    if not index_path.exists():
        sys.stderr.write(
            "configure_helper read-manifests: index.json not found at {0}\n".format(
                index_path
            )
        )
        return 1
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-manifests: cannot read {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1
    try:
        index = json.loads(text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper read-manifests: cannot parse {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1

    packages_out = []
    raw_packages = index.get("packages", {})
    # Tolerate both shapes: dict-of-path->record (current /init-forge format
    # emitted by index_helper.py) and list-of-records (legacy/alternate
    # format). The dict-of-path is the one shipped by /init-forge today.
    if isinstance(raw_packages, dict):
        pkg_iter = [
            {"path": p, **(v if isinstance(v, dict) else {})}
            for p, v in raw_packages.items()
        ]
    elif isinstance(raw_packages, list):
        pkg_iter = raw_packages
    else:
        pkg_iter = []

    for pkg in pkg_iter:
        path = pkg.get("path", "")
        # Manifest filename: prefer "manifest", fall back to "manifest_file"
        # (index_helper.py emits "manifest_file").
        manifest = pkg.get("manifest") or pkg.get("manifest_file", "")
        # Scripts: prefer "manifest_scripts", fall back to "scripts"
        # (index_helper.py emits "scripts").
        scripts = pkg.get("manifest_scripts") or pkg.get("scripts") or {}
        # Dependencies: original code expected dict-shape split into
        # dependencies + dev_dependencies. index_helper.py emits a single
        # "manifest_deps" list of {name, version} records. Normalize the
        # list to a name→version dict and treat as combined dependencies
        # with empty dev_dependencies (build_tool_hint derivation walks
        # both, so the combine is safe).
        raw_deps = pkg.get("manifest_dependencies")
        raw_dev = pkg.get("manifest_dev_dependencies")
        if raw_deps is None and raw_dev is None:
            md = pkg.get("manifest_deps")
            if isinstance(md, list):
                deps = {}
                for entry in md:
                    if isinstance(entry, dict):
                        nm = entry.get("name")
                        if nm:
                            deps[nm] = entry.get("version", "")
                dev_deps = {}
            elif isinstance(md, dict):
                deps = md
                dev_deps = {}
            else:
                deps = {}
                dev_deps = {}
        else:
            deps = raw_deps or {}
            dev_deps = raw_dev or {}
        build_hint = _derive_build_tool_hint(deps, dev_deps)
        framework_hint = _derive_framework_hint(deps, dev_deps)
        packages_out.append({
            "path": path,
            "manifest": manifest,
            "scripts": scripts,
            "dependencies": deps,
            "dev_dependencies": dev_deps,
            "build_tool_hint": build_hint,
            "framework_hint": framework_hint,
        })

    sys.stdout.write(json.dumps({"packages": packages_out}, indent=2))
    sys.stdout.write("\n")
    return 0


# Fixed pattern set for config file basename matching.
_CONFIG_FILE_BASENAMES = {
    "vite.config.ts", "vite.config.js", "vite.config.mjs",
    "next.config.ts", "next.config.js", "next.config.mjs",
    "nuxt.config.ts", "nuxt.config.js",
    "webpack.config.ts", "webpack.config.js",
    "vitest.config.ts", "vitest.config.js",
    "jest.config.ts", "jest.config.js",
    ".env", ".env.local", ".env.development",
}

# Maximum bytes to read per config file (10 KB).
_CONFIG_FILE_MAX_BYTES = 10 * 1024


def cmd_read_configs(args: argparse.Namespace) -> int:
    """Basename-match config files from index.json; emit JSON.

    Reads .devforge/index.json, walks every package's files[], matches
    basenames against _CONFIG_FILE_BASENAMES. Reads matched files from
    <install_root>/<package_path>/<file>. Caps each file at 10 KB
    (truncated: true flag set when cap is hit).

    Exits 0 even if no matches found. Exits 1 only if index.json missing.
    """
    index_path = Path(args.devforge_dir) / "index.json"
    if not index_path.exists():
        sys.stderr.write(
            "configure_helper read-configs: index.json not found at {0}\n".format(
                index_path
            )
        )
        return 1
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-configs: cannot read {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1
    try:
        index = json.loads(text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper read-configs: cannot parse {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1

    install_root = Path(args.install_root)
    matched_files = []

    # Wrapper-mode awareness: in wrapper installs, source files live at
    # <install_root>/<project_root>/..., not <install_root>/.... index_helper
    # writes file paths relative to project_root, so abs_path construction
    # must prepend project_root when in wrapper mode. Read init.yaml to
    # discover workspace_mode + project_root; standalone defaults are
    # mode="standalone", project_root="." which collapse the prefix.
    project_root_prefix = ""
    init_path = Path(args.devforge_dir) / "init.yaml"
    if init_path.exists():
        try:
            init_state = init_helper.parse_yaml(
                init_path.read_text(encoding="utf-8")
            )
        except Exception:
            init_state = {}
        ws_mode = init_state.get("workspace_mode")
        proj_root = init_state.get("project_root") or "."
        if ws_mode == "wrapper" and proj_root and proj_root != ".":
            project_root_prefix = proj_root

    raw_packages = index.get("packages", {})
    if isinstance(raw_packages, dict):
        pkg_iter = [
            {"path": p, **(v if isinstance(v, dict) else {})}
            for p, v in raw_packages.items()
        ]
    elif isinstance(raw_packages, list):
        pkg_iter = raw_packages
    else:
        pkg_iter = []

    for pkg in pkg_iter:
        pkg_path = pkg.get("path", "")
        for file_rel in pkg.get("files", []):
            basename = Path(file_rel).name
            if basename not in _CONFIG_FILE_BASENAMES:
                continue
            # Construct absolute path: install_root / [project_root] / pkg_path / file_rel
            base = install_root / project_root_prefix if project_root_prefix else install_root
            if pkg_path and pkg_path != ".":
                abs_path = base / pkg_path / file_rel
            else:
                abs_path = base / file_rel
            # Relative path for output (package_path / file_rel; project_root
            # NOT prepended — the output path is project-root-relative to
            # match how index_helper emits paths in init.yaml-tracked refs).
            if pkg_path and pkg_path != ".":
                out_path = "{0}/{1}".format(pkg_path, file_rel)
            else:
                out_path = file_rel

            contents = ""
            truncated = False
            try:
                raw = abs_path.read_bytes()
                if len(raw) > _CONFIG_FILE_MAX_BYTES:
                    raw = raw[:_CONFIG_FILE_MAX_BYTES]
                    truncated = True
                contents = raw.decode("utf-8", errors="replace")
            except OSError:
                # File listed in index but not readable — skip.
                continue

            matched_files.append({
                "path": out_path,
                "basename": basename,
                "contents": contents,
                "truncated": truncated,
            })

    sys.stdout.write(json.dumps({"matched_files": matched_files}, indent=2))
    sys.stdout.write("\n")
    return 0
