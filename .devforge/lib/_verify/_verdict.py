"""_verdict.py — deterministic verdict computation for /verify.

Public surface
--------------
  compute_verdict(ac_results, mechanical_status, review_findings,
                  hygiene, ac_verification_mode) -> dict

      Deterministic APPROVED / NEEDS WORK / REJECTED decision.

      Parameters
      ----------
      ac_results : list[dict]
          Output of merge_ac_results: per-AC dicts with ``status`` field
          (PASS, FAIL, PARTIAL, MANUAL, PASS (code), FAIL (code), PARTIAL (code),
          UNVERIFIED).  Empty list = no ACs = skip AC checks.
      mechanical_status : str
          String from implement_helper verify-touched's ``status`` field.
          Passing values: ``"pass"`` or ``""`` / None.
          Non-passing: ``"self_repair"``, ``"failed"``,
          ``"isolation_failure"``, ``"tooling_unavailable"``.
      review_findings : dict
          Output of read_review_findings: folded findings dict with keys
          ``confirmed``, ``contested``, ``missing``, ``summary``.
      hygiene : dict
          Output of check_hygiene: keys ``scope_creep``, ``leftover_artifacts``.
      ac_verification_mode : str
          One of: ``"code-only"``, ``"tests"``, ``"runtime-assisted"``, ``"off"``.

      Returns
      -------
      dict with keys:
        verdict  : str    — "APPROVED", "NEEDS WORK", or "REJECTED"
        reasons  : list[str]   — human-readable explanation lines
        blockers : list[dict]  — structured blockers for report/bug-filing
            Each blocker dict: {type, detail}  where type is one of:
              "constitution_confirmed", "constitution_contested",
              "ac_failure", "mechanical_failed",
              "critical_high_finding"

Verdict rule (deterministic — document every branch here)
----------------------------------------------------------

Step 1 — gather facts:
  - ac_failures: ACs with status FAIL or PARTIAL (any suffix).
  - verifiable_count: ACs whose status is NOT UNVERIFIED or MANUAL.
  - constitution_confirmed: any confirmed finding with tag [CONSTITUTION-VIOLATION]
    or category "constitution".
  - constitution_contested: any contested finding with tag [CONSTITUTION-VIOLATION]
    or category "constitution".
  - critical_high: any confirmed OR contested finding with severity Critical or High.
  - mechanical_failed: mechanical_status not in {"pass", "", None}.

Advisory (never blocks verdict):
  - hygiene_flags: scope_creep non-empty OR leftover_artifacts non-empty.
    Surfaced as a reason line for visibility but NEVER added to blockers and
    NEVER causes NEEDS WORK on its own.  Hygiene is a heuristic over a heuristic;
    a clean feature should not be demoted to NEEDS WORK by it.

Step 2 — mode-aware AC blocking:
  Under ac_verification_mode == "off", AC failures are ADVISORY only — they
  appear in reasons but do NOT count as blockers and do NOT trigger REJECTED.
  Under all other modes, FAIL/PARTIAL ACs ARE blockers.

  OQ-1 resolution: "off" mode enables APPROVED (verdict explicitly notes
  ACs were verified by code-reading floor only).

Step 3 — verdict (priority order):
  REJECTED   if:
    - constitution_confirmed (confirmed [CONSTITUTION-VIOLATION]) OR
    - mode != "off" AND failing_count >= 2 AND failure_rate >= 0.5
      (failure_rate = failing_count / verifiable_count;
       failing_count = number of FAIL/PARTIAL verifiable ACs;
       both conditions required — a single AC failure, regardless of rate,
       is a task bug (NEEDS WORK) not a spec-level problem (REJECTED))
  NEEDS WORK if any blocker present:
    - (mode-aware) ac_failures not empty
    - mechanical_failed
    - critical_high finding
    - constitution_contested (always Critical — D7 invariant: a contested
      constitution violation is at least NEEDS WORK, never APPROVED)
  APPROVED   otherwise (no blockers)

  NOTE: hygiene_flags (scope_creep / leftover_artifacts) are ADVISORY and
  are intentionally NOT in the blocker list above.  They appear in reasons
  for visibility; they never cause NEEDS WORK on an otherwise-clean feature.

D7 invariant (constitution violations always block APPROVED):
  - confirmed [CONSTITUTION-VIOLATION] → always REJECTED
  - contested [CONSTITUTION-VIOLATION] → always at least NEEDS WORK
  This is enforced structurally: constitution_confirmed triggers REJECTED
  in Step 3 first-check, and constitution_contested is a separate blocker
  class that prevents APPROVED even when all ACs pass.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

# mechanical_status values that mean "checks passed"
_PASSING_MECHANICAL = frozenset(["pass", "", None])

# AC status values that represent a failure or partial pass
# (PARTIAL means the AC is only partially satisfied — treated as failure)
_FAIL_STATUSES = frozenset([
    "FAIL", "PARTIAL",
    "FAIL (code)", "PARTIAL (code)",
])

# AC status values that are "verifiable" (not skipped/unknown)
# UNVERIFIED and MANUAL are excluded from failure-rate denominator
_UNVERIFIABLE_STATUSES = frozenset(["UNVERIFIED", "MANUAL"])

# Severity levels that constitute a "critical_high" blocker
_CRITICAL_HIGH = frozenset(["Critical", "High"])

# The tag that marks a finding as a constitution violation
_CONSTITUTION_TAG = "[CONSTITUTION-VIOLATION]"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_constitution_violation(finding):
    # type: (dict) -> bool
    """Return True if the finding is a constitution violation."""
    tags = finding.get("tags") or []
    category = finding.get("category") or ""
    return _CONSTITUTION_TAG in tags or category == "constitution"


def _is_critical_high(finding):
    # type: (dict) -> bool
    """Return True if the finding has Critical or High severity."""
    sev = finding.get("severity") or ""
    return sev in _CRITICAL_HIGH


# ---------------------------------------------------------------------------
# compute_verdict
# ---------------------------------------------------------------------------


def compute_verdict(
    ac_results,        # type: List[Dict]
    mechanical_status, # type: Optional[str]
    review_findings,   # type: Dict
    hygiene,           # type: Dict
    ac_verification_mode,  # type: str
):
    # type: (...) -> Dict
    """Compute the APPROVED / NEEDS WORK / REJECTED verdict.

    See module docstring for the full rule.

    Parameters
    ----------
    ac_results : list[dict]
        merge_ac_results output.
    mechanical_status : str or None
        verify-touched status string.
    review_findings : dict
        read_review_findings output.
    hygiene : dict
        check_hygiene output.
    ac_verification_mode : str
        "code-only" | "tests" | "runtime-assisted" | "off"

    Returns
    -------
    dict: {verdict, reasons, blockers}
    """
    reasons = []   # type: List[str]
    blockers = []  # type: List[Dict]

    # --- 1. Gather facts -------------------------------------------------------

    # AC failures and verifiable count
    ac_failures = [
        ac for ac in (ac_results or [])
        if ac.get("status", "") in _FAIL_STATUSES
    ]
    verifiable_acs = [
        ac for ac in (ac_results or [])
        if ac.get("status", "UNVERIFIED") not in _UNVERIFIABLE_STATUSES
    ]
    verifiable_count = len(verifiable_acs)

    failure_count = len(ac_failures)
    failure_rate = (failure_count / verifiable_count) if verifiable_count > 0 else 0.0

    # Review findings
    confirmed_findings = (review_findings or {}).get("confirmed") or []
    contested_findings = (review_findings or {}).get("contested") or []
    review_missing = (review_findings or {}).get("missing", False)

    constitution_confirmed = [f for f in confirmed_findings if _is_constitution_violation(f)]
    constitution_contested = [f for f in contested_findings if _is_constitution_violation(f)]

    critical_high_headline = [
        f for f in (confirmed_findings + contested_findings)
        if _is_critical_high(f) and not _is_constitution_violation(f)
    ]

    # Mechanical status
    mech_norm = (mechanical_status or "").strip()
    mechanical_failed = mech_norm not in _PASSING_MECHANICAL

    # Hygiene flags
    scope_creep = (hygiene or {}).get("scope_creep") or []
    leftover_artifacts = (hygiene or {}).get("leftover_artifacts") or []
    hygiene_flags = bool(scope_creep or leftover_artifacts)

    # --- 2. Build structured blockers (mode-aware for AC) ----------------------

    off_mode = (ac_verification_mode == "off")

    # Constitution-confirmed — always a blocker regardless of mode
    if constitution_confirmed:
        blockers.append({
            "type": "constitution_confirmed",
            "detail": "Confirmed constitution violation(s): {0}".format(
                "; ".join(
                    f.get("pattern") or f.get("file") or "(unknown)"
                    for f in constitution_confirmed
                )
            ),
        })
        reasons.append(
            "CONSTITUTION VIOLATION (confirmed): {0} finding(s) confirm a "
            "constitution rule was broken. This always triggers REJECTED.".format(
                len(constitution_confirmed)
            )
        )

    # Constitution-contested — always a blocker (D7: never APPROVED)
    if constitution_contested:
        blockers.append({
            "type": "constitution_contested",
            "detail": "Contested (unresolved) constitution violation(s): {0}".format(
                len(constitution_contested)
            ),
        })
        reasons.append(
            "CONSTITUTION VIOLATION (contested): {0} finding(s) could not be "
            "confirmed or dismissed. These are always surfaced as blockers.".format(
                len(constitution_contested)
            )
        )

    # AC failures
    if ac_failures:
        if off_mode:
            # Advisory only — note in reasons, but NOT added to blockers
            reasons.append(
                "AC advisory (mode=off): {0} AC(s) did not pass ({1}). "
                "Under ac_verification_mode=off, ACs are verified by "
                "code-reading only and failures are advisory, not blocking.".format(
                    failure_count,
                    ", ".join(a.get("id", "?") for a in ac_failures),
                )
            )
        else:
            blockers.append({
                "type": "ac_failure",
                "detail": "{0} AC(s) failed or partially passed: {1}".format(
                    failure_count,
                    ", ".join(a.get("id", "?") for a in ac_failures),
                ),
            })
            reasons.append(
                "AC failure: {0} of {1} verifiable ACs did not pass.".format(
                    failure_count, verifiable_count
                )
            )

    # Mechanical failures
    if mechanical_failed:
        blockers.append({
            "type": "mechanical_failed",
            "detail": "verify-touched status: {0}".format(mech_norm),
        })
        reasons.append(
            "Mechanical checks failed: verify-touched reported status={0!r}.".format(
                mech_norm
            )
        )

    # Critical/High findings (not already constitution violations)
    if critical_high_headline:
        blockers.append({
            "type": "critical_high_finding",
            "detail": "{0} Critical/High finding(s) from review report.".format(
                len(critical_high_headline)
            ),
        })
        sev_summary = ", ".join(
            "[{0}] {1}".format(
                f.get("severity", "?"),
                (f.get("pattern") or f.get("file") or "(unknown)")[:60],
            )
            for f in critical_high_headline[:3]
        )
        if len(critical_high_headline) > 3:
            sev_summary += " (+ {0} more)".format(len(critical_high_headline) - 3)
        reasons.append(
            "Critical/High review findings: {0}.".format(sev_summary)
        )

    # Hygiene flags — ADVISORY only, never added to blockers
    if hygiene_flags:
        detail_parts = []
        if scope_creep:
            detail_parts.append("{0} scope-creep file(s)".format(len(scope_creep)))
        if leftover_artifacts:
            detail_parts.append(
                "{0} leftover artifact(s)".format(len(leftover_artifacts))
            )
        reasons.append(
            "Hygiene (advisory, non-blocking): {0} — review but does not "
            "block the verdict.".format(", ".join(detail_parts))
        )

    # Missing review report — not a blocker, but noted
    if review_missing:
        reasons.append(
            "Review report not found (run /review first). "
            "Proceeding without folded review findings."
        )

    # --- 3. Determine verdict --------------------------------------------------

    # REJECTED conditions (check before NEEDS WORK)
    is_rejected = False

    if constitution_confirmed:
        is_rejected = True

    if (
        not off_mode
        and failure_count >= 2
        and failure_rate >= 0.5
    ):
        is_rejected = True
        if not any(b["type"] == "ac_failure" for b in blockers):
            # Edge case: might already be in blockers, but add reason if not
            reasons.append(
                "AC failure pattern: {:.0%} ({}/{}) >= 50% with {} absolute failures"
                " — REJECTED.".format(
                    failure_rate, failure_count, verifiable_count, failure_count
                )
            )
        else:
            # Add rejection rationale even if ac_failure blocker is already noted
            reasons.append(
                "AC failure pattern: {:.0%} ({}/{}) >= 50% with {} absolute failures"
                " — triggers REJECTED.".format(
                    failure_rate, failure_count, verifiable_count, failure_count
                )
            )

    if is_rejected:
        verdict = "REJECTED"
    elif blockers:
        verdict = "NEEDS WORK"
    else:
        verdict = "APPROVED"

    # Ensure APPROVED is not possible when constitution violations exist (D7 guard)
    # This is structurally guaranteed by the blocker logic above, but assert here
    # for clarity in testing:
    if verdict == "APPROVED" and (constitution_confirmed or constitution_contested):
        # Should never happen — constitution blockers always populate `blockers`
        verdict = "REJECTED" if constitution_confirmed else "NEEDS WORK"

    return {
        "verdict": verdict,
        "reasons": reasons,
        "blockers": blockers,
    }
