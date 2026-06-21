"""argparse parser + dispatch + main entry for pr_review_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches every cmd_* handler.
main parses argv + dispatches.

Step 2 verbs (ensure-cbm-index, detect-forge-state) are fully implemented.
Step 3 verb (intake) is fully implemented.
Step 4 verb (detect-smells) is fully implemented.
Step 5 verb (compute-blast-radius) is fully implemented.
Step 6 verbs (bundle-context, import-handoffs) are fully implemented.
Step 7 verb (check-scope-drift) is fully implemented.
Step 8 verb (dispatch-review) is fully implemented.
Step 9 verbs (finalize-output, append-to-replay-corpus) are fully implemented.
All 11 verbs are implemented; zero stubs remain.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import tempfile


# ---------------------------------------------------------------------------
# Step 2 handlers — real implementations replacing stubs.
# ---------------------------------------------------------------------------


def cmd_ensure_cbm_index(args: argparse.Namespace) -> int:
    """Phase -1: ensure CBM index is current before review.

    Invokes cbm_sync_helper check and emits a structured JSON dict to
    stdout. The LLM reads the JSON to decide whether to run detect_changes
    or index_repository before proceeding.

    Returns 0 on success, 1 on subprocess / I/O error.
    """
    from ._ensure_cbm import run as _run_ensure_cbm

    target = getattr(args, "target", None) or os.getcwd()
    devforge_dir = getattr(args, "devforge_dir", ".devforge")
    try:
        result = _run_ensure_cbm(target=target, devforge_dir=devforge_dir)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "pr_review_helper ensure-cbm-index: error: {0}\n".format(exc)
        )
        return 1
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_detect_forge_state(args: argparse.Namespace) -> int:
    """Phase 0: detect forge-tier (full/partial/none) for the target repo.

    Pure filesystem scan — no subprocess, no network. Emits a structured
    JSON dict to stdout classifying the repo's forge state.

    Returns 0 on success, 1 on I/O error.
    """
    from ._detect_tier import run as _run_detect_tier

    target = getattr(args, "target", None) or os.getcwd()
    devforge_dir = getattr(args, "devforge_dir", ".devforge")
    try:
        result = _run_detect_tier(target=target, devforge_dir=devforge_dir)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "pr_review_helper detect-forge-state: error: {0}\n".format(exc)
        )
        return 1
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    """Phase 1: fetch PR metadata + diff and write initial state.

    Invokes `gh pr view` and `gh pr diff`, builds a PRReviewState, and
    writes it to <target>/.devforge/pr-reviews/<pr>/state.json.

    Returns 0 on success, 1 on any error.
    """
    from ._intake import run as _run_intake
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper intake: {0}\n".format(exc))
        return 1

    repo = args.repo
    target = getattr(args, "target", None) or os.getcwd()
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    # Resolve ticket text (mutually exclusive group enforced by argparse).
    ticket_text = ""
    if getattr(args, "ticket_text", None) is not None:
        ticket_text = args.ticket_text
    elif getattr(args, "ticket_file", None) is not None:
        from ._intake import _read_ticket_file
        try:
            ticket_text = _read_ticket_file(args.ticket_file)
        except ValueError as exc:
            sys.stderr.write("pr_review_helper intake: {0}\n".format(exc))
            return 1

    try:
        result = _run_intake(
            target=target,
            pr_number=pr_number,
            repo=repo,
            ticket_text=ticket_text,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write("pr_review_helper intake: {0}\n".format(exc))
        return 1
    except OSError as exc:
        sys.stderr.write("pr_review_helper intake: I/O error: {0}\n".format(exc))
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_detect_smells(args: argparse.Namespace) -> int:
    """Phase 4: run all registered smell heuristics and persist findings to state.

    Reads existing state.json (written by Step 3 intake), runs each heuristic
    in registration order, appends findings to state.smells, writes state back
    atomically, and outputs a summary JSON dict to stdout.

    Returns 0 on success, 1 on error.
    """
    from ._state import PRReviewState, state_path
    from ._validators import _validate_pr_number
    from . import _smells

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper detect-smells: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")
    abs_devforge = os.path.join(target, devforge_dir)
    sp = state_path(abs_devforge, pr_number)

    if not os.path.exists(sp):
        sys.stderr.write(
            "pr_review_helper detect-smells: no state.json at {path};"
            " run `intake` first\n".format(path=sp)
        )
        return 1

    try:
        with open(sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            "pr_review_helper detect-smells: cannot read state: {0}\n".format(exc)
        )
        return 1

    try:
        state = PRReviewState(**state_dict)
    except TypeError as exc:
        sys.stderr.write(
            "pr_review_helper detect-smells: state schema error: {0}\n".format(exc)
        )
        return 1

    # Inject target into state for heuristics that need filesystem access
    # (duplication_ratio, literal_archaeology_adapter, hallucinated_api).
    # target is a declared PRReviewState field (default ""); set here at
    # run time. The value IS persisted to state.json via asdict() but is
    # always overwritten from --target args on the next invocation —
    # so the persisted value is irrelevant across machines.
    state.target = target

    # Run all heuristics.  Each may emit multiple findings.
    findings = _smells._catalog.run_all(state)

    # Append (don't replace — preserves findings from any prior runs).
    state.smells.extend(findings)

    # Atomic write: temp file in the same directory, then os.replace.
    state_dir = os.path.dirname(sp)
    fd, tmp_path = tempfile.mkstemp(prefix="state-", suffix=".tmp.json", dir=state_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(state), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, sp)
    except Exception as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        sys.stderr.write(
            "pr_review_helper detect-smells: write error: {0}\n".format(exc)
        )
        return 1

    # Summary JSON to stdout.
    by_severity = {"nit": 0, "low": 0, "medium": 0, "high": 0}
    for finding in findings:
        sev = finding.get("severity", "low")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    output = {
        "status": "ok",
        "state_path": sp,
        "smells_count": len(findings),
        "by_severity": by_severity,
    }
    sys.stdout.write(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_compute_blast_radius(args: argparse.Namespace) -> int:
    """Phase 3: parse diff to extract changed symbols; write probe-spec list to state.blast.

    Reads state.json (written by Step 3 intake), identifies NEW or MODIFIED
    symbols (functions, classes, methods, components, exported types) via
    per-language regex patterns applied to added lines in the diff, and
    REPLACES state.blast with one probe-spec entry per unique (symbol, file).

    Does NOT call CBM / MCP tools. The mcp_hints field in each probe spec
    carries the symbol name for the LLM to pass to CBM trace_path at Step 8.

    Returns 0 on success, 1 on error.
    """
    from ._blast import run as _run_blast
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper compute-blast-radius: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_blast(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write(
            "pr_review_helper compute-blast-radius: {0}\n".format(exc)
        )
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper compute-blast-radius: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_bundle_context(args: argparse.Namespace) -> int:
    """Phase 4a: aggregate filesystem context sources into state.bundle.

    Reads state.json (written by Step 3 intake), assembles constitution,
    constitute.json, concern docs, ADRs, and *-PLAN.md files from the
    local filesystem, and writes the bundle to state.bundle.

    Returns 0 on success, 1 on any error.
    """
    from ._bundle import run as _run_bundle
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper bundle-context: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_bundle(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write(
            "pr_review_helper bundle-context: {0}\n".format(exc)
        )
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper bundle-context: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_import_handoffs(args: argparse.Namespace) -> int:
    """Phase 4b: scan research/ for relevant handoffs and write to state.bundle.

    Reads state.json (written by Step 3 intake), discovers handoff.json
    files under <target>/research/, filters by relevance to state.ticket_text
    and PR title, and writes the filtered set to state.bundle["research_handoffs"].

    Returns 0 on success, 1 on any error.
    """
    from ._handoff_import import run as _run_handoff_import
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper import-handoffs: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_handoff_import(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write(
            "pr_review_helper import-handoffs: {0}\n".format(exc)
        )
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper import-handoffs: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_check_scope_drift(args: argparse.Namespace) -> int:
    """Phase 5: extract ticket bullets and write drift scaffold to state.drift.

    Reads state.json (written by Step 3 intake), applies regex-based bullet
    extraction strategies to state.ticket_text and state.pr_body, deduplicates,
    and REPLACES state.drift with a scaffold for LLM-fill at Step 8.

    Does NOT call LLM or MCP tools. Extraction is fully deterministic.

    Returns 0 on success, 1 on any error.
    """
    from ._scope_drift import run as _run_scope_drift
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper check-scope-drift: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_scope_drift(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write(
            "pr_review_helper check-scope-drift: {0}\n".format(exc)
        )
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper check-scope-drift: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_dispatch_review(args: argparse.Namespace) -> int:
    """Phase 6: assemble reviewer brief and write to brief.md.

    Reads state.json (populated by Steps 3-7), assembles a fat Markdown brief
    at <target>/.devforge/pr-reviews/<pr>/brief.md, and outputs a summary JSON
    dict to stdout.

    Does NOT invoke cavecrew-reviewer or any LLM/MCP tool — that is the
    orchestrator's responsibility after reading this module's JSON output.

    Returns 0 on success, 1 on error.
    """
    from ._dispatch import run as _run_dispatch
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper dispatch-review: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_dispatch(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write(
            "pr_review_helper dispatch-review: {0}\n".format(exc)
        )
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper dispatch-review: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_finalize_output(args: argparse.Namespace) -> int:
    """Phase 7: render state.findings to findings.md.

    Reads state.json (populated by Step 8 dispatch-review), renders a Markdown
    findings report sorted by severity then location, writes it atomically to
    <target>/.devforge/pr-reviews/<pr>/findings.md, and emits a summary JSON
    dict to stdout.

    Returns 0 on success, 1 on error.
    """
    from ._output import run as _run_output
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper finalize-output: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_output(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write("pr_review_helper finalize-output: {0}\n".format(exc))
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper finalize-output: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_append_to_replay_corpus(args: argparse.Namespace) -> int:
    """Phase 7: write bundle snapshot + upsert corpus index.

    Reads state.json, writes a full state snapshot to
    <target>/.devforge/pr-reviews/<pr>/pr-review-bundle.json, and upserts an
    entry in the corpus-wide index at
    <target>/.devforge/pr-reviews/_corpus_index.json.

    Both files are written atomically.  Re-running increments review_count;
    first_reviewed_at is preserved.

    Returns 0 on success, 1 on error.
    """
    from ._replay import run as _run_replay
    from ._validators import _validate_pr_number

    try:
        pr_number = _validate_pr_number(args.pr)
    except (TypeError, ValueError) as exc:
        sys.stderr.write("pr_review_helper append-to-replay-corpus: {0}\n".format(exc))
        return 1

    target = os.path.abspath(getattr(args, "target", None) or os.getcwd())
    devforge_dir = getattr(args, "devforge_dir", ".devforge")

    try:
        result = _run_replay(
            target=target,
            pr_number=pr_number,
            devforge_dir=devforge_dir,
        )
    except ValueError as exc:
        sys.stderr.write(
            "pr_review_helper append-to-replay-corpus: {0}\n".format(exc)
        )
        return 1
    except OSError as exc:
        sys.stderr.write(
            "pr_review_helper append-to-replay-corpus: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Parser construction.
# ---------------------------------------------------------------------------

# Registry: (verb, help-text, handler).
# Adding a new subcommand = append a tuple here; no other edits needed.
_SUBCOMMAND_REGISTRY = [
    (
        "ensure-cbm-index",
        "Ensure CBM index is current before review (Step 2).",
        cmd_ensure_cbm_index,
    ),
    (
        "detect-forge-state",
        "Detect forge-tier (full/partial/none) for the target repo (Step 2).",
        cmd_detect_forge_state,
    ),
    (
        "intake",
        "Fetch PR metadata + diff and write initial state (Step 3).",
        cmd_intake,
    ),
    (
        "detect-smells",
        "Run AI-slop heuristics over the diff and record smells (Step 4).",
        cmd_detect_smells,
    ),
    (
        "compute-blast-radius",
        "Trace changed symbols to dependents and record blast list (Step 5).",
        cmd_compute_blast_radius,
    ),
    (
        "bundle-context",
        "Assemble concern docs + architecture context bundle (Step 6).",
        cmd_bundle_context,
    ),
    (
        "import-handoffs",
        "Import relevant /research + /discover handoff docs (Step 6).",
        cmd_import_handoffs,
    ),
    (
        "check-scope-drift",
        "Compare diff scope against PR body / linked issue and flag drift (Step 7).",
        cmd_check_scope_drift,
    ),
    (
        "dispatch-review",
        "Assemble reviewer brief and dispatch review agent (Step 8).",
        cmd_dispatch_review,
    ),
    (
        "finalize-output",
        "Render review findings to console + save output artefact (Step 9).",
        cmd_finalize_output,
    ),
    (
        "append-to-replay-corpus",
        "Append this PR review to the replay corpus for regression tests (Step 9).",
        cmd_append_to_replay_corpus,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="pr_review_helper",
        description=(
            "State + review helper for /pr-review. "
            "Personal-overlay PR review of foreign repos; "
            "AI-slop + blast-radius + scope-drift detection."
        ),
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """Attach all handlers from _SUBCOMMAND_REGISTRY.

    Step 2 verbs (ensure-cbm-index, detect-forge-state) receive a --target
    argument.  Step 3 verb (intake) receives --pr, --repo, mutually exclusive
    --ticket-text / --ticket-file, and --target.  Step 4 verb (detect-smells)
    and Step 5 verb (compute-blast-radius) both receive --pr (int, required)
    and --target (str, default cwd).  All other verbs get no extra arguments
    until their step lands.
    """
    _STEP2_VERBS = frozenset(["ensure-cbm-index", "detect-forge-state"])
    _PR_REQUIRED_VERBS = frozenset([
        "detect-smells",
        "compute-blast-radius",
        "bundle-context",
        "import-handoffs",
        "check-scope-drift",
        "dispatch-review",
        "finalize-output",
        "append-to-replay-corpus",
    ])
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)
        if verb in _STEP2_VERBS:
            sp.add_argument(
                "--target",
                default=os.getcwd(),
                help=(
                    "Absolute path to the repository root to inspect "
                    "(default: current working directory)."
                ),
            )
        elif verb == "intake":
            sp.add_argument(
                "--pr",
                type=int,
                required=True,
                help="PR number to intake (e.g. 42).",
            )
            sp.add_argument(
                "--repo",
                required=True,
                help="GitHub repository in owner/name format (e.g. acme/myapp).",
            )
            ticket_group = sp.add_mutually_exclusive_group()
            ticket_group.add_argument(
                "--ticket-text",
                default=None,
                help="Inline ticket text (JIRA / Linear prose) as a string.",
            )
            ticket_group.add_argument(
                "--ticket-file",
                default=None,
                help="Path to a UTF-8 text file containing the ticket body.",
            )
            sp.add_argument(
                "--target",
                default=os.getcwd(),
                help=(
                    "Path to the reviewer's local repo root where .devforge/ "
                    "lives (default: current working directory)."
                ),
            )
        elif verb in _PR_REQUIRED_VERBS:
            sp.add_argument(
                "--pr",
                required=True,
                type=int,
                help="PR number (the state file for this PR must already exist)",
            )
            sp.add_argument(
                "--target",
                default=os.getcwd(),
                help="Path to the reviewer's local repo (default: CWD)",
            )
        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point.
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
