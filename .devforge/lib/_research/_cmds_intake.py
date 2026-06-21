"""Step 5 — intake-interrogation gate command handlers for research_helper.

Two verbs:
  record-intake-classification  — setter: persists per-statement binary
                                   classification (requirement vs hypothesis)
                                   + the orchestrator-composed minimal_fix.
  render-intake-echo             — render verb: emits the echo-back block
                                   (requirements / hypotheses-to-verify /
                                   minimal fix) to stdout verbatim for the
                                   orchestrator to copy to the user.

Helper-owns-shape: the orchestrator supplies the classification values;
this module owns the echo-block structure and storage layout.

Binary classification is DELIBERATE (not a 5-type taxonomy). See plan
Step 5 §"Binary classification" for rationale — a two-class partition
(hypothesis-vs-requirement conflation) is the minimal fix that traces
directly to the observed over-build failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from ._state import _load_memo, _state_transaction
from ._validators import _die, _validate_scalar


# ---------------------------------------------------------------------------
# Enum — single source of truth for the binary classification kind.
# ---------------------------------------------------------------------------

INTAKE_KIND_ENUM = ("requirement", "hypothesis")


# ---------------------------------------------------------------------------
# Setter handler.
# ---------------------------------------------------------------------------


def cmd_record_intake_classification(args: argparse.Namespace) -> int:
    """Append (or replace) a per-statement intake classification in memo.

    Persists {statement, kind, minimal_fix} into memo.intake_classifications.
    If an entry with the same statement already exists it is overwritten
    (idempotent re-recording on correction).

    --kind must be one of: requirement | hypothesis.
    --minimal-fix is optional; when omitted the field is stored as None.
    A None minimal_fix is valid for a hypothesis (the minimal fix is "verify
    this before acting on it", not a code change). A None minimal_fix for a
    requirement means the orchestrator has not yet determined the minimal
    change — the render verb will surface this as "(not set)".
    """
    try:
        statement = _validate_scalar(args.statement, "record-intake-classification.statement")
    except ValueError as err:
        return _die(str(err), code=2)

    kind = args.kind
    if kind not in INTAKE_KIND_ENUM:
        return _die(
            "record-intake-classification: --kind {0!r} is not valid; "
            "allowed: {1}".format(kind, list(INTAKE_KIND_ENUM)),
            code=2,
        )

    minimal_fix = None
    if args.minimal_fix is not None:
        try:
            minimal_fix = _validate_scalar(args.minimal_fix, "record-intake-classification.minimal_fix")
        except ValueError as err:
            return _die(str(err), code=2)

    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            classifications = memo.setdefault("intake_classifications", [])
            # Idempotent: replace existing entry with the same statement.
            for entry in classifications:
                if isinstance(entry, dict) and entry.get("statement") == statement:
                    entry["kind"] = kind
                    entry["minimal_fix"] = minimal_fix
                    break
            else:
                classifications.append({
                    "statement": statement,
                    "kind": kind,
                    "minimal_fix": minimal_fix,
                })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-intake-classification: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Render handler.
# ---------------------------------------------------------------------------


def cmd_render_intake_echo(args: argparse.Namespace) -> int:
    """Render the intake echo-back block to stdout (verbatim copy to user).

    Block structure:
      ## Intake interpretation

      ### Requirements (what you asked for)
      - <statement>
        Minimal scope: <minimal_fix>

      ### Hypotheses to verify — NOT requirements
      These are suspected causes or mechanism guesses. They will route
      to investigation, not to implementation direction.
      - <statement>

      ### Minimal scope
      The simplest change that satisfies the stated desired outcome alone:
      <minimal_fix from the first requirement entry, else "(not set)">

    Proportionality: when there are no hypotheses the hypothesis section
    is omitted entirely (a clean prompt needs no interrogation section).
    When there are no requirements, the Requirements header and "*(no
    requirements classified)*" placeholder are suppressed — only the
    hypotheses section is shown. The Minimal scope section is omitted
    entirely when there are no requirements.
    When intake_classifications is empty, emits a notice.
    """
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-intake-echo: {0}".format(err))

    classifications = memo.get("intake_classifications") or []

    if not classifications:
        sys.stdout.write(
            "<!-- intake-echo: no classifications recorded -->\n"
        )
        return 0

    requirements = [e for e in classifications if e.get("kind") == "requirement"]
    hypotheses = [e for e in classifications if e.get("kind") == "hypothesis"]

    lines = []  # type: List[str]
    lines.append("## Intake interpretation")
    lines.append("")

    # Requirements section — rendered only when non-empty (F2: suppress header
    # and placeholder when only hypotheses are recorded).
    if requirements:
        lines.append("### Requirements (what you asked for)")
        lines.append("")
        for entry in requirements:
            lines.append("- {0}".format(entry.get("statement", "")))
            mf = entry.get("minimal_fix")
            if mf:
                lines.append("  Minimal scope: {0}".format(mf))
        lines.append("")

    # Hypotheses section — OMITTED when empty (proportionality rule).
    if hypotheses:
        lines.append("### Hypotheses to verify — NOT requirements")
        lines.append("")
        lines.append(
            "These are suspected causes or mechanism guesses. They route "
            "to investigation, not to implementation direction."
        )
        lines.append("")
        for entry in hypotheses:
            lines.append("- {0}".format(entry.get("statement", "")))
        lines.append("")

    # Minimal scope — omitted entirely when there are no requirements (F2:
    # no noise on a hypothesis-only prompt). When present, derives from the
    # first requirement's minimal_fix, or "(not set)" when absent.
    if requirements:
        minimal_fix_for_scope = None
        for entry in requirements:
            mf = entry.get("minimal_fix")
            if mf:
                minimal_fix_for_scope = mf
                break

        lines.append("### Minimal scope")
        lines.append("")
        lines.append(
            "The simplest change that satisfies the stated desired outcome alone:"
        )
        lines.append("")
        lines.append(minimal_fix_for_scope or "(not set)")
        lines.append("")

    sys.stdout.write("\n".join(lines) + "\n")
    return 0
