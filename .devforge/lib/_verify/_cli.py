"""argparse parser + dispatch + main entry for verify_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 1 (scaffold) ships 2 verbs:
  check-status-and-flip  — read or update per-feature verify session state
  preflight              — gate on setup-chain artefacts + constitution check

Extension point for later phases: append to _SUBCOMMAND_REGISTRY and add
the corresponding argument block in _register_subcommands's elif chain.

Phase 2 ships input verbs (AC parsing, scope, review-findings reading):
  resolve-feature-scope    — resolve assembled-feature diff + emit scope JSON (Phase 2)
  read-ac-config           — read AC config keys from project-config.json (Phase 2)
  parse-acs                — parse spec AC checkboxes into structured list (Phase 2)
  read-review-findings     — parse specs/<feature>/review.md into folded findings (Phase 2)

Phase 4 ships AC-result merge + hygiene check verbs:
  merge-ac-results    — merge the ac-verifier agent's per-AC Results table
                        into the parse-acs structured list (Phase 4).
  check-hygiene       — flag scope-creep + leftover artifacts across the
                        assembled diff (Phase 4).

Phase 5 ships verdict computation + report + spec-flip + bug-filing verbs:
  compute-verdict       — deterministic APPROVED/NEEDS WORK/REJECTED (Phase 5).
  render-report         — write specs/[feature]/verification.md (Phase 5).
  render-inline-summary — count-first console block (Phase 5).
  flip-spec-status      — task cross-check + flip spec Complete + tick ACs (Phase 5).
  file-bugs             — write bugs/NNN-*.md in storage-rules.md format (Phase 5).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_check_status_and_flip(args: argparse.Namespace) -> int:
    """Read current verify state, optionally flip phase/status, emit JSON.

    Without --to: read current state (empty VerifyState if none) and print.
    With --to: call flip_phase, print resulting state.
    Returns 0 on success, 1 on I/O error, 2 on ValueError (empty --to).
    """
    from ._state import VerifyState, flip_phase, read_state, state_path

    feature_dir = getattr(args, "feature_dir", ".") or "."
    to_phase = getattr(args, "to", None)
    to_status = getattr(args, "status", None)
    verdict = getattr(args, "verdict", None)

    sp = state_path(feature_dir)

    if to_phase is None:
        # Read-only mode.
        state = read_state(sp)
        if state is None:
            state = VerifyState()
        sys.stdout.write(
            json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
        )
        return 0

    # Flip mode.
    try:
        state = flip_phase(sp, to_phase, to_status, verdict=verdict)
    except ValueError as exc:
        sys.stderr.write(
            "verify_helper check-status-and-flip: {0}\n".format(exc)
        )
        return 2
    except OSError as exc:
        sys.stderr.write(
            "verify_helper check-status-and-flip: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(
        json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
    )
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """Check setup-chain artefacts, constitution-populated guard, Source-Root.

    Always emits JSON to stdout before any non-zero exit.

    Returns:
      0 — all checks pass (setup chain ok, constitution present + populated)
      2 — missing setup-chain artefact (including constitution.md, which is
          entry #1 in _SETUP_CHAIN_ARTEFACTS), or unpopulated sentinel found
          (user-facing message to stderr)
    """
    from ._preflight import preflight_context

    workspace_root = getattr(args, "workspace_root", ".") or "."

    # preflight_context never raises — it wraps every file read in its own
    # try/except OSError: pass (see _preflight.py docstring).
    result = preflight_context(workspace_root)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    # Gate: missing setup-chain artefacts → exit 2.
    # constitution.md is entry #1 in _SETUP_CHAIN_ARTEFACTS, so its absence
    # is already caught here — no separate constitution_present gate needed.
    if not result["setup_chain_ok"]:
        missing = result.get("missing_artefacts", [])
        sys.stderr.write(
            "verify_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /init-forge → /generate-docs → /configure → /constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    # Gate: constitution unpopulated → exit 2.
    if not result["constitution_populated"]:
        sys.stderr.write(
            "verify_helper preflight: constitution.md contains an unpopulated "
            "sentinel. Run /constitute to populate it before running /verify.\n"
        )
        return 2

    return 0


# ---------------------------------------------------------------------------
# Phase 2 handler: resolve-feature-scope
# ---------------------------------------------------------------------------


def cmd_resolve_feature_scope(args):
    # type: (argparse.Namespace) -> int
    """CLI handler for the resolve-feature-scope verb.

    Mirrors _review._scope.cmd_resolve_feature_scope but passes
    heading_label="Verification Scope" to distinguish the scope block
    output from /review's "Review Scope" banner.

    Emits JSON on stdout on success; error message on stderr + exit 2 on failure.

    Returns:
      0 — success (files list may be empty — HEAD == merge-base is valid)
      2 — user error (not a git repo, bad ref, no auto-detectable base, etc.)
    """
    from _shared.feature_scope import resolve_feature_scope  # type: ignore[import]

    feature_dir = getattr(args, "feature", ".") or "."
    source_root = getattr(args, "source_root", None) or os.getcwd()
    install_root = getattr(args, "install_root", None)
    base = getattr(args, "base", None)

    source_root = os.path.realpath(source_root)

    if install_root:
        install_root = os.path.realpath(install_root)
    else:
        install_root = source_root

    result, error = resolve_feature_scope(
        feature_dir=feature_dir,
        source_root=source_root,
        install_root=install_root,
        base=base,
        heading_label="Verification Scope",
    )

    if error is not None:
        sys.stderr.write(
            "verify_helper resolve-feature-scope: {0}\n".format(error)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 2 handler: read-ac-config
# ---------------------------------------------------------------------------

# Default values when keys are absent or project-config.json is missing.
_AC_CONFIG_DEFAULTS = {
    "ac_verification_mode": "off",
    "ac_runtime_url": "",
    "ac_runtime_api_base": "",
    "ac_runtime_cli_command": "",
}

# project-config.json stores these keys UPPERCASED (confirmed: _configure/_render.py
# _PROJECT_CONFIG_KEY_ORDER lists AC_VERIFICATION_MODE, AC_RUNTIME_URL, etc.).
_AC_CONFIG_JSON_KEYS = {
    "ac_verification_mode": "AC_VERIFICATION_MODE",
    "ac_runtime_url": "AC_RUNTIME_URL",
    "ac_runtime_api_base": "AC_RUNTIME_API_BASE",
    "ac_runtime_cli_command": "AC_RUNTIME_CLI_COMMAND",
}


def cmd_read_ac_config(args):
    # type: (argparse.Namespace) -> int
    """Read AC config keys from .devforge/project-config.json.

    Emits JSON to stdout with the four ac_* keys.  Falls back to safe
    defaults when the file is absent or a key is missing:
      ac_verification_mode  — "off"  (the conservative default: no agent dispatch)
      ac_runtime_url        — ""
      ac_runtime_api_base   — ""
      ac_runtime_cli_command — ""

    Returns 0 always (missing file / missing keys are not errors — the
    caller receives the defaults and can inform the user that AC config
    has not been set up).
    """
    root = getattr(args, "root", None) or os.getcwd()
    config_path = os.path.join(root, ".devforge", "project-config.json")

    config_data = {}  # type: dict
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as fh:
                config_data = json.load(fh)
        except (OSError, ValueError):
            pass  # treat as absent; defaults will be used

    result = {}  # type: dict
    for logical_key, json_key in _AC_CONFIG_JSON_KEYS.items():
        val = config_data.get(json_key)
        if val is None or val == "":
            result[logical_key] = _AC_CONFIG_DEFAULTS[logical_key]
        else:
            result[logical_key] = val

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 2 handler: parse-acs
# ---------------------------------------------------------------------------


def cmd_parse_acs(args):
    # type: (argparse.Namespace) -> int
    """Parse AC checkboxes from a spec file and emit JSON array.

    Returns:
      0 — always (empty array on no ACs or missing file)
    """
    from ._ac import parse_acs

    spec_path = getattr(args, "spec", None) or ""
    acs = parse_acs(spec_path) if spec_path else []

    sys.stdout.write(json.dumps(acs, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 2 handler: read-review-findings
# ---------------------------------------------------------------------------


def cmd_read_review_findings(args):
    # type: (argparse.Namespace) -> int
    """Parse specs/<feature>/review.md into folded findings JSON.

    The feature argument accepts either:
      - a feature directory (e.g. "specs/001-auth") — review.md is appended
      - a direct path to review.md

    Returns:
      0 — always (missing flag in JSON when the file is absent)
    """
    from ._review_findings import read_review_findings

    feature_arg = getattr(args, "feature", None) or ""
    result = read_review_findings(feature_arg) if feature_arg else {
        "missing": True,
        "confirmed": [],
        "contested": [],
        "summary": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "info": 0,
            "confirmed_count": 0,
            "contested_count": 0,
            "dismissed_count": 0,
            "uncertain_count": 0,
        },
    }

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 handler: merge-ac-results
# ---------------------------------------------------------------------------


def cmd_merge_ac_results(args):
    # type: (argparse.Namespace) -> int
    """Merge ac-verifier agent's per-AC Results table into the structured AC list.

    Reads:
      --acs <path>          — path to a JSON file containing the parse-acs output
                              (list of AC dicts with id/text/checked/subsection).
      --agent-report <path> — path to the ac-verifier's markdown report.
                              Pass "-" to read from stdin.

    Emits the merged list as JSON to stdout.  Each dict has the original four
    keys plus ``status`` (e.g. "PASS", "FAIL", "PARTIAL", "MANUAL",
    "PASS (code)", or "UNVERIFIED") and ``evidence`` (the Evidence cell, or "").

    Returns:
      0 — always (missing/unreadable files produce UNVERIFIED status or empty list)
      2 — argument error (required flag missing or JSON parse failure)
    """
    from ._ac import merge_ac_results

    acs_path = getattr(args, "acs", None) or ""
    report_path = getattr(args, "agent_report", None) or ""

    # Load the AC list from JSON.
    if not acs_path:
        sys.stderr.write("verify_helper merge-ac-results: --acs is required\n")
        return 2

    try:
        with open(acs_path, encoding="utf-8") as fh:
            acs = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "verify_helper merge-ac-results: cannot read --acs file: {0}\n".format(exc)
        )
        return 2
    except ValueError as exc:
        sys.stderr.write(
            "verify_helper merge-ac-results: --acs file is not valid JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(acs, list):
        sys.stderr.write(
            "verify_helper merge-ac-results: --acs JSON must be a list\n"
        )
        return 2

    # Load the agent report text.
    if not report_path:
        sys.stderr.write("verify_helper merge-ac-results: --agent-report is required\n")
        return 2

    if report_path == "-":
        agent_report_text = sys.stdin.read()
    else:
        try:
            with open(report_path, encoding="utf-8") as fh:
                agent_report_text = fh.read()
        except OSError as exc:
            # Treat unreadable report as empty — all ACs will be UNVERIFIED.
            sys.stderr.write(
                "verify_helper merge-ac-results: cannot read --agent-report: {0}; "
                "all ACs will be UNVERIFIED\n".format(exc)
            )
            agent_report_text = ""

    merged = merge_ac_results(acs, agent_report_text)
    sys.stdout.write(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 handler: check-hygiene
# ---------------------------------------------------------------------------


def cmd_check_hygiene(args):
    # type: (argparse.Namespace) -> int
    """Flag scope-creep + leftover artifacts across the assembled diff.

    Reads:
      --files <path>          — path to a JSON file containing the list of
                                changed file paths (e.g. from resolve-feature-scope's
                                ``files_for_finders`` array). Pass "-" to read stdin.
      --scope-baseline <path> — path to ``breakdown-handoff.json``; the union of
                                all TaskRow.touched_files is the planned file set.
                                Pass "none" (literal string) to skip scope-creep
                                checking (only leftover artifacts are reported).
      --source-root <dir>     — absolute path to the source tree. Changed files
                                are read from here. Default: CWD.

    Emits JSON to stdout:
      {
        "scope_creep":         [...],   # changed files not in the planned scope
        "leftover_artifacts":  [...],   # per-line findings
        "scope_creep_checked": bool,    # True when a baseline was used
        "files_checked":       int,
        "files_unreadable":    [...]
      }

    Returns:
      0 — always (missing/unreadable files are noted in files_unreadable)
      2 — argument error (--files missing or not valid JSON)
    """
    from ._hygiene import check_hygiene

    files_path = getattr(args, "files", None) or ""
    baseline_path = getattr(args, "scope_baseline", None) or "none"
    source_root = getattr(args, "source_root", None) or os.getcwd()
    source_root = os.path.realpath(source_root)

    # Load the changed-files list.
    if not files_path:
        sys.stderr.write("verify_helper check-hygiene: --files is required\n")
        return 2

    if files_path == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(files_path, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            sys.stderr.write(
                "verify_helper check-hygiene: cannot read --files: {0}\n".format(exc)
            )
            return 2

    try:
        changed_files = json.loads(raw)
    except ValueError as exc:
        sys.stderr.write(
            "verify_helper check-hygiene: --files JSON is not valid: {0}\n".format(exc)
        )
        return 2

    if not isinstance(changed_files, list):
        sys.stderr.write(
            "verify_helper check-hygiene: --files JSON must be a list\n"
        )
        return 2

    # Load the scope baseline from breakdown-handoff.json, unless "none".
    scope_baseline = None  # type: ignore[assignment]

    if baseline_path.lower() != "none":
        try:
            with open(baseline_path, encoding="utf-8") as fh:
                handoff = json.load(fh)
        except OSError:
            # Treat unreadable baseline as absent — skip scope-creep check.
            handoff = None
        except ValueError:
            handoff = None

        if handoff and isinstance(handoff.get("tasks"), list):
            baseline_files = []  # type: ignore[var-annotated]
            for task in handoff["tasks"]:
                tf = task.get("touched_files") or []
                baseline_files.extend(tf)
            scope_baseline = baseline_files
        # If handoff is None or tasks is absent, leave scope_baseline as None.

    result = check_hygiene(
        changed_files=changed_files,
        scope_baseline=scope_baseline,
        source_root=source_root,
    )
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 5 handlers
# ---------------------------------------------------------------------------


def cmd_compute_verdict(args):
    # type: (argparse.Namespace) -> int
    """Compute the APPROVED / NEEDS WORK / REJECTED verdict.

    Reads four JSON files (ac-results, review-findings, hygiene, and optionally
    the mechanical status string) plus the AC verification mode, then emits
    the verdict JSON to stdout.

    Returns:
      0 — always (verdict is always computable; partial/empty inputs are handled)
      2 — argument error (required flag missing or JSON parse failure)
    """
    from ._verdict import compute_verdict

    def _load_json(path, flag_name, allow_missing=False):
        # type: (str, str, bool) -> Optional[object]
        if not path:
            if allow_missing:
                return None
            sys.stderr.write(
                "verify_helper compute-verdict: {0} is required\n".format(flag_name)
            )
            return "ERROR"
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except OSError:
            if allow_missing:
                return None
            sys.stderr.write(
                "verify_helper compute-verdict: cannot read {0}: {1}\n".format(
                    flag_name, path
                )
            )
            return "ERROR"
        except ValueError as exc:
            sys.stderr.write(
                "verify_helper compute-verdict: {0} is not valid JSON: {1}\n".format(
                    flag_name, exc
                )
            )
            return "ERROR"

    ac_path = getattr(args, "ac_results", None) or ""
    review_path = getattr(args, "review_findings", None) or ""
    hygiene_path = getattr(args, "hygiene", None) or ""
    mech_status = getattr(args, "mechanical_status", None) or ""
    ac_mode = getattr(args, "ac_mode", None) or "code-only"

    ac_results = _load_json(ac_path, "--ac-results")
    if ac_results == "ERROR":
        return 2
    if ac_results is None:
        ac_results = []

    review_findings = _load_json(review_path, "--review-findings", allow_missing=True)
    if review_findings is None:
        review_findings = {
            "missing": True,
            "confirmed": [],
            "contested": [],
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "info": 0,
                "confirmed_count": 0,
                "contested_count": 0,
                "dismissed_count": 0,
                "uncertain_count": 0,
            },
        }

    hygiene = _load_json(hygiene_path, "--hygiene", allow_missing=True)
    if hygiene is None:
        hygiene = {
            "scope_creep": [],
            "leftover_artifacts": [],
            "scope_creep_checked": False,
            "files_checked": 0,
            "files_unreadable": [],
        }

    result = compute_verdict(
        ac_results=ac_results,
        mechanical_status=mech_status,
        review_findings=review_findings,
        hygiene=hygiene,
        ac_verification_mode=ac_mode,
    )

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_report(args):
    # type: (argparse.Namespace) -> int
    """Render verification.md and write it atomically to <feature>/verification.md.

    Reads verdict JSON, ac-results JSON, review-findings JSON, and hygiene JSON.
    The --date flag is REQUIRED (determinism — never calls the clock).

    Returns:
      0 — success (verification.md written; path emitted to stdout)
      2 — argument error
      1 — I/O error writing the file
    """
    from ._report import render_report, write_verification_report
    from ._verdict import compute_verdict as _compute_verdict

    def _load_json_or_default(path, default):
        if not path:
            return default
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return default

    verdict_path = getattr(args, "verdict", None) or ""
    ac_path = getattr(args, "ac_results", None) or ""
    review_path = getattr(args, "review_findings", None) or ""
    hygiene_path = getattr(args, "hygiene", None) or ""
    feature = getattr(args, "feature", None) or ""
    date_str = getattr(args, "date", None) or ""
    mech_status = getattr(args, "mechanical_status", None) or ""
    ac_mode = getattr(args, "ac_mode", None) or "code-only"

    if not feature:
        sys.stderr.write("verify_helper render-report: --feature is required\n")
        return 2
    if not date_str:
        sys.stderr.write("verify_helper render-report: --date is required\n")
        return 2

    _empty_review = {
        "missing": True,
        "confirmed": [],
        "contested": [],
        "summary": {
            "critical": 0, "high": 0, "medium": 0, "info": 0,
            "confirmed_count": 0, "contested_count": 0,
            "dismissed_count": 0, "uncertain_count": 0,
        },
    }
    _empty_hygiene = {
        "scope_creep": [],
        "leftover_artifacts": [],
        "scope_creep_checked": False,
        "files_checked": 0,
        "files_unreadable": [],
    }

    verdict = _load_json_or_default(verdict_path, None)
    if verdict is None:
        # Fallback: compute from the other inputs if verdict JSON not supplied
        ac_results_for_verdict = _load_json_or_default(ac_path, [])
        review_findings_for_verdict = _load_json_or_default(review_path, _empty_review)
        hygiene_for_verdict = _load_json_or_default(hygiene_path, _empty_hygiene)
        verdict = _compute_verdict(
            ac_results=ac_results_for_verdict,
            mechanical_status=mech_status,
            review_findings=review_findings_for_verdict,
            hygiene=hygiene_for_verdict,
            ac_verification_mode=ac_mode,
        )

    ac_results = _load_json_or_default(ac_path, [])
    review_findings = _load_json_or_default(review_path, _empty_review)
    hygiene = _load_json_or_default(hygiene_path, _empty_hygiene)

    content = render_report(
        verdict=verdict,
        ac_results=ac_results,
        review_findings=review_findings,
        hygiene=hygiene,
        feature=feature,
        date_str=date_str,
        mechanical_status=mech_status,
        ac_verification_mode=ac_mode,
    )

    try:
        out_path = write_verification_report(feature, content)
    except OSError as exc:
        sys.stderr.write(
            "verify_helper render-report: I/O error writing verification.md: "
            "{0}\n".format(exc)
        )
        return 1

    sys.stdout.write(out_path + "\n")
    return 0


def cmd_render_inline_summary(args):
    # type: (argparse.Namespace) -> int
    """Render the count-first inline summary block to stdout.

    Returns:
      0 — always
      2 — argument error
    """
    from ._report import render_inline_summary

    verdict_path = getattr(args, "verdict", None) or ""
    ac_path = getattr(args, "ac_results", None) or ""
    review_path = getattr(args, "review_findings", None) or ""
    mech_status = getattr(args, "mechanical_status", None) or ""
    feature = getattr(args, "feature", None) or ""

    def _load(path):
        if not path:
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    verdict = _load(verdict_path) or {"verdict": "NEEDS WORK", "reasons": [], "blockers": []}
    ac_results = _load(ac_path) or []
    review_findings = _load(review_path) or {
        "missing": True,
        "confirmed": [],
        "contested": [],
        "summary": {
            "critical": 0, "high": 0, "medium": 0, "info": 0,
            "confirmed_count": 0, "contested_count": 0,
            "dismissed_count": 0, "uncertain_count": 0,
        },
    }

    summary = render_inline_summary(
        verdict=verdict,
        ac_results=ac_results,
        review_findings=review_findings,
        mechanical_status=mech_status,
        feature=feature,
    )

    sys.stdout.write(summary)
    return 0


def cmd_flip_spec_status(args):
    # type: (argparse.Namespace) -> int
    """Task cross-check + flip spec.md to Complete + tick passed AC checkboxes.

    Reads ac-results JSON.  Scans tasks/*.md for Status.
    Returns JSON to stdout: {flipped, blocker, ticked, spec_path}.

    Returns:
      0 — always (flipped=False is not an error; the orchestrator acts on it)
      2 — argument error (required flag missing)
      1 — I/O error
    """
    from ._specstatus import flip_spec_status

    feature = getattr(args, "feature", None) or ""
    ac_path = getattr(args, "ac_results", None) or ""

    if not feature:
        sys.stderr.write("verify_helper flip-spec-status: --feature is required\n")
        return 2

    ac_results = []
    if ac_path:
        try:
            with open(ac_path, encoding="utf-8") as fh:
                ac_results = json.load(fh)
        except OSError as exc:
            sys.stderr.write(
                "verify_helper flip-spec-status: cannot read --ac-results: {0}\n".format(exc)
            )
            return 1
        except ValueError as exc:
            sys.stderr.write(
                "verify_helper flip-spec-status: --ac-results is not valid JSON: "
                "{0}\n".format(exc)
            )
            return 2

    spec_path = getattr(args, "spec_path", None) or None

    try:
        result = flip_spec_status(
            feature_dir=feature,
            ac_results=ac_results,
            spec_path=spec_path,
        )
    except OSError as exc:
        sys.stderr.write(
            "verify_helper flip-spec-status: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_file_bugs(args):
    # type: (argparse.Namespace) -> int
    """Write bug files in bugs/NNN-<slug>.md format (storage-rules.md format).

    Reads issues from a JSON file.  Emits paths written to stdout as JSON array.

    Returns:
      0 — always (empty issues list = empty output, not an error)
      2 — argument error
      1 — I/O error
    """
    from .._shared.bug_file import file_bugs

    issues_path = getattr(args, "issues", None) or ""
    bugs_dir = getattr(args, "bugs_dir", None) or ""
    feature_spec = getattr(args, "feature_spec", None) or "N/A"
    date_str = getattr(args, "date", None) or ""

    if not bugs_dir:
        sys.stderr.write("verify_helper file-bugs: --bugs-dir is required\n")
        return 2
    if not date_str:
        sys.stderr.write("verify_helper file-bugs: --date is required\n")
        return 2

    issues = []
    if issues_path:
        try:
            with open(issues_path, encoding="utf-8") as fh:
                issues = json.load(fh)
        except OSError as exc:
            sys.stderr.write(
                "verify_helper file-bugs: cannot read --issues: {0}\n".format(exc)
            )
            return 1
        except ValueError as exc:
            sys.stderr.write(
                "verify_helper file-bugs: --issues is not valid JSON: {0}\n".format(exc)
            )
            return 2

    if not isinstance(issues, list):
        sys.stderr.write(
            "verify_helper file-bugs: --issues JSON must be a list\n"
        )
        return 2

    try:
        written = file_bugs(
            bugs_dir=bugs_dir,
            issues=issues,
            feature_spec_path=feature_spec,
            date=date_str,
        )
    except OSError as exc:
        sys.stderr.write(
            "verify_helper file-bugs: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(written, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# _SUBCOMMAND_REGISTRY is the extension point for new verbs.
# Each entry is a (verb_name, help_text, handler_function) triple.
# To add a Phase-2+ verb:
#   1. Write the cmd_<verb> function above.
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "check-status-and-flip",
        "Read or update per-feature verify session state phase/status (Phase 1).",
        cmd_check_status_and_flip,
    ),
    (
        "preflight",
        "Gate on setup-chain artefacts + populated constitution (Phase 1).",
        cmd_preflight,
    ),
    (
        "resolve-feature-scope",
        "Resolve assembled-feature diff and emit scope JSON with Verification Scope label (Phase 2).",
        cmd_resolve_feature_scope,
    ),
    (
        "read-ac-config",
        "Read AC verification config keys from .devforge/project-config.json (Phase 2).",
        cmd_read_ac_config,
    ),
    (
        "parse-acs",
        "Parse spec AC checkboxes into structured JSON list (Phase 2).",
        cmd_parse_acs,
    ),
    (
        "read-review-findings",
        "Parse specs/<feature>/review.md into folded findings JSON (Phase 2).",
        cmd_read_review_findings,
    ),
    (
        "merge-ac-results",
        (
            "Merge the ac-verifier agent's per-AC Results table into the parse-acs "
            "structured list; emit extended AC list with status + evidence (Phase 4)."
        ),
        cmd_merge_ac_results,
    ),
    (
        "check-hygiene",
        (
            "Flag scope-creep (changed files outside planned touched_files) and "
            "leftover artifacts (debug prints, bare TODOs, commented-out code) "
            "across the assembled diff (Phase 4)."
        ),
        cmd_check_hygiene,
    ),
    (
        "compute-verdict",
        (
            "Compute the deterministic APPROVED / NEEDS WORK / REJECTED verdict "
            "from AC results, mechanical status, review findings, and hygiene (Phase 5)."
        ),
        cmd_compute_verdict,
    ),
    (
        "render-report",
        (
            "Render verification.md and write it atomically to "
            "<feature>/verification.md (Phase 5)."
        ),
        cmd_render_report,
    ),
    (
        "render-inline-summary",
        "Render the count-first inline console block to stdout (Phase 5).",
        cmd_render_inline_summary,
    ),
    (
        "flip-spec-status",
        (
            "Task cross-check (all Complete/Skipped) + flip spec **Status**: to Complete "
            "+ tick passed AC checkboxes (Phase 5)."
        ),
        cmd_flip_spec_status,
    ),
    (
        "file-bugs",
        (
            "Write bug reports to bugs/NNN-<slug>.md in the storage-rules.md format "
            "with Source: verify, sequential NNN numbering (Phase 5)."
        ),
        cmd_file_bugs,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="verify_helper",
        description=(
            "Helper for /verify — the per-feature AC verification + verdict. "
            "Proves acceptance criteria, runs assembled mechanical checks, "
            "folds in /review findings, and renders APPROVED/NEEDS WORK/REJECTED."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "check-status-and-flip":
            sp.add_argument(
                "--feature-dir",
                default=".",
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Path to the feature directory where verify-state.json lives "
                    "(e.g. specs/001-auth/). Default: CWD."
                ),
            )
            sp.add_argument(
                "--to",
                default=None,
                metavar="PHASE",
                help=(
                    "Phase label to flip to (e.g. 'preflight', '1', '2'). "
                    "Omit to read current state without modifying it."
                ),
            )
            sp.add_argument(
                "--status",
                default=None,
                help=(
                    "Optional status to set alongside the phase flip "
                    "(e.g. 'complete'). Only used when --to is given."
                ),
            )
            sp.add_argument(
                "--verdict",
                default=None,
                metavar="VERDICT",
                help=(
                    "Optional verdict to record in verify-state.json alongside the "
                    "phase flip (e.g. 'APPROVED', 'NEEDS WORK', 'REJECTED'). "
                    "Only used when --to is given. When omitted, the existing "
                    "verdict value is left unchanged."
                ),
            )

        elif verb == "preflight":
            sp.add_argument(
                "--workspace-root",
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Workspace root to check for setup-chain artefacts. "
                    "In wrapper mode this is the wrapper root (not the project "
                    "sub-directory). Default: CWD."
                ),
            )

        elif verb == "resolve-feature-scope":
            sp.add_argument(
                "--feature",
                default=".",
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth). "
                    "Used for context only — not for git operations. Default: CWD."
                ),
            )
            sp.add_argument(
                "--source-root",
                default=None,
                dest="source_root",
                metavar="DIR",
                help=(
                    "Absolute path to the source tree (where git runs). "
                    "Default: CWD."
                ),
            )
            sp.add_argument(
                "--install-root",
                default=None,
                dest="install_root",
                metavar="DIR",
                help=(
                    "Absolute path to the forge install root (where .devforge/ lives). "
                    "Required for wrapper-mode path prefixing. Default: same as --source-root."
                ),
            )
            sp.add_argument(
                "--base",
                default=None,
                metavar="REF",
                help=(
                    "Git ref for the branch the feature forked from (e.g. 'main'). "
                    "When omitted, auto-detected via origin/HEAD → main → develop → master."
                ),
            )

        elif verb == "read-ac-config":
            sp.add_argument(
                "--root",
                default=None,
                metavar="DIR",
                help=(
                    "Install root directory (where .devforge/ lives). "
                    "Default: CWD."
                ),
            )

        elif verb == "parse-acs":
            sp.add_argument(
                "--spec",
                required=True,
                metavar="PATH",
                help="Path to the spec.md file containing ## Acceptance Criteria.",
            )

        elif verb == "read-review-findings":
            sp.add_argument(
                "--feature",
                required=True,
                metavar="PATH",
                help=(
                    "Feature directory (e.g. specs/001-auth) or direct path to review.md. "
                    "When a directory is given, review.md is appended."
                ),
            )

        elif verb == "merge-ac-results":
            sp.add_argument(
                "--acs",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the parse-acs output (list of AC dicts "
                    "with id, text, checked, subsection).  Typically written from "
                    "``verify_helper parse-acs --spec <spec.md>``."
                ),
            )
            sp.add_argument(
                "--agent-report",
                required=True,
                dest="agent_report",
                metavar="PATH",
                help=(
                    "Path to the ac-verifier agent's markdown report containing the "
                    "``### Results`` table.  Pass \"-\" to read from stdin."
                ),
            )

        elif verb == "check-hygiene":
            sp.add_argument(
                "--files",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the list of changed file paths "
                    "(e.g. the ``files_for_finders`` array from resolve-feature-scope). "
                    "Pass \"-\" to read from stdin."
                ),
            )
            sp.add_argument(
                "--scope-baseline",
                required=True,
                dest="scope_baseline",
                metavar="PATH|none",
                help=(
                    "Path to breakdown-handoff.json; the union of all TaskRow.touched_files "
                    "is the declared planned scope.  Pass \"none\" (literal) to skip "
                    "scope-creep checking and report only leftover artifacts."
                ),
            )
            sp.add_argument(
                "--source-root",
                default=None,
                dest="source_root",
                metavar="DIR",
                help=(
                    "Absolute path to the source tree.  Changed files are read from here. "
                    "Default: CWD."
                ),
            )

        elif verb == "compute-verdict":
            sp.add_argument(
                "--ac-results",
                required=True,
                dest="ac_results",
                metavar="PATH",
                help="Path to JSON file from merge-ac-results.",
            )
            sp.add_argument(
                "--review-findings",
                default=None,
                dest="review_findings",
                metavar="PATH",
                help=(
                    "Path to JSON file from read-review-findings. "
                    "Omit when no review.md exists (missing=True implied)."
                ),
            )
            sp.add_argument(
                "--hygiene",
                default=None,
                dest="hygiene",
                metavar="PATH",
                help=(
                    "Path to JSON file from check-hygiene. "
                    "Omit when hygiene check was skipped."
                ),
            )
            sp.add_argument(
                "--mechanical-status",
                default="",
                dest="mechanical_status",
                metavar="STATUS",
                help=(
                    "Status string from verify-touched (pass / failed / self_repair / "
                    "isolation_failure / tooling_unavailable). Default: '' (not run)."
                ),
            )
            sp.add_argument(
                "--ac-mode",
                default="code-only",
                dest="ac_mode",
                metavar="MODE",
                help=(
                    "ac_verification_mode value: code-only | tests | runtime-assisted | off. "
                    "Default: code-only."
                ),
            )

        elif verb == "render-report":
            sp.add_argument(
                "--verdict",
                default=None,
                dest="verdict",
                metavar="PATH",
                help=(
                    "Path to JSON file from compute-verdict. "
                    "When omitted, the verdict is computed from the other inputs."
                ),
            )
            sp.add_argument(
                "--ac-results",
                default=None,
                dest="ac_results",
                metavar="PATH",
                help="Path to JSON file from merge-ac-results.",
            )
            sp.add_argument(
                "--review-findings",
                default=None,
                dest="review_findings",
                metavar="PATH",
                help="Path to JSON file from read-review-findings.",
            )
            sp.add_argument(
                "--hygiene",
                default=None,
                dest="hygiene",
                metavar="PATH",
                help="Path to JSON file from check-hygiene.",
            )
            sp.add_argument(
                "--feature",
                required=True,
                dest="feature",
                metavar="DIR",
                help="Feature directory path (e.g. specs/001-auth).",
            )
            sp.add_argument(
                "--date",
                required=True,
                dest="date",
                metavar="YYYY-MM-DD",
                help="Report date (REQUIRED — never calls the clock).",
            )
            sp.add_argument(
                "--mechanical-status",
                default="",
                dest="mechanical_status",
                metavar="STATUS",
                help="Status string from verify-touched. Default: '' (not run).",
            )
            sp.add_argument(
                "--ac-mode",
                default="code-only",
                dest="ac_mode",
                metavar="MODE",
                help=(
                    "ac_verification_mode value. Default: code-only."
                ),
            )

        elif verb == "render-inline-summary":
            sp.add_argument(
                "--verdict",
                default=None,
                dest="verdict",
                metavar="PATH",
                help="Path to JSON file from compute-verdict.",
            )
            sp.add_argument(
                "--ac-results",
                default=None,
                dest="ac_results",
                metavar="PATH",
                help="Path to JSON file from merge-ac-results.",
            )
            sp.add_argument(
                "--review-findings",
                default=None,
                dest="review_findings",
                metavar="PATH",
                help="Path to JSON file from read-review-findings.",
            )
            sp.add_argument(
                "--mechanical-status",
                default="",
                dest="mechanical_status",
                metavar="STATUS",
                help="Status string from verify-touched.",
            )
            sp.add_argument(
                "--feature",
                default="",
                dest="feature",
                metavar="DIR",
                help="Feature directory path (for display).",
            )

        elif verb == "flip-spec-status":
            sp.add_argument(
                "--feature",
                required=True,
                dest="feature",
                metavar="DIR",
                help="Feature directory path (e.g. specs/001-auth).",
            )
            sp.add_argument(
                "--ac-results",
                default=None,
                dest="ac_results",
                metavar="PATH",
                help=(
                    "Path to JSON file from merge-ac-results. "
                    "Used to determine which ACs to tick."
                ),
            )
            sp.add_argument(
                "--spec-path",
                default=None,
                dest="spec_path",
                metavar="PATH",
                help=(
                    "Explicit path to spec.md. "
                    "Default: <feature>/spec.md."
                ),
            )

        elif verb == "file-bugs":
            sp.add_argument(
                "--issues",
                required=True,
                dest="issues",
                metavar="PATH",
                help="Path to JSON file containing the list of issue dicts.",
            )
            sp.add_argument(
                "--bugs-dir",
                required=True,
                dest="bugs_dir",
                metavar="DIR",
                help="Path to the bugs/ directory (created if absent).",
            )
            sp.add_argument(
                "--feature-spec",
                default="N/A",
                dest="feature_spec",
                metavar="PATH",
                help=(
                    "Path to the feature spec file "
                    "(e.g. specs/001-auth/spec.md). Default: N/A."
                ),
            )
            sp.add_argument(
                "--date",
                required=True,
                dest="date",
                metavar="YYYY-MM-DD",
                help="Report date (REQUIRED — never calls the clock).",
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    """Parse argv and dispatch to the selected subcommand handler.

    Returns the handler's exit code (0 = success, non-zero = error).
    When no subcommand is given, prints help and returns 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2

    return args.func(args)
