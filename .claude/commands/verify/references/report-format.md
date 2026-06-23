# Feature verification report format

This is the skeleton that the `verify_helper render-report` verb produces and writes to `specs/[feature]/verification.md` (PHASE 5). The helper's render module (`src/devforge/lib/_verify/_report.py`, `render_report`) owns the actual render — this file is **orientation only**, documenting the shape so the orchestrator knows what the report contains. Do not hand-author the report: call `render-report`.

## Verdict-bearing — UNLIKE /review

This report ENDS in a verdict. `/verify` owns the verdict; `/review` does not. The report folds in `/review`'s findings (read from `specs/[feature]/review.md`) and adds AC conformance + assembled mechanical checks on top, then renders the single APPROVED / NEEDS WORK / REJECTED decision. The verdict line is the defining output — do not omit it, and do not treat the report as findings-only.

## Inputs that shape the report

`render-report` assembles the markdown from four helper outputs, all captured to `$WORKDIR` during the run:

1. **The verdict** (`compute-verdict` → `$WORKDIR/verdict.json`) — `verdict` (APPROVED / NEEDS WORK / REJECTED), `reasons` (explanation lines), `blockers` (structured blocker dicts). The verdict is deterministic; the report never re-derives it.
2. **The merged AC results** (`merge-ac-results` → `$WORKDIR/ac-results.json`) — one dict per AC with `id`, `status` (`PASS` / `FAIL` / `PARTIAL` / `MANUAL` / `PASS (code)` / `FAIL (code)` / `PARTIAL (code)` / `UNVERIFIED`), and `evidence`. Drives the Acceptance Criteria table.
3. **The folded review findings** (`read-review-findings` → `$WORKDIR/review.json`) — `missing`, `confirmed`, `contested`, `summary`. Drives the Review Findings block and the Issues Found listing. When `missing` is true, the report says so and points the reader at `/review`.
4. **The hygiene result** (`check-hygiene` → `$WORKDIR/hygiene.json`) — `scope_creep`, `leftover_artifacts`, `scope_creep_checked`, `files_skipped`. Drives the scope-creep + leftover-artifact lines of the Code Quality block.

Plus the `mechanical-status` string carried from `verify-touched` (PHASE 4.1) and the `ac_verification_mode` (PHASE 3.1), both threaded as flags.

## Skeleton

```markdown
# Feature Verification — [feature] — YYYY-MM-DD

**Feature**: specs/[feature]
**Date**: YYYY-MM-DD
**AC Verification Mode**: [code-only | tests | runtime-assisted | off]

## Acceptance Criteria

| AC   | Status      | Evidence                                          |
| ---- | ----------- | ------------------------------------------------- |
| AC-1 | PASS        | [snapshot/response/file:line evidence]            |
| AC-2 | FAIL        | [expected-vs-observed]                            |
| AC-3 | PASS (code) | [implementation in file:line satisfies criterion] |

...

(When the spec defines no ACs, the table is replaced by "_No ACs defined in spec._")

## Code Quality

**Mechanical checks**: [PASS | not run | SELF-REPAIR (warnings) | FAILED | ISOLATION FAILURE | TOOLING UNAVAILABLE]
**Cross-task consistency**: see /review report at specs/[feature]/review.md
**Scope creep**[ _(advisory — does not block the verdict)_ when populated]: [none detected | N changed file(s) outside the planned scope: <files> | not checked (no breakdown-handoff.json baseline)]
**Leftover artifacts**[ _(advisory — does not block the verdict)_ when populated]: [N flagged (debug prints / bare TODOs / commented-out code) | none detected]

(NOTE: the Mechanical checks line is a REPORT of the assembled type-check / lint / build / test run ONCE via verify-touched. /verify does NOT self-repair. The Cross-task consistency line POINTS TO the /review report — /verify does NOT re-review; cross-task code-quality reasoning is /review's job.)

## Review Findings

(Folded from specs/[feature]/review.md.)
N confirmed | N contested | N dismissed | N uncertain
Severity breakdown: N Critical, N High, N Medium, N Info

(When review.md is absent: "_No review report found — run `/review` before `/verify` to fold cross-task findings into this verdict._")

## Issues Found

(Grouped by severity — Critical → High → Medium → Info — drawn from the confirmed + contested findings of the review report. Each entry names the severity, the file:line, the pattern, and any tags such as [CONTESTED].)

### Critical

- [Critical] src/auth.py:42 — [description] [CONTESTED]
  ...

### High

- [High] src/orders.py:88 — [description]
  ...

(When there are no confirmed or contested findings: "_No confirmed or contested findings in the review report._"; when review.md is missing: "_No review report — run /review to identify issues._")

## Verdict

**APPROVED** | **NEEDS WORK** | **REJECTED**

**Reasons**:

- [reason line 1 — e.g. "AC failure: 1 of 5 verifiable ACs did not pass."]
- [reason line 2 — e.g. "Mechanical checks failed: verify-touched reported status='failed'."]
  ...

(On a clean APPROVED with no reasons: "All acceptance criteria satisfied, no blocking issues found.")

**Next step**: [run `/summarize` then `/finalize`. | address the issues above, then re-run `/verify`. Run `/implement` for code fixes. | revise the spec via `/specify` → `/plan` → `/breakdown`, then re-implement.]
```

## Verdict semantics (so the report reads correctly)

The verdict is deterministic (`compute-verdict`), in priority order:

- **REJECTED** — a confirmed `[CONSTITUTION-VIOLATION]` (D7), OR a spec-level AC failure pattern (mode != `off` AND ≥ 2 failing ACs AND ≥ 50% failure rate).
- **NEEDS WORK** — any blocker present: a failing/partial AC (mode != `off`), a mechanical failure, a Critical/High review finding (confirmed or contested, **excluding** constitution-violation-tagged findings — those route to the constitution paths above/below, not this one), a contested `[CONSTITUTION-VIOLATION]` (D7 — always at least NEEDS WORK). Hygiene flags (`scope_creep` / `leftover_artifacts`) are **advisory only** — they appear in `reasons` but never in `blockers` and never cause NEEDS WORK on their own.
- **APPROVED** — no blockers. Under `ac_verification_mode=off`, AC failures are advisory (they appear in `reasons` but do not block), and the verdict notes ACs were verified by code-reading only.

Constitution violations ALWAYS block APPROVED — a confirmed one forces REJECTED, a contested one forces at least NEEDS WORK. This is the D7 invariant and is enforced structurally in `compute-verdict`; the report never relaxes it.
