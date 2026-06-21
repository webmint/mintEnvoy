"""argparse parser + dispatch + main entry for grill_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 1 ships 2 verbs:
  check-status-and-flip  — read or update per-feature grill session state
  preflight              — gate on setup-chain artefacts + spec/plan gate

Phase 2 ships 1 verb (scope resolution):
  resolve-scope          — resolve target feature + build path manifest (Phase 2)

Phase 3 ships 3 verbs (brief assembly + consume/validate):
  render-brief           — assemble the devils-advocate dispatch brief (Phase 3)
  consume-tmp            — parse one agent tmp file → ParsedFinding list JSON (Phase 3)
  validate-findings      — anti-hallucination guard on ParsedFinding list (Phase 3)

Phase 4 ships 4 verbs (refutation cross-examination, imported from _shared):
  route-refutation       — assign refuter per non-author policy (Phase 4)
  render-verify-brief    — assemble refuter cross-examination block (Phase 4)
  consume-verdicts       — parse refuter verdict file → verdict list JSON (Phase 4)
  apply-verdicts         — partition findings by verdict (Phase 4)

Phase 5 ships 2 verbs (report rendering + seed production):
  render-report          — render + write specs/<feature>/grill.md (Phase 5)
  write-seed             — build + write grill-seed.json backward handoff (Phase 5)

Key difference from _review/_cli.py:
  route-refutation passes priority=["code-reviewer", "qa-reviewer",
  "security-reviewer"] (architect-excluded) to route_refutation. /grill
  uses a single devils-advocate finder; the architect is NOT a finder and
  must not be a refuter either (it would cross-examine its own conceptual
  domain without having generated any finding).

Stdlib only. Targets Python 3.8+. No from __future__ import annotations.
"""

import argparse
import dataclasses
import json
import os
import sys

# ---------------------------------------------------------------------------
# _shared import resolution
#
# _shared is a sibling package under src/devforge/lib/. The sys.path insert
# below makes _shared importable when _cli.py is invoked directly or imported
# by grill_helper.py (the Python shim). In-repo tests add _LIB_DIR explicitly
# in their own path-setup block. The type: ignore[import] suppresses linters
# that can't resolve the path statically.
# ---------------------------------------------------------------------------

_LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

