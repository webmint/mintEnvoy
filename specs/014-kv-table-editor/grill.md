# Plan Grill -- specs/014-kv-table-editor -- 2026-07-04

**Feature**: specs/014-kv-table-editor
**Scope**: plan.md + referenced specs -- 2 files
**Finders invoked**: devils-advocate
**Refuters invoked**: code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React

## Disposition

**Verdict**: REVISE-PLAN

**Rationale**:

Two grounded design defects survived refutation, both plan-local (a different HOW fixes each against the same spec). F1 (High): the plan mandates a computed-style CT locking the .var.missing state, but envVars is hardwired to return ∅ in v1 (env store T14 is §6 out-of-scope) and KVTable exposes only a field prop — no seam to inject a non-empty validVars set, so AC-19 and the .var.missing fidelity assertion are structurally unreachable at runtime; fix = a validVars prop defaulting to envVars(). F2 (Med): the plan creates a new organisms/request/ subfolder holding one component (KVTable) while the sibling RequestBar sits un-foldered at organisms/RequestBar.tsx, violating constitution §2.2's >=2-components / no-empty-future-domain-folders gate; fix = flat placement OR co-migrate RequestBar. Both fixes revise the HOW without touching the WHAT, so the recommendation is REVISE-PLAN. Findings 3 (type-only Row import breaches §5.2) and 4 (sole-row delete focus edge) were refuted and dropped: import type is compile-erased so it does not value-couple the component to requestSpec (§5.2 targets value imports, which the spec states explicitly), and the delete-refocus edge is a conditional worth a /breakdown note, not a demonstrable defect.

> The defects are real but correctable at the plan level. Revise `plan.md` to address the confirmed findings, then re-run `/plan` (or hand-patch `plan.md`), and optionally re-run `/grill` before proceeding to `/breakdown`.

## Confirmed -- Top Priorities
Force-ranked across the confirmed findings. Fix these first.
1. [High] specs/014-kv-table-editor/plan.md:110 -- Mandated fidelity-CT state is unreachable in the running v1 component (no injection seam) [Likely]
2. [Medium] constitution.md:61 -- New single-component organisms/<domain>/ subfolder violates the ≥2-components placement gate [Likely]

## Confirmed Findings

### constitution.md

#### System Design
- [F-002] [Medium] :61 -- New single-component organisms/<domain>/ subfolder violates the ≥2-components placement gate  [Likely]
  Severity: Medium
  File: constitution.md
  Line: 61
  Pattern: New single-component organisms/<domain>/ subfolder violates the ≥2-components placement gate
  Confidence: Likely
  Category: system_design
  Evidence:
  ```
  create an `organisms/<domain>/` subfolder only when a domain reaches ≥2 components (no empty future domain folders)
  ```
  Why it's wrong: The plan creates a brand-new `organisms/request/` domain subfolder holding exactly ONE component — KVTable (plan.md File Impact line 84: "src/renderer/src/components/organisms/request/KVTable.tsx", Layer Map line 53). The quoted constitution rule (§2.2, line 61) permits an `organisms/<domain>/` subfolder ONLY when the domain "reaches ≥2 components" and explicitly forbids "empty future domain folders". A single-component `request/` folder is exactly the premature-domain-folder case the rule bars. The inconsistency is confirmed by the existing tree: the sibling request-domain component RequestBar lives UN-foldered at `src/renderer/src/components/organisms/RequestBar.tsx` (verified by directory listing — organisms/ contains RequestBar.tsx, Sidebar.tsx, TabBar.tsx, shell/). So either the request domain has only one component (KVTable) and the folder is premature, or it already has two (RequestBar + KVTable) and the plan should have co-located them — but it foldered one and left the other flat. Both readings leave the plan's placement inconsistent with the constitution's own convention and the established layout.
  Remediation: Place KVTable directly in `organisms/` (matching RequestBar, Sidebar, TabBar) until a second request-domain component (e.g. the deferred RequestSubTabs container) actually lands, at which point both move into `organisms/request/` together in one deliberate step. If the architect judges the request domain already qualifies (RequestBar + KVTable ≥ 2), then the plan must also relocate RequestBar into `organisms/request/` so the domain-folder decision is applied consistently rather than to one of two peers.


