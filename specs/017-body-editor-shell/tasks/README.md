# Tasks: 017-body-editor-shell

**Spec**: specs/017-body-editor-shell/spec.md
**Plan**: specs/017-body-editor-shell/plan.md
**Generated**: 2026-07-11
**Total tasks**: 11

## Dependency Graph

```
001 (migrate body → tagged record) ──→ 002 (re-export body types) ──→ 006 (BodyEditor)
003 (jsonTokens lib) ───────────────────────────────────────────────→ 006
009 (--tk-* tokens) ─────────────────────────────────────────────────→ 006
                     └───────────────────────────────────────────────→ 010

006 (BodyEditor) ──→ 008 (App wire)
007 (RequestSubTabs body slot) ──→ 008
005 (KVTable controlled) ──→ 008
005 ──→ 011 (KVTable CT regression)

004 (CT fidelity util) ──→ 010 (BodyEditor CT)
006 ──→ 010
```

Independent roots (no deps): 001, 003, 004, 005, 007, 009.
Convergence sinks: 006 (deps 002/003/009), 008 (deps 005/006/007), 010 (deps 004/006/009).

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | Migrate RequestSpec body to tagged record | frontend-engineer | None | Complete |
| 002 | Re-export Body types from tabsStore | frontend-engineer | 001 | Complete |
| 003 | JSON tokenizer lib + two-pass compose | frontend-engineer | None | Complete |
| 004 | CT fidelity util (fail-closed) | qa-engineer | None | Complete |
| 005 | KVTable controlled-mode prop union | frontend-engineer | None | Complete |
| 006 | BodyEditor organism + CSS | frontend-engineer | 002, 003, 009 | Complete |
| 007 | RequestSubTabs body slot | frontend-engineer | None | Complete |
| 008 | App composition — wire BodyEditor | frontend-engineer | 005, 006, 007 | Complete |
| 009 | tokens.css --tk-* per-theme tokens | frontend-engineer | None | Complete |
| 010 | BodyEditor CT — fidelity + behavior | qa-engineer | 004, 006, 009 | Complete |
| 011 | KVTable CT regression | qa-engineer | 005 | Complete |

## Additions to Spec

None. Two clarifications surfaced in Phase 1/Phase 2 (already inside the plan's decisions, not new files):
- The codebase CT convention pairs each `*.ct.tsx` with a co-located `*.stories.tsx` fixture (Playwright experimental-ct-react). Task 010 adds `BodyEditor.stories.tsx`; task 011 extends `KVTable.stories.tsx`. Both are covered by the plan's File Impact "BodyEditor.ct.tsx (Create)" / "KVTable.ct.tsx (Create/Extend)" rows.
- The shared CT fidelity util lands at `src/renderer/src/test-utils/fidelityAssert.ts` — the `test-utils/` directory already exists (holds `simulateDrag.ts`).

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate the 11-task decomposition: atomicity/bundling, dependency ordering/direction, contract-chain integrity, implementability; and the frontend-engineer vs qa-engineer assignment split | Structure GO (T006 rightly monolithic; T009 rightly separate; graph acyclic + correctly directed; no missing T006→T005 edge — render-prop decoupling enforces the match at T008). REVISE (targeted, all wording/completeness, no plan-level escalation): add `*.stories.tsx` fixtures to T010/T011; convert line-number Expects anchors to semantic identifiers; pin T006 `renderUrlencoded` signature; clarify §2.2-safe deferred placeholder + pin T004 path to `test-utils/`; make T009-tokens/T006-classes boundary explicit; close AC-7/8/9/10/19/26 coverage holes. qa-engineer correct for T004/T010/T011 (CT harness + fixtures + fail-closed strategy = dedicated test work); T003 unit tests correctly inline (pure Vitest, no harness) | modified | own-reasoning; requestSpec.ts:82,131; tabsStore.test.ts:232; KVTable.tsx:99,36-39; RequestSubTabs.tsx:75,261-267; existing test-utils/ + *.stories.tsx convention |

All six architect revisions were applied to the task files before writing (verdict recorded `modified` — accepted with the orchestrator applying the revisions).

## Risk Assessment

> **Contract-chain gate (advisory deferral)**: `verify-contract-chain` exits 2 with only its advisory class of findings — the helper is a literal string-matcher that cannot see spec-AC mappings or existing-codebase state. Every "orphan Produces" here maps to a spec AC (e.g. T001's `Body` export → AC-4/AC-13), and every "unsatisfied Expects" is either existing-codebase state (T001's flat body at requestSpec.ts:82) or an upstream task's Produces phrased in task-referenced prose (T006 Expects "task 002" ← T002 Produces). The chain was hand-traced end-to-end: all Depends-on edges resolve (T002←T001; T006←T002/T003/T009; T008←T005/T006/T007; T010←T004/T006/T009; T011←T005). No genuine orphan/unsatisfied contract. Accepted as advisory.

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low | Production-consumer-free migration (no reader beyond the seed); blast radius is the one reseeded test — bundled into this task so type-check + test stay green. Let the type-checker enumerate any access site. |
| 002 | Low | ~6-symbol type re-export; no logic change. |
| 003 | Med | Two-pass var-pass-wins tie-break inside JSON strings is subtle; pinned by a dedicated unit fixture. Perf-ceiling is a tunable constant. |
| 004 | Med | Fail-closed correctness is the whole point: `getPropertyValue('--x')` returns `""` (not a throw) when undefined — must be intercepted as UNVERIFIED before any `expect`, else false-green. |
| 005 | Med | Controlled-mode extension touches KVTable's selector + writeRows dispatcher; must not regress params/headers (guarded selector + writeRows early-return + task 011 CT regression). |
| 006 | High | Largest task: three-layer textarea/pre/gutter alignment + single-scroll-source across themes, debounced-coloring-only (visible text stays live), ARIA radiogroup, §2.2 render-prop + §2.2-safe placeholder. Review checkpoint. |
| 007 | Low | Mirrors the existing params/headers slot pattern; other panels untouched. |
| 008 | Med | Convergence of 3 tasks; the `renderUrlencoded` signature must line up with KVTable controlled props. Review checkpoint. |
| 009 | Low | Four per-theme CSS tokens; the §4 fidelity-driven literal-hex exception is documented. |
| 010 | High | Fidelity CT is the anti-false-green gate; needs the fail-closed util + theme-wrapper fixtures for both light (AC-20) and dark (AC-21). Review checkpoint. |
| 011 | Med | Regression guard protecting params/headers after the KVTable prop-union change. |

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 006 | High-risk + convergence (deps 002/003/009) | Three-layer alignment + single scroll source across both themes; debounce applies to coloring only (visible text + gutter stay live); ARIA radiogroup semantics + roving focus; §2.2 — BodyEditor imports zero sibling organisms and the deferred placeholder is its own markup; `updateActiveSpec({body})` write path + re-select early-returns. |
| 008 | Convergence (deps 005/006/007) | The `renderUrlencoded` signature matches KVTable controlled props; KVTable meets BodyEditor only at App root (§2.2); params/headers wiring unchanged. |
| 010 | High-risk fidelity gate + convergence (deps 004/006/009) | Fail-closed channel reports UNVERIFIED (never PASS) when computed-style is unavailable; both light + dark theme fixtures exercised; gutter/pre alignment asserted structurally, not via a CSS shortcut. |