# /grill refuter priority: architect intentionally excluded.
# /grill dispatches a single devils-advocate finder; the architect is not a
# finder and must not be a refuter (it would be cross-examining findings in
# its own conceptual domain without having generated them).
_GRILL_REFUTER_PRIORITY = ["code-reviewer", "qa-reviewer", "security-reviewer"]


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_check_status_and_flip(args):
    # type: (argparse.Namespace) -> int
    """Read current grill state, optionally flip phase/status, emit JSON.

    Without --to: read current state (empty GrillState if none) and print.
    With --to: call flip_phase, print resulting state.
    Returns 0 on success, 1 on I/O error, 2 on ValueError (empty --to).
    """
    from ._state import GrillState, flip_phase, read_state, state_path

    feature_dir = getattr(args, "feature_dir", ".") or "."
    to_phase = getattr(args, "to", None)
    to_status = getattr(args, "status", None)

    sp = state_path(feature_dir)

    if to_phase is None:
        # Read-only mode.
        state = read_state(sp)
        if state is None:
            state = GrillState()
        sys.stdout.write(
            json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
        )
        return 0

    # Flip mode.
    try:
        state = flip_phase(sp, to_phase, to_status)
    except ValueError as exc:
        sys.stderr.write(
            "grill_helper check-status-and-flip: {0}\n".format(exc)
        )
        return 2
    except OSError as exc:
        sys.stderr.write(
            "grill_helper check-status-and-flip: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(
        json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
    )
    return 0


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Check setup-chain artefacts + spec/plan gate + memory excerpt.

    Always emits JSON to stdout before any non-zero exit.

    Returns:
      0 — all checks pass (setup chain ok, constitution present + populated,
          feature gate ok — spec.md + plan.md both exist)
      2 — missing setup-chain artefact, unpopulated constitution sentinel, or
          missing feature artefact (spec.md / plan.md)
    """
    from ._preflight import preflight_context

    workspace_root = getattr(args, "workspace_root", ".") or "."
    feature_dir = getattr(args, "feature_dir", None) or None

    result = preflight_context(workspace_root, feature_dir)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    # Gate 1: missing setup-chain artefacts.
    if not result["setup_chain_ok"]:
        missing = result.get("missing_artefacts", [])
        sys.stderr.write(
            "grill_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /init-forge → /generate-docs → /configure → /constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    # Gate 2: constitution unpopulated.
    if not result["constitution_populated"]:
        sys.stderr.write(
            "grill_helper preflight: constitution.md contains an unpopulated "
            "sentinel. Run /constitute to populate it before running /grill.\n"
        )
        return 2

    # Gate 3: feature artefacts (spec.md + plan.md) when feature_dir provided.
    if feature_dir is not None and not result["feature_gate_ok"]:
        missing_feat = result.get("missing_feature_artefacts", [])
        sys.stderr.write(
            "grill_helper preflight: feature artefacts missing in {0!r}: {1}\n"
            "Run /specify then /plan to produce these before running /grill.\n".format(
                feature_dir, ", ".join(missing_feat)
            )
        )
        return 2

    return 0


def cmd_resolve_scope(args):
    # type: (argparse.Namespace) -> int
    """Resolve the target feature and build the path manifest; emit JSON.

    Delegates entirely to _scope.cmd_resolve_scope (already a full handler).

    Returns:
      0 — success (manifest JSON emitted to stdout)
      2 — user error (feature dir not found, missing plan.md / spec.md, etc.)
    """
    from ._scope import cmd_resolve_scope as _impl
    return _impl(args)


def cmd_render_brief(args):
    # type: (argparse.Namespace) -> int
    """Assemble and print the devils-advocate dispatch brief.

    Reads manifest JSON from --manifest file, assembles brief from
    references_dir and the manifest paths.

    Returns 0 on success, 2 on error (missing file, bad JSON, etc.).
    """
    from ._brief import render_agent_brief
    from ._scope import GrillScopeManifest

    manifest_path = getattr(args, "manifest", None)
    if not manifest_path:
        sys.stderr.write(
            "grill_helper render-brief: --manifest <path> required\n"
        )
        return 2

    references_dir = (
        getattr(args, "references_dir", None)
        or ".claude/commands/grill/references"
    )

    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest_dict = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper render-brief: cannot read --manifest file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper render-brief: --manifest file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(manifest_dict, dict):
        sys.stderr.write(
            "grill_helper render-brief: --manifest must be a JSON object\n"
        )
        return 2

    # Reconstruct the GrillScopeManifest dataclass from the dict.
    known = {f.name for f in dataclasses.fields(GrillScopeManifest)}
    filtered = {k: v for k, v in manifest_dict.items() if k in known}
    manifest = GrillScopeManifest(**filtered)

    ring1_cap_raw = getattr(args, "ring1_cap", None)
    finding_cap_raw = getattr(args, "finding_cap", None)
    tmp_path = getattr(args, "tmp_path", None)

    ring1_cap = None
    if ring1_cap_raw is not None:
        try:
            ring1_cap = int(ring1_cap_raw)
        except (ValueError, TypeError):
            ring1_cap = None

    finding_cap = None
    if finding_cap_raw is not None:
        try:
            finding_cap = int(finding_cap_raw)
        except (ValueError, TypeError):
            finding_cap = None

    kwargs = {}
    if ring1_cap is not None:
        kwargs["ring1_cap"] = ring1_cap
    if finding_cap is not None:
        kwargs["finding_cap"] = finding_cap
    if tmp_path is not None:
        kwargs["tmp_path"] = tmp_path

    try:
        brief = render_agent_brief(
            manifest=manifest,
            references_dir=references_dir,
            **kwargs
        )
    except ValueError as exc:
        sys.stderr.write(
            "grill_helper render-brief: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(brief)
    if not brief.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_consume_tmp(args):
    # type: (argparse.Namespace) -> int
    """Parse one agent tmp file into status + ParsedFinding list.

    Delegates to _shared.parse_agent_tmp (same parser used by /audit and /review).

    Returns 0 on success, 2 on missing/unreadable file.
    When the tmp file does not exist the result carries status=STATUS_MISSING
    so callers can distinguish "agent never wrote output" from a failed/corrupt file.
    """
    from _shared._consume import parse_agent_tmp, STATUS_MISSING, STATUS_FAILED  # type: ignore[import]

    tmp_path = getattr(args, "tmp", None)
    if not tmp_path:
        sys.stderr.write(
            "grill_helper consume-tmp: --tmp <path> required\n"
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
        sys.stderr.write("grill_helper consume-tmp: {0}\n".format(exc))
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
        sys.stderr.write("grill_helper consume-tmp: {0}\n".format(exc))
        return 2

    result = parse_agent_tmp(text, agent_name=agent_hint or "unknown")
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_validate_findings(args):
    # type: (argparse.Namespace) -> int
    """Run anti-hallucination checks on a JSON list of ParsedFinding dicts.

    Delegates to _shared.validate_findings (same guard used by /audit and /review).

    Input: --findings <path>  (JSON list of ParsedFinding dicts)
           --repo-root <dir>  (root for resolving relative file paths)
           --source-root <rel>  (optional subdirectory within repo-root)

    Returns 0 on success, 2 on missing/unreadable file or bad input.
    """
    from _shared._validate import validate_findings  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "grill_helper validate-findings: --findings <path> required\n"
        )
        return 2

    repo_root = getattr(args, "repo_root", ".") or "."
    source_root = getattr(args, "source_root", "") or ""

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper validate-findings: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper validate-findings: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "grill_helper validate-findings: --findings must be a JSON array\n"
        )
        return 2

    try:
        result = validate_findings(findings, repo_root, source_root)
    except Exception as exc:
        sys.stderr.write(
            "grill_helper validate-findings: unexpected error: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 handlers (refutation / cross-examination) — shared engine
# ---------------------------------------------------------------------------


def cmd_route_refutation(args):
    # type: (argparse.Namespace) -> int
    """Group working findings by author and assign each group a non-author refuter.

    Grill's refuter roster EXCLUDES the architect: only code-reviewer,
    qa-reviewer, and security-reviewer are eligible.  /grill dispatches a
    single devils-advocate finder; the architect was not a finder and must not
    cross-examine its own conceptual domain here.  The exclusion is achieved by
    passing priority=_GRILL_REFUTER_PRIORITY to route_refutation.

    Input: --findings <path>  (JSON array of ParsedFinding dicts)
           --finders <comma-list>  (present finder agent names from Phase 2)
    Returns 0 on success, 2 on missing/bad input.
    Output: JSON list of {refuter, findings} routing groups, one per refuter.
    """
    from _shared._verify import route_refutation  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "grill_helper route-refutation: --findings <path> required\n"
        )
        return 2

    finders_raw = getattr(args, "finders", None) or ""
    present_finders = [f.strip() for f in finders_raw.split(",") if f.strip()]

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper route-refutation: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper route-refutation: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "grill_helper route-refutation: --findings must be a JSON array\n"
        )
        return 2

    # Pass grill's architect-excluded priority list.  This is the critical
    # difference from _review/_cli which uses the _shared default
    # [code-reviewer, architect, qa-reviewer, security-reviewer].
    result = route_refutation(findings, present_finders,
                              priority=_GRILL_REFUTER_PRIORITY)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_verify_brief(args):
    # type: (argparse.Namespace) -> int
    """Assemble a refuter's cross-examination instruction block.

    Input: --findings <path>       (JSON array of ParsedFinding dicts — the
                                    subset routed to this refuter)
           --refuter <name>        (refuter agent name)
           --references-dir <dir>  (directory containing refutation-preamble.md)
           --scope-block <path>    (file whose content is the pre-rendered scope
                                    block, e.g. the scope manifest JSON)
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
        or ".claude/commands/grill/references"
    )
    scope_block_path = getattr(args, "scope_block", None)
    source_root = getattr(args, "source_root", ".") or "."
    tmp_path = getattr(args, "tmp_path", None)

    if not findings_path:
        sys.stderr.write(
            "grill_helper render-verify-brief: --findings <path> required\n"
        )
        return 2
    if not refuter:
        sys.stderr.write(
            "grill_helper render-verify-brief: --refuter <name> required\n"
        )
        return 2
    if not scope_block_path:
        sys.stderr.write(
            "grill_helper render-verify-brief: --scope-block <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper render-verify-brief: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper render-verify-brief: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "grill_helper render-verify-brief: --findings must be a JSON array\n"
        )
        return 2

    try:
        with open(scope_block_path, "r", encoding="utf-8") as fh:
            scope_block = fh.read()
    except OSError as exc:
        sys.stderr.write(
            "grill_helper render-verify-brief: cannot read --scope-block file: "
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
            "grill_helper render-verify-brief: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(brief)
    if not brief.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_consume_verdicts(args):
    # type: (argparse.Namespace) -> int
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
            "grill_helper consume-verdicts: --verdicts <path> required\n"
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
        sys.stderr.write("grill_helper consume-verdicts: {0}\n".format(exc))
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
        sys.stderr.write("grill_helper consume-verdicts: {0}\n".format(exc))
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


def cmd_apply_verdicts(args):
    # type: (argparse.Namespace) -> int
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
            "grill_helper apply-verdicts: --findings <path> required\n"
        )
        return 2
    if not verdicts_path:
        sys.stderr.write(
            "grill_helper apply-verdicts: --verdicts <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper apply-verdicts: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper apply-verdicts: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "grill_helper apply-verdicts: --findings must be a JSON array\n"
        )
        return 2

    try:
        with open(verdicts_path, "r", encoding="utf-8") as fh:
            verdicts_raw = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper apply-verdicts: cannot read --verdicts file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper apply-verdicts: --verdicts file is not valid "
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
            "grill_helper apply-verdicts: --verdicts must be a JSON array or "
            "an object with a 'verdicts' key\n"
        )
        return 2

    if not isinstance(verdicts, list):
        sys.stderr.write(
            "grill_helper apply-verdicts: --verdicts must be a JSON array\n"
        )
        return 2

    result = apply_verdicts(findings, verdicts)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 5 handlers (report rendering + seed production)
