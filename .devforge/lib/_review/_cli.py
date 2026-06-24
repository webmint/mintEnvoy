"""argparse parser + dispatch + main entry for review_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 1 (scaffold) ships 2 verbs:
  check-status-and-flip  — read or update per-feature review session state
  preflight              — gate on setup-chain artefacts + constitution check

Extension point for later phases: append to _SUBCOMMAND_REGISTRY and add
the corresponding argument block in _register_subcommands's elif chain.

Phase 2 ships 1 verb (scope resolution):
  resolve-feature-scope    — resolve assembled-feature diff + emit scope JSON (Phase 2)

Phase 3 ships 3 verbs (brief assembly + shared consume/validate):
  render-agent-brief       — assemble per-agent review instruction block (Phase 3)
  consume-tmp              — parse one agent tmp file → ParsedFinding list JSON (Phase 3)
  validate-findings        — anti-hallucination guard on ParsedFinding list (Phase 3)

Phase 4 ships 4 verbs (refutation cross-examination):
  route-refutation         — assign refuter per non-author policy (Phase 4)
  render-verify-brief      — assemble refuter cross-examination block (Phase 4)
  consume-verdicts         — parse refuter verdict file → verdict list JSON (Phase 4)
  apply-verdicts           — partition findings by verdict (Phase 4)

Phase 5 ships 2 verbs (report rendering):
  render-report            — render + write specs/<feature>/review.md (Phase 5)
  render-inline-summary    — render ## Review Complete console block (Phase 5)
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_check_status_and_flip(args: argparse.Namespace) -> int:
    """Read current review state, optionally flip phase/status, emit JSON.

    Without --to: read current state (empty ReviewState if none) and print.
    With --to: call flip_phase, print resulting state.
    Returns 0 on success, 1 on I/O error, 2 on ValueError (empty --to).
    """
    from ._state import ReviewState, flip_phase, read_state, state_path

    feature_dir = getattr(args, "feature_dir", ".") or "."
    to_phase = getattr(args, "to", None)
    to_status = getattr(args, "status", None)

    sp = state_path(feature_dir)

    if to_phase is None:
        # Read-only mode.
        state = read_state(sp)
        if state is None:
            state = ReviewState()
        sys.stdout.write(
            json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
        )
        return 0

    # Flip mode.
    try:
        state = flip_phase(sp, to_phase, to_status)
    except ValueError as exc:
        sys.stderr.write(
            "review_helper check-status-and-flip: {0}\n".format(exc)
        )
        return 2
    except OSError as exc:
        sys.stderr.write(
            "review_helper check-status-and-flip: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(
        json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
    )
    return 0


def cmd_resolve_feature_scope(args: argparse.Namespace) -> int:
    """Compute the assembled-feature diff and emit scope JSON.

    Runs: git diff --name-only $(git merge-base <base> HEAD)..HEAD
    in the source tree.  Emits JSON to stdout; error to stderr + exit 2.

    Returns:
      0 — success (empty file list is valid — HEAD == merge-base)
      2 — user error (not a git repo, bad ref, no auto-detectable base, etc.)
    """
    from ._scope import cmd_resolve_feature_scope as _impl
    return _impl(args)


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
            "review_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /init-forge → /generate-docs → /configure → /constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    # Gate: constitution unpopulated → exit 2.
    if not result["constitution_populated"]:
        sys.stderr.write(
            "review_helper preflight: constitution.md contains an unpopulated "
            "sentinel. Run /constitute to populate it before running /review.\n"
        )
        return 2

    return 0


# ---------------------------------------------------------------------------
# Phase 3 handlers
# ---------------------------------------------------------------------------


def cmd_render_agent_brief(args: argparse.Namespace) -> int:
    """Assemble and print the per-agent review instruction block.

    Reads scope_block from --scope-block file, assembles brief from references_dir.
    Returns 0 on success, 2 on error (unknown agent, missing file, etc.).
    """
    from ._brief import render_agent_brief

    agent = getattr(args, "agent", None)
    if not agent:
        sys.stderr.write(
            "review_helper render-agent-brief: --agent <name> required\n"
        )
        return 2

    scope_block_path = getattr(args, "scope_block", None)
    if not scope_block_path:
        sys.stderr.write(
            "review_helper render-agent-brief: --scope-block <path> required\n"
        )
        return 2

    references_dir = (
        getattr(args, "references_dir", None)
        or ".claude/commands/review/references"
    )

    try:
        with open(scope_block_path, "r", encoding="utf-8") as fh:
            scope_block = fh.read()
    except OSError as exc:
        sys.stderr.write(
            "review_helper render-agent-brief: cannot read --scope-block file: "
            "{0}\n".format(exc)
        )
        return 2

    tmp_path = getattr(args, "tmp_path", None)

    try:
        brief = render_agent_brief(
            agent=agent,
            references_dir=references_dir,
            scope_block=scope_block,
            tmp_path=tmp_path,
        )
    except ValueError as exc:
        sys.stderr.write(
            "review_helper render-agent-brief: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(brief + "\n")
    return 0


def cmd_consume_tmp(args: argparse.Namespace) -> int:
    """Parse one agent tmp file into status + ParsedFinding list.

    Delegates to _shared.parse_agent_tmp (same parser used by /audit).

    Returns 0 on success, 2 on missing/unreadable file.
    When the tmp file does not exist the result carries status=STATUS_MISSING
    so callers can distinguish "agent never wrote output" from a failed/corrupt file.
    """
    from _shared._consume import parse_agent_tmp, STATUS_MISSING, STATUS_FAILED  # type: ignore[import]

    tmp_path = getattr(args, "tmp", None)
    if not tmp_path:
        sys.stderr.write(
            "review_helper consume-tmp: --tmp <path> required\n"
        )
        return 2

    agent_hint = getattr(args, "agent", "") or ""

    try:
        with open(tmp_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError as exc:
        result = {
            "status": STATUS_MISSING,
            "reason": "tmp file not found: {0}".format(exc),
            "agent": agent_hint or "unknown",
            "finding_count": 0,
            "findings": [],
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stderr.write("review_helper consume-tmp: {0}\n".format(exc))
        return 2
    except OSError as exc:
        result = {
            "status": STATUS_FAILED,
            "reason": "cannot read tmp file: {0}".format(exc),
            "agent": agent_hint or "unknown",
            "finding_count": 0,
            "findings": [],
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stderr.write("review_helper consume-tmp: {0}\n".format(exc))
        return 2

    result = parse_agent_tmp(text, agent_name=agent_hint or "unknown")
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_validate_findings(args: argparse.Namespace) -> int:
    """Run anti-hallucination checks on a JSON list of ParsedFinding dicts.

    Delegates to _shared.validate_findings (same guard used by /audit).

    Input: --findings <path>  (JSON list of ParsedFinding dicts)
           --repo-root <dir>  (root for resolving relative file paths)
           --source-root <rel>  (optional subdirectory within repo-root)

    Returns 0 on success, 2 on missing/unreadable file or bad input.
    """
    from _shared._validate import validate_findings  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "review_helper validate-findings: --findings <path> required\n"
        )
        return 2

    repo_root = getattr(args, "repo_root", ".") or "."
    source_root = getattr(args, "source_root", "") or ""

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper validate-findings: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper validate-findings: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "review_helper validate-findings: --findings must be a JSON array\n"
        )
        return 2

    try:
        result = validate_findings(findings, repo_root, source_root)
    except Exception as exc:
        sys.stderr.write(
            "review_helper validate-findings: unexpected error: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 handlers (refutation / cross-examination)
# ---------------------------------------------------------------------------


def cmd_route_refutation(args: argparse.Namespace) -> int:
    """Group working findings by author and assign each group a non-author refuter.

    Review's refuter roster is the default _REFUTER_PRIORITY (the same four
    priority refuters as /audit: code-reviewer, architect, qa-reviewer,
    security-reviewer).  performance-analyst and design-auditor are FINDERS
    ONLY in /review's setup and must never appear as refuters — both are
    simply absent from the default priority list so no priority= override is
    needed.

    Input: --findings <path>  (JSON array of ParsedFinding dicts)
           --finders <comma-list>  (present finder agent names from Phase 2)
    Returns 0 on success, 2 on missing/bad input.
    Output: JSON list of {refuter, findings} routing groups, one per refuter.
    """
    from _shared._verify import route_refutation  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "review_helper route-refutation: --findings <path> required\n"
        )
        return 2

    finders_raw = getattr(args, "finders", None) or ""
    present_finders = [f.strip() for f in finders_raw.split(",") if f.strip()]

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper route-refutation: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper route-refutation: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "review_helper route-refutation: --findings must be a JSON array\n"
        )
        return 2

    # Do NOT pass a custom priority — review's refuters are the _shared
    # default [code-reviewer, architect, qa-reviewer, security-reviewer].
    # performance-analyst is present as a finder but is NOT in the priority
    # list, so it is excluded from refuter selection without any special logic.
    result = route_refutation(findings, present_finders)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_verify_brief(args: argparse.Namespace) -> int:
    """Assemble a refuter's cross-examination instruction block.

    Review uses a pre-rendered scope block file (--scope-block <path>) rather
    than a scope JSON because /review's scope is already rendered as a string
    by resolve-feature-scope.  This mirrors render-agent-brief's --scope-block
    convention (see Phase 3).

    Input: --findings <path>       (JSON array of ParsedFinding dicts — the
                                    subset routed to this refuter)
           --refuter <name>        (refuter agent name)
           --references-dir <dir>  (directory containing refutation-preamble.md)
           --scope-block <path>    (file whose content is the pre-rendered scope
                                    block, e.g. the scope_block field from
                                    resolve-feature-scope JSON)
           --source-root <dir>     (workspace/repo root label)
           --tmp-path <path>       (optional write-path for the verdict file)
    Returns 0 on success, 2 on bad input.
    Prints the rendered brief as plain text to stdout.
    """
    from _shared._verify import render_verify_brief  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    refuter = getattr(args, "refuter", None)
    references_dir = (
        getattr(args, "references_dir", None)
        or ".claude/commands/review/references"
    )
    scope_block_path = getattr(args, "scope_block", None)
    source_root = getattr(args, "source_root", ".") or "."
    tmp_path = getattr(args, "tmp_path", None)

    if not findings_path:
        sys.stderr.write(
            "review_helper render-verify-brief: --findings <path> required\n"
        )
        return 2
    if not refuter:
        sys.stderr.write(
            "review_helper render-verify-brief: --refuter <name> required\n"
        )
        return 2
    if not scope_block_path:
        sys.stderr.write(
            "review_helper render-verify-brief: --scope-block <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper render-verify-brief: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper render-verify-brief: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "review_helper render-verify-brief: --findings must be a JSON array\n"
        )
        return 2

    try:
        with open(scope_block_path, "r", encoding="utf-8") as fh:
            scope_block = fh.read()
    except OSError as exc:
        sys.stderr.write(
            "review_helper render-verify-brief: cannot read --scope-block file: "
            "{0}\n".format(exc)
        )
        return 2

    try:
        brief = render_verify_brief(
            refuter=refuter,
            findings=findings,
            references_dir=references_dir,
            scope_block=scope_block,
            source_root=source_root,
            tmp_path=tmp_path,
        )
    except ValueError as exc:
        sys.stderr.write(
            "review_helper render-verify-brief: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(brief)
    if not brief.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_consume_verdicts(args: argparse.Namespace) -> int:
    """Parse one refuter verdict file into status + verdict list JSON.

    Input: --verdicts <path>  (the raw refuter markdown verdict file)
           --refuter <name>   (optional agent name hint when # Refuter: header absent)
    Returns 0 on success, 2 on missing/unreadable file.
    The result JSON always includes a 'status' field.
    """
    from _shared._verify import consume_verdicts, VERDICT_STATUS_MISSING, VERDICT_STATUS_FAILED  # type: ignore[import]

    verdicts_path = getattr(args, "verdicts", None)
    if not verdicts_path:
        sys.stderr.write(
            "review_helper consume-verdicts: --verdicts <path> required\n"
        )
        return 2

    refuter_hint = getattr(args, "refuter", "") or ""

    try:
        with open(verdicts_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError as exc:
        result = {
            "status": VERDICT_STATUS_MISSING,
            "reason": "verdicts file not found: {0}".format(exc),
            "refuter": refuter_hint or "unknown",
            "verdict_count": 0,
            "verdicts": [],
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stderr.write("review_helper consume-verdicts: {0}\n".format(exc))
        return 2
    except OSError as exc:
        result = {
            "status": VERDICT_STATUS_FAILED,
            "reason": "cannot read verdicts file: {0}".format(exc),
            "refuter": refuter_hint or "unknown",
            "verdict_count": 0,
            "verdicts": [],
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stderr.write("review_helper consume-verdicts: {0}\n".format(exc))
        return 2

    result = consume_verdicts(text)
    # If the # Refuter: header was absent and we have a hint, apply the hint.
    if result.get("refuter") == "unknown" and refuter_hint:
        result = dict(result)
        result["refuter"] = refuter_hint
        for v in result.get("verdicts", []):
            if v.get("refuter") == "unknown":
                v["refuter"] = refuter_hint
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_apply_verdicts(args: argparse.Namespace) -> int:
    """Partition working findings by merged verdicts per D7 category rules.

    Input: --findings <path>  (JSON array of ParsedFinding dicts — the full
                               working list after consensus/merge)
           --verdicts <path>  (JSON array of verdict dicts — merged across all
                               refuters; each element is a verdict dict from
                               consume_verdicts; also accepts a consume-verdicts
                               result object with a 'verdicts' key)
    Returns 0 on success, 2 on missing/bad input.
    Output: JSON object with keys: confirmed, dismissed, uncertain, contested.
    """
    from _shared._verify import apply_verdicts  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    verdicts_path = getattr(args, "verdicts", None)

    if not findings_path:
        sys.stderr.write(
            "review_helper apply-verdicts: --findings <path> required\n"
        )
        return 2
    if not verdicts_path:
        sys.stderr.write(
            "review_helper apply-verdicts: --verdicts <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper apply-verdicts: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper apply-verdicts: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "review_helper apply-verdicts: --findings must be a JSON array\n"
        )
        return 2

    try:
        with open(verdicts_path, "r", encoding="utf-8") as fh:
            verdicts_raw = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper apply-verdicts: cannot read --verdicts file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper apply-verdicts: --verdicts file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    # Accept either a bare JSON array of verdict dicts OR a consume-verdicts
    # result object with a "verdicts" key.
    if isinstance(verdicts_raw, dict) and "verdicts" in verdicts_raw:
        verdicts = verdicts_raw["verdicts"]
    elif isinstance(verdicts_raw, list):
        verdicts = verdicts_raw
    else:
        sys.stderr.write(
            "review_helper apply-verdicts: --verdicts must be a JSON array or "
            "an object with a 'verdicts' key\n"
        )
        return 2

    if not isinstance(verdicts, list):
        sys.stderr.write(
            "review_helper apply-verdicts: --verdicts must be a JSON array\n"
        )
        return 2

    result = apply_verdicts(findings, verdicts)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 5 handlers (report rendering)
# ---------------------------------------------------------------------------


def cmd_render_report(args: argparse.Namespace) -> int:
    """Render the /review report and write to specs/<feature>/review.md.

    Input: --partition <path>  (JSON object from apply-verdicts: confirmed/
                                dismissed/uncertain/contested)
           --feature <dir>     (feature directory, e.g. specs/001-auth/)
           --date <YYYY-MM-DD> (report date; required for determinism)
           --finders <comma>   (finder agent names invoked)
           --refuters <comma>  (refuter agent names invoked)
           --source-root <str> (Source Root value from CLAUDE.md)
           --framework <str>   (Framework / Language value)
           --scope-files <N>   (number of files in the assembled-feature diff)
           --finders-skipped <comma>  (skipped / not-installed finder names)
    Returns 0 on success, 2 on bad input.
    Output on stdout: JSON ack {"path": "<written>", "confirmed": N,
                                 "contested": N, "dismissed": N, "uncertain": N}.
    """
    from ._report import render_report, write_review_report

    partition_path = getattr(args, "partition", None)
    feature = getattr(args, "feature", None) or "."
    date_str = getattr(args, "date", None) or ""
    finders_raw = getattr(args, "finders", None) or ""
    refuters_raw = getattr(args, "refuters", None) or ""
    source_root = getattr(args, "source_root", None) or "(unset)"
    framework = getattr(args, "framework", None) or "(unset)"
    scope_files_raw = getattr(args, "scope_files", None) or "0"
    skipped_raw = getattr(args, "finders_skipped", None) or ""

    if not partition_path:
        sys.stderr.write(
            "review_helper render-report: --partition <path> required\n"
        )
        return 2
    if not date_str:
        sys.stderr.write(
            "review_helper render-report: --date <YYYY-MM-DD> required\n"
        )
        return 2

    finders = [f.strip() for f in finders_raw.split(",") if f.strip()]
    refuters = [r.strip() for r in refuters_raw.split(",") if r.strip()]
    finders_skipped = [s.strip() for s in skipped_raw.split(",") if s.strip()]

    try:
        n_scope_files = int(scope_files_raw)
    except ValueError:
        n_scope_files = 0

    try:
        with open(partition_path, "r", encoding="utf-8") as fh:
            partition = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper render-report: cannot read --partition file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper render-report: --partition file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(partition, dict):
        sys.stderr.write(
            "review_helper render-report: --partition must be a JSON object\n"
        )
        return 2

    content = render_report(
        partition=partition,
        feature=feature,
        date_str=date_str,
        finders=finders,
        refuters=refuters,
        source_root=source_root,
        framework=framework,
        n_scope_files=n_scope_files,
        finders_skipped=finders_skipped,
    )

    try:
        out_path = write_review_report(feature, content)
    except OSError as exc:
        sys.stderr.write(
            "review_helper render-report: cannot write review.md: "
            "{0}\n".format(exc)
        )
        return 2

    ack = {
        "path": out_path,
        "confirmed": len((partition.get("confirmed") or [])),
        "contested": len((partition.get("contested") or [])),
        "dismissed": len((partition.get("dismissed") or [])),
        "uncertain": len((partition.get("uncertain") or [])),
    }
    sys.stdout.write(json.dumps(ack, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_inline_summary(args: argparse.Namespace) -> int:
    """Render the ## Review Complete inline console block.

    Input: --partition <path>  (JSON object from apply-verdicts)
           --feature <dir>     (feature directory path)
           --finders-skipped <comma>  (skipped / not-installed finder names)
    Returns 0 on success, 2 on bad input.
    Output: the inline summary block as plain text (ends with newline).
    """
    from ._report import render_inline_summary

    partition_path = getattr(args, "partition", None)
    feature = getattr(args, "feature", None) or "."
    skipped_raw = getattr(args, "finders_skipped", None) or ""

    if not partition_path:
        sys.stderr.write(
            "review_helper render-inline-summary: --partition <path> required\n"
        )
        return 2

    finders_skipped = [s.strip() for s in skipped_raw.split(",") if s.strip()]

    try:
        with open(partition_path, "r", encoding="utf-8") as fh:
            partition = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "review_helper render-inline-summary: cannot read --partition file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "review_helper render-inline-summary: --partition file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(partition, dict):
        sys.stderr.write(
            "review_helper render-inline-summary: --partition must be a JSON object\n"
        )
        return 2

    summary = render_inline_summary(partition, feature, finders_skipped)
    sys.stdout.write(summary)
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
        "Read or update per-feature review session state phase/status (Phase 1).",
        cmd_check_status_and_flip,
    ),
    (
        "preflight",
        "Gate on setup-chain artefacts + populated constitution (Phase 1).",
        cmd_preflight,
    ),
    (
        "resolve-feature-scope",
        (
            "Compute the assembled-feature diff (merge-base..HEAD) and emit "
            "scope JSON with changed files + rendered scope block (Phase 2)."
        ),
        cmd_resolve_feature_scope,
    ),
    (
        "render-agent-brief",
        "Assemble per-agent review instruction block from references + scope (Phase 3).",
        cmd_render_agent_brief,
    ),
    (
        "consume-tmp",
        "Parse one agent tmp file into status + ParsedFinding list JSON (Phase 3).",
        cmd_consume_tmp,
    ),
    (
        "validate-findings",
        "Anti-hallucination guard: 5-check validation pipeline on ParsedFinding list (Phase 3).",
        cmd_validate_findings,
    ),
    (
        "route-refutation",
        "Group findings by author and assign each group a non-author refuter (Phase 4).",
        cmd_route_refutation,
    ),
    (
        "render-verify-brief",
        "Assemble refuter cross-examination instruction block (Phase 4).",
        cmd_render_verify_brief,
    ),
    (
        "consume-verdicts",
        "Parse one refuter verdict markdown file into status + verdict list JSON (Phase 4).",
        cmd_consume_verdicts,
    ),
    (
        "apply-verdicts",
        "Partition working findings by merged verdicts per D7 category rules (Phase 4).",
        cmd_apply_verdicts,
    ),
    (
        "render-report",
        "Render + write specs/<feature>/review.md from the apply-verdicts partition (Phase 5).",
        cmd_render_report,
    ),
    (
        "render-inline-summary",
        "Render ## Review Complete inline console block from the apply-verdicts partition (Phase 5).",
        cmd_render_inline_summary,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="review_helper",
        description=(
            "Helper for /review — the feature-level emergent cross-task review. "
            "Runs a 5-finder ensemble + refutation pass over the assembled "
            "feature diff; writes findings-only specs/[feature]/review.md."
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
                    "Path to the feature directory where review-state.json lives "
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
                    "Path to the feature directory (e.g. specs/001-auth/). "
                    "Included in the JSON output as context. Default: CWD."
                ),
            )
            sp.add_argument(
                "--source-root",
                default=None,
                dest="source_root",
                metavar="PATH",
                help=(
                    "Absolute path to the source tree where git runs. "
                    "In standalone mode, this is the repo root. "
                    "In wrapper mode, this is the inner project directory "
                    "(e.g. /wrapper/my-project). Default: CWD."
                ),
            )
            sp.add_argument(
                "--install-root",
                default=None,
                dest="install_root",
                metavar="PATH",
                help=(
                    "Absolute path to the forge install root "
                    "(where .devforge/ lives). Used for wrapper-mode path "
                    "prefixing so finders see install-root-relative paths. "
                    "Default: same as --source-root (standalone assumed)."
                ),
            )
            sp.add_argument(
                "--base",
                default=None,
                metavar="REF",
                help=(
                    "Git ref for the trunk the feature forked from "
                    "(e.g. 'main', 'origin/main'). "
                    "When omitted, auto-detect via: "
                    "origin/HEAD → main → develop → master. "
                    "Pass this when auto-detection fails (exit 2 will say so)."
                ),
            )

        elif verb == "render-agent-brief":
            sp.add_argument(
                "--agent",
                required=True,
                metavar="NAME",
                help=(
                    "Agent name: code-reviewer | architect | qa-reviewer | "
                    "security-reviewer | performance-analyst."
                ),
            )
            sp.add_argument(
                "--scope-block",
                required=True,
                dest="scope_block",
                metavar="PATH",
                help=(
                    "Path to a file whose content is the pre-rendered scope block "
                    "(the scope_block field from resolve-feature-scope JSON, or "
                    "any plain-text scope summary)."
                ),
            )
            sp.add_argument(
                "--references-dir",
                default=".claude/commands/review/references",
                dest="references_dir",
                metavar="DIR",
                help=(
                    "Directory containing anti-relitigation-preamble.md and "
                    "emergent-issue-checklist.md "
                    "(default: .claude/commands/review/references)."
                ),
            )
            sp.add_argument(
                "--tmp-path",
                default=None,
                dest="tmp_path",
                metavar="PATH",
                help=(
                    "Agent findings write-path emitted in the closing instruction. "
                    "When omitted, defaults to specs/.tmp-{agent-name}.md. "
                    "When provided, the given path is emitted verbatim."
                ),
            )

        elif verb == "consume-tmp":
            sp.add_argument(
                "--tmp",
                required=True,
                metavar="PATH",
                help="Path to the agent tmp file (specs/.tmp-{agent}.md).",
            )
            sp.add_argument(
                "--agent",
                default="",
                metavar="NAME",
                help=(
                    "Agent name hint used when the # Agent: header is absent "
                    "(default: 'unknown')."
                ),
            )

        elif verb == "validate-findings":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help="Path to a JSON file containing a list of ParsedFinding dicts.",
            )
            sp.add_argument(
                "--repo-root",
                default=".",
                dest="repo_root",
                metavar="DIR",
                help=(
                    "Repo root for resolving relative file paths in findings "
                    "(default: CWD)."
                ),
            )
            sp.add_argument(
                "--source-root",
                default="",
                dest="source_root",
                metavar="REL",
                help=(
                    "Optional subdirectory within repo-root (e.g. 'src'). "
                    "Tried first before repo-root when resolving paths "
                    "(default: empty — use repo-root directly)."
                ),
            )

        elif verb == "route-refutation":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON array of ParsedFinding dicts (the working "
                    "list after consensus/merge)."
                ),
            )
            sp.add_argument(
                "--finders",
                default="",
                metavar="NAMES",
                help=(
                    "Comma-separated list of present finder agent names from "
                    "Phase 2 (e.g. 'code-reviewer,architect,qa-reviewer,"
                    "security-reviewer,performance-analyst'). "
                    "Only present finders are eligible. performance-analyst and "
                    "design-auditor are finders only — neither is in the refuter "
                    "priority list and neither will ever be assigned as a refuter."
                ),
            )

        elif verb == "render-verify-brief":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON array of ParsedFinding dicts — the subset "
                    "routed to this refuter (from route-refutation output)."
                ),
            )
            sp.add_argument(
                "--refuter",
                required=True,
                metavar="NAME",
                help=(
                    "Refuter agent name: code-reviewer | architect | "
                    "qa-reviewer | security-reviewer."
                ),
            )
            sp.add_argument(
                "--references-dir",
                default=".claude/commands/review/references",
                dest="references_dir",
                metavar="DIR",
                help=(
                    "Directory containing refutation-preamble.md "
                    "(default: .claude/commands/review/references)."
                ),
            )
            sp.add_argument(
                "--scope-block",
                required=True,
                dest="scope_block",
                metavar="PATH",
                help=(
                    "Path to a file whose content is the pre-rendered scope "
                    "block (the scope_block field from resolve-feature-scope "
                    "JSON, or any plain-text scope summary)."
                ),
            )
            sp.add_argument(
                "--source-root",
                default=".",
                dest="source_root",
                help="Workspace / repo root label (default: CWD).",
            )
            sp.add_argument(
                "--tmp-path",
                default=None,
                dest="tmp_path",
                metavar="PATH",
                help=(
                    "Override the verdict file write-path in the output contract. "
                    "When omitted, defaults to '$WORKDIR/verdicts-<refuter>.md'. "
                    "When provided, the given path is emitted verbatim."
                ),
            )

        elif verb == "consume-verdicts":
            sp.add_argument(
                "--verdicts",
                required=True,
                metavar="PATH",
                help=(
                    "Path to the raw refuter markdown verdict file "
                    "(e.g. $WORKDIR/verdicts-code-reviewer.md)."
                ),
            )
            sp.add_argument(
                "--refuter",
                default="",
                metavar="NAME",
                help=(
                    "Refuter agent name hint used when the # Refuter: header "
                    "is absent (default: 'unknown')."
                ),
            )

        elif verb == "apply-verdicts":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON array of ParsedFinding dicts — the full "
                    "working list (after consensus/merge)."
                ),
            )
            sp.add_argument(
                "--verdicts",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the merged verdict list "
                    "(a bare JSON array of verdict dicts, or a consume-verdicts "
                    "output object with a 'verdicts' key)."
                ),
            )

        elif verb == "render-report":
            sp.add_argument(
                "--partition",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the apply-verdicts partition "
                    "(object with keys: confirmed, dismissed, uncertain, contested)."
                ),
            )
            sp.add_argument(
                "--feature",
                default=".",
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth/). "
                    "review.md is written here. Default: CWD."
                ),
            )
            sp.add_argument(
                "--date",
                required=True,
                metavar="YYYY-MM-DD",
                help=(
                    "Report date in YYYY-MM-DD format. "
                    "Required for deterministic output."
                ),
            )
            sp.add_argument(
                "--finders",
                default="",
                metavar="NAMES",
                help=(
                    "Comma-separated list of finder agent names invoked "
                    "(e.g. 'code-reviewer,architect,qa-reviewer,"
                    "security-reviewer,performance-analyst')."
                ),
            )
            sp.add_argument(
                "--refuters",
                default="",
                metavar="NAMES",
                help=(
                    "Comma-separated list of refuter agent names invoked "
                    "(e.g. 'code-reviewer,architect')."
                ),
            )
            sp.add_argument(
                "--source-root",
                default="(unset)",
                dest="source_root",
                metavar="STR",
                help="Source Root value from CLAUDE.md (default: '(unset)').",
            )
            sp.add_argument(
                "--framework",
                default="(unset)",
                metavar="STR",
                help="Framework / Language value from CLAUDE.md (default: '(unset)').",
            )
            sp.add_argument(
                "--scope-files",
                default="0",
                dest="scope_files",
                metavar="N",
                help="Number of files in the assembled-feature diff scope (default: 0).",
            )
            sp.add_argument(
                "--finders-skipped",
                default="",
                dest="finders_skipped",
                metavar="NAMES",
                help=(
                    "Comma-separated list of finder names that were skipped / "
                    "not installed (default: empty)."
                ),
            )

        elif verb == "render-inline-summary":
            sp.add_argument(
                "--partition",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the apply-verdicts partition "
                    "(object with keys: confirmed, dismissed, uncertain, contested)."
                ),
            )
            sp.add_argument(
                "--feature",
                default=".",
                metavar="DIR",
                help=(
                    "Feature directory path for display in the block "
                    "(default: CWD)."
                ),
            )
            sp.add_argument(
                "--finders-skipped",
                default="",
                dest="finders_skipped",
                metavar="NAMES",
                help=(
                    "Comma-separated list of finder names that were skipped / "
                    "not installed (default: empty)."
                ),
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
