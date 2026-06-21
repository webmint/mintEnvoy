"""Phase 2.4c/2.4d/2.5/Patch-8/Step-5 dataflow + archaeology setters.

record-fix-path-helper (anchor + sticky-reject), record-inbound-caller,
record-dead-sibling, record-consumer-chain, set-value-semantics
(invariant guards), record-value-production-site, record-data-flow-chain
(intermediate→Finding cross-check), record-literal-archaeology (Patch 8),
record-probe-script (Step 5).
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from typing import Optional

from ._layer_package import _is_presentation_layer
from _shared.literal_call_shape import LITERAL_TOKEN_RE
from ._state import _load_memo, _load_report, _state_transaction
from ._validators import (
    _die,
    _has_anchor_finding,
    _validate_file_line,
    _validate_inlines_from_tokens,
    _validate_runtime_on_path,
    _validate_scalar,
    _validate_script_within_research_dir,
    _validate_string_array_json,
)


# --- Phase 2.4c setters (helper-API surface enumeration) --------------------


def cmd_record_fix_path_helper(args: argparse.Namespace) -> int:
    """Append a {qn, file_line} entry to fix_path_helpers (deduped on qn).

    file_line is the HELPER'S DEFINITION location (from search_graph result),
    NOT the call-site. The sentinel '(none)' is explicitly rejected — the
    definition file is required for layer-boundary package extraction in check 8b.

    Patch 5 — anchor gate: --file-line must collide with at least one
    existing finding's file_line (exact match OR same path with line within ±5).
    Once rejected for a (qn, file_line) combo, sticky-reject all future attempts
    with that combo even if a matching finding is added post-hoc — closes the
    adversarial generator path where the LLM unblocks rejection by recording a
    fabricated finding.
    """
    try:
        helper_qn = _validate_scalar(args.helper_qn, "fix_path_helper.helper_qn")
        file_line = _validate_file_line(args.file_line, "fix_path_helper.file_line")
    except ValueError as err:
        return _die(str(err), code=2)
    if file_line == "(none)":
        return _die(
            "record-fix-path-helper: --file-line cannot be (none) — "
            "the helper's definition must have a real file path for "
            "layer-boundary detection",
            code=2,
        )

    # Collect the reject message and code outside the transaction so the
    # write (rejection log update) completes before we emit to stderr and return.
    reject_message = None  # type: Optional[str]
    reject_code = 0
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rejection_log = report.get("helper_rejection_log") or []
            # Sticky-reject: if this (qn, file_line) was previously rejected,
            # refuse even if findings now contain a collision (closes the
            # post-hoc-anchor adversarial path).
            for r in rejection_log:
                if r.get("qn") == helper_qn and r.get("file_line") == file_line:
                    reject_message = (
                        "record-fix-path-helper: this (helper_qn, file_line) combo was "
                        "previously rejected as unanchored ({0!r} at {1!r}); cannot retry "
                        "even if findings now contain a collision (sticky-reject closes "
                        "the post-hoc-anchor adversarial path). Either pick a different "
                        "--file-line that anchored to a finding at the time of THIS call, "
                        "or restart /research to clear rejection state.\n".format(
                            helper_qn, file_line
                        )
                    )
                    reject_code = 2
                    break

            if reject_code == 0:
                # Anchor check: does any finding's file_line collide?
                findings = report.get("findings") or []
                if not _has_anchor_finding(file_line, findings):
                    # Persist the rejection in the same transaction so future
                    # retries with the same (qn, file_line) are sticky-blocked.
                    rejection_log.append({"qn": helper_qn, "file_line": file_line})
                    report["helper_rejection_log"] = rejection_log
                    finding_paths = sorted({
                        f.get("file_line")
                        for f in findings
                        if f.get("file_line")
                    })
                    reject_message = (
                        "record-fix-path-helper: --file-line {0!r} does not anchor to any "
                        "recorded finding (no finding's file_line collides — exact match or "
                        "same path within ±5 lines). Fix-path helpers MUST anchor to CBM "
                        "evidence already in the report. Record the relevant finding via "
                        "record-finding FIRST (with the file:line from a search_graph or "
                        "search_code result row), then re-call record-fix-path-helper with "
                        "a DIFFERENT --file-line if you've identified a closer-anchored "
                        "helper site. Current finding file_lines: {1!r}.\n".format(
                            file_line, finding_paths
                        )
                    )
                    reject_code = 2

            if reject_code == 0:
                lst = report.setdefault("fix_path_helpers", [])
                # Dedupe on qn: skip if an entry with the same qn already exists.
                if not any(entry.get("qn") == helper_qn for entry in lst):
                    lst.append({"qn": helper_qn, "file_line": file_line})

    except (OSError, json.JSONDecodeError) as err:
        return _die("record-fix-path-helper: {0}".format(err))

    if reject_code == 2:
        sys.stderr.write(reject_message)
        return 2
    return 0


def cmd_record_inbound_caller(args: argparse.Namespace) -> int:
    """Append a {helper_qn, caller_qn, file_line} record to inbound_callers."""
    try:
        helper_qn = _validate_scalar(args.helper_qn, "inbound_caller.helper_qn")
        caller_qn = _validate_scalar(args.caller_qn, "inbound_caller.caller_qn")
        file_line = _validate_file_line(args.file_line, "inbound_caller.file_line")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("inbound_callers", []).append(
                {"helper_qn": helper_qn, "caller_qn": caller_qn, "file_line": file_line}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-inbound-caller: {0}".format(err))
    return 0


def cmd_record_dead_sibling(args: argparse.Namespace) -> int:
    """Append a {class_qn, method_qn, verified_via} record to dead_siblings."""
    try:
        class_qn = _validate_scalar(args.class_qn, "dead_sibling.class_qn")
        method_qn = _validate_scalar(args.method_qn, "dead_sibling.method_qn")
    except ValueError as err:
        return _die(str(err), code=2)
    # verified_via is already constrained by argparse choices=
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            # Intentional: no dedupe. Two recordings of the same (class_qn, method_qn)
            # from different trace passes are both kept; verify checks tolerate duplicates.
            report.setdefault("dead_siblings", []).append(
                {"class_qn": class_qn, "method_qn": method_qn, "verified_via": args.verified_via}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-dead-sibling: {0}".format(err))
    return 0


def cmd_record_consumer_chain(args: argparse.Namespace) -> int:
    """Append a {value, consumer_qn, file_line, role} record to consumer_chain."""
    try:
        value = _validate_scalar(args.value, "consumer_chain.value")
        consumer_qn = _validate_scalar(args.consumer_qn, "consumer_chain.consumer_qn")
        file_line = _validate_file_line(args.file_line, "consumer_chain.file_line")
        role = _validate_scalar(args.role, "consumer_chain.role")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("consumer_chain", []).append(
                {"value": value, "consumer_qn": consumer_qn, "file_line": file_line, "role": role}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-consumer-chain: {0}".format(err))
    return 0


def cmd_set_value_semantics(args: argparse.Namespace) -> int:
    """Upsert a {value, classification, evidence} record in value_semantics.

    Last-write-wins on value key. When classification==invariant, requires:
      - --stable-across-calls (true|false|unknown) — REQUIRED for invariant.
      - At least one consumer_chain row with matching value field.
      - When --stable-across-calls==unknown AND symptom is presentation-layer,
        rejected (must investigate via Phase 2.4d data-flow chain first).
      - When --stable-across-calls==false, at least one value_production_sites
        row must already exist for this value.

    Row shape: {value, classification, evidence} for non-invariant.
               {value, classification, evidence, stable_across_calls} for invariant.
    """
    try:
        value = _validate_scalar(args.value, "value_semantics.value")
        evidence = _validate_scalar(args.evidence, "value_semantics.evidence")
    except ValueError as err:
        return _die(str(err), code=2)
    # classification is already constrained by argparse choices=
    classification = args.classification
    stable_across_calls = getattr(args, "stable_across_calls", None)

    # Invariant guards: all checked before entering the state transaction so
    # the file is never rewritten on a validation rejection.
    if classification == "invariant":
        # Gate 1: --stable-across-calls is required when classification==invariant.
        if stable_across_calls is None:
            return _die(
                "set-value-semantics: --stable-across-calls is required when "
                "--classification == 'invariant'; values invariant by kind may still be "
                "randomized per call (the production-site rewriter pattern). "
                "Pass --stable-across-calls true|false|unknown.",
                code=2,
            )

        try:
            report_snapshot = _load_report(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-value-semantics: {0}".format(err))

        # Gate 2: --stable-across-calls==unknown + presentation-layer → reject.
        if stable_across_calls == "unknown":
            # Determine if the primary finding is presentation-layer (same pattern
            # as check 8b / check 15 in cmd_verify).
            all_findings = report_snapshot.get("findings") or []
            primary_path = None  # type: Optional[str]
            for f in all_findings:
                framing_val = f.get("framing") or "primary"
                if framing_val == "primary":
                    fl = f.get("file_line") or ""
                    colon_pos = fl.rfind(":")
                    if colon_pos > 0:
                        primary_path = fl[:colon_pos]
                    elif fl:
                        primary_path = fl
                    break
            if primary_path and _is_presentation_layer(primary_path):
                return _die(
                    "set-value-semantics: --stable-across-calls cannot be 'unknown' when "
                    "--classification is 'invariant' AND symptom is presentation-layer; "
                    "investigate the production site (where the value is assigned) "
                    "via Phase 2.4d data-flow chain (already recorded) before classifying",
                    code=2,
                )

        # Gate 3: consumer_chain row required.
        chain = report_snapshot.get("consumer_chain") or []
        if not any(r.get("value") == value for r in chain):
            return _die(
                "set-value-semantics: classification=invariant requires at least one "
                "consumer_chain entry for value={0!r}; record-consumer-chain first".format(value),
                code=2,
            )

        # Gate 4: --stable-across-calls==false requires at least one
        # value_production_sites row for this value.
        if stable_across_calls == "false":
            sites = report_snapshot.get("value_production_sites") or []
            if not any(s.get("value") == value for s in sites):
                return _die(
                    "set-value-semantics: --stable-across-calls=false for value {0!r} requires "
                    "at least one record-value-production-site call for this value first. Call "
                    "record-value-production-site with the file:line where the value is "
                    "randomized/rewritten (e.g., Math.random, Date.now, manual id reassignment), "
                    "then re-run set-value-semantics.".format(value),
                    code=2,
                )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rows = report.setdefault("value_semantics", [])
            # Build row — include stable_across_calls only for invariant classification.
            if classification == "invariant":
                new_row = {
                    "value": value,
                    "classification": classification,
                    "evidence": evidence,
                    "stable_across_calls": stable_across_calls,
                }
            else:
                new_row = {"value": value, "classification": classification, "evidence": evidence}
            for i, row in enumerate(rows):
                if row.get("value") == value:
                    rows[i] = new_row
                    break
            else:
                rows.append(new_row)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-value-semantics: {0}".format(err))
    return 0


# --- Patch 7: value production site setter -----------------------------------


def cmd_record_value_production_site(args: argparse.Namespace) -> int:
    """Append a {value, file_line, is_stable} record to value_production_sites.

    Dedupes by (value, file_line) pair: same pair is no-op (do not append,
    do not modify). Multiple file_lines for the same value all append
    (multi-site per value, concern C5).

    Rejects (none) sentinel for file_line — production site must be a real path.
    """
    try:
        value = _validate_scalar(args.value, "value_production_sites.value")
        file_line = _validate_file_line(args.file_line, "value_production_sites.file_line")
    except ValueError as err:
        return _die(str(err), code=2)

    # Reject (none) sentinel — production site must be a real path.
    if file_line == "(none)":
        return _die(
            "record-value-production-site: --file-line cannot be (none) — "
            "production site must be a real path",
            code=2,
        )

    # args.is_stable is constrained by argparse choices=("true","false").
    # Store as string (not bool) so the field is type-consistent with
    # value_semantics.stable_across_calls ("true"/"false"/"unknown").
    is_stable_str = args.is_stable

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            sites = report.setdefault("value_production_sites", [])
            # Dedupe by (value, file_line) pair.
            for existing in sites:
                if existing.get("value") == value and existing.get("file_line") == file_line:
                    # No-op: same (value, file_line) already recorded.
                    return 0
            sites.append({"value": value, "file_line": file_line, "is_stable": is_stable_str})
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-value-production-site: {0}".format(err))
    return 0


# --- Patch 6: data-flow chain setter ----------------------------------------


def cmd_record_data_flow_chain(args: argparse.Namespace) -> int:
    """Record the data-flow chain from click handler to write-boundary call.

    Validates each intermediate has a prior Finding row referencing its QN
    (substring match in finding's relevance or surface). Persists
    {handler_qn, write_boundary_qn, intermediate_qns} to report state.
    Last-write-wins — subsequent calls overwrite the prior chain.

    Empty intermediate_qns list [] is valid (direct handler→write-boundary).

    Gate: each intermediate_qn must appear in at least one existing Finding's
    relevance or surface field (simple substring match). The spec instructs
    the LLM to record intermediates via record-finding --surface / --relevance
    before calling this setter.

    KNOWN GAP: intermediate-qn ↔ Finding cross-check runs only at set time.
    Direct JSON mutation that writes an arbitrary truthy `data_flow_chain`
    value bypasses this validation; verify check 15 only confirms the field
    is non-null at verify time and does NOT re-validate intermediate_qns
    against findings. Closing the gap would require a verify-time re-walk
    of the same substring check — deferred until empirical evidence shows
    the bypass is being exploited.
    """
    try:
        handler_qn = _validate_scalar(args.handler_qn, "data_flow_chain.handler_qn")
        write_boundary_qn = _validate_scalar(
            args.write_boundary_qn, "data_flow_chain.write_boundary_qn"
        )
        intermediate_qns = _validate_string_array_json(
            args.intermediate_qns, "data_flow_chain.intermediate_qns"
        )
    except ValueError as err:
        return _die(str(err), code=2)

    # Validate each intermediate has a Finding row referencing it before entering
    # the state transaction (so the file is never rewritten on validation failure).
    if intermediate_qns:
        try:
            report_snapshot = _load_report(args.devforge_dir)
        except (OSError, json.JSONDecodeError) as err:
            return _die("record-data-flow-chain: {0}".format(err))
        findings = report_snapshot.get("findings") or []
        for qn in intermediate_qns:
            referenced = any(
                qn in (f.get("relevance") or "") or qn in (f.get("surface") or "")
                for f in findings
            )
            if not referenced:
                existing_surfaces = sorted(
                    f.get("surface") or "" for f in findings if f.get("surface")
                )
                return _die(
                    "record-data-flow-chain: intermediate_qn {0!r} has no Finding row "
                    "referencing it (record-finding must be called for each intermediate "
                    "before record-data-flow-chain). Existing findings: {1!r}".format(
                        qn, existing_surfaces
                    ),
                    code=2,
                )

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["data_flow_chain"] = {
                "handler_qn": handler_qn,
                "write_boundary_qn": write_boundary_qn,
                "intermediate_qns": intermediate_qns,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-data-flow-chain: {0}".format(err))
    return 0


# --- Patch 8: literal-archaeology setter ------------------------------------


def cmd_record_literal_archaeology(args: argparse.Namespace) -> int:
    """Append a {literal, file_line, introduced_by, introduced_when, commit_subject, intent}
    record to literal_archaeology.

    Dedupes by (literal, file_line) pair: re-recording the same pair is a no-op
    (original intent is retained; no error emitted — matches record-value-production-site
    behavior). Multiple file_lines for the same literal are all appended.

    Validates:
      - --literal: non-empty + must fully match LITERAL_TOKEN_RE (primitive only).
      - --file-line: via _validate_file_line; (none) sentinel rejected.
      - --introduced-by: 7-40 hex char commit SHA.
      - --introduced-when: ISO date YYYY-MM-DD.
      - --commit-subject: non-empty.
      - --intent: enforced by argparse choices.
    """
    # Validate --literal: non-empty, then fullmatch against LITERAL_TOKEN_RE.
    literal_raw = args.literal
    if not literal_raw or not literal_raw.strip():
        return _die(
            "record-literal-archaeology: --literal value cannot be empty",
            code=2,
        )
    literal = literal_raw.strip()
    if not re.fullmatch(LITERAL_TOKEN_RE.pattern, literal, re.VERBOSE):
        return _die(
            "record-literal-archaeology: --literal {0!r} is not a recognizable literal "
            "token (expected: bool / number / null-like / quoted string; arrays / objects "
            "/ regex / function literals are out of scope — record them as findings "
            "instead).".format(literal),
            code=2,
        )

    # Validate --file-line via existing helper; then reject (none) sentinel.
    try:
        file_line = _validate_file_line(args.file_line, "literal_archaeology.file_line")
    except ValueError as err:
        return _die(str(err), code=2)
    if file_line == "(none)":
        return _die(
            "record-literal-archaeology: --file-line cannot be (none) — "
            "archaeology requires a real path",
            code=2,
        )

    # Validate --introduced-by: 7-40 hex chars.
    introduced_by = args.introduced_by.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", introduced_by):
        return _die(
            "record-literal-archaeology: --introduced-by {0!r} must be a 7-40 char hex "
            "commit SHA.".format(introduced_by),
            code=2,
        )

    # Validate --introduced-when: ISO date YYYY-MM-DD.
    introduced_when = args.introduced_when.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", introduced_when):
        return _die(
            "record-literal-archaeology: --introduced-when {0!r} must be ISO date "
            "YYYY-MM-DD.".format(introduced_when),
            code=2,
        )
    try:
        datetime.date.fromisoformat(introduced_when)
    except ValueError:
        return _die(
            "record-literal-archaeology: --introduced-when {0!r} must be ISO date "
            "YYYY-MM-DD.".format(introduced_when),
            code=2,
        )

    # Validate --commit-subject: non-empty.
    try:
        commit_subject = _validate_scalar(args.commit_subject, "literal_archaeology.commit_subject")
    except ValueError as err:
        return _die(str(err), code=2)

    # --intent is enforced by argparse choices.
    intent = args.intent

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rows = report.setdefault("literal_archaeology", [])
            # Dedupe by (literal, file_line) pair — no-op if same pair exists.
            for existing in rows:
                if existing.get("literal") == literal and existing.get("file_line") == file_line:
                    return 0
            rows.append({
                "literal": literal,
                "file_line": file_line,
                "introduced_by": introduced_by,
                "introduced_when": introduced_when,
                "commit_subject": commit_subject,
                "intent": intent,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-literal-archaeology: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Step 5 — record-probe-script command.
# ---------------------------------------------------------------------------


def cmd_record_probe_script(args: argparse.Namespace) -> int:
    """Append {script_path, runtime, inlines_from, recorded_at} to probe_scripts.

    Validates:
      - script_path exists on disk AND lives under research/<date>-<slug>/
      - runtime resolves via shutil.which
      - inlines_from is a non-empty JSON array of path:line tokens
    Idempotent: same script_path is a no-op (exit 0 + stderr notice).
    """
    devforge_dir = args.devforge_dir

    # Load report to read date + topic_slug for path validation.
    try:
        report_snapshot = _load_report(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: cannot load report state: {0}".format(err))

    research_date = (report_snapshot.get("date") or "").strip()
    if not research_date:
        return _die(
            "record-probe-script: report.date not set; run set-date first",
            code=2,
        )

    try:
        memo_snapshot = _load_memo(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: cannot load memo state: {0}".format(err))

    topic_slug = (memo_snapshot.get("topic_slug") or "").strip()
    if not topic_slug:
        return _die(
            "record-probe-script: memo.topic_slug not set; run set-topic first",
            code=2,
        )

    script_path = args.script_path

    # Validate script_path is within the research dir and exists on disk.
    try:
        _validate_script_within_research_dir(script_path, research_date, topic_slug)
    except ValueError as err:
        return _die(str(err), code=2)

    # Validate runtime on PATH.
    try:
        _validate_runtime_on_path(args.runtime)
    except ValueError as err:
        return _die(str(err), code=2)

    # Validate --inlines-from JSON tokens.
    try:
        inlines_from = _validate_inlines_from_tokens(args.inlines_from)
    except ValueError as err:
        return _die(str(err), code=2)

    runtime = args.runtime

    # F5: Pre-check idempotency BEFORE entering the transaction (avoids no-op fsync).
    try:
        report_preread = _load_report(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: cannot load report state: {0}".format(err))

    existing = next(
        (e for e in report_preread.get("probe_scripts", [])
         if e.get("script_path") == script_path),
        None,
    )
    if existing is not None:
        # F3: Strict-match idempotency — same path must carry same runtime + inlines_from.
        if existing.get("runtime") != runtime or existing.get("inlines_from") != inlines_from:
            return _die(
                "record-probe-script: script_path {0!r} already recorded with "
                "different runtime/inlines_from; remove via reset-report and re-record"
                .format(script_path),
                code=2,
            )
        # Exact match → no-op (true idempotent).
        sys.stderr.write(
            "record-probe-script: script_path already recorded (exact match); no-op\n"
        )
        return 0

    recorded_at = datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds"
    )

    # Append path — real work needs transaction.
    try:
        with _state_transaction(devforge_dir, "report") as report:
            report.setdefault("probe_scripts", []).append({
                "script_path": script_path,
                "runtime": runtime,
                "inlines_from": inlines_from,
                "recorded_at": recorded_at,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-probe-script: {0}".format(err))
    return 0