### specs/014-kv-table-editor/plan.md

#### Mislogic
- [F-001] [High] :110 -- Mandated fidelity-CT state is unreachable in the running v1 component (no injection seam)  [Likely]
  Severity: High
  File: specs/014-kv-table-editor/plan.md
  Line: 110
  Pattern: Mandated fidelity-CT state is unreachable in the running v1 component (no injection seam)
  Confidence: Likely
  Category: blind_spot
  Evidence:
  ```
  Computed-style CT assertions locking every pinned `.kv` value across states (default/disabled/hover/var/var-missing)
  ```
  Why it's wrong: The plan and the spec's fidelity contract both REQUIRE a computed-style CT that locks the `.var-missing` (rendered `.var.missing`) state (this quote lists `var-missing` as a required CT state; spec.md line 117 pins "`.var.missing` color var(--m-delete) + line-through dotted"). But the design guarantees that state can NEVER be produced in the v1 component: Decision (f) at plan.md line 71 renders `.var.missing` "ONLY when `set.size > 0` AND name absent", the `envVars` selector at plan.md line 56 returns a "frozen empty `ReadonlySet<string>` until env store T14 lands", and the env store (T14) is explicitly Out of Scope (spec.md §6, line 108) — so `validVars` is ALWAYS ∅ in v1 and AC-20 (spec.md line 67) forces every token neutral. KVTable's only wiring to the set is an INTERNAL `envVars` call (plan.md Layer Map line 53: "calls varTokens for key/value highlight + envVars for missing-flag") and its only prop is `field` (plan.md line 53) — there is no seam to inject a non-empty set, and Playwright experimental-ct renders the real component with no module-mock facility (the CT fixtures reproduce production styling context, per the project's own CT-fixture memory lesson). Net effect: AC-19 and the mandated `.var.missing` fidelity assertion cannot be exercised, so they will either be silently skipped or the CT will be written against a state the component cannot enter — a green pipeline that never tested the missing-token path.
  Remediation: Add an explicit injection seam so the missing-token branch is reachable under test while `envVars` still ∅-defaults in production. The minimal change is to have KVTable accept the validVars set (or a `validVars`/`resolveVars` prop) whose default is `envVars()`, so the CT can render KVTable with a non-empty set to assert `.var` vs `.var.missing` computed styles and satisfy AC-19, while the un-provided prop keeps AC-20's ∅-default behavior in the running app. Alternatively, factor the flag decision into a pure function that the varTokens/Vitest suite can drive AND keep the component-level prop for the computed-style CT — but the pure-unit path alone cannot satisfy the getComputedStyle fidelity requirement, which needs the rendered component.


## Summary
- Critical: 0 | High: 1 | Medium: 1 | Info: 0
- Confirmed: 2 | Contested: 0 | Dismissed: 1 | Uncertain: 1
- Disposition: REVISE-PLAN
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable plan-level defect; uncertain findings could not be resolved from the plan alone. A reviewer may want to glance at them before accepting the verdict.

### Dismissed
- [D-001] [Medium] specs/014-kv-table-editor/spec.md:60 -- AC-13 focus edge — deleting the sole real row has no adjacent real cell to receive focus

### Uncertain (low-stakes)
- [U-001] [Medium] specs/014-kv-table-editor/plan.md:93 -- Sole compensating control for the §2.2 "SHARP" invariant is optional/deferred and scoped to the wrong import kind

## Methodology
Findings are grounded -- every finding carries a verbatim quote from the
actual plan/spec/research artefacts. A refutation stage cross-examines each
grounded finding before it reaches the report: a finding earns the headline
only by surviving an adversary who default-dismisses anything not
demonstrable as a real plan-level defect. Confirmed findings reach the
headline; dismissed and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; high-stakes [CONTESTED] findings
(security / [CONSTITUTION-VIOLATION] the refuter could not confirm) are
surfaced in the headline, flagged [CONTESTED], never buried.
