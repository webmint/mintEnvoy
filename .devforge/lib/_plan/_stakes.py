"""_plan/_stakes.py -- stakes-hint signal computation for plan_helper.

Computes whether a just-finalized plan (plan-handoff.json's breakdown_seeds,
plus the filesystem) crosses a "high-stakes" threshold worth an advisory
nudge toward /grill. This module is pure computation + rendering -- no I/O
beyond a single filesystem existence check (sibling data-model.md) and no
argparse/CLI concerns; those stay in plan_helper.py per the house SRP split
(schema/parsing modules vs. CLI dispatch).

Threshold design (must fire on a MINORITY of plans -- see plan_helper.py's
stakes-hint help text): each signal was picked so a small/typical plan (a
handful of files, no new data model, no new dependency, no security-adjacent
risk/decision, a normal risk count) stays silent, while a plan doing
something structurally significant fires. Composition is OR-of-signals --
ANY one signal is sufficient, because each was individually tuned to be rare:

  - file_impact rows >= FILE_IMPACT_THRESHOLD (8) -- wide blast radius.
    A typical small-to-medium feature plan touches 2-6 files (see the
    checked-in plan_handoff_fixture.md: 4 real File Impact rows); 8+ is an
    unusually large surface for a single plan.
  - risks rows >= RISK_THRESHOLD (4) -- unusually risk-laden. Typical plans
    record 1-2 risks (the fixture records 2); 4+ signals the author
    themselves flagged this as more fraught than average.
  - a "real" (non-negated) Dependencies entry -- approximates "introduces a
    new dependency". The plan-handoff schema carries no new-vs-existing
    flag (BreakdownSeeds.dependencies is just parsed prose lines), so a
    naive "dependencies list is non-empty" signal would fire on nearly
    every plan -- most plans discuss dependencies even to say "none". A
    line counts as a real dependency when it contains a positive
    dependency verb (adds/introduces/requires/needs/depends on/uses/pulls
    in) whose immediate object is NOT itself a negation word -- this
    catches phrasing like "None needed for the core, but adds Redux" where
    a genuine dependency follows an opening negation, while still treating
    a negated verb ("Requires no changes.") or a pure negation phrase
    ("None.", "No new dependencies.") as not-a-dependency. Lines with none
    of those verb keywords fall back to the plain open-with-a-negation-word
    check.
  - sibling data-model.md present -- a new/changed data model is a
    deliberate authoring decision (the file only exists when /plan wrote
    one), not a default artifact every plan produces.
  - a security-relevant keyword in risks (risk + impact text) or
    key_design_decisions (decision + why text) -- per spec, scanning only
    those fields (not likelihood/mitigation/chosen_approach/alternatives)
    keeps the scan focused on stated risk/rationale prose rather than
    process metadata.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Thresholds.
# ---------------------------------------------------------------------------

FILE_IMPACT_THRESHOLD = 8
RISK_THRESHOLD = 4


# ---------------------------------------------------------------------------
# Dependency negation filter.
# ---------------------------------------------------------------------------

# Negation words a dependency line uses to say "nothing new". Covers the
# bare `no`/`no <noun>` forms AND the run-on `nothing`/`nobody` forms whose
# lack of a word boundary after `no` a naive `no\b` misses -- plus `zero`.
# KNOWN, ACCEPTED limitation: a negation SEPARATED from its verb by an
# interposed clause (e.g. "Requires, after review, no changes at all.")
# is not detected -- the verb's immediate object is the clause, not the
# negation, and general clause-distance negation is regex-infeasible without
# risking over-suppression of legitimate lines. Such a line may fire a
# spurious (low-harm, advisory-only) hint. Accepted, not a bug.
_NEGATION_RE = re.compile(r"^(?:no(?:thing|body)?|none|n/a|nil|zero)\b", re.IGNORECASE)

# A positive dependency verb, matched anywhere in a line (not just at the
# start) -- this is what lets "None needed for the core, but adds Redux"
# be recognized as a real dependency even though the line opens with a
# negation. See module docstring for the full rationale + the negated-verb
# guard (_has_positive_dependency_verb below).
_POSITIVE_DEP_VERB_RE = re.compile(
    r"\b(?:adds?|introduces?|requires?|needs?|depends?\s+on|uses?|pulls?\s+in)\b",
    re.IGNORECASE,
)


def _has_positive_dependency_verb(stripped_line):
    # type: (str) -> Optional[bool]
    """Classify a single stripped line by its positive-dependency-verb usage.

    Returns:
      True  -- at least one verb occurrence whose immediate object is NOT
               a negation word (a genuine positive dependency assertion,
               e.g. "adds Redux").
      False -- one or more verb occurrences, but EVERY one is immediately
               followed by a negation word (e.g. "Requires no changes.") --
               a negated claim, not a real dependency.
      None  -- no recognized verb keyword appears in the line at all; the
               caller falls back to the plain negation-prefix heuristic.
    """
    matches = list(_POSITIVE_DEP_VERB_RE.finditer(stripped_line))
    if not matches:
        return None
    for match in matches:
        rest = stripped_line[match.end():].lstrip()
        if not _NEGATION_RE.match(rest):
            return True
    return False


def _has_real_dependency(dependencies):
    # type: (List[Any]) -> bool
    """Return True if dependencies has >=1 non-blank, non-negated entry.

    Approximates 'introduces a new dependency' -- see module docstring for
    why a naive non-empty check is too noisy to use directly. A non-string
    entry (a malformed/hand-authored shape the real producer cannot emit)
    is treated as not-a-dependency rather than raising.
    """
    for line in dependencies:
        if not isinstance(line, str):
            continue
        stripped = line.strip()
        if not stripped:
            continue

        verb_hit = _has_positive_dependency_verb(stripped)
        if verb_hit is True:
            return True
        if verb_hit is False:
            # Every recognized verb occurrence was negated -- a negated
            # claim, not a real dependency. Do not fall through.
            continue

        # No recognized verb keyword at all -- fall back to the plain
        # negation-prefix heuristic.
        if _NEGATION_RE.match(stripped):
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Security keyword scan.
# ---------------------------------------------------------------------------

_SECURITY_KEYWORDS = (
    "auth",
    "authentication",
    "authorization",
    "token",
    "password",
    "secret",
    "credential",
    "pii",
    "encrypt",
    "encryption",
    "permission",
    "access control",
    "session",
    "oauth",
    "jwt",
    "api key",
    "apikey",
)

_SECURITY_WORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _SECURITY_KEYWORDS) + r")\w*",
    re.IGNORECASE,
)


def _security_hit(*texts):
    # type: (Any) -> bool
    """Return True if any text contains a case-insensitive security keyword.

    A non-string text (a malformed/hand-authored field value the real
    producer cannot emit) is skipped rather than raising -- this function
    never assumes its arguments are strings.
    """
    for text in texts:
        if isinstance(text, str) and text and _SECURITY_WORD_RE.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Signal computation.
# ---------------------------------------------------------------------------


def compute_signals(breakdown_seeds, handoff_dir):
    # type: (Dict[str, Any], Path) -> Dict[str, Any]
    """Compute stakes signals from a breakdown_seeds dict + the handoff dir.

    breakdown_seeds is the plain dict (not the dataclass) loaded from
    plan-handoff.json -- callers must have already confirmed it is a dict.
    Every field is read defensively (.get() with a type check + fallback to
    an empty list/string) so a partially-shaped or malformed breakdown_seeds
    degrades individual signals to False rather than raising -- this module
    never raises on shape mismatches; callers additionally wrap file I/O and
    JSON parsing in their own fail-soft guard.

    Returns a dict with per-signal booleans/counts and an overall 'fires' bool.
    """
    file_impact = breakdown_seeds.get("file_impact")
    if not isinstance(file_impact, list):
        file_impact = []

    risks = breakdown_seeds.get("risks")
    if not isinstance(risks, list):
        risks = []

    decisions = breakdown_seeds.get("key_design_decisions")
    if not isinstance(decisions, list):
        decisions = []

    dependencies = breakdown_seeds.get("dependencies")
    if not isinstance(dependencies, list):
        dependencies = []

    file_count = len(file_impact)
    risk_count = len(risks)

    large_blast_radius = file_count >= FILE_IMPACT_THRESHOLD
    many_risks = risk_count >= RISK_THRESHOLD
    new_dependency = _has_real_dependency(dependencies)

    data_model_path = Path(handoff_dir) / "data-model.md"
    new_data_model = data_model_path.is_file()

    security_relevant = False
    for row in risks:
        if not isinstance(row, dict):
            continue
        if _security_hit(row.get("risk"), row.get("impact")):
            security_relevant = True
            break
    if not security_relevant:
        for row in decisions:
            if not isinstance(row, dict):
                continue
            if _security_hit(row.get("decision"), row.get("why")):
                security_relevant = True
                break

    fires = (
        large_blast_radius
        or many_risks
        or new_dependency
        or new_data_model
        or security_relevant
    )

    return {
        "fires": fires,
        "file_count": file_count,
        "risk_count": risk_count,
        "large_blast_radius": large_blast_radius,
        "many_risks": many_risks,
        "new_dependency": new_dependency,
        "new_data_model": new_data_model,
        "security_relevant": security_relevant,
    }


# ---------------------------------------------------------------------------
# Rendering.
# ---------------------------------------------------------------------------


def render_hint(signals, plan_path):
    # type: (Dict[str, Any], str) -> str
    """Render the advisory hint block. Callers only echo this string verbatim.

    Ends with the literal next step '/grill <plan_path>' as its final line
    per the stakes-hint output contract. Reason order is fixed (blast radius,
    data model, security, dependency, risk count) so output is deterministic.
    """
    reasons = []
    if signals.get("large_blast_radius"):
        reasons.append("touches {0} files".format(signals.get("file_count", 0)))
    if signals.get("new_data_model"):
        reasons.append("new data model")
    if signals.get("security_relevant"):
        reasons.append("security-relevant")
    if signals.get("new_dependency"):
        reasons.append("introduces a dependency")
    if signals.get("many_risks"):
        reasons.append("{0} risks recorded".format(signals.get("risk_count", 0)))

    reason_str = " · ".join(reasons) if reasons else "high-stakes signals detected"

    return (
        "**High-stakes plan detected**: {0}.\n"
        "Consider running /grill for a design-level adversarial review "
        "before /breakdown decomposes this plan into tasks (optional, not "
        "a gate).\n"
        "\n"
        "/grill {1}\n"
    ).format(reason_str, plan_path)
