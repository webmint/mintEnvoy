# Tasks: 014-kv-table-editor

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/014-kv-table-editor/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/014-kv-table-editor/plan.md
**Generated**: 2026-07-04
**Total tasks**: 4

## Dependency Graph

```
001 (varTokens tokeniser) ──┐
                            ├──→ 003 (KVTable component + styles) ──→ 004 (KVTable CT + fixtures)
002 (envVars selector) ─────┘
```

001 and 002 are independent pure lib leaves (parallel-eligible). 003 consumes both. 004 tests 003.

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | varTokens tokeniser | frontend-engineer | None | Complete |
| 002 | envVars validVars selector | frontend-engineer | None | Complete |
| 003 | KVTable component + styles | frontend-engineer | 001, 002 | Complete |
| 004 | KVTable component tests + fixtures | qa-engineer | 003 | Complete |

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate the 4-task decomposition — atomicity, ordering, contract chain, implementability, agent assignments | Approved with 3 revisions: (1) reconcile stale spec AC-1/31/32/33 paths `organisms/request/`→`organisms/` [applied]; (2) pin `VarSegment[]` type in 001 Produces + 003 Expects [applied]; (3) add R9 (paste, AC-23/24) + R10 (description-tokenise, AC-11) CT scenarios to 004 [applied]. 003 atomic as one unit; 002 stays separate; ordering acyclic; agents confirmed | modified | specs/014-kv-table-editor/plan.md decisions a–f; constitution.md §2.2 |

## Additions to Spec

- **Spec path reconciliation (applied during breakdown)**: the grill-revision flattened placement to `organisms/KVTable.tsx`, but the spec's §3/§4 + AC-1/31/32/33 verification commands still hard-coded the pre-grill `organisms/request/` paths. The architect flagged this as a `/verify` blocker (a correct flat build would fail those ACs on path miss). The 7 stale `organisms/request/` paths were corrected to `organisms/` in `spec.md`, and the spec re-stamped. Tasks were authored flat from the start.
- **Empty design-manifest**: the feature declares `design source: html:design/reference.html`, but `design_helper resolve-reference` found 0 `data-ref`-anchored elements (the export uses `data-om-*` attrs the build bars, not `data-ref`), so `design-manifest.json` is empty-but-valid. The per-element runtime fidelity contract is therefore NOT machine-populated; fidelity enforcement rests on task 004's CT computed-style asserts (var→token, across states) — treated as the fidelity vehicle per the runtime-design-auditor + CT-lock memory lessons.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Med | Tokeniser edge rules (non-greedy/nested-shortest/unicode/empty/unclosed) are easy to get subtly wrong; the unit suite is the guard. |
| 002 | Low | Thin frozen-∅ selector; the only trap is a fresh set per call (identity loop) — pinned by the stable-identity test. |
| 003 | High | The complex controlled grid: no-local-copy write path, R7 frozen-sentinel selector, R9 paste double-promote, R10 description leak, and the `useLayoutEffect` caret/focus strategy (spec §9.2 High/High). Carries 24 ACs. Review checkpoint. |
| 004 | Med | The sole runtime vehicle (component unmounted); must assert BOTH validVars paths (R11) + fidelity computed-styles + the empty-manifest gap means CT is the fidelity contract. Review checkpoint. |

Plan risks R7–R12 + spec §9 risks 1–6 are addressed across tasks 003 (R7/R8/R9/R10/R12 + §9.2/§9.3/§9.4) and 004 (R11 + §9.1/§9.5/§9.6 CT-fixture-scoping + watchdog).

### Deferred gate findings (documented per Phase 3.5)

- **Contract-chain advisories (verify-contract-chain exit 2)**: every finding is the helper's own hedged-advisory kind — "may map to a spec AC, which verify-contract-chain cannot see" or "may be existing-codebase state, which verify-contract-chain cannot see". The real cross-task links are sound and verified manually: task 001 Produces `tokenizeVars`/`VarSegment` → task 003 Expects them; task 002 Produces `envVars` → task 003 Expects it; task 003 Produces `KVTable` + `KVTable.css` → task 004 Expects them. The "unsatisfied expects" that remain (`src/renderer/src/lib/` exists, the Vitest/Playwright stacks, the `Row` type, `updateActiveSpec`) are all EXISTING feature-001/004/009 codebase state the helper cannot see. No genuine orphan or broken edge. Deferred — no revision needed.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 003 | Convergence (depends 001+002) + layer crossing (lib → presentation) + High risk | The `tokenizeVars`/`envVars` contracts are stable before the component builds off them; the no-local-copy write path, frozen `EMPTY_ROWS` selector, and `useLayoutEffect` caret strategy are correct. |
| 004 | Convergence on 003 + High-risk fidelity | Both validVars paths (injected + ∅-default) are asserted; R9/R10 scenarios present; fidelity computed-style asserts lock the pinned `.kv` values; fixtures reproduce the full styling context. |
