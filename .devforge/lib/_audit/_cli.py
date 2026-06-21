"""argparse parser + dispatch + main entry for audit_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 0 ships 4 verbs:
  resolve-mode        — parse raw $ARGUMENTS into mode + knobs
  check-agents        — verify audit-capable agent .md files are present
  preflight-context   — best-effort read of constitution, CLAUDE.md, memory
  check-status-and-flip — read or update session state phase/status

Phase 1 adds 2 verbs:
  compute-hotspots    — enumerate files, compute churn/loc, merge CBM caller
                        counts, score + rank → JSON (requires --callers payload)
  render-hotspot-summary — render a human-readable table from a hotspot JSON

Phase 2 adds 3 verbs:
  resolve-scope       — resolve file list + metadata from a mode_result JSON
  render-scope-block  — render human-readable scope summary from scope JSON
  render-agent-brief  — assemble per-agent audit instruction block

Phase 3 adds 5 verbs:
  consume-tmp         — parse one agent tmp file → ParsedFinding list JSON
  validate-findings   — anti-hallucination guard on a list of ParsedFinding dicts
  compute-consensus   — cross-agent exact-match merge with severity bump
  force-rank-top10    — force-rank Top 10 (or Top 5 in narrow mode) by score
  map-recurring-issues — tag findings with RECURRING/RECURRING-SPREAD from past

Phase 4 adds 3 verbs:
  render-report         — render + write the full audit markdown report
  render-inline-summary — render the ## Audit Complete console block
  cleanup-tmps          — delete leftover audits/.tmp-*.md files

Phase 5 adds 1 verb:
  merge-passes        — union-merge per-pass validated-findings JSON files via
                        tolerant line clustering
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_resolve_mode(args: argparse.Namespace) -> int:
    """Parse raw $ARGUMENTS string and emit mode + knobs as JSON.

    Returns 0 on success, 2 when parse error (error field is set).
    When --passes N was clamped, a one-line note is written to stderr
    (stdout carries only the JSON result for the orchestrator).
    """
    from ._preflight import resolve_mode

    raw = getattr(args, "arguments", "") or ""
    try:
        result = resolve_mode(raw)
    except OSError as exc:
        sys.stderr.write("audit_helper resolve-mode: I/O error: {0}\n".format(exc))
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result.get("error"):
        sys.stderr.write("audit_helper resolve-mode: {0}\n".format(result["error"]))
        return 2
    if result.get("passes_clamp_note"):
        sys.stderr.write(
            "audit_helper resolve-mode: note: {0}\n".format(result["passes_clamp_note"])
        )
    return 0


def cmd_check_agents(args: argparse.Namespace) -> int:
    """Check which audit-capable agent .md files are present and emit JSON.

    Always prints the JSON result first.
    Returns 3 when all_missing is True (fail-fast signal for shell callers),
    else 0.
    """
    from ._preflight import check_agents

    agents_dir = getattr(args, "agents_dir", ".claude/agents")
    try:
        result = check_agents(agents_dir)
    except OSError as exc:
        sys.stderr.write("audit_helper check-agents: I/O error: {0}\n".format(exc))
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result.get("all_missing"):
        return 3
    return 0


def cmd_preflight_context(args: argparse.Namespace) -> int:
    """Read context sources and emit JSON. Orchestrator decides what to do.

    Returns 0 always (helper just reports; caller decides whether to stop).
    """
    from ._preflight import preflight_context

    workspace_root = getattr(args, "workspace_root", ".") or "."
    try:
        result = preflight_context(workspace_root)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper preflight-context: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_check_status_and_flip(args: argparse.Namespace) -> int:
    """Read current audit state, optionally flip phase/status, emit JSON.

    Without --to: read current state (empty AuditState if none) and print.
    With --to: call flip_phase, print resulting state.
    Returns 0 on success, 1 on I/O error, 2 on ValueError (empty --to).
    """
    from ._state import AuditState, flip_phase, read_state, state_path

    workspace_root = getattr(args, "workspace_root", ".") or "."
    to_phase = getattr(args, "to", None)
    to_status = getattr(args, "status", None)

    sp = state_path(workspace_root)

    if to_phase is None:
        # Read-only mode. read_state absorbs OSError internally and returns
        # None (file absent or unreadable), so no try/except is needed here.
        state = read_state(sp)
        if state is None:
            state = AuditState()
        sys.stdout.write(
            json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
        )
        return 0

    # Flip mode.
    try:
        state = flip_phase(sp, to_phase, to_status)
    except ValueError as exc:
        sys.stderr.write(
            "audit_helper check-status-and-flip: {0}\n".format(exc)
        )
        return 2
    except OSError as exc:
        sys.stderr.write(
            "audit_helper check-status-and-flip: I/O error: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(
        json.dumps(dataclasses.asdict(state), indent=2, sort_keys=True) + "\n"
    )
    return 0


# ---------------------------------------------------------------------------
# Phase 1 handlers
# ---------------------------------------------------------------------------

_CBM_GATE_MSG = (
    "hotspot scoring requires CBM caller counts (--callers <json>); "
    "CBM is not optional for --top mode. "
    "Ensure the codebase-memory-mcp index exists and the orchestrator "
    "supplied the caller payload.\n"
)


def _parse_weights_arg(weights_str):
    # type: (str) -> dict
    """Parse a 'c=0.5,k=0.4,s=0.1' style string into a dict.

    Raises ValueError on parse errors (propagated to caller for stderr + exit 2).
    """
    parsed = {}
    for part in weights_str.split(","):
        if "=" not in part:
            raise ValueError(
                "expected key=value pair, got {0!r}".format(part)
            )
        key, _, val_str = part.partition("=")
        key = key.strip()
        try:
            parsed[key] = float(val_str.strip())
        except ValueError:
            raise ValueError(
                "weights value for {0!r} is not a float: {1!r}".format(
                    key, val_str
                )
            )
    return parsed


def cmd_compute_hotspots(args: argparse.Namespace) -> int:
    """Enumerate source files, score them, emit JSON hotspot result.

    Requires --callers <path>; exits 2 if absent or unreadable.
    """
    from ._hotspot import run_compute_hotspots, parse_weights

    callers_path = getattr(args, "callers", None)
    if not callers_path:
        sys.stderr.write(_CBM_GATE_MSG)
        return 2

    try:
        with open(callers_path, "r", encoding="utf-8") as fh:
            callers_payload = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper compute-hotspots: cannot read --callers file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper compute-hotspots: --callers file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    repo_root = getattr(args, "repo_root", ".") or "."
    top_n = getattr(args, "top", 25)
    since = getattr(args, "since", "90.days.ago") or "90.days.ago"
    weights_str = getattr(args, "weights", None)

    weights_dict = None
    if weights_str:
        try:
            raw = _parse_weights_arg(weights_str)
            weights_dict = parse_weights(raw)
        except ValueError as exc:
            sys.stderr.write(
                "audit_helper compute-hotspots: invalid --weights: "
                "{0}\n".format(exc)
            )
            return 2

    try:
        result = run_compute_hotspots(
            repo_root=repo_root,
            callers_payload=callers_payload,
            top_n=top_n,
            weights=weights_dict,
            since=since,
        )
    except (ValueError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(
            "audit_helper compute-hotspots: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_hotspot_summary(args: argparse.Namespace) -> int:
    """Render a human-readable table from a hotspot result JSON file.

    Prints to stdout. Returns 0 on success, 2 on I/O or parse error.
    """
    hotspot_path = getattr(args, "hotspot", None)
    if not hotspot_path:
        sys.stderr.write(
            "audit_helper render-hotspot-summary: --hotspot <path> required\n"
        )
        return 2

    try:
        with open(hotspot_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-hotspot-summary: cannot read file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-hotspot-summary: not valid JSON: "
            "{0}\n".format(exc)
        )
        return 2

    top = data.get("top", [])
    next_cands = data.get("next_candidates", [])
    total = data.get("total_files_scored", 0)
    weights = data.get("weights", {})

    lines = []
    lines.append(
        "Hotspot summary  (top={0}, total_scored={1})".format(
            len(top), total
        )
    )
    w_str = "c={c}, k={k}, s={s}".format(
        c=weights.get("c", "?"),
        k=weights.get("k", "?"),
        s=weights.get("s", "?"),
    )
    lines.append("Weights: {0}".format(w_str))
    lines.append("")

    if top:
        lines.append("Top {0} hotspots:".format(len(top)))
        for item in top:
            lines.append(
                "{rank}. {file} · score={score:.2f} · "
                "(churn={churn}, callers={callers}, size={size_loc})".format(
                    rank=item.get("rank", "?"),
                    file=item.get("file", "?"),
                    score=float(item.get("score", 0)),
                    churn=item.get("churn", 0),
                    callers=item.get("callers", 0),
                    size_loc=item.get("size_loc", 0),
                )
            )
    else:
        lines.append("Top hotspots: (none)")

    lines.append("")

    if next_cands:
        lines.append("Next {0} candidates:".format(len(next_cands)))
        for item in next_cands:
            lines.append(
                "{rank}. {file} · score={score:.2f} · "
                "(churn={churn}, callers={callers}, size={size_loc})".format(
                    rank=item.get("rank", "?"),
                    file=item.get("file", "?"),
                    score=float(item.get("score", 0)),
                    churn=item.get("churn", 0),
                    callers=item.get("callers", 0),
                    size_loc=item.get("size_loc", 0),
                )
            )
    else:
        lines.append("Next candidates: (none)")

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 2 handlers
# ---------------------------------------------------------------------------


def cmd_resolve_scope(args: argparse.Namespace) -> int:
    """Resolve file list + metadata from a mode_result JSON file.

    Reads mode_result from --mode-result <path>.  Optional --hotspot <path>
    for hotspot mode (extracts top file list).  Prints JSON to stdout.
    Returns 0 on success, 2 on error (including scope resolution error).
    """
    from ._scope import resolve_scope

    mode_result_path = getattr(args, "mode_result", None)
    if not mode_result_path:
        sys.stderr.write(
            "audit_helper resolve-scope: --mode-result <path> required\n"
        )
        return 2

    try:
        with open(mode_result_path, "r", encoding="utf-8") as fh:
            mode_result = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper resolve-scope: cannot read --mode-result file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper resolve-scope: --mode-result file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    repo_root = getattr(args, "repo_root", ".") or "."

    hotspot_files = None
    hotspot_path = getattr(args, "hotspot", None)
    if hotspot_path:
        try:
            with open(hotspot_path, "r", encoding="utf-8") as fh:
                hotspot_data = json.load(fh)
            hotspot_files = [
                fs["file"] for fs in hotspot_data.get("top", [])
                if "file" in fs
            ]
        except OSError as exc:
            sys.stderr.write(
                "audit_helper resolve-scope: cannot read --hotspot file: "
                "{0}\n".format(exc)
            )
            return 2
        except (json.JSONDecodeError, TypeError) as exc:
            sys.stderr.write(
                "audit_helper resolve-scope: --hotspot file is not valid "
                "JSON: {0}\n".format(exc)
            )
            return 2

    result = resolve_scope(mode_result, repo_root, hotspot_files=hotspot_files)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result.get("error"):
        sys.stderr.write(
            "audit_helper resolve-scope: {0}\n".format(result["error"])
        )
        return 2
    return 0


def cmd_render_scope_block(args: argparse.Namespace) -> int:
    """Render a human-readable scope summary from a resolve-scope JSON file.

    Prints to stdout. Returns 0 on success, 2 on I/O or parse error.
    """
    from ._scope import render_scope_block

    scope_path = getattr(args, "scope", None)
    if not scope_path:
        sys.stderr.write(
            "audit_helper render-scope-block: --scope <path> required\n"
        )
        return 2

    try:
        with open(scope_path, "r", encoding="utf-8") as fh:
            scope_result = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-scope-block: cannot read --scope file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-scope-block: --scope file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    source_root = getattr(args, "source_root", ".") or "."
    block = render_scope_block(scope_result, source_root)
    sys.stdout.write(block + "\n")
    return 0


def cmd_render_agent_brief(args: argparse.Namespace) -> int:
    """Assemble and print the per-agent audit instruction block.

    Reads scope from --scope JSON, renders scope block, then assembles brief.
    Returns 0 on success, 2 on error (unknown agent, missing file, etc.).
    """
    from ._scope import render_agent_brief, render_scope_block

    agent = getattr(args, "agent", None)
    if not agent:
        sys.stderr.write(
            "audit_helper render-agent-brief: --agent <name> required\n"
        )
        return 2

    scope_path = getattr(args, "scope", None)
    if not scope_path:
        sys.stderr.write(
            "audit_helper render-agent-brief: --scope <path> required\n"
        )
        return 2

    try:
        with open(scope_path, "r", encoding="utf-8") as fh:
            scope_result = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-agent-brief: cannot read --scope file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-agent-brief: --scope file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    source_root = getattr(args, "source_root", ".") or "."
    references_dir = (
        getattr(args, "references_dir", None)
        or ".claude/commands/audit/references"
    )

    extra_context = ""
    extra_context_file = getattr(args, "extra_context_file", None)
    if extra_context_file:
        try:
            with open(extra_context_file, "r", encoding="utf-8") as fh:
                extra_context = fh.read()
        except OSError as exc:
            sys.stderr.write(
                "audit_helper render-agent-brief: cannot read "
                "--extra-context-file: {0}\n".format(exc)
            )
            return 2

    finding_cap = getattr(args, "finding_cap", 30) or 30
    tmp_path = getattr(args, "tmp_path", None)

    scope_block = render_scope_block(scope_result, source_root)

    try:
        brief = render_agent_brief(
            agent=agent,
            references_dir=references_dir,
            scope_block=scope_block,
            source_root=source_root,
            extra_context=extra_context,
            finding_cap=finding_cap,
            tmp_path=tmp_path,
        )
    except ValueError as exc:
        sys.stderr.write(
            "audit_helper render-agent-brief: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(brief + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 3 handlers
# ---------------------------------------------------------------------------


def cmd_consume_tmp(args: argparse.Namespace) -> int:
    """Parse one agent tmp file into status + ParsedFinding list.

    Returns 0 on success, 2 on missing/unreadable file or bad input.
    The result JSON always includes a 'status' field; 'failed' status
    still exits 0 (the caller decides whether to stop the pipeline).

    When the tmp file does not exist (FileNotFoundError) the result carries
    status=STATUS_MISSING so callers can distinguish "agent never wrote output"
    from "agent wrote a failed/corrupt file".  Other OSError conditions
    (permissions, etc.) produce status=STATUS_FAILED.
    """
    from _shared._consume import parse_agent_tmp, STATUS_MISSING, STATUS_FAILED  # type: ignore[import]

    tmp_path = getattr(args, "tmp", None)
    if not tmp_path:
        sys.stderr.write(
            "audit_helper consume-tmp: --tmp <path> required\n"
        )
        return 2

    agent_hint = getattr(args, "agent", "") or ""

    try:
        with open(tmp_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError as exc:
        # File was never written by the agent → distinct "missing" status
        result = {
            "status": STATUS_MISSING,
            "reason": "tmp file not found: {0}".format(exc),
            "agent": agent_hint or "unknown",
            "finding_count": 0,
            "findings": [],
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stderr.write("audit_helper consume-tmp: {0}\n".format(exc))
        return 2
    except OSError as exc:
        # File exists but is unreadable (permissions, etc.) → failed
        result = {
            "status": STATUS_FAILED,
            "reason": "cannot read tmp file: {0}".format(exc),
            "agent": agent_hint or "unknown",
            "finding_count": 0,
            "findings": [],
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stderr.write("audit_helper consume-tmp: {0}\n".format(exc))
        return 2

    result = parse_agent_tmp(text, agent_name=agent_hint or "unknown")
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_validate_findings(args: argparse.Namespace) -> int:
    """Run anti-hallucination checks on a JSON list of ParsedFinding dicts.

    Input: --findings <path>  (JSON list of ParsedFinding dicts)
           --repo-root <dir>  (root for resolving relative file paths)
           --source-root <rel>  (optional subdirectory within repo-root)

    Returns 0 on success, 2 on missing/unreadable file or bad input.
    """
    from _shared._validate import validate_findings  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "audit_helper validate-findings: --findings <path> required\n"
        )
        return 2

    repo_root = getattr(args, "repo_root", ".") or "."
    source_root = getattr(args, "source_root", "") or ""

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper validate-findings: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper validate-findings: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper validate-findings: --findings must be a JSON array\n"
        )
        return 2

    try:
        result = validate_findings(findings, repo_root, source_root)
    except Exception as exc:
        sys.stderr.write(
            "audit_helper validate-findings: unexpected error: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_compute_consensus(args: argparse.Namespace) -> int:
    """Dedup findings by exact (file, line, category) into one representative each.

    Same-location same-category findings (including a single agent's
    wording-varied re-reports) collapse to one; groups with >=2 distinct agents
    are corroborated with a [CROSS-AGENT] tag + a one-level severity bump. Each
    representative carries merged_count (raw findings collapsed). No SHA-1/hash,
    no pattern-text, no semantic matching.

    Input: --findings <path>  (JSON list of ParsedFinding dicts, all agents combined)
    Returns 0 on success, 2 on missing/bad input.
    """
    from _shared._consensus import compute_consensus  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "audit_helper compute-consensus: --findings <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper compute-consensus: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper compute-consensus: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper compute-consensus: --findings must be a JSON array\n"
        )
        return 2

    result = compute_consensus(findings)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_force_rank_top10(args: argparse.Namespace) -> int:
    """Force-rank findings by score; output top 10 (or top 5 in narrow mode).

    Input: --findings <path>  (JSON list of ParsedFinding dicts)
           --narrow           (flag: output top 5 instead of top 10)
    Returns 0 on success, 2 on missing/bad input.
    """
    from ._rank import force_rank

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "audit_helper force-rank-top10: --findings <path> required\n"
        )
        return 2

    narrow = getattr(args, "narrow", False)

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper force-rank-top10: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper force-rank-top10: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper force-rank-top10: --findings must be a JSON array\n"
        )
        return 2

    result = force_rank(findings, narrow=narrow)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_map_recurring_issues(args: argparse.Namespace) -> int:
    """Tag findings with RECURRING/RECURRING-SPREAD from past findings list.

    Input: --findings <path>   (JSON list of current ParsedFinding dicts)
           --recurring <path>  (JSON list of {file, fingerprint} past entries)
    Returns 0 on success, 2 on missing/bad input.
    """
    from ._rank import map_recurring_issues

    findings_path = getattr(args, "findings", None)
    recurring_path = getattr(args, "recurring", None)

    if not findings_path:
        sys.stderr.write(
            "audit_helper map-recurring-issues: --findings <path> required\n"
        )
        return 2
    if not recurring_path:
        sys.stderr.write(
            "audit_helper map-recurring-issues: --recurring <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper map-recurring-issues: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper map-recurring-issues: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    try:
        with open(recurring_path, "r", encoding="utf-8") as fh:
            past_findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper map-recurring-issues: cannot read --recurring file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper map-recurring-issues: --recurring file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper map-recurring-issues: --findings must be a JSON array\n"
        )
        return 2
    if not isinstance(past_findings, list):
        sys.stderr.write(
            "audit_helper map-recurring-issues: --recurring must be a JSON array\n"
        )
        return 2

    result = map_recurring_issues(findings, past_findings)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 4 handlers
# ---------------------------------------------------------------------------


def cmd_render_report(args: argparse.Namespace) -> int:
    """Render the full audit markdown report and write to disk.

    Reads report_dict JSON from --report <path>, renders via _report.render_report,
    writes to <audits_dir>/YYYY-MM-DD-audit.md (with collision suffix), prints
    the final path to stdout, and returns 0.  Bad input exits 2.
    """
    from ._report import render_report, write_report

    report_path = getattr(args, "report", None)
    if not report_path:
        sys.stderr.write(
            "audit_helper render-report: --report <path> required\n"
        )
        return 2

    audits_dir = getattr(args, "audits_dir", None) or "audits"
    date_str = getattr(args, "date", None)
    if not date_str:
        sys.stderr.write(
            "audit_helper render-report: --date <YYYY-MM-DD> required\n"
        )
        return 2

    try:
        with open(report_path, "r", encoding="utf-8") as fh:
            report_dict = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-report: cannot read --report file: {0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-report: --report file is not valid JSON: "
            "{0}\n".format(exc)
        )
        return 2

    # Inject passes_run from CLI arg into report_dict.  The render layer reads
    # it from the dict (default 1 when absent), so single-pass callers that
    # omit --passes-run get byte-identical output.
    passes_run = getattr(args, "passes_run", 1) or 1
    if isinstance(passes_run, int) and not isinstance(passes_run, bool) and passes_run >= 1:
        report_dict["passes_run"] = passes_run
    # else: leave report_dict unchanged; render_report defaults to 1.

    try:
        content = render_report(report_dict)
        out_path = write_report(audits_dir, date_str, content)
    except Exception as exc:
        sys.stderr.write(
            "audit_helper render-report: failed to render/write report: "
            "{0}\n".format(exc)
        )
        return 2

    sys.stdout.write(out_path + "\n")
    return 0


def cmd_render_inline_summary(args: argparse.Namespace) -> int:
    """Render the ## Audit Complete inline console block.

    Reads report_dict JSON from --report <path>, renders via
    _inline.render_inline_summary, prints to stdout, returns 0.
    Bad input exits 2.
    """
    from ._inline import render_inline_summary

    report_path = getattr(args, "report", None)
    if not report_path:
        sys.stderr.write(
            "audit_helper render-inline-summary: --report <path> required\n"
        )
        return 2

    try:
        with open(report_path, "r", encoding="utf-8") as fh:
            report_dict = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-inline-summary: cannot read --report file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-inline-summary: --report file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    try:
        block = render_inline_summary(report_dict)
    except Exception as exc:
        sys.stderr.write(
            "audit_helper render-inline-summary: failed to render: "
            "{0}\n".format(exc)
        )
        return 2

    sys.stdout.write(block)
    return 0


def cmd_cleanup_tmps(args: argparse.Namespace) -> int:
    """Delete leftover audits/.tmp-*.md files from an interrupted run.

    Prints a JSON result {"deleted": N, "files": [...]} to stdout.
    Does NOT delete final reports or .gitignore.
    Returns 0 always (missing audits_dir is not an error — nothing to clean).
    """
    import glob

    audits_dir = getattr(args, "audits_dir", None) or "audits"

    if not os.path.isdir(audits_dir):
        result = {"deleted": 0, "files": []}
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 0

    pattern = os.path.join(audits_dir, ".tmp-*.md")
    candidates = glob.glob(pattern)
    deleted = []
    for path in sorted(candidates):
        try:
            os.unlink(path)
            deleted.append(path)
        except OSError as exc:
            sys.stderr.write(
                "audit_helper cleanup-tmps: could not delete {0}: {1}\n".format(
                    path, exc
                )
            )

    result = {"deleted": len(deleted), "files": deleted}
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Phase 5 handlers
# ---------------------------------------------------------------------------


def cmd_merge_passes(args: argparse.Namespace) -> int:
    """Merge per-pass validated-findings JSON files via _merge.merge_passes.

    Reads one or more pool files (--pools), each either a bare JSON array of
    ParsedFinding dicts or a validate-findings output object with a "passed"
    key.  Sorts resolved paths lexically (deterministic pass order for
    .validated-p1.json, .validated-p2.json, ... naming convention).  Calls
    merge_passes(pools) and writes the merged bare JSON array to stdout.

    Returns 0 on success.
    Returns 2 on no matching files, unreadable file, or malformed JSON.
    """
    import glob as _glob

    from ._merge import merge_passes

    pool_tokens = getattr(args, "pools", None) or []
    if not pool_tokens:
        sys.stderr.write(
            "audit_helper merge-passes: --pools <path> [path ...] required\n"
        )
        return 2

    # Expand glob metacharacters in any token; collect all resolved paths.
    resolved = []  # type: list
    for token in pool_tokens:
        if any(c in token for c in ("*", "?", "[")):
            expanded = sorted(_glob.glob(token))
            resolved.extend(expanded)
        else:
            resolved.append(token)

    # Deduplicate while preserving insertion order, then sort lexically for
    # deterministic pass order.  Duplicates arise when a glob token and an
    # explicit token both expand to the same path; merging the same file twice
    # would inflate pass_count / [MULTI-PASS:k] tags.
    seen = set()  # type: set
    deduped = []  # type: list
    for p in resolved:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    resolved = sorted(deduped)

    if not resolved:
        sys.stderr.write(
            "audit_helper merge-passes: no files matched by --pools tokens\n"
        )
        return 2

    pools = []  # type: list
    for path in resolved:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except OSError as exc:
            sys.stderr.write(
                "audit_helper merge-passes: cannot read pool file {0!r}: "
                "{1}\n".format(path, exc)
            )
            return 2
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                "audit_helper merge-passes: pool file {0!r} is not valid "
                "JSON: {1}\n".format(path, exc)
            )
            return 2

        # Accept either the full validate-findings output object or a bare list.
        if isinstance(raw, dict) and "passed" in raw:
            pool_findings = raw["passed"]
            if not isinstance(pool_findings, list):
                sys.stderr.write(
                    "audit_helper merge-passes: pool file {0!r} has 'passed' "
                    "key but its value is not a JSON array\n".format(path)
                )
                return 2
        elif isinstance(raw, dict):
            # dict present but no 'passed' key
            sys.stderr.write(
                "audit_helper merge-passes: pool file {0!r} must be a JSON "
                "array or an object with a 'passed' key\n".format(path)
            )
            return 2
        elif isinstance(raw, list):
            pool_findings = raw
        else:
            sys.stderr.write(
                "audit_helper merge-passes: pool file {0!r} must be a JSON "
                "array or an object with a 'passed' key\n".format(path)
            )
            return 2

        pools.append(pool_findings)

    merged = merge_passes(pools)
    sys.stdout.write(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Plan-19 Step-1 handlers (refutation / cross-examination stage)
# ---------------------------------------------------------------------------


def cmd_route_refutation(args: argparse.Namespace) -> int:
    """Group working findings by author and assign each group a non-author refuter.

    Input: --findings <path>  (JSON array of ParsedFinding dicts)
           --finders <comma-list>  (present finder agent names from Phase 1.2)
    Returns 0 on success, 2 on missing/bad input.
    Output: JSON list of {refuter, findings} routing groups, one per refuter.
    """
    from _shared._verify import route_refutation  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    if not findings_path:
        sys.stderr.write(
            "audit_helper route-refutation: --findings <path> required\n"
        )
        return 2

    finders_raw = getattr(args, "finders", None) or ""
    present_finders = [f.strip() for f in finders_raw.split(",") if f.strip()]

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper route-refutation: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper route-refutation: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper route-refutation: --findings must be a JSON array\n"
        )
        return 2

    result = route_refutation(findings, present_finders)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_verify_brief(args: argparse.Namespace) -> int:
    """Assemble a refuter's cross-examination instruction block.

    Input: --findings <path>       (JSON array of ParsedFinding dicts — the
                                    subset routed to this refuter)
           --refuter <name>        (refuter agent name)
           --references-dir <dir>  (directory containing refutation-preamble.md)
           --scope <path>          (resolve-scope JSON output file)
           --source-root <dir>     (workspace/repo root label)
           --tmp-path <path>       (optional write-path for the verdict file)
    Returns 0 on success, 2 on bad input.
    Prints the rendered brief as plain text to stdout.
    """
    from ._scope import render_scope_block
    from _shared._verify import render_verify_brief  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    refuter = getattr(args, "refuter", None)
    references_dir = getattr(args, "references_dir", None) or ".claude/commands/audit/references"
    scope_path = getattr(args, "scope", None)
    source_root = getattr(args, "source_root", ".") or "."
    tmp_path = getattr(args, "tmp_path", None)

    if not findings_path:
        sys.stderr.write(
            "audit_helper render-verify-brief: --findings <path> required\n"
        )
        return 2
    if not refuter:
        sys.stderr.write(
            "audit_helper render-verify-brief: --refuter <name> required\n"
        )
        return 2
    if not scope_path:
        sys.stderr.write(
            "audit_helper render-verify-brief: --scope <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-verify-brief: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-verify-brief: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper render-verify-brief: --findings must be a JSON array\n"
        )
        return 2

    try:
        with open(scope_path, "r", encoding="utf-8") as fh:
            scope_result = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper render-verify-brief: cannot read --scope file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper render-verify-brief: --scope file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    scope_block = render_scope_block(scope_result, source_root)

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
            "audit_helper render-verify-brief: {0}\n".format(exc)
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
            "audit_helper consume-verdicts: --verdicts <path> required\n"
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
        sys.stderr.write("audit_helper consume-verdicts: {0}\n".format(exc))
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
        sys.stderr.write("audit_helper consume-verdicts: {0}\n".format(exc))
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
                               working list: consensus-findings.json or merged.json)
           --verdicts <path>  (JSON array of verdict dicts — merged across all
                               refuters; each element is a verdict dict from
                               consume_verdicts)
    Returns 0 on success, 2 on missing/bad input.
    Output: JSON object with keys: confirmed, dismissed, uncertain, contested.
    """
    from _shared._verify import apply_verdicts  # type: ignore[import]

    findings_path = getattr(args, "findings", None)
    verdicts_path = getattr(args, "verdicts", None)

    if not findings_path:
        sys.stderr.write(
            "audit_helper apply-verdicts: --findings <path> required\n"
        )
        return 2
    if not verdicts_path:
        sys.stderr.write(
            "audit_helper apply-verdicts: --verdicts <path> required\n"
        )
        return 2

    try:
        with open(findings_path, "r", encoding="utf-8") as fh:
            findings = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper apply-verdicts: cannot read --findings file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper apply-verdicts: --findings file is not valid "
            "JSON: {0}\n".format(exc)
        )
        return 2

    if not isinstance(findings, list):
        sys.stderr.write(
            "audit_helper apply-verdicts: --findings must be a JSON array\n"
        )
        return 2

    try:
        with open(verdicts_path, "r", encoding="utf-8") as fh:
            verdicts_raw = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            "audit_helper apply-verdicts: cannot read --verdicts file: "
            "{0}\n".format(exc)
        )
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "audit_helper apply-verdicts: --verdicts file is not valid "
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
            "audit_helper apply-verdicts: --verdicts must be a JSON array or "
            "an object with a 'verdicts' key\n"
        )
        return 2

    if not isinstance(verdicts, list):
        sys.stderr.write(
            "audit_helper apply-verdicts: --verdicts must be a JSON array\n"
        )
        return 2

    result = apply_verdicts(findings, verdicts)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