# ---------------------------------------------------------------------------


def cmd_render_report(args):
    # type: (argparse.Namespace) -> int
    """Render the /grill report and write to specs/<feature>/grill.md.

    Input: --partition <path>    (JSON object from apply-verdicts)
           --feature <dir>       (feature directory, e.g. specs/001-auth/)
           --date <YYYY-MM-DD>   (report date; required for determinism)
           --finders <comma>     (finder agent names invoked)
           --refuters <comma>    (refuter agent names invoked)
           --source-root <str>   (Source Root value from CLAUDE.md)
           --framework <str>     (Framework / Language value)
           --scope-files <N>     (number of files in scope)
           --disposition <str>   (PROCEED|REVISE-PLAN|RE-ENTER-UPSTREAM|KILL)
           --rationale <str>     (rationale for the disposition)
           --re-entry-target <str>  (required when disposition=RE-ENTER-UPSTREAM)
           --finders-skipped <comma>  (skipped / not-installed finder names)
    Returns 0 on success, 2 on bad input.
    Output on stdout: JSON ack {"path": "<written>", "confirmed": N,
                                 "contested": N, "dismissed": N, "uncertain": N}.
    """
    from ._report import render_report, write_grill_report

    partition_path = getattr(args, "partition", None)
    feature = getattr(args, "feature", None) or "."
    date_str = getattr(args, "date", None) or ""
    finders_raw = getattr(args, "finders", None) or ""
    refuters_raw = getattr(args, "refuters", None) or ""
    source_root = getattr(args, "source_root", None) or "(unset)"
    framework = getattr(args, "framework", None) or "(unset)"
    scope_files_raw = getattr(args, "scope_files", None) or "0"
    disposition = getattr(args, "disposition", None) or ""
    rationale = getattr(args, "rationale", None) or ""
    re_entry_target = getattr(args, "re_entry_target", None) or None
    skipped_raw = getattr(args, "finders_skipped", None) or ""

    if not partition_path:
        sys.stderr.write(
            "grill_helper render-report: --partition <path> required\n"
        )
        return 2
    if not date_str:
        sys.stderr.write(
            "grill_helper render-report: --date <YYYY-MM-DD> required\n"
        )
        return 2
    if not disposition:
        sys.stderr.write(
            "grill_helper render-report: --disposition required\n"
        )
        return 2
    if not rationale:
        sys.stderr.write(
            "grill_helper render-report: --rationale required\n"
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
            "grill_helper render-report: cannot read --partition file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "grill_helper render-report: --partition file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(partition, dict):
        sys.stderr.write(
            "grill_helper render-report: --partition must be a JSON object\n"
        )
        return 2

    try:
        content = render_report(
            partition=partition,
            feature=feature,
            date_str=date_str,
            finders=finders,
            refuters=refuters,
            source_root=source_root,
            framework=framework,
            n_scope_files=n_scope_files,
            disposition=disposition,
            rationale=rationale,
            re_entry_target=re_entry_target,
            finders_skipped=finders_skipped,
        )
    except ValueError as exc:
        sys.stderr.write(
            "grill_helper render-report: {0}\n".format(exc)
        )
        return 2

    try:
        out_path = write_grill_report(feature, content)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper render-report: cannot write grill.md: "
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


def cmd_write_seed(args):
    # type: (argparse.Namespace) -> int
    """Build a ReEntrySeed and write it to <feature>/grill-seed.json.

    Input: --feature <dir>               (feature directory)
           --target-stage <stage>        (spec|discovery|research)
           --prior-conclusion <str>      (what the upstream stage concluded)
           --invalidating-evidence <str> (the grounded finding that invalidates it)
           --must-satisfy <str>          (what the re-run must additionally satisfy)
           --cycle-count <N>             (int >= 1, bounded-compounding counter)
           --carried-findings <comma>    (prior findings carried forward; may be empty)
           --provenance <str>            (pointer to source grill.md / plan path)
    Returns 0 on success, 2 on bad input (missing required field, invalid value).
    Output on stdout: JSON ack {"path": "<written>"}.
    """
    from ._report import build_seed, write_seed

    feature = getattr(args, "feature", None) or "."
    target_stage = getattr(args, "target_stage", None) or ""
    prior_conclusion = getattr(args, "prior_conclusion", None) or ""
    invalidating_evidence = getattr(args, "invalidating_evidence", None) or ""
    must_satisfy = getattr(args, "must_satisfy", None) or ""
    cycle_count_raw = getattr(args, "cycle_count", None) or "1"
    carried_raw = getattr(args, "carried_findings", None) or ""
    provenance = getattr(args, "provenance", None) or ""

    if not target_stage:
        sys.stderr.write(
            "grill_helper write-seed: --target-stage required\n"
        )
        return 2
    if not prior_conclusion:
        sys.stderr.write(
            "grill_helper write-seed: --prior-conclusion required\n"
        )
        return 2
    if not invalidating_evidence:
        sys.stderr.write(
            "grill_helper write-seed: --invalidating-evidence required\n"
        )
        return 2
    if not must_satisfy:
        sys.stderr.write(
            "grill_helper write-seed: --must-satisfy required\n"
        )
        return 2
    if not provenance:
        sys.stderr.write(
            "grill_helper write-seed: --provenance required\n"
        )
        return 2

    try:
        cycle_count = int(cycle_count_raw)
    except ValueError:
        sys.stderr.write(
            "grill_helper write-seed: --cycle-count must be an integer, "
            "got {0!r}\n".format(cycle_count_raw)
        )
        return 2

    carried_findings = [c.strip() for c in carried_raw.split(",") if c.strip()] \
        if carried_raw.strip() else []

    try:
        seed = build_seed(
            target_stage=target_stage,
            feature=feature,
            prior_conclusion=prior_conclusion,
            invalidating_evidence=invalidating_evidence,
            must_satisfy=must_satisfy,
            cycle_count=cycle_count,
            carried_findings=carried_findings,
            provenance=provenance,
        )
    except ValueError as exc:
        sys.stderr.write(
            "grill_helper write-seed: {0}\n".format(exc)
        )
        return 2

    try:
        out_path = write_seed(feature, seed)
    except OSError as exc:
        sys.stderr.write(
            "grill_helper write-seed: cannot write grill-seed.json: "
            "{0}\n".format(exc)
        )
        return 2

    ack = {"path": out_path}
    sys.stdout.write(json.dumps(ack, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# _SUBCOMMAND_REGISTRY is the extension point for new verbs.
# Each entry is a (verb_name, help_text, handler_function) triple.
# To add a Phase-N+ verb:
#   1. Write the cmd_<verb> function above.
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "check-status-and-flip",
        "Read or update per-feature grill session state phase/status (Phase 1).",
        cmd_check_status_and_flip,
    ),
    (
        "preflight",
        "Gate on setup-chain artefacts + populated constitution + spec/plan (Phase 1).",
        cmd_preflight,
    ),
    (
        "resolve-scope",
        "Resolve the target feature and build the static path manifest JSON (Phase 2).",
        cmd_resolve_scope,
    ),
    (
        "render-brief",
        "Assemble the devils-advocate dispatch brief from manifest + references (Phase 3).",
        cmd_render_brief,
    ),
    (
        "consume-tmp",
        "Parse one agent tmp file into status + ParsedFinding list JSON (Phase 3).",
        cmd_consume_tmp,
    ),
    (
        "validate-findings",
        "Anti-hallucination guard: validation pipeline on ParsedFinding list (Phase 3).",
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
        "Render + write specs/<feature>/grill.md from the apply-verdicts partition (Phase 5).",
        cmd_render_report,
    ),
    (
        "write-seed",
        "Build + write grill-seed.json backward handoff for RE-ENTER-UPSTREAM (Phase 5).",
        cmd_write_seed,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="grill_helper",
        description=(
            "Helper for /grill — the plan-level adversarial attack. "
            "Dispatches a single devils-advocate agent to grill the plan "
            "and spec before /breakdown; emits a 4-way disposition verdict "
            "(PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL) + optional "
            "backward grill-seed.json handoff for upstream re-entry."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (object) -> None
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
                    "Path to the feature directory where grill-state.json lives "
                    "(e.g. specs/001-auth/). Default: CWD."
                ),
            )
            sp.add_argument(
                "--to",
                default=None,
                metavar="PHASE",
                help=(
                    "Phase label to flip to (e.g. 'scope', 'attack', '1'). "
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
                    "Workspace root to check for setup-chain artefacts "
                    "(constitution.md / CLAUDE.md / .devforge/). "
                    "Default: CWD."
                ),
            )
            sp.add_argument(
                "--feature-dir",
                default=None,
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Feature directory to check for spec.md + plan.md "
                    "(e.g. specs/001-auth/). "
                    "When omitted, the feature gate is skipped."
                ),
            )

        elif verb == "resolve-scope":
            sp.add_argument(
                "--feature",
                default=None,
                metavar="DIR_OR_PLAN",
                help=(
                    "Explicit feature directory (e.g. specs/001-auth/) or a "
                    "path to a plan.md file. "
                    "When omitted, auto-detects the lowest-numbered feature "
                    "under specs/ that has a plan.md."
                ),
            )
            sp.add_argument(
                "--workspace-root",
                default=None,
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Workspace install root (where constitution.md / CLAUDE.md "
                    "live). Default: CWD."
                ),
            )
            sp.add_argument(
                "--specs-dir",
                default=None,
                dest="specs_dir",
                metavar="DIR",
                help=(
                    "Override for the specs/ directory "
                    "(default: <workspace-root>/specs)."
                ),
            )

        elif verb == "render-brief":
            sp.add_argument(
                "--manifest",
                required=True,
                metavar="PATH",
                help=(
                    "Path to the JSON file produced by resolve-scope "
                    "(a GrillScopeManifest serialized as JSON)."
                ),
            )
            sp.add_argument(
                "--references-dir",
                default=".claude/commands/grill/references",
                dest="references_dir",
                metavar="DIR",
                help=(
                    "Directory containing anti-relitigation-preamble.md and "
                    "design-attack-checklist.md "
                    "(default: .claude/commands/grill/references)."
                ),
            )
            sp.add_argument(
                "--ring1-cap",
                default=None,
                dest="ring1_cap",
                metavar="N",
                help=(
                    "Maximum Ring-1 CBM entries the agent should follow "
                    "(default: 15)."
                ),
            )
            sp.add_argument(
                "--finding-cap",
                default=None,
                dest="finding_cap",
                metavar="N",
                help=(
                    "Maximum findings the agent should report "
                    "(default: 30)."
                ),
            )
            sp.add_argument(
                "--tmp-path",
                default=None,
                dest="tmp_path",
                metavar="PATH",
                help=(
                    "Agent findings write-path emitted in the output contract. "
                    "When omitted, defaults to specs/.tmp-devils-advocate.md."
                ),
            )

        elif verb == "consume-tmp":
            sp.add_argument(
                "--tmp",
                required=True,
                metavar="PATH",
                help="Path to the agent tmp file (specs/.tmp-devils-advocate.md).",
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
                    "list after consume-tmp / validate-findings)."
                ),
            )
            sp.add_argument(
                "--finders",
                default="",
                metavar="NAMES",
                help=(
                    "Comma-separated list of present finder agent names "
                    "(e.g. 'devils-advocate'). "
                    "Only present finders are eligible as refuters. "
                    "Architect is never a refuter in /grill."
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
                    "Refuter agent name: code-reviewer | qa-reviewer | "
                    "security-reviewer. (Architect is excluded from grill.)"
                ),
            )
            sp.add_argument(
                "--references-dir",
                default=".claude/commands/grill/references",
                dest="references_dir",
                metavar="DIR",
                help=(
                    "Directory containing refutation-preamble.md "
                    "(default: .claude/commands/grill/references)."
                ),
            )
            sp.add_argument(
                "--scope-block",
                required=True,
                dest="scope_block",
                metavar="PATH",
                help=(
                    "Path to a file whose content is the pre-rendered scope "
                    "block (plain text summary of what is being reviewed)."
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
                    "When omitted, defaults to '$WORKDIR/verdicts-<refuter>.md'."
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
                    "working list."
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
                    "grill.md is written here. Default: CWD."
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
                    "(e.g. 'devils-advocate')."
                ),
            )
            sp.add_argument(
                "--refuters",
                default="",
                metavar="NAMES",
                help=(
                    "Comma-separated list of refuter agent names invoked "
                    "(e.g. 'code-reviewer,security-reviewer')."
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
                help="Number of files in the plan scope (default: 0).",
            )
            sp.add_argument(
                "--disposition",
                required=True,
                metavar="VERDICT",
                help=(
                    "4-way verdict: PROCEED | REVISE-PLAN | "
                    "RE-ENTER-UPSTREAM | KILL."
                ),
            )
            sp.add_argument(
                "--rationale",
                required=True,
                metavar="TEXT",
                help="Human-readable rationale for the disposition (non-empty).",
            )
            sp.add_argument(
                "--re-entry-target",
                default=None,
                dest="re_entry_target",
                metavar="STAGE",
                help=(
                    "Target upstream stage for RE-ENTER-UPSTREAM: "
                    "spec | discovery | research. "
                    "Required when --disposition=RE-ENTER-UPSTREAM; "
                    "must be absent for other verdicts."
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

        elif verb == "write-seed":
            sp.add_argument(
                "--feature",
                default=".",
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth/). "
                    "grill-seed.json is written here. Default: CWD."
                ),
            )
            sp.add_argument(
                "--target-stage",
                required=True,
                dest="target_stage",
                metavar="STAGE",
                help=(
                    "Upstream stage to re-enter: spec | discovery | research."
                ),
            )
            sp.add_argument(
                "--prior-conclusion",
                required=True,
                dest="prior_conclusion",
                metavar="TEXT",
                help="What the upstream stage concluded that is now invalidated.",
            )
            sp.add_argument(
                "--invalidating-evidence",
                required=True,
                dest="invalidating_evidence",
                metavar="TEXT",
                help=(
                    "Grounded grill finding (verbatim quote / ref) that "
                    "invalidates the prior_conclusion."
                ),
            )
            sp.add_argument(
                "--must-satisfy",
                required=True,
                dest="must_satisfy",
                metavar="TEXT",
                help="What the re-run must additionally satisfy.",
            )
            sp.add_argument(
                "--cycle-count",
                default="1",
                dest="cycle_count",
                metavar="N",
                help=(
                    "Bounded-compounding-loop counter (int >= 1). "
                    "Increment on each grill loop. Default: 1."
                ),
            )
            sp.add_argument(
                "--carried-findings",
                default="",
                dest="carried_findings",
                metavar="ITEMS",
                help=(
                    "Comma-separated list of prior finding descriptions carried "
                    "forward (monotonic compounding). May be empty."
                ),
            )
            sp.add_argument(
                "--provenance",
                required=True,
                metavar="PATH",
                help="Pointer to the source grill.md / plan path.",
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (object) -> int
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
