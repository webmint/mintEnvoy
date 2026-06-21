"""RESEARCH-HANDOFF-PLAN subcommands.

set-probe-feasibility (Step 4 — 5 booleans), finalize-handoff (terminal
phase: memo+report → handoff.json), append-outcome (Step 7 — record
post-probe outcome), check-outcome (Step 7 — unmarked / marked status).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

from . import handoff_schema
from ._handoff_build import _asdict_handoff, _build_handoff_from_state
from ._state import _atomic_write_json, _load_memo, _load_report, _state_transaction
from ._validators import _die, _validate_enum


# ---------------------------------------------------------------------------
# set-probe-feasibility command.
# ---------------------------------------------------------------------------


def cmd_set_probe_feasibility(args):
    # type: (argparse.Namespace) -> int
    """Write probe_feasibility flags (5 booleans) to research-report.json.

    All five flags are required. Each accepts only lowercase "true" or "false" (argparse exact-match).
    """
    devforge_dir = args.devforge_dir
    flag_names = [
        ("data_shape_only", args.data_shape_only),
        ("auth_required", args.auth_required),
        ("network_dependent", args.network_dependent),
        ("timing_dependent", args.timing_dependent),
        ("is_test_code", args.is_test_code),
    ]
    parsed = {}
    for field_name, raw in flag_names:
        try:
            canonical = _validate_enum(raw, "set-probe-feasibility --{0}".format(
                field_name.replace("_", "-")
            ), ("true", "false"))
        except ValueError as err:
            return _die(str(err), code=2)
        parsed[field_name] = (canonical == "true")

    with _state_transaction(devforge_dir, "report") as report:
        feasibility = report.get("probe_feasibility")
        if not isinstance(feasibility, dict):
            feasibility = {
                "data_shape_only": None,
                "auth_required": None,
                "network_dependent": None,
                "timing_dependent": None,
                "is_test_code": None,
            }
        for field_name, value in parsed.items():
            feasibility[field_name] = value
        report["probe_feasibility"] = feasibility

    sys.stdout.write("probe_feasibility written: {0}\n".format(parsed))
    return 0


# ---------------------------------------------------------------------------
# finalize-handoff command.
# ---------------------------------------------------------------------------


def cmd_finalize_handoff(args):
    # type: (argparse.Namespace) -> int
    """Read research state → build Handoff → validate → write handoff.json."""
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("finalize-handoff: cannot load state: {0}".format(err))

    # Required-field guard.
    if not memo.get("mode"):
        return _die(
            "finalize-handoff: memo.mode not set (run detect-mode first)", code=2
        )
    if not memo.get("topic_slug"):
        return _die(
            "finalize-handoff: memo.topic_slug not set (run set-topic first)", code=2
        )
    if not report.get("date"):
        return _die(
            "finalize-handoff: report.date not set (run set-date first)", code=2
        )
    if report.get("recommended_approach") is None:
        return _die(
            "finalize-handoff: recommended_approach not set "
            "(run set-recommended-approach first)",
            code=2,
        )
    if report.get("complexity") is None:
        return _die(
            "finalize-handoff: complexity not set (run set-complexity first)", code=2
        )
    if not memo.get("verbatim_prompt"):
        return _die(
            "finalize-handoff: memo.verbatim_prompt not set "
            "(run set-verbatim-prompt first)",
            code=2,
        )

    # Step 4: probe_feasibility completeness guard (all 5 booleans must be set
    # before the classifier runs — None means LLM skipped set-probe-feasibility).
    feasibility = report.get("probe_feasibility") or {}
    required_feas = ["data_shape_only", "auth_required", "network_dependent",
                     "timing_dependent", "is_test_code"]
    missing_feas = [k for k in required_feas if feasibility.get(k) is None]
    if missing_feas:
        return _die(
            "finalize-handoff: probe_feasibility incomplete; missing flags: {0}. "
            "Run `research_helper set-probe-feasibility --data-shape-only ... "
            "--auth-required ... --network-dependent ... --timing-dependent ... "
            "--is-test-code ...` before finalize.".format(missing_feas),
            code=2,
        )

    try:
        handoff = _build_handoff_from_state(
            memo, report, args.research_md_path, devforge_dir=args.devforge_dir
        )
    except ValueError as err:
        return _die(
            "finalize-handoff: schema validation failed: {0}".format(err), code=2
        )

    target = Path(args.emit_handoff_json).resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(_asdict_handoff(handoff), target)
    except OSError as err:
        return _die(
            "finalize-handoff: cannot write {0}: {1}".format(target, err)
        )

    sys.stdout.write("wrote: {0}\n".format(target))
    return 0


# ---------------------------------------------------------------------------
# Step 7 — append-outcome + check-outcome.
# ---------------------------------------------------------------------------


def _load_handoff_json(handoff_path):
    # type: (str) -> Tuple[Optional[dict], Optional[str]]
    """Load and JSON-parse handoff.json at handoff_path.

    Returns (data_dict, None) on success, (None, error_message) on failure.
    """
    p = Path(handoff_path)
    if not p.is_file():
        return None, "handoff.json not found: {0}".format(handoff_path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return None, "cannot read handoff.json: {0}".format(err)
    if not isinstance(data, dict):
        return None, "handoff.json must be a JSON object"
    return data, None


def _build_outcome_md_section(outcome):
    # type: (dict) -> str
    """Render a markdown '## Outcome' section from an outcome dict.

    Used by append-outcome to append to the parallel .md file.
    """
    lines = [
        "## Outcome",
        "",
        "- **hypothesis_confirmed**: {0}".format(outcome["hypothesis_confirmed"]),
        "- **evidence_source**: {0}".format(outcome["evidence_source"]),
        "- **evidence_cite**: {0}".format(outcome["evidence_cite"]),
        "- **actual_fix_path**: {0}".format(outcome["actual_fix_path"]),
        "- **confidence_grade**: {0}".format(outcome["confidence_grade"]),
        "- **confirmed_date**: {0}".format(outcome["confirmed_date"]),
    ]
    if outcome.get("delta_from_recommendation"):
        lines.append("- **delta_from_recommendation**: {0}".format(
            outcome["delta_from_recommendation"]
        ))
    if outcome.get("confirmed_commit_sha"):
        lines.append("- **confirmed_commit_sha**: {0}".format(
            outcome["confirmed_commit_sha"]
        ))
    lines.append("")
    return "\n".join(lines)


def cmd_append_outcome(args):
    # type: (argparse.Namespace) -> int
    """Record post-probe outcome into handoff.json and optionally its parallel .md.

    Idempotency: re-running OVERWRITES the existing outcome block in handoff.json
    (last-write-wins). The parallel .md file gets a NEW '## Outcome' section appended
    each time (append-only audit trail — no de-dup).

    Steps:
    1. Read and validate handoff.json schema (must be parseable dict with 'probe' block).
    2. Compute confidence_grade via handoff_schema.compute_confidence_grade().
    3. Build outcome dict; validate via handoff_schema.Outcome(**...) for enum/format errors.
    4. Mutate handoff.json: set handoff["outcome"] = outcome dict. Atomic write.
    5. If research_path is set and the parallel .md exists, append '## Outcome' section.
    6. Print confirmation with confidence_grade. Exit 0.
    """
    handoff_path_str = args.handoff_path
    data, err = _load_handoff_json(handoff_path_str)
    if err is not None:
        return _die("append-outcome: handoff.json schema validation failed: {0}".format(err), code=2)

    # Validate minimum structure: must have 'probe' with 'tier' and 'discriminator'.
    probe = data.get("probe")
    if not isinstance(probe, dict):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "missing or non-dict 'probe' block",
            code=2,
        )
    tier = probe.get("tier")
    if not isinstance(tier, str):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "probe.tier must be a string",
            code=2,
        )
    discriminator = probe.get("discriminator")
    if not isinstance(discriminator, dict):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "probe.discriminator must be a dict",
            code=2,
        )

    # Compute has_production_site_check from probe.discriminator.production_site_check.
    has_production_site_check = discriminator.get("production_site_check") is not None

    # Compute confidence_grade via the schema function.
    confidence_grade = handoff_schema.compute_confidence_grade(
        tier=tier,
        evidence_source=args.evidence_source,
        hypothesis_confirmed=args.hypothesis_confirmed,
        has_production_site_check=has_production_site_check,
    )

    # Build outcome dict.
    confirmed_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    outcome_dict = {
        "hypothesis_confirmed": args.hypothesis_confirmed,
        "evidence_source": args.evidence_source,
        "evidence_cite": args.evidence_cite,
        "actual_fix_path": args.actual_fix_path,
        "delta_from_recommendation": args.delta_from_recommendation,
        "confirmed_date": confirmed_date,
        "confirmed_commit_sha": args.confirmed_commit_sha,
        "confidence_grade": confidence_grade,
    }

    # Validate outcome via schema dataclass (catches enum / format errors).
    try:
        handoff_schema.Outcome(**outcome_dict)
    except (TypeError, ValueError) as err:
        return _die(
            "append-outcome: handoff.json schema validation failed: {0}".format(err), code=2
        )

    # Mutate and atomically write handoff.json.
    data["outcome"] = outcome_dict
    target = Path(handoff_path_str).resolve()
    try:
        _atomic_write_json(data, target)
    except OSError as err:
        return _die("append-outcome: cannot write {0}: {1}".format(target, err))

    # Optionally append '## Outcome' section to the parallel .md file.
    research_path = data.get("research_path")
    if research_path and isinstance(research_path, str):
        md_path = (Path(handoff_path_str).parent / research_path).resolve()
        if md_path.is_file():
            md_section = _build_outcome_md_section(outcome_dict)
            try:
                with open(str(md_path), "a", encoding="utf-8") as f:
                    f.write("\n")
                    f.write(md_section)
            except OSError:
                # Non-fatal: handoff.json is source of truth.
                pass

    sys.stdout.write(
        "appended outcome to {0} (confidence_grade={1})\n".format(
            handoff_path_str, confidence_grade
        )
    )
    return 0


def cmd_check_outcome(args):
    # type: (argparse.Namespace) -> int
    """Print 'unmarked' or 'marked: <details>' for the outcome block in handoff.json.

    Dispatches on handoff_kind:
    - absent / "research" -> research branch: "marked: <hypothesis_confirmed> (confidence=<grade>, evidence=<source>)"
    - "discover"          -> discover branch: "marked: shipped=<id> (confidence=<grade>, build_vs_buy=<val>, internal_extension=<true|false|n/a>)"
    - any other value     -> exit 2

    Non-blocking: always exits 0 unless the file is missing or unknown kind (exit 2).

    Steps:
    1. Read handoff.json. Missing → exit 2.
    2. Detect kind. Unknown kind → exit 2.
    3. If outcome is None/absent → stdout "unmarked", exit 0.
    4. If outcome is present → stdout "marked: <details>", exit 0.
    """
    data, err = _load_handoff_json(args.handoff_path)
    if err is not None:
        return _die("check-outcome: {0}".format(err), code=2)

    kind = data.get("handoff_kind", "research")
    if kind not in ("research", "discover"):
        return _die(
            "check-outcome: unknown handoff_kind={0!r};"
            " expected 'research' or 'discover'".format(kind),
            code=2,
        )

    outcome = data.get("outcome")
    if outcome is None:
        if kind == "discover":
            sys.stdout.write(
                "unmarked\n"
                "  Task shipped? Linked discovery handoff has no outcome marker.\n"
                "  Run .devforge/lib/discover_helper append-outcome to record:\n"
                "    - which design option (A/B/C/hybrid/none) actually shipped\n"
                "    - whether the recommended build-vs-buy direction held\n"
                "    - whether the internal-canonical-pattern extension was followed\n"
                "  Skipping leaves the discovery report as speculation in empirical-memory corpus.\n"
            )
        else:
            sys.stdout.write("unmarked\n")
        return 0

    if kind == "discover":
        shipped_id = outcome.get("design_option_shipped_id", "unknown")
        grade = outcome.get("confidence_grade", "unknown")
        bvb = outcome.get("build_vs_buy_actual", "unknown")
        internal_raw = outcome.get("internal_extension_followed")
        if internal_raw is None:
            internal_str = "n/a"
        else:
            internal_str = "true" if internal_raw else "false"
        sys.stdout.write(
            "marked: shipped={0} (confidence={1}, build_vs_buy={2},"
            " internal_extension={3})\n".format(shipped_id, grade, bvb, internal_str)
        )
    else:
        # research branch
        hypothesis = outcome.get("hypothesis_confirmed", "unknown")
        grade = outcome.get("confidence_grade", "unknown")
        evidence = outcome.get("evidence_source", "unknown")
        sys.stdout.write(
            "marked: {0} (confidence={1}, evidence={2})\n".format(hypothesis, grade, evidence)
        )
    return 0