_SUBCOMMAND_REGISTRY = [
    (
        "resolve-mode",
        "Parse raw $ARGUMENTS string into mode + knobs (Phase 0).",
        cmd_resolve_mode,
    ),
    (
        "check-agents",
        "Check which audit-capable agent .md files are present (Phase 0).",
        cmd_check_agents,
    ),
    (
        "preflight-context",
        "Best-effort read of constitution, CLAUDE.md, and memory (Phase 0).",
        cmd_preflight_context,
    ),
    (
        "check-status-and-flip",
        "Read or update audit session state phase/status (Phase 0).",
        cmd_check_status_and_flip,
    ),
    (
        "compute-hotspots",
        "Score + rank source files by risk (Phase 1). Requires --callers CBM payload.",
        cmd_compute_hotspots,
    ),
    (
        "render-hotspot-summary",
        "Render human-readable hotspot table from a compute-hotspots JSON (Phase 1).",
        cmd_render_hotspot_summary,
    ),
    (
        "resolve-scope",
        "Resolve file list + metadata from a mode_result JSON (Phase 2).",
        cmd_resolve_scope,
    ),
    (
        "render-scope-block",
        "Render human-readable scope summary from a resolve-scope JSON (Phase 2).",
        cmd_render_scope_block,
    ),
    (
        "render-agent-brief",
        "Assemble per-agent audit instruction block (Phase 2).",
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
        "compute-consensus",
        "Cross-agent exact-match merge with [CROSS-AGENT] tag + severity bump (Phase 3).",
        cmd_compute_consensus,
    ),
    (
        "force-rank-top10",
        "Force-rank findings by score → top 10 (top 5 with --narrow) (Phase 3).",
        cmd_force_rank_top10,
    ),
    (
        "map-recurring-issues",
        "Tag findings RECURRING/RECURRING-SPREAD from past findings list (Phase 3).",
        cmd_map_recurring_issues,
    ),
    (
        "render-report",
        "Render + write the full audit markdown report to disk (Phase 4).",
        cmd_render_report,
    ),
    (
        "render-inline-summary",
        "Render the ## Audit Complete inline console block (Phase 4).",
        cmd_render_inline_summary,
    ),
    (
        "cleanup-tmps",
        "Delete leftover audits/.tmp-*.md files from an interrupted run (Phase 4/5).",
        cmd_cleanup_tmps,
    ),
    (
        "merge-passes",
        "Union-merge per-pass validated-findings JSON files via tolerant line clustering (Phase 5).",
        cmd_merge_passes,
    ),
    (
        "route-refutation",
        "Group findings by author and assign each group a non-author refuter (Plan-19 Phase 4.2.5).",
        cmd_route_refutation,
    ),
    (
        "render-verify-brief",
        "Assemble refuter cross-examination instruction block (Plan-19 Phase 4.2.5).",
        cmd_render_verify_brief,
    ),
    (
        "consume-verdicts",
        "Parse one refuter verdict markdown file into status + verdict list JSON (Plan-19 Phase 4.2.5).",
        cmd_consume_verdicts,
    ),
    (
        "apply-verdicts",
        "Partition working findings by merged verdicts per D7 category rules (Plan-19 Phase 4.2.5).",
        cmd_apply_verdicts,
    ),
]


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="audit_helper",
        description=(
            "Session state + preflight helper for /audit. "
            "Adversarial whole-codebase audit: mislogic hunt + agent ensemble."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "resolve-mode":
            sp.add_argument(
                "arguments",
                nargs="?",
                default="",
                help=(
                    "Raw $ARGUMENTS string from the slash command invocation. "
                    "Always pass as a single quoted string from shell: "
                    'audit_helper resolve-mode "$ARGUMENTS". '
                    "Examples: '--top 25', '--full', '--uncommitted', 'src/auth.py:1-40'."
                ),
            )

        elif verb == "check-agents":
            sp.add_argument(
                "--agents-dir",
                default=".claude/agents",
                help=(
                    "Path to the .claude/agents directory to scan "
                    "(default: .claude/agents in CWD)."
                ),
            )

        elif verb == "preflight-context":
            sp.add_argument(
                "--workspace-root",
                default=".",
                help="Workspace root to read context from (default: CWD).",
            )

        elif verb == "check-status-and-flip":
            sp.add_argument(
                "--workspace-root",
                default=".",
                help="Workspace root where audits/.state.json lives (default: CWD).",
            )
            sp.add_argument(
                "--to",
                default=None,
                metavar="PHASE",
                help=(
                    "Phase label to flip to (e.g. '1', 'preflight'). "
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

        elif verb == "compute-hotspots":
            sp.add_argument(
                "--repo-root",
                default=".",
                dest="repo_root",
                help="Path to the git repo root to analyse (default: CWD).",
            )
            sp.add_argument(
                "--callers",
                default=None,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing CBM caller counts "
                    "(orchestrator-supplied). Required — omitting exits 2."
                ),
            )
            sp.add_argument(
                "--top",
                type=int,
                default=25,
                metavar="N",
                help="Number of highest-risk files to include in top list (default: 25).",
            )
            sp.add_argument(
                "--weights",
                default=None,
                metavar="WEIGHTS",
                help=(
                    "Risk-weight override as 'c=0.5,k=0.4,s=0.1' "
                    "(default: c=0.5,k=0.4,s=0.1). "
                    "Values must be in [0,1] and sum to 1.0."
                ),
            )
            sp.add_argument(
                "--since",
                default="90.days.ago",
                metavar="DATE",
                help=(
                    "git --since string for churn window "
                    "(default: '90.days.ago'). "
                    "Accepts any git date expression or ISO date."
                ),
            )

        elif verb == "render-hotspot-summary":
            sp.add_argument(
                "--hotspot",
                required=True,
                metavar="PATH",
                help="Path to a compute-hotspots JSON output file to render.",
            )

        elif verb == "resolve-scope":
            sp.add_argument(
                "--repo-root",
                default=".",
                dest="repo_root",
                help="Path to the git repo root (default: CWD).",
            )
            sp.add_argument(
                "--mode-result",
                required=True,
                dest="mode_result",
                metavar="PATH",
                help="Path to a resolve-mode JSON output file.",
            )
            sp.add_argument(
                "--hotspot",
                default=None,
                metavar="PATH",
                help=(
                    "Path to a compute-hotspots JSON file. When supplied and "
                    "mode is hotspot, the top file list is extracted automatically."
                ),
            )

        elif verb == "render-scope-block":
            sp.add_argument(
                "--scope",
                required=True,
                metavar="PATH",
                help="Path to a resolve-scope JSON output file.",
            )
            sp.add_argument(
                "--source-root",
                default=".",
                dest="source_root",
                help="Source / workspace root label shown in the scope block (default: CWD).",
            )

        elif verb == "render-agent-brief":
            sp.add_argument(
                "--agent",
                required=True,
                metavar="NAME",
                help=(
                    "Agent name: code-reviewer | architect | "
                    "qa-reviewer | security-reviewer."
                ),
            )
            sp.add_argument(
                "--references-dir",
                default=".claude/commands/audit/references",
                dest="references_dir",
                metavar="DIR",
                help=(
                    "Directory containing adversarial-preamble.md and "
                    "mislogic-checklist.md "
                    "(default: .claude/commands/audit/references)."
                ),
            )
            sp.add_argument(
                "--scope",
                required=True,
                metavar="PATH",
                help="Path to a resolve-scope JSON output file.",
            )
            sp.add_argument(
                "--source-root",
                default=".",
                dest="source_root",
                help="Workspace / repo root label (default: CWD).",
            )
            sp.add_argument(
                "--extra-context-file",
                default=None,
                dest="extra_context_file",
                metavar="PATH",
                help=(
                    "Optional file whose contents are appended to the scope "
                    "section (constitution excerpts, MEMORY.md, recurring issues)."
                ),
            )
            sp.add_argument(
                "--finding-cap",
                type=int,
                default=30,
                dest="finding_cap",
                metavar="N",
                help=(
                    "Maximum findings the agent should report (default: 30). "
                    "Substituted for the __FINDING_CAP__ token in the output "
                    "contract and closing reminder."
                ),
            )
            sp.add_argument(
                "--tmp-path",
                default=None,
                dest="tmp_path",
                metavar="PATH",
                help=(
                    "Override the agent findings write-path in the output "
                    "contract. When omitted, the contract uses the default "
                    "audits/.tmp-{agent-name}.md path (backward-compatible). "
                    "When provided, the given path is emitted verbatim wherever "
                    "the write-path appears in the contract (main sentence and "
                    "failure/empty-file instructions). Useful for relocating "
                    "scratch files to a run-scoped temp dir or for multi-pass "
                    "per-pass path suffixes."
                ),
            )

        elif verb == "consume-tmp":
            sp.add_argument(
                "--tmp",
                required=True,
                metavar="PATH",
                help="Path to the agent tmp file (audits/.tmp-{agent}.md).",
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

        elif verb == "compute-consensus":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing a combined list of "
                    "ParsedFinding dicts from all agents."
                ),
            )

        elif verb == "force-rank-top10":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the validated + consensus "
                    "ParsedFinding list to rank."
                ),
            )
            sp.add_argument(
                "--narrow",
                action="store_true",
                default=False,
                help="Output top 5 instead of top 10 (narrow audit mode).",
            )

        elif verb == "map-recurring-issues":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help="Path to a JSON file containing the current ParsedFinding list.",
            )
            sp.add_argument(
                "--recurring",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing past finding entries "
                    "[{file, fingerprint}, ...] (orchestrator-extracted from "
                    "specs/*/review.md)."
                ),
            )

        elif verb == "render-report":
            sp.add_argument(
                "--report",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the report_dict produced "
                    "by the audit pipeline."
                ),
            )
            sp.add_argument(
                "--audits-dir",
                default="audits",
                dest="audits_dir",
                metavar="DIR",
                help=(
                    "Directory to write the audit report into "
                    "(default: 'audits' in CWD — workspace root)."
                ),
            )
            sp.add_argument(
                "--date",
                required=True,
                metavar="YYYY-MM-DD",
                help="Audit date string used in the output filename.",
            )
            sp.add_argument(
                "--passes-run",
                type=int,
                default=1,
                dest="passes_run",
                metavar="N",
                help=(
                    "Number of audit passes that produced this report "
                    "(default: 1). When >= 2, a 'Passes run' line is "
                    "added to the ## Summary block. Single-pass callers "
                    "should omit this flag to preserve byte-identical output."
                ),
            )

        elif verb == "render-inline-summary":
            sp.add_argument(
                "--report",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON file containing the report_dict (same shape "
                    "as accepted by render-report). The out_path key should be "
                    "set by the caller to the path already written by render-report."
                ),
            )

        elif verb == "cleanup-tmps":
            sp.add_argument(
                "--audits-dir",
                default="audits",
                dest="audits_dir",
                metavar="DIR",
                help=(
                    "Directory to clean .tmp-*.md files from "
                    "(default: 'audits' in CWD)."
                ),
            )

        elif verb == "merge-passes":
            sp.add_argument(
                "--pools",
                nargs="+",
                required=True,
                metavar="PATH",
                help=(
                    "One or more pool file paths (or a glob pattern) to merge. "
                    "Each file must be a JSON array of ParsedFinding dicts or a "
                    "validate-findings output object with a 'passed' key. "
                    "Files are sorted lexically before merging so that "
                    ".validated-p1.json, .validated-p2.json, ... resolve in "
                    "pass order. At least one path is required."
                ),
            )

        elif verb == "route-refutation":
            sp.add_argument(
                "--findings",
                required=True,
                metavar="PATH",
                help=(
                    "Path to a JSON array of ParsedFinding dicts (the working "
                    "list after consensus/merge — consensus-findings.json or "
                    "merged.json)."
                ),
            )
            sp.add_argument(
                "--finders",
                default="",
                metavar="NAMES",
                help=(
                    "Comma-separated list of present finder agent names from the "
                    "Phase-1.2 agent-existence check (e.g. "
                    "'code-reviewer,architect,qa-reviewer,security-reviewer'). "
                    "Only present finders are eligible refuters."
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
                default=".claude/commands/audit/references",
                dest="references_dir",
                metavar="DIR",
                help=(
                    "Directory containing refutation-preamble.md "
                    "(default: .claude/commands/audit/references)."
                ),
            )
            sp.add_argument(
                "--scope",
                required=True,
                metavar="PATH",
                help="Path to a resolve-scope JSON output file.",
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
                    "working list (consensus-findings.json or merged.json)."
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
