"""_cmds_gate -- run-forcing-functions-gate verb for implement_helper.

After scope-aware verification and the autonomous review loop, this helper
invokes ``constitute_helper verify-<rule>`` for every rule that is enabled in
``.devforge/constitute.json`` and aggregates the results.

Algorithm
---------
1. Locate ``.devforge/constitute.json`` relative to --root (or use --config if
   provided).
2. Parse the ``forcing_functions`` dict.  For each rule with ``enabled: true``,
   map the rule config-key → verb name using the same RULE_TO_VERB table that
   ``constitute_helper list-forcing-functions --format verb`` uses:
     magic_enum_duplication         → verify-magic-enum
     cross_layer_imports            → verify-cross-layer-imports
     any_with_generated_available   → verify-any-leak
3. For each enabled rule, subprocess constitute_helper verify-<rule>
   --root <root> [--config <config>].  Locate constitute_helper as a sibling
   of the lib directory that contains this file:
     Path(__file__).resolve().parent.parent / "constitute_helper"
   This path resolves correctly in both the forge repo
   (src/devforge/lib/_implement/_cmds_gate.py → src/devforge/lib/)
   and in a consumer install (.devforge/lib/_implement/ → .devforge/lib/).
4. Collect each rule's exit code and stdout JSON.
5. Emit:
     {
       "gate": "forcing_functions",
       "rules_run": [...],            # verb names of rules that ran
       "rules_failed": [...],         # verb names of rules that exited non-zero
       "reports": {                   # rule verb → stdout text (may be empty)
         "verify-magic-enum": "...",
         ...
       },
       "aggregate_exit": 0 | 2
     }
6. Exit 0 if no enabled rule failed; exit 2 if any failed.
   If NO rules are enabled → exit 0 + empty rules_run.

Exit codes
----------
  0 -- all enabled rules pass (or no rules enabled)
  1 -- config I/O / parse error
  2 -- one or more enabled rules failed

Subprocess timeout: 120 s per constitute_helper invocation (same as _cmds_verify).

Stdlib only.  Python 3.8+.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1
EXIT_FINDINGS = 2

# Subprocess timeout per constitute_helper call (seconds).
_CMD_TIMEOUT = 120

# Path fragment for constitute.json inside the consumer devforge dir.
_CONSTITUTE_JSON = ".devforge/constitute.json"


def _get_rule_to_verb():
    # type: () -> Dict[str, str]
    """Return the authoritative rule-key → verb mapping.

    Imported lazily from _constitute._forcing_functions._setters so this
    module stays importable even before the _constitute package is on the
    path — and so there is a single source of truth.  Both packages live
    under the same lib/ directory in the forge repo and in consumer installs
    (.devforge/lib/), so the sibling import is always resolvable at runtime.
    """
    from _constitute._forcing_functions._setters import RULE_TO_VERB  # noqa: PLC0415
    return RULE_TO_VERB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _locate_constitute_helper():
    # type: () -> Path
    """Return the path to the constitute_helper POSIX launcher.

    Resolves to the parent of the _implement package directory, which is the
    lib directory containing all sibling helpers.

    In the forge repo:
        src/devforge/lib/_implement/_cmds_gate.py
        → parent.parent == src/devforge/lib/
        → src/devforge/lib/constitute_helper

    In a consumer install:
        .devforge/lib/_implement/_cmds_gate.py
        → .devforge/lib/constitute_helper
    """
    return Path(__file__).resolve().parent.parent / "constitute_helper"


def _load_constitute_json(config_path):
    # type: (Path) -> Tuple[Optional[dict], Optional[str]]
    """Read and parse constitute.json.  Returns (data, error_msg)."""
    if not config_path.exists():
        # Missing config is not an error — it means no rules configured.
        return {}, None
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, "run-forcing-functions-gate: cannot read {path}: {err}".format(
            path=config_path, err=exc
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, (
            "run-forcing-functions-gate: malformed JSON in {path}: {err}".format(
                path=config_path, err=exc
            )
        )
    if not isinstance(data, dict):
        return None, (
            "run-forcing-functions-gate: {path}: expected a JSON object".format(
                path=config_path
            )
        )
    return data, None


def _enabled_rules(forcing_functions):
    # type: (dict) -> Tuple[List[str], Optional[str]]
    """Return (enabled_rule_keys, error_msg).

    enabled_rule_keys lists rule config-keys that have enabled: true and
    whose verb is known in the authoritative RULE_TO_VERB mapping.

    If a rule key has enabled: true but is NOT in RULE_TO_VERB, this is
    treated as a gate error: the caller expressed intent to verify a rule
    the gate has no verb for.  Silently skipping would produce a false-pass
    guarantee.  Returns ([], error_msg) in that case.
    """
    rule_to_verb = _get_rule_to_verb()
    result = []  # type: List[str]
    for rule_key, block in forcing_functions.items():
        if not isinstance(block, dict):
            continue
        if not block.get("enabled", False):
            continue
        if rule_key not in rule_to_verb:
            return [], (
                "run-forcing-functions-gate: constitute.json enables rule "
                "{key!r} which is not known to this gate (no verb in "
                "RULE_TO_VERB); add the rule to constitute_helper or disable "
                "it".format(key=rule_key)
            )
        result.append(rule_key)
    return result, None


def _run_verify_verb(constitute_helper_path, verb, root, config_path):
    # type: (Path, str, str, Optional[str]) -> Tuple[int, str]
    """Invoke constitute_helper <verb> and return (exit_code, stdout_text).

    stderr is not captured — it flows through to the caller's terminal for
    human eyeballing (per _shared.emit_findings design: stderr is human,
    stdout JSON is machine).
    """
    cmd = [
        sys.executable,
        str(constitute_helper_path) + ".py",
        verb,
        "--root",
        root,
    ]
    if config_path:
        cmd += ["--config", config_path]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            # stderr intentionally not captured; flows to terminal.
            stderr=None,
            timeout=_CMD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return EXIT_FINDINGS, ""
    except OSError as exc:
        sys.stderr.write(
            "run-forcing-functions-gate: cannot execute {path}: {err}\n".format(
                path=constitute_helper_path, err=exc
            )
        )
        return EXIT_ERR, ""

    stdout_text = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    return proc.returncode, stdout_text


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_run_forcing_functions_gate(args):
    # type: (object) -> int
    """Handler for the ``run-forcing-functions-gate`` subcommand."""
    root = getattr(args, "root", None) or os.getcwd()
    config_arg = getattr(args, "config", None)

    # Resolve constitute.json path.
    if config_arg:
        config_path = Path(config_arg).resolve()
    else:
        config_path = Path(root).resolve() / ".devforge" / "constitute.json"

    # Load config.
    data, err = _load_constitute_json(config_path)
    if err:
        sys.stderr.write(err + "\n")
        return EXIT_ERR

    forcing_functions = data.get("forcing_functions") if data else None
    if not forcing_functions or not isinstance(forcing_functions, dict):
        # No forcing_functions block → exit 0, empty report.
        payload = {
            "gate": "forcing_functions",
            "rules_run": [],
            "rules_failed": [],
            "reports": {},
            "aggregate_exit": EXIT_OK,
        }
        sys.stdout.write(json.dumps(payload))
        sys.stdout.write("\n")
        return EXIT_OK

    # Collect enabled rules.
    enabled_rule_keys, enabled_err = _enabled_rules(forcing_functions)
    if enabled_err:
        sys.stderr.write(enabled_err + "\n")
        return EXIT_FINDINGS
    if not enabled_rule_keys:
        payload = {
            "gate": "forcing_functions",
            "rules_run": [],
            "rules_failed": [],
            "reports": {},
            "aggregate_exit": EXIT_OK,
        }
        sys.stdout.write(json.dumps(payload))
        sys.stdout.write("\n")
        return EXIT_OK

    # Locate the constitute_helper launcher.
    constitute_helper = _locate_constitute_helper()
    rule_to_verb = _get_rule_to_verb()

    rules_run = []   # type: List[str]
    rules_failed = []  # type: List[str]
    reports = {}  # type: Dict[str, str]

    for rule_key in enabled_rule_keys:
        verb = rule_to_verb[rule_key]
        exit_code, stdout_text = _run_verify_verb(
            constitute_helper,
            verb,
            str(root),
            config_arg,
        )
        rules_run.append(verb)
        reports[verb] = stdout_text
        if exit_code != EXIT_OK:
            rules_failed.append(verb)

    aggregate_exit = EXIT_FINDINGS if rules_failed else EXIT_OK

    payload = {
        "gate": "forcing_functions",
        "rules_run": rules_run,
        "rules_failed": rules_failed,
        "reports": reports,
        "aggregate_exit": aggregate_exit,
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n")
    return aggregate_exit


# ---------------------------------------------------------------------------
# Argparse registration (called from _cli.py)
# ---------------------------------------------------------------------------


def add_args_run_forcing_functions_gate(parser):
    # type: (object) -> None
    """Add arguments for run-forcing-functions-gate to the subparser."""
    parser.add_argument(
        "--root",
        default=None,
        metavar="PATH",
        help=(
            "Consumer project root directory (default: current working directory). "
            "Used to locate .devforge/constitute.json and passed to each "
            "constitute_helper verify-<rule> call."
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help=(
            "Explicit path to constitute.json. Overrides the default "
            "<root>/.devforge/constitute.json. "
            "Passed through to each constitute_helper verify-<rule> call."
        ),
    )
