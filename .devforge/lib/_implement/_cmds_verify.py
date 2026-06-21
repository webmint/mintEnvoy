"""_cmds_verify -- verify-touched verb for implement_helper.

Runs scope-aware type-check + lint + build + test over the files the agent
touched, and implements a bounded self-repair counter so the orchestrator
knows when to request a fix vs when to give up.

Algorithm
---------
1. Parse the touched-files list (--files, JSON array string).
2. Resolve workspace via resolve_workspace(--root): gives install_root,
   source_root, is_wrapper.  Config is loaded from install_root; commands
   run with cwd = source_root; touched files + PACKAGE_STACKS paths are
   all source-root-relative.
3. Load PACKAGE_STACKS + TYPE_CHECK_COMMANDS + LINT_COMMANDS + BUILD_COMMANDS
   + TEST_COMMANDS from .devforge/project-config.json (relative to install_root).
4. For every touched file: longest-path-prefix match against each package's
   `path` field.  Matching package → that package's `type_check_command`,
   `lint_command`, and `test_command`.  No match → primary-stack fallback
   (TYPE_CHECK_COMMANDS[0] / LINT_COMMANDS[0] / TEST_COMMANDS[0]).
5. Aggregate: de-duplicate identical commands so each runs exactly once (the
   same tsc invocation from two packages is not run twice).
6. Build: once per task at the end, de-dup across touched packages.
   Non-package files → BUILD_COMMANDS[0].
7. Test: per-package, de-duped, same collection logic as type-check/lint.
   Non-package files → TEST_COMMANDS[0].  Run AFTER build (fail-fast ordering:
   static checks → build → tests; a broken build surfaces first).
8. "N/A" commands are silently skipped (not a failure).  Commands are BARE
   (e.g. "npm run check", path ".") — NOT pre-prefixed with "cd SOURCE_ROOT &&".
   Run each command with cwd=source_root so the bare command works correctly.
9. Wrapper-isolation check (wrapper mode ONLY, ported from 1.x line 259):
   After the agent edits, scan source_root for forge artifacts that must NOT
   be there: .claude/, specs/, docs/overview.md, docs/architecture.md,
   constitution.md, CLAUDE.md, bugs/, research/, .mcp.json.
   If any exist inside source_root → report a verification FAILURE (the agent
   polluted the source tree).  This check is SKIPPED entirely in standalone
   mode — standalone's single repo legitimately contains .claude/, specs/, etc.
10. Self-repair counter (helper-owned, zero-escape-hatch):
    - --iteration N (the orchestrator increments it across repair attempts).
    - Run ALL commands.  If ALL pass → emit {status:"pass", ...}; exit 0.
    - If any fails AND N < SELF_REPAIR_CAP (3) →
        emit {status:"self_repair", iteration:N, failed_command, output}; exit 0.
        (The orchestrator re-runs the implementing agent then re-calls with N+1.)
    - If any fails AND N >= SELF_REPAIR_CAP →
        emit {status:"failed", failed_command, output}; EXIT_FINDINGS (exit 2).
    The helper owns the cap constant.  The orchestrator cannot extend past the
    cap; the helper simply escalates at N>=3.

Arguments (argparse):
  --files <json>      Required. JSON array of source-relative file paths
                      (output of capture-touched-files; always source-root-relative).
  --root  <path>      Optional. Install root; defaults to cwd.
                      (The install root contains .devforge/project-config.json.
                       source_root is resolved via PROJECT_ROOT from config.)
  --iteration N       Optional. Current self-repair iteration count. Default 0.

Emitted JSON (stdout):
  status:"pass"        → {status:"pass", commands_run:[...], build_commands_run:[...],
                           test_commands_run:[...]}
  status:"self_repair" → {status:"self_repair", iteration:N,
                           failed_command:"...", output:"..."}
  status:"failed"      → {status:"failed", failed_command:"...", output:"..."}
  status:"isolation_failure"
                       → {status:"isolation_failure", artifacts:[...]}  (wrapper mode only;
                          forge artifact detected inside source_root; exits EXIT_FINDINGS)
  status:"tooling_unavailable"
                       → {status:"tooling_unavailable", failed_command:"...", output:"..."}
                          Emitted when a configured command could not be EXECUTED (the binary
                          is missing from PATH), as distinct from a command that ran and found
                          real errors.  Triggered by: returncode==127 (POSIX "command not
                          found") OR output containing one of the anchored shell/OS signals:
                          "command not found" or
                          "not recognized as an internal or external command" (Windows cmd).
                          NOTE: ": not found" is intentionally excluded — that idiom appears
                          in real bundler/loader diagnostics (e.g. Webpack "Loader: not found
                          for .vue files") and would cause false-positive short-circuits for
                          genuine, agent-fixable config errors.  The rc==127 branch already
                          covers all true missing-binary cases on POSIX.
                          This status is TERMINAL — the helper short-circuits immediately
                          without running remaining commands and exits EXIT_FINDINGS (exit 2).
                          It does NOT self-repair: re-running the implementing agent cannot
                          install a missing binary; the human must fix the tooling config.

Exit codes:
  0 — pass or self_repair (orchestrator re-tries on self_repair).
  1 — configuration / I/O error (missing project-config.json, malformed JSON).
  2 — self-repair cap reached (status:"failed") OR wrapper-isolation pollution
      (status:"isolation_failure") OR missing binary (status:"tooling_unavailable");
      all three emit JSON to stdout before exiting.

PACKAGE_STACKS JSON shape (as produced by `configure_helper render-config`):
  Each record in project-config.json's "PACKAGE_STACKS" array:
    {
      "path": "services/api",           # path prefix RELATIVE TO source_root
      "language": "TypeScript",
      "framework": "Express",
      "build_tool": "tsc",
      "build_command": "npm run build",         # BARE command; may be null or "N/A"
      "type_check_command": "npx tsc --noEmit", # BARE command; may be null or "N/A"
      "lint_command": "npx eslint src/",        # BARE command; may be null or "N/A"
      "test_command": "npm test"                # BARE command; may be null or "N/A"
    }
  Primary-stack arrays at the top level of project-config.json:
    "TYPE_CHECK_COMMANDS": ["npx tsc --noEmit", ...]
    "LINT_COMMANDS": ["npx eslint .", ...]
    "BUILD_COMMANDS": ["npm run build", ...]
    "TEST_COMMANDS": ["npm test", ...]
  [0] of each array is the fallback for files outside any detected package.

Design notes:
- Longest-path-prefix match: sort packages by path length (desc); first match
  wins.  "services/api/users.py" → package path "services/api", not "services".
- Commands are BARE (e.g. "npm run check", path ".") — NOT pre-prefixed with
  "cd SOURCE_ROOT &&".  Each command is run with cwd=source_root so the bare
  command naturally resolves relative paths correctly.  shell=True is still
  used so commands with shell operators (&&, pipes) work without further
  processing.
- subprocess timeout: 120 s per command (reasonable for tsc/eslint/build).
  This is intentionally generous; short timeouts cause false self-repair cycles.
- All commands are captured (stdout+stderr combined to output) so the
  orchestrator can relay the failure text to the repairing agent.
- An empty touched-files list → no type-check/lint runs, build still runs once.
  This is the case when the agent made zero file changes (e.g., interrupted
  before writing, or a pure-config task handled by the orchestrator). The
  primary build runs as a final sanity check.
- Primary-stack fallback: if TYPE_CHECK_COMMANDS/LINT_COMMANDS/BUILD_COMMANDS
  are absent or empty in project-config.json, the fallback is silently skipped
  (treated as "N/A" — the project declared no primary-stack command).
- Wrapper-isolation check: only runs when workspace.is_wrapper is True.
  Standalone repos legitimately contain .claude/, specs/, CLAUDE.md, etc. —
  running the isolation check there would false-fail every task.

Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from _implement._workspace import resolve_workspace  # type: ignore[import]
from _shared.node_bin import node_bin_dirs as _node_bin_dirs  # type: ignore[import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1
EXIT_FINDINGS = 2

# The helper owns this cap; the orchestrator cannot extend it.
SELF_REPAIR_CAP = 3  # max self-repair iterations before escalating

_NA = "N/A"
_CMD_TIMEOUT = 120  # seconds per command

# Path to project-config.json inside .devforge/.
_CONFIG_FILENAME = "project-config.json"

# Forge artifacts that must NOT appear inside source_root in wrapper mode.
# If the agent wrote any of these into the source repo, that's a pollution failure.
# Check: path-relative entries checked as os.path.exists(source_root / entry).
ISOLATION_ARTIFACTS = (
    ".claude",
    "specs",
    "docs/overview.md",
    "docs/architecture.md",
    "constitution.md",
    "CLAUDE.md",
    "bugs",
    "research",
    ".mcp.json",
)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_project_config(root):
    # type: (str) -> dict
    """Load .devforge/project-config.json relative to root.

    Raises FileNotFoundError if the file is absent.
    Raises ValueError if the file is not valid JSON or not a JSON object.
    """
    config_path = os.path.join(root, ".devforge", _CONFIG_FILENAME)
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise FileNotFoundError(
            "project-config.json not found at: {0}".format(config_path)
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "project-config.json is not valid JSON: {0}".format(exc)
        )
    if not isinstance(data, dict):
        raise ValueError("project-config.json must be a JSON object, not {0}".format(
            type(data).__name__
        ))
    return data


# ---------------------------------------------------------------------------
# Longest-path-prefix matcher
# ---------------------------------------------------------------------------


def _match_package(file_path, package_stacks):
    # type: (str, List[dict]) -> Optional[dict]
    """Find the package whose path is the longest prefix of file_path.

    Packages are checked longest-path first; first match wins.
    Returns the matching package dict, or None if no package matches.

    Matching rule: package.path is a prefix of the file's directory when
    the file path starts with '<package_path>/' (slash-normalized).
    An exact path match (package.path == file_path) is also accepted.

    Example: file 'services/api/routes/users.ts', package path 'services/api'
    → matches because 'services/api/routes/users.ts' starts with 'services/api/'.
    """
    if not package_stacks:
        return None

    # Normalize the file path to forward slashes (git always emits forward slashes).
    norm_file = file_path.replace("\\", "/")

    # Sort by path length descending so the longest (most specific) prefix wins.
    sorted_stacks = sorted(
        package_stacks,
        key=lambda p: len((p.get("path") or "").strip()),
        reverse=True,
    )

    for pkg in sorted_stacks:
        pkg_path = (pkg.get("path") or "").strip().rstrip("/")
        if not pkg_path:
            continue
        norm_pkg = pkg_path.replace("\\", "/")
        # Match: file starts with '<pkg_path>/' OR file == pkg_path.
        if norm_file == norm_pkg or norm_file.startswith(norm_pkg + "/"):
            return pkg

    return None


# ---------------------------------------------------------------------------
# Command aggregation
# ---------------------------------------------------------------------------


def _collect_commands(touched_files, package_stacks, primary_type_check, primary_lint,
                      primary_test=None):
    # type: (List[str], List[dict], Optional[str], Optional[str], Optional[str]) -> Tuple[List[str], List[str], List[str]]
    """Build de-duplicated (type_check_commands, lint_commands, test_commands) for touched files.

    For each touched file: longest-prefix match → package commands.
    If no package matches → primary fallback.
    "N/A" commands and None values are excluded.
    Preserves first-seen order.

    Returns (type_check_cmds, lint_cmds, test_cmds) as three ordered de-duped lists.
    test_cmds is collected using the same per-package / primary-fallback logic as
    type_check_cmds and lint_cmds: pkg.get("test_command") for matched packages,
    primary_test for unmatched files.
    """
    tc_seen = []    # type: List[str]  (ordered, de-duped)
    lint_seen = []  # type: List[str]
    test_seen = []  # type: List[str]

    tc_set = set()    # type: Set[str]
    lint_set = set()  # type: Set[str]
    test_set = set()  # type: Set[str]

    for fpath in touched_files:
        pkg = _match_package(fpath, package_stacks)
        if pkg is not None:
            tc_cmd = pkg.get("type_check_command")
            lint_cmd = pkg.get("lint_command")
            test_cmd = pkg.get("test_command")
        else:
            tc_cmd = primary_type_check
            lint_cmd = primary_lint
            test_cmd = primary_test

        # Register type_check_command.
        if tc_cmd and tc_cmd != _NA and tc_cmd not in tc_set:
            tc_set.add(tc_cmd)
            tc_seen.append(tc_cmd)

        # Register lint_command.
        if lint_cmd and lint_cmd != _NA and lint_cmd not in lint_set:
            lint_set.add(lint_cmd)
            lint_seen.append(lint_cmd)

        # Register test_command.
        if test_cmd and test_cmd != _NA and test_cmd not in test_set:
            test_set.add(test_cmd)
            test_seen.append(test_cmd)

    return tc_seen, lint_seen, test_seen


def _collect_build_commands(touched_files, package_stacks, primary_build):
    # type: (List[str], List[dict], Optional[str]) -> List[str]
    """Build de-duplicated build_commands for touched files.

    One build command per touched package (de-duped).  Files outside any
    package contribute the primary build fallback.
    "N/A" commands and None values are excluded.
    """
    build_seen = []   # type: List[str]
    build_set = set()  # type: Set[str]

    # Track whether we have any non-package file (for primary fallback).
    need_primary = False

    for fpath in touched_files:
        pkg = _match_package(fpath, package_stacks)
        if pkg is not None:
            build_cmd = pkg.get("build_command")
            if build_cmd and build_cmd != _NA and build_cmd not in build_set:
                build_set.add(build_cmd)
                build_seen.append(build_cmd)
        else:
            need_primary = True

    # If any file fell outside a package, include the primary build fallback.
    if need_primary and primary_build and primary_build != _NA:
        if primary_build not in build_set:
            build_set.add(primary_build)
            build_seen.append(primary_build)

    # Edge case: empty touched_files — still run build once.
    if not touched_files and primary_build and primary_build != _NA:
        build_seen.append(primary_build)

    return build_seen


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


def _run_command(cmd, cwd, extra_paths=None):
    # type: (str, str, Optional[List[str]]) -> Tuple[int, str]
    """Run a shell command and return (returncode, combined_output).

    shell=True: required because stored commands may contain `cd X && ...`
    chains that the OS cannot exec directly.
    Output is stdout+stderr combined (the orchestrator relays this to the
    repairing agent; combining avoids ordering ambiguity).

    extra_paths: optional list of directory paths to prepend to PATH in the
    subprocess environment.  Used to expose `node_modules/.bin` directories
    so locally-installed tools (e.g. vue-tsc, eslint) resolve without
    requiring global installation.  os.environ is NEVER mutated; a copy is
    made.  When extra_paths is None or empty, env is unchanged (subprocess
    inherits os.environ as-is).
    """
    env = None
    if extra_paths:
        env = dict(os.environ)
        existing_path = env.get("PATH", "")
        env["PATH"] = os.pathsep.join(extra_paths) + (
            os.pathsep + existing_path if existing_path else ""
        )

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=_CMD_TIMEOUT,
            env=env,
        )
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired:
        return 1, "Command timed out after {0}s: {1}".format(_CMD_TIMEOUT, cmd)
    except OSError as exc:
        return 1, "OS error running command: {0}".format(exc)


# ---------------------------------------------------------------------------
# Tooling-unavailable classifier
# ---------------------------------------------------------------------------

# Anchored shell/OS messages that indicate a missing binary, not a code error.
# Each is a distinct idiom; together they cover bash/zsh/sh and Windows cmd.
# Deliberately NOT "not found" alone — that substring appears in TS diagnostics
# ("Cannot find module", "Cannot find name") and must NOT be matched.
# NOTE: ": not found" (sh/dash) is intentionally absent — it appears verbatim in
# real bundler/loader diagnostics (e.g. Webpack "Loader: not found for .vue files",
# Vite "Plugin: not found: @vitejs/plugin-vue") and would cause false-positive
# tooling_unavailable results for genuine, agent-fixable config errors.  The
# rc==127 check covers all true missing-binary cases on POSIX systems.
# All signals are stored lowercase; matched against output.lower() in
# _is_tooling_unavailable — case-insensitive comparison without repeated lower().
_TOOLING_UNAVAILABLE_SIGNALS = (
    "command not found",                                  # bash/zsh/sh generic
    "not recognized as an internal or external command",  # Windows cmd
)


def _is_tooling_unavailable(returncode, output):
    # type: (int, str) -> bool
    """Return True when a command could not be EXECUTED (binary missing), not when it ran and found errors.

    Classifies as tooling-unavailable when:
      - returncode == 127  (canonical POSIX "command not found"), OR
      - the combined output contains one of the anchored shell/OS signals
        (case-insensitive): "command not found" or
        "not recognized as an internal or external command" (Windows cmd).

    Deliberately rejects generic substrings like "not found" alone, and
    specifically excludes ": not found" (sh/dash idiom) because that phrase
    appears in real bundler/loader diagnostics (Webpack, Vite) that are
    genuine, agent-fixable config errors — misclassifying them as
    tooling-unavailable would wrongly short-circuit self-repair.
    True missing-binary cases on POSIX always produce rc==127, which is
    caught unconditionally above without any string matching.
    """
    if returncode == 127:
        return True
    lower_output = output.lower()
    for signal in _TOOLING_UNAVAILABLE_SIGNALS:
        if signal in lower_output:
            return True
    return False


# ---------------------------------------------------------------------------
# Wrapper-isolation check
# ---------------------------------------------------------------------------


def _check_wrapper_isolation(source_root):
    # type: (Path) -> List[str]
    """Scan source_root for forge artifacts that must NOT be there.

    Returns a list of relative artifact paths that were found.
    An empty list means the source tree is clean (no forge pollution).

    Called ONLY when workspace.is_wrapper is True.  In standalone mode,
    the source root IS the install root and legitimately contains .claude/,
    specs/, CLAUDE.md, etc. — do not call this function in standalone mode.
    """
    found = []
    for entry in ISOLATION_ARTIFACTS:
        candidate = source_root / entry
        if candidate.exists():
            found.append(entry)
    return found


# ---------------------------------------------------------------------------
# Public command
# ---------------------------------------------------------------------------


def cmd_verify_touched(args):
    # type: (object) -> int
    """Run scope-aware verification and emit a self-repair-aware JSON result."""
    install_root = args.root if args.root else os.getcwd()

    # --- Resolve workspace (single source of truth for repo targeting) ---
    workspace = resolve_workspace(install_root)
    # source_root: where commands run and where touched files live.
    # install_root: where project-config.json lives (inside .devforge/).
    source_root_str = str(workspace.source_root)

    # --- Parse --files argument ---
    try:
        touched_files = json.loads(args.files)
        if not isinstance(touched_files, list):
            raise ValueError("--files must be a JSON array")
        # Validate each element is a string.
        for item in touched_files:
            if not isinstance(item, str):
                raise ValueError(
                    "--files items must be strings, got: {0!r}".format(item)
                )
    except (json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write("verify-touched: invalid --files: {0}\n".format(exc))
        return EXIT_ERR

    # --- Parse --iteration argument ---
    iteration = args.iteration if args.iteration is not None else 0
    if iteration < 0:
        sys.stderr.write("verify-touched: --iteration must be >= 0\n")
        return EXIT_ERR

    # --- Load project config (from install_root, where .devforge/ lives) ---
    try:
        config = _load_project_config(str(workspace.install_root))
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write("verify-touched: {0}\n".format(exc))
        return EXIT_ERR

    package_stacks = config.get("PACKAGE_STACKS") or []
    if not isinstance(package_stacks, list):
        package_stacks = []

    # Primary-stack fallbacks: first element of each array (or None if absent).
    type_check_commands = config.get("TYPE_CHECK_COMMANDS") or []
    lint_commands = config.get("LINT_COMMANDS") or []
    build_commands = config.get("BUILD_COMMANDS") or []
    test_commands = config.get("TEST_COMMANDS") or []

    primary_type_check = type_check_commands[0] if type_check_commands else None
    primary_lint = lint_commands[0] if lint_commands else None
    primary_build = build_commands[0] if build_commands else None
    primary_test = test_commands[0] if test_commands else None

    # --- Wrapper-isolation check (wrapper mode ONLY) ---
    # Run BEFORE the type-check/lint/build commands so a pollution failure is
    # surfaced immediately, before burning time on further verification.
    # CRITICAL: skip this check entirely in standalone mode — the standalone
    # source_root IS the install root and legitimately contains .claude/, specs/,
    # CLAUDE.md, etc.  Running the check there would false-fail every task.
    if workspace.is_wrapper:
        polluted = _check_wrapper_isolation(workspace.source_root)
        if polluted:
            payload = {
                "status": "isolation_failure",
                "artifacts": polluted,
            }
            sys.stdout.write(json.dumps(payload))
            sys.stdout.write("\n")
            return EXIT_FINDINGS

    # --- Build command lists ---
    # Touched files and PACKAGE_STACKS paths are both source-root-relative.
    tc_cmds, lint_cmds, test_cmds = _collect_commands(
        touched_files, package_stacks, primary_type_check, primary_lint, primary_test
    )
    build_cmds = _collect_build_commands(touched_files, package_stacks, primary_build)

    # All commands to run: type-check, then lint, then build, then test.
    # Ordering rationale: fail fast on cheap static checks and build before
    # running the (typically slower) test suite.  A broken build surfaces first;
    # tests run only on a building tree.
    verify_cmds = tc_cmds + lint_cmds
    all_cmds = verify_cmds + build_cmds + test_cmds

    # --- Compute node_modules/.bin dirs for locally-installed JS/TS tools ---
    # Union the bin dirs for all packages that contributed commands, plus always
    # include the source-root-level hoisted bins.  This lets bare tool invocations
    # like "vue-tsc --noEmit" resolve when the binary is a devDependency rather
    # than a global install — matching npm's own upward-walk resolution order.
    # os.environ is NOT mutated; _run_command receives a copy with an augmented PATH.
    _pkg_paths_seen = set()  # type: Set[str]
    for fpath in touched_files:
        pkg = _match_package(fpath, package_stacks)
        if pkg is not None:
            _pkg_paths_seen.add((pkg.get("path") or "").strip())
    # Always include the source-root level (hoisted node_modules/.bin).
    _pkg_paths_seen.add("")

    _bin_dirs_ordered = []  # type: List[str]
    _bin_dirs_seen = set()  # type: Set[str]
    for _pkg_path in sorted(_pkg_paths_seen, key=len, reverse=True):
        for _d in _node_bin_dirs(source_root_str, _pkg_path):
            if _d not in _bin_dirs_seen:
                _bin_dirs_seen.add(_d)
                _bin_dirs_ordered.append(_d)

    # --- Run commands with cwd = source_root ---
    # Commands are BARE (e.g. "npm run check") — not pre-prefixed with
    # "cd SOURCE_ROOT &&".  Setting cwd=source_root is the correct way to
    # make them operate in the right directory.
    failed_command = None
    failed_output = None

    for cmd in all_cmds:
        rc, output = _run_command(cmd, source_root_str, extra_paths=_bin_dirs_ordered)
        if rc != 0:
            # Tooling-unavailable check comes FIRST — a missing binary cannot be
            # fixed by re-running the implementing agent, so skip self-repair entirely.
            if _is_tooling_unavailable(rc, output):
                payload = {
                    "status": "tooling_unavailable",
                    "failed_command": cmd,
                    "output": output,
                }
                sys.stdout.write(json.dumps(payload))
                sys.stdout.write("\n")
                return EXIT_FINDINGS
            failed_command = cmd
            failed_output = output
            break  # Stop at first failure; report it.

    # --- Emit result ---
    if failed_command is None:
        # All passed.
        payload = {
            "status": "pass",
            "commands_run": verify_cmds,
            "build_commands_run": build_cmds,
            "test_commands_run": test_cmds,
        }
        sys.stdout.write(json.dumps(payload))
        sys.stdout.write("\n")
        return EXIT_OK

    # A command failed.
    if iteration < SELF_REPAIR_CAP:
        # Self-repair: tell the orchestrator to fix and retry.
        payload = {
            "status": "self_repair",
            "iteration": iteration,
            "failed_command": failed_command,
            "output": failed_output,
        }
        sys.stdout.write(json.dumps(payload))
        sys.stdout.write("\n")
        return EXIT_OK
    else:
        # Cap reached: escalate.
        payload = {
            "status": "failed",
            "failed_command": failed_command,
            "output": failed_output,
        }
        sys.stdout.write(json.dumps(payload))
        sys.stdout.write("\n")
        return EXIT_FINDINGS


# ---------------------------------------------------------------------------
# Argparse registration (called from _cli.py)
# ---------------------------------------------------------------------------


def add_args_verify_touched(parser):
    # type: (object) -> None
    """Add arguments for verify-touched to the subparser."""
    parser.add_argument(
        "--files",
        required=True,
        help=(
            "JSON array string of touched file paths "
            "(output of capture-touched-files). "
            "Example: --files '[\"src/foo.ts\", \"src/bar.ts\"]'"
        ),
    )
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "Install root directory (contains .devforge/project-config.json). "
            "The source root (where commands run) is resolved from PROJECT_ROOT "
            "inside project-config.json.  Defaults to the current working directory."
        ),
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=0,
        help=(
            "Current self-repair iteration count (0-based). "
            "The orchestrator increments this across repair attempts. "
            "When iteration >= {cap}, a failing command causes exit 2 "
            "(cap reached; escalate to user).".format(cap=SELF_REPAIR_CAP)
        ),
    )
