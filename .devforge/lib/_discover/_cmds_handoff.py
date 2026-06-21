"""03-DISCOVER-HANDOFF-PLAN subcommands.

finalize-handoff (Step 3 -- memo+report -> handoff.json),
append-outcome (Step 5 -- record post-discovery outcome).
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
from ._state import _atomic_write_json, _load_memo, _load_report
from ._validators import _die, _validate_enum


# ---------------------------------------------------------------------------
# finalize-handoff command.
# ---------------------------------------------------------------------------


def cmd_finalize_handoff(args):
    # type: (argparse.Namespace) -> int
    """Read discover state -> build Handoff -> validate -> write handoff.json."""
    devforge_dir = args.devforge_dir
    try:
        memo = _load_memo(devforge_dir)
        report = _load_report(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("finalize-handoff: cannot load state: {0}".format(err))

    # Defensive double-gate: run verify invariants A-G before schema mapping.
    # Lazy import avoids potential circular-import issues as module graph grows.
    from ._cmds_core import cmd_verify  # noqa: PLC0415
    verify_args = argparse.Namespace(devforge_dir=args.devforge_dir)
    rc = cmd_verify(verify_args)
    if rc != 0:
        return rc

    # Required-field guards.
    if not memo.get("topic_slug"):
        return _die(
            "finalize-handoff: memo.topic_slug not set (run set-topic first)", code=2
        )
    if not report.get("date"):
        return _die(
            "finalize-handoff: report.date not set (run set-date first)", code=2
        )
    if not report.get("verdict"):
        return _die(
            "finalize-handoff: report.verdict not set (run set-verdict first)", code=2
        )
    if not report.get("summary"):
        return _die(
            "finalize-handoff: report.summary not set (run set-summary first)", code=2
        )
    # recommended_option required when verdict is in proceeding-set.
    verdict = (report.get("verdict") or "").strip()
    if verdict in {"Worth pursuing", "Promising with caveats"}:
        if not report.get("recommended_option"):
            return _die(
                "finalize-handoff: report.recommended_option not set "
                "(run set-recommended-option first)",
                code=2,
            )
    if not memo.get("verbatim_prompt"):
        return _die(
            "finalize-handoff: memo.verbatim_prompt not set "
            "(run set-verbatim-prompt first)",
            code=2,
        )

    try:
        handoff = _build_handoff_from_state(memo, report)
    except ValueError as err:
        return _die(
            "finalize-handoff: schema validation failed: {0}".format(err), code=2
        )

    # Determine target path.
    emit_path = getattr(args, "emit_handoff_json", None)
    if not emit_path:
        date = report.get("date", "")
        slug = memo.get("topic_slug", "unknown")
        emit_path = "discover/{0}-{1}.handoff.json".format(date, slug)

    target = Path(emit_path).resolve()
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
# append-outcome helpers.
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
        "- **design_option_shipped_id**: {0}".format(outcome["design_option_shipped_id"]),
        "- **design_option_shipped_summary**: {0}".format(outcome["design_option_shipped_summary"]),
        "- **matches_recommendation**: {0}".format(outcome["matches_recommendation"]),
        "- **build_vs_buy_actual**: {0}".format(outcome["build_vs_buy_actual"]),
        "- **matches_build_vs_buy_recommendation**: {0}".format(
            outcome["matches_build_vs_buy_recommendation"]
        ),
        "- **verdict_held**: {0}".format(outcome["verdict_held"]),
        "- **confidence_grade**: {0}".format(outcome["confidence_grade"]),
        "- **shipped_date**: {0}".format(outcome["shipped_date"]),
    ]
    if outcome.get("shipped_commit_sha"):
        lines.append("- **shipped_commit_sha**: {0}".format(outcome["shipped_commit_sha"]))
    if outcome.get("internal_extension_followed") is not None:
        lines.append(
            "- **internal_extension_followed**: {0}".format(
                outcome["internal_extension_followed"]
            )
        )
    if outcome.get("delta_from_recommendation"):
        lines.append(
            "- **delta_from_recommendation**: {0}".format(outcome["delta_from_recommendation"])
        )
    lines.append("")
    return "\n".join(lines)


def _has_internal_prior_art_in_dict(cited_patterns_list):
    # type: (list) -> bool
    """Return True when any cited_pattern dict has is_internal=True."""
    for cp in cited_patterns_list:
        if isinstance(cp, dict) and cp.get("is_internal") is True:
            return True
    return False


# ---------------------------------------------------------------------------
# append-outcome command.
# ---------------------------------------------------------------------------


def cmd_append_outcome(args):
    # type: (argparse.Namespace) -> int
    """Record post-discovery outcome into handoff.json and optionally its parallel .md.

    Idempotency: re-running OVERWRITES the existing outcome block in handoff.json
    (last-write-wins). The parallel .md file gets a NEW '## Outcome' section appended
    each time (append-only audit trail -- no de-dup).
    """
    handoff_path_str = args.handoff_path
    data, err = _load_handoff_json(handoff_path_str)
    if err is not None:
        return _die(
            "append-outcome: handoff.json schema validation failed: {0}".format(err), code=2
        )

    # Validate minimum structure.
    if data.get("handoff_kind") != "discover":
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "expected handoff_kind='discover', got {0!r}".format(
                data.get("handoff_kind")
            ),
            code=2,
        )

    plan_seeds = data.get("plan_seeds")
    if not isinstance(plan_seeds, dict):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "missing or non-dict 'plan_seeds' block",
            code=2,
        )

    discovery_block = data.get("discovery_block")
    if not isinstance(discovery_block, dict):
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "missing or non-dict 'discovery_block' block",
            code=2,
        )

    recommended_option_id = plan_seeds.get("recommended_option_id")
    bvb_dict = plan_seeds.get("build_vs_buy") or {}
    bvb_recommendation = bvb_dict.get("recommendation")
    if not bvb_recommendation:
        return _die(
            "append-outcome: handoff.json schema validation failed: "
            "plan_seeds.build_vs_buy.recommendation is missing or empty",
            code=2,
        )
    try:
        bvb_recommendation = _validate_enum(
            bvb_recommendation,
            "plan_seeds.build_vs_buy.recommendation",
            ("Build", "Buy", "Hybrid"),
        )
    except ValueError as err:
        return _die(
            "append-outcome: handoff.json schema validation failed: {0}".format(err),
            code=2,
        )
    cited_patterns = plan_seeds.get("cited_canonical_patterns") or []
    verdict = (discovery_block.get("verdict") or "Reconsider").strip()

    # Parse args.
    design_option_shipped_id = (args.design_option_shipped_id or "").strip()
    design_option_shipped_summary = (args.design_option_shipped_summary or "").strip()
    build_vs_buy_actual = (args.build_vs_buy_actual or "").strip()
    shipped_commit_sha = getattr(args, "shipped_commit_sha", None)
    delta_from_recommendation = getattr(args, "delta_from_recommendation", None)
    internal_extension_followed_raw = getattr(args, "internal_extension_followed", None)

    # Parse internal_extension_followed.
    if internal_extension_followed_raw in ("true",):
        internal_extension_followed = True  # type: Optional[bool]
    elif internal_extension_followed_raw in ("false",):
        internal_extension_followed = False
    else:
        internal_extension_followed = None

    # Compute helper-derived match flags.
    matches_recommendation = (design_option_shipped_id == recommended_option_id)
    matches_build_vs_buy_recommendation = (build_vs_buy_actual == bvb_recommendation)

    # Compute verdict_held.
    verdict_held = True  # type: bool
    if verdict == "Reconsider" and shipped_commit_sha is not None:
        verdict_held = False
    elif verdict in {"Worth pursuing", "Promising with caveats"} and design_option_shipped_id == "none":
        verdict_held = False

    # Compute confidence_grade.
    confidence_grade = handoff_schema.compute_confidence_grade(
        verdict_held=verdict_held,
        matches_recommendation=matches_recommendation,
        matches_build_vs_buy_recommendation=matches_build_vs_buy_recommendation,
        internal_extension_followed=internal_extension_followed,
    )

    # Enforce internal_extension_followed presence rule.
    has_internal = _has_internal_prior_art_in_dict(cited_patterns)
    if has_internal and internal_extension_followed is None:
        return _die(
            "append-outcome: --internal-extension-followed must be supplied (true or false) "
            "when handoff has internal prior-art entries; "
            "run with --internal-extension-followed <true|false>",
            code=2,
        )
    if not has_internal and internal_extension_followed is not None:
        return _die(
            "append-outcome: --internal-extension-followed must be omitted "
            "when handoff has no internal prior-art entries",
            code=2,
        )

    # Enforce delta_from_recommendation when any match flag is False.
    needs_delta = (
        not matches_recommendation
        or not matches_build_vs_buy_recommendation
        or internal_extension_followed is False
    )
    if needs_delta and not (delta_from_recommendation and delta_from_recommendation.strip()):
        return _die(
            "append-outcome: --delta-from-recommendation is required when any of "
            "(matches_recommendation, matches_build_vs_buy_recommendation, "
            "internal_extension_followed) is False",
            code=2,
        )

    shipped_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    outcome_dict = {
        "design_option_shipped_id": design_option_shipped_id,
        "design_option_shipped_summary": design_option_shipped_summary,
        "matches_recommendation": matches_recommendation,
        "build_vs_buy_actual": build_vs_buy_actual,
        "matches_build_vs_buy_recommendation": matches_build_vs_buy_recommendation,
        "internal_extension_followed": internal_extension_followed,
        "verdict_held": verdict_held,
        "shipped_commit_sha": shipped_commit_sha,
        "shipped_date": shipped_date,
        "confidence_grade": confidence_grade,
        "delta_from_recommendation": delta_from_recommendation,
    }

    # Validate outcome via schema dataclass (catches enum / format errors).
    try:
        handoff_schema.Outcome(**outcome_dict)
    except (TypeError, ValueError) as err:
        return _die(
            "append-outcome: outcome schema validation failed: {0}".format(err), code=2
        )

    # Mutate and atomically write handoff.json.
    data["outcome"] = outcome_dict
    target = Path(handoff_path_str).resolve()
    try:
        _atomic_write_json(data, target)
    except OSError as err:
        return _die("append-outcome: cannot write {0}: {1}".format(target, err))

    # Optionally append '## Outcome' section to the parallel .md file.
    report_path = data.get("report_path")
    md_appended_path = None
    if report_path and isinstance(report_path, str):
        # report_path is relative to the project root; resolve relative to handoff location.
        handoff_dir = Path(handoff_path_str).resolve().parent
        # Try relative to handoff dir first, then relative to cwd.
        candidate_paths = [
            handoff_dir / report_path,
            Path(report_path),
        ]
        for candidate in candidate_paths:
            if candidate.is_file():
                md_section = _build_outcome_md_section(outcome_dict)
                try:
                    with open(str(candidate), "a", encoding="utf-8") as f:
                        f.write("\n")
                        f.write(md_section)
                    md_appended_path = str(candidate)
                except OSError:
                    # Non-fatal: handoff.json is source of truth.
                    pass
                break

    sys.stdout.write("wrote: {0}\n".format(target))
    if md_appended_path:
        sys.stdout.write("appended outcome section to: {0}\n".format(md_appended_path))
    return 0
