# Tasks: 005-tab-bar-visual-fidelity

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/005-tab-bar-visual-fidelity/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/005-tab-bar-visual-fidelity/plan.md
**Generated**: 2026-06-26
**Total tasks**: 10

## Dependency Graph

```
001 (method tokens) ──→ 002 (Tabs render contract) ──→ 003 (Tabs fidelity CSS) ──→ 005 (TabBar+Shell CSS) ─┐
                    └─→ 006 (CT token harness) ───────────────────────────────────────────────────────────┤
                                                  002 ──→ 004 (TabBar descriptor+actions) ──→ 005 ─────────┤
                                                                                          └─→ 008 (TabBar tests)
                                                  002 ──→ 007 (Tabs behavior tests)
                                                  002 ──→ 010 (002 lineage)
   {002, 003, 005, 006} ──────────────────────────────────────────────────────────────────→ 009 (fidelity CT)
```

Execution waves: **W1** 001 · **W2** 002, 006 · **W3** 003, 004, 007, 010 · **W4** 005, 008 · **W5** 009.

## Task Index

| #   | Title                                                         | Agent             | Depends on         | Status   |
| --- | ------------------------------------------------------------- | ----------------- | ------------------ | -------- |
| 001 | complete method tokens and HEAD color                         | frontend-engineer | None               | Complete |
| 002 | extend Tabs render contract (method chip + dirty-XOR-close)   | frontend-engineer | 001                | Complete |
| 003 | Tabs fidelity CSS (active accent, dirty dot, close, geometry) | frontend-engineer | 002                | Complete |
| 004 | TabBar descriptor mapping + actions row                       | frontend-engineer | 002                | Complete |
| 005 | TabBar strip CSS + Shell border de-dup                        | frontend-engineer | 003, 004           | Complete |
| 006 | CT fidelity-harness token context                             | frontend-engineer | 001                | Complete |
| 007 | Tabs behavior tests (byte-identical, dirty-XOR-close)         | frontend-engineer | 002                | Complete |
| 008 | TabBar tests (migrate badge assertions, actions row)          | frontend-engineer | 004                | Complete |
| 009 | Tabs fidelity CT suite + fixture                              | frontend-engineer | 002, 003, 005, 006 | Complete |
| 010 | record the 005 contract extension in 002 lineage              | frontend-engineer | 002                | Complete |

## Additions to Spec

- `playwright/index.tsx` — added by the grill-revision (Decision (g) CT fidelity-harness). It is in the plan's File Impact but NOT in the spec's §4 Affected Areas (which scoped the fidelity work to the test files). It is the test-harness wiring those CT tests require; covered by task 006.

## Risk Assessment

| Task | Risk | Reason                                                                                                                                                                                                                                                                                         |
| ---- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 002  | Med  | Shared 002 contract mutation + highest fan-out producer (feeds 003/004/007/009/010); plan Risk-1/4. Mitigated by the closable=false byte-identical regression (task 007) + review checkpoint.                                                                                                  |
| 003  | Med  | Active-CSS rewrite (box-shadow → ::before/::after) + `overflow:visible` override could regress a global `.tabs` consumer or clip the accent; plan Risk-1. Mitigated by `.tabbar`-scoping + the task-009 runtime fidelity probe.                                                                |
| 005  | Med  | Load-bearing Shell border de-dup must converge atomically with the `.tabbar` border (no two-border / zero-border intermediate); AC-17 is runtime-verified (task 009 + `/verify` design-auditor), not a code-only grep.                                                                         |
| 006  | Med  | Global tokens.css import into the CT mount root perturbs every existing CT suite (Dropdown/Modal/Toast/Shell/Icon); plan Risk-5. The F2 isolated existing-suite-shift check lives HERE (run full CT suite, flag any out-of-scope `.ct.tsx` shift) — deliberately NOT co-mingled into task 009. |
| 009  | Med  | The feature's fidelity proof; 4-way convergence; first-ever screenshot baseline (plan Risk-6 — confirm before commit). Carries the grill F1 binding (fixture MUST be `.tabbar`+closable+active, not a bare `<Tabs>`).                                                                          |

**Cross-cutting hygiene ACs**: AC-25 (typecheck), AC-26 (ESLint — distinct from feature-004's AC-26 dirty-marker assertions migrated in tasks 007/008), and AC-27 (build) are verified by the per-task scope-aware gate on EVERY task, not owned by one task. AC-27 is additionally pinned to task 009 (the final assembled convergence).

**Contract-chain deferral (documented)**: `verify-contract-chain` exited 2 with advisory-only findings, every one self-annotated `may map to a spec AC` (orphan-Produces) or `may be existing-codebase state` (unsatisfied-Expects). These are the heuristic's literal-string-matcher false positives: each `Produces` lands on a spec AC (e.g. T001 `--m-head`→AC-1) or a downstream `Expects` worded in prose (e.g. T002 `TabDescriptor.method/dirty`→T004 "Task 002 added method/dirty"), and each `Expects` is either existing code state or an upstream `Produces`. The Phase-2 architect explicitly validated contract-chain integrity (no orphans). Deferred — no real orphan or dangling consumer.

## Review Checkpoints

| Before Task | Reason                                                         | What to Review                                                                                                                                               |
| ----------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 002         | Highest-fan-out contract producer + shared 002 mutation        | TabDescriptor change is additive + the non-closable path is byte-identical; dirty-XOR-close keeps one roving stop; chip narrows unknown methods to uncolored |
| 003         | High-risk active-CSS rewrite (Risk-1)                          | The active ::before/::after + geometry are `.tabbar`-scoped and don't leak to a global `.tabs` consumer; the ::after mask isn't clipped                      |
| 005         | Convergence (003+004) + load-bearing AC-17 border de-dup       | Exactly one strip bottom border after the Shell de-dup; the `.tabbar` border owns it; the actions row styling matches the reference                          |
| 006         | Risk-5 global CT-import blast radius (F2)                      | The full CT suite is green after the tokens.css import; any existing-suite assertion shift is flagged as an out-of-scope consequence, not silently fixed     |
| 009         | 4-way convergence + the feature's fidelity proof (grill F1/F2) | The fidelity fixture is `.tabbar`+closable+active (not bare `<Tabs>`); computed-style EXACT passes; the first screenshot baseline is correct before commit   |

## Specialist Consultation

| Specialist | Sub-question                                                                                                         | Input summary                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Verdict  | Cites                                                                                               |
| ---------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| architect  | Validate task atomicity, dependency ordering, contract-chain integrity, agent assignment (mandatory Phase 2 consult) | Approved the 10-task graph (acyclic, correctly directed, bundles justified); 3 revisions applied — disambiguate 004-AC-26 vs 005-AC-26 across tasks 002/007/008, relocate the F2 existing-CT-suite-shift check from task 009 → task 006, mark AC-25/26/27 cross-cutting (fix AC-27 orphan) + note AC-17 runtime route on task 005; +1 review checkpoint added to task 002. All agents confirmed frontend-engineer (renderer = the app's frontend stack, not backend). | modified | specs/005-tab-bar-visual-fidelity/plan.md (Layer Map / File Impact / Risks 1,5,6); grill.md (F1/F2) |
| (none)     | —                                                                                                                    | —                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | —        | —                                                                                                   |
