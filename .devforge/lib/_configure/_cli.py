"""argparse parser + dispatch + main entry for configure_helper.

Dispatcher-only. All cmd_* handler bodies live in sibling modules:
  _cmds_set    — all 28 cmd_set_* + cmd_reset + cmd_add_package_stack
                 + cmd_set_package_stacks
  _cmds_read   — read-init / read-docs / read-manifests / read-configs
  _cmds_render — render-config / substitute-templates / substitute-file / prune-agents
  _cmds_verify — verify / summary
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from ._cmds_read import (
    cmd_read_configs,
    cmd_read_docs,
    cmd_read_init,
    cmd_read_manifests,
)
from ._cmds_lint_ignore import cmd_lint_ignore
from ._cmds_render import (
    cmd_prune_agents,
    cmd_render_config,
    cmd_substitute_file,
    cmd_substitute_templates,
)
from ._cmds_set import (
    cmd_add_package_stack,
    cmd_set_package_stacks,
    cmd_reset,
    cmd_set_ac_runtime_api_base,
    cmd_set_ac_runtime_cli_command,
    cmd_set_ac_runtime_url,
    cmd_set_ac_verification_mode,
    cmd_set_ai_attribution,
    cmd_set_api_layers,
    cmd_set_architecture_details,
    cmd_set_architectures,
    cmd_set_build_commands,
    cmd_set_build_tools,
    cmd_set_claude_tier_do,
    cmd_set_claude_tier_think,
    cmd_set_claude_tier_verify,
    cmd_set_dev_commands,
    cmd_set_error_handlings,
    cmd_set_frameworks,
    cmd_set_languages,
    cmd_set_lint_commands,
    cmd_set_primary_language,
    cmd_set_project_description,
    cmd_set_project_name,
    cmd_set_project_natures,
    cmd_set_project_structure,
    cmd_set_project_type,
    cmd_set_test_commands,
    cmd_set_testings,
    cmd_set_type_check_commands,
    cmd_set_workflow_enforcement,
)
from ._cmds_verify import cmd_summary, cmd_verify


def build_parser() -> argparse.ArgumentParser:
    default_devforge_dir = os.environ.get("DEVFORGE_DIR", ".devforge")

    parser = argparse.ArgumentParser(
        prog="configure_helper",
        description="Compose the configuration state file for /configure.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=default_devforge_dir,
        dest="devforge_dir",
        help=(
            "Directory for devforge state files. "
            "Default: DEVFORGE_DIR env var, or '.devforge'."
        ),
    )
    parser.add_argument(
        "--install-root",
        dest="install_root",
        default=None,
        help=(
            "Install root (parent of devforge-dir). "
            "Default: parent of --devforge-dir. Used by read-docs + read-configs."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser("reset", help="Write a fresh defaults yaml.")
    sp.set_defaults(func=cmd_reset)

    sp = subparsers.add_parser(
        "read-init",
        help="Read .devforge/init.yaml and emit JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_init)

    sp = subparsers.add_parser(
        "read-docs",
        help="Parse Plan F docs sections and emit structured JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_docs)

    sp = subparsers.add_parser(
        "read-manifests",
        help="Read index.json and emit per-package script tables as JSON.",
    )
    sp.set_defaults(func=cmd_read_manifests)

    sp = subparsers.add_parser(
        "read-configs",
        help="Basename-match config files from index.json and emit JSON.",
    )
    sp.set_defaults(func=cmd_read_configs)

    # ------------------------------------------------------------------
    # Identity scalar setters.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser("set-project-name", help="Set project_name scalar.")
    sp.add_argument("value", help="Project name.")
    sp.set_defaults(func=cmd_set_project_name)

    sp = subparsers.add_parser("set-project-description", help="Set project_description scalar.")
    sp.add_argument("value", help="Project description.")
    sp.set_defaults(func=cmd_set_project_description)

    sp = subparsers.add_parser("set-project-type", help="Set project_type scalar.")
    sp.add_argument("value", help="Project type.")
    sp.set_defaults(func=cmd_set_project_type)

    # ------------------------------------------------------------------
    # Stack scalar setter.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser("set-primary-language", help="Set primary_language scalar.")
    sp.add_argument("value", help="Primary language.")
    sp.set_defaults(func=cmd_set_primary_language)

    # ------------------------------------------------------------------
    # Stack string_array setters (comma-sep; replace semantics).
    # ------------------------------------------------------------------

    sp = subparsers.add_parser("set-languages", help="Set languages (comma-sep list).")
    sp.add_argument("value", help="Comma-separated language list.")
    sp.set_defaults(func=cmd_set_languages)

    sp = subparsers.add_parser("set-frameworks", help="Set frameworks (comma-sep list).")
    sp.add_argument("value", help="Comma-separated framework list.")
    sp.set_defaults(func=cmd_set_frameworks)

    sp = subparsers.add_parser("set-architectures", help="Set architectures (comma-sep list).")
    sp.add_argument("value", help="Comma-separated architecture list.")
    sp.set_defaults(func=cmd_set_architectures)

    sp = subparsers.add_parser(
        "set-project-natures",
        help=(
            "Set project_natures (comma-sep list). Advisory vocabulary: "
            "web, backend, mobile, desktop, cli, library, plugin, data, ml, game, infra, docs."
        ),
    )
    sp.add_argument("value", help="Comma-separated project nature list.")
    sp.set_defaults(func=cmd_set_project_natures)

    sp = subparsers.add_parser("set-error-handlings", help="Set error_handlings (comma-sep list).")
    sp.add_argument("value", help="Comma-separated error-handling list.")
    sp.set_defaults(func=cmd_set_error_handlings)

    sp = subparsers.add_parser("set-api-layers", help="Set api_layers (comma-sep list).")
    sp.add_argument("value", help="Comma-separated API layer list.")
    sp.set_defaults(func=cmd_set_api_layers)

    sp = subparsers.add_parser("set-testings", help="Set testings (comma-sep list).")
    sp.add_argument("value", help="Comma-separated testing list.")
    sp.set_defaults(func=cmd_set_testings)

    sp = subparsers.add_parser("set-build-tools", help="Set build_tools (comma-sep list).")
    sp.add_argument("value", help="Comma-separated build-tool list.")
    sp.set_defaults(func=cmd_set_build_tools)

    # ------------------------------------------------------------------
    # Per-package string_array setters.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser("set-build-commands", help="Set build_commands (comma-sep list).")
    sp.add_argument("value", help="Comma-separated build command list.")
    sp.set_defaults(func=cmd_set_build_commands)

    sp = subparsers.add_parser(
        "set-type-check-commands", help="Set type_check_commands (comma-sep list)."
    )
    sp.add_argument("value", help="Comma-separated type-check command list.")
    sp.set_defaults(func=cmd_set_type_check_commands)

    sp = subparsers.add_parser("set-lint-commands", help="Set lint_commands (comma-sep list).")
    sp.add_argument("value", help="Comma-separated lint command list.")
    sp.set_defaults(func=cmd_set_lint_commands)

    sp = subparsers.add_parser("set-test-commands", help="Set test_commands (comma-sep list).")
    sp.add_argument("value", help="Comma-separated test command list.")
    sp.set_defaults(func=cmd_set_test_commands)

    # ------------------------------------------------------------------
    # Per-package record append setter.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser(
        "add-package-stack",
        help="Append a package_stack record. --path and --language required.",
    )
    sp.add_argument("--path", required=True, help="Package path.")
    sp.add_argument("--language", required=True, help="Package primary language.")
    sp.add_argument("--framework", default=None, help="Package framework (optional).")
    sp.add_argument("--build-tool", dest="build_tool", default=None, help="Package build tool (optional).")
    sp.add_argument("--build-command", dest="build_command", default=None, help="Package build command (optional).")
    sp.add_argument("--type-check-command", dest="type_check_command", default=None, help="Package type-check command (optional).")
    sp.add_argument("--lint-command", dest="lint_command", default=None, help="Package lint command (optional).")
    sp.add_argument("--test-command", dest="test_command", default=None, help="Package test command (optional).")
    sp.set_defaults(func=cmd_add_package_stack)

    sp = subparsers.add_parser(
        "set-package-stacks",
        help=(
            "Replace the whole package_stacks list from JSON on stdin. "
            "Input must be a JSON object: {\"package_stacks\": [...]}. "
            "Replace semantics: overwrites any prior list (use to recover from "
            "a corrupt/duplicate state). Each record must contain 'path' and "
            "'language' (required) and up to 6 optional nullable fields "
            "(framework, build_tool, build_command, type_check_command, "
            "lint_command, test_command). Unknown keys are rejected (exit 2)."
        ),
    )
    sp.set_defaults(func=cmd_set_package_stacks)

    # ------------------------------------------------------------------
    # Verbatim docs scalar setters (--text flag for multi-line content).
    # ------------------------------------------------------------------

    sp = subparsers.add_parser("set-project-structure", help="Set project_structure verbatim scalar.")
    sp.add_argument("--text", required=True, help="Verbatim project structure text.")
    sp.set_defaults(func=cmd_set_project_structure)

    sp = subparsers.add_parser("set-dev-commands", help="Set dev_commands verbatim scalar.")
    sp.add_argument("--text", required=True, help="Verbatim dev commands text.")
    sp.set_defaults(func=cmd_set_dev_commands)

    sp = subparsers.add_parser("set-architecture-details", help="Set architecture_details verbatim scalar.")
    sp.add_argument("--text", required=True, help="Verbatim architecture details text.")
    sp.set_defaults(func=cmd_set_architecture_details)

    # ------------------------------------------------------------------
    # Enum scalar setters.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser(
        "set-workflow-enforcement",
        help="Set workflow_enforcement enum (Strict | Moderate | Light).",
    )
    sp.add_argument("value", help="Enforcement level.")
    sp.set_defaults(func=cmd_set_workflow_enforcement)

    sp = subparsers.add_parser(
        "set-ai-attribution",
        help="Set ai_attribution enum (Yes | No).",
    )
    sp.add_argument("value", help="AI attribution setting.")
    sp.set_defaults(func=cmd_set_ai_attribution)

    sp = subparsers.add_parser(
        "set-claude-tier-think",
        help="Set claude_tier_think enum (Opus | Sonnet | Haiku | Other).",
    )
    sp.add_argument("value", help="Thinking tier.")
    sp.set_defaults(func=cmd_set_claude_tier_think)

    sp = subparsers.add_parser(
        "set-claude-tier-do",
        help="Set claude_tier_do enum (Opus | Sonnet | Haiku | Other).",
    )
    sp.add_argument("value", help="Doing tier.")
    sp.set_defaults(func=cmd_set_claude_tier_do)

    sp = subparsers.add_parser(
        "set-claude-tier-verify",
        help="Set claude_tier_verify enum (Opus | Sonnet | Haiku | Other).",
    )
    sp.add_argument("value", help="Verifying tier.")
    sp.set_defaults(func=cmd_set_claude_tier_verify)

    sp = subparsers.add_parser(
        "set-ac-verification-mode",
        help="Set ac_verification_mode enum (code-only | tests | runtime-assisted | off).",
    )
    sp.add_argument("value", help="AC verification mode.")
    sp.set_defaults(func=cmd_set_ac_verification_mode)

    # ------------------------------------------------------------------
    # AC runtime scalar setters.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser("set-ac-runtime-url", help="Set ac_runtime_url scalar.")
    sp.add_argument("value", help="AC runtime URL.")
    sp.set_defaults(func=cmd_set_ac_runtime_url)

    sp = subparsers.add_parser("set-ac-runtime-api-base", help="Set ac_runtime_api_base scalar.")
    sp.add_argument("value", help="AC runtime API base URL.")
    sp.set_defaults(func=cmd_set_ac_runtime_api_base)

    sp = subparsers.add_parser("set-ac-runtime-cli-command", help="Set ac_runtime_cli_command scalar.")
    sp.add_argument("value", help="AC runtime CLI command.")
    sp.set_defaults(func=cmd_set_ac_runtime_cli_command)

    # ------------------------------------------------------------------
    # Step 3: render-config / verify / summary.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser(
        "render-config",
        help=(
            "Read configure.yaml + init.yaml; derive AGENT_LIST from "
            ".claude/agents/*.md; write .devforge/project-config.json."
        ),
    )
    sp.set_defaults(func=cmd_render_config)

    sp = subparsers.add_parser(
        "verify",
        help=(
            "Cross-check configure.yaml + project-config.json. "
            "Exit 0 = ok; exit 2 = violations."
        ),
    )
    sp.set_defaults(func=cmd_verify)

    sp = subparsers.add_parser(
        "summary",
        help="Render the configure report to stdout. Read-only.",
    )
    sp.set_defaults(func=cmd_summary)

    # ------------------------------------------------------------------
    # Step 4: substitute-templates.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser(
        "substitute-templates",
        help=(
            "Substitute {{KEY}} placeholders in CLAUDE.md + .claude/agents/*.md. "
            "Reads project-config.json; writes files atomically. "
            "Exit 0 = all substituted; exit 1 = config missing; exit 2 = unknown placeholder."
        ),
    )
    sp.set_defaults(func=cmd_substitute_templates)

    sp = subparsers.add_parser(
        "substitute-file",
        help=(
            "Substitute {{KEY}} placeholders in a single arbitrary file in place. "
            "Reads project-config.json; writes atomically. "
            "Exit 0 = substituted; exit 1 = config or file missing/malformed; "
            "exit 2 = unknown placeholder (file unchanged)."
        ),
    )
    sp.add_argument(
        "--file",
        required=True,
        help="Path to the file to substitute in place.",
    )
    sp.set_defaults(func=cmd_substitute_file)

    # ------------------------------------------------------------------
    # Step 5a: prune-agents.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser(
        "prune-agents",
        help=(
            "Prune .claude/agents/*.md whose applies_to doesn't match project_natures. "
            "Without --apply: dry-run, JSON report to stdout. "
            "With --apply: deletes dropped files + JSON report to stdout. "
            "Exit 0 = success; exit 2 = project_natures unset."
        ),
    )
    sp.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually delete dropped agent files (default: dry-run).",
    )
    sp.set_defaults(func=cmd_prune_agents)

    # ------------------------------------------------------------------
    # Step 6: lint-ignore — exclude framework folders from consumer linters.
    # ------------------------------------------------------------------

    sp = subparsers.add_parser(
        "lint-ignore",
        help=(
            "Detect linter/formatter configs and compute framework-folder excludes. "
            "Without --apply: dry-run, JSON report to stdout. "
            "With --apply: writes auto-tier changes, leaves manual-tier as instructions. "
            "Exit 0 = report emitted."
        ),
    )
    sp.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually write the exclude entries (default: dry-run).",
    )
    sp.set_defaults(func=cmd_lint_ignore)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2

    # Resolve --install-root default (top-level flag, used by read-docs + read-configs).
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)

    return args.func(args)
