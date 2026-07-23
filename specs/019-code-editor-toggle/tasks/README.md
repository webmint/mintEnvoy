# Tasks: 019-code-editor-toggle

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/019-code-editor-toggle/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/019-code-editor-toggle/plan.md
**Generated**: 2026-07-21
**Total tasks**: 5

## Dependency Graph

```
001 (CodeEditor toggle molecule) ──→ 002 (BodyEditor toggle + reset) ──→ 004 (BodyEditor CT)
                                 │                                    └─→ 005 (docs)
                                 └─→ 003 (CodeEditor CT)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | Rebuild CodeEditor as edit-preview toggle molecule | frontend-engineer | None | Complete |
| 002 | Add edit/preview toggle + render-phase reset to BodyEditor | frontend-engineer | 001 | Complete |
| 003 | CodeEditor CT + stories (toggle/caret/focus/recolor) | qa-engineer | 001 | Complete |
| 004 | BodyEditor CT + stories (toggle/AC-6/focus) | qa-engineer | 002 | Complete |
| 005 | Document CodeEditor edit/preview toggle in architecture.md | tech-writer | 002 | Complete |

## Additions to Spec

None — every touched file is in the plan's File Impact table.

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate atomicity / dependency ordering / contract-chain / implementability of the 5-task decomposition, and validate agent routing | 5-task set sound; DAG acyclic + correctly directed (molecule→organism→tests/docs); contract chain intact; full AC coverage. Revisions folded: R1 review-checkpoint on 001; R2 AC-10/AC-11 verification on 003; R3 AC-16 also on 001 (blur half) + AC-7 preservation-covered on 002; R4 CT-harness constraints block on 003/004 with test:ct UNVERIFIED; 001/002 reframed "execute pinned decisions, do not re-derive". 001 kept atomic (overlay-delete + conditional-mount inseparable). qa-engineer confirmed correct for CT tasks | modified | specs/019-code-editor-toggle/plan.md, src/renderer/src/components/molecules/CodeEditor.tsx, src/renderer/src/components/organisms/BodyEditor.tsx, own-reasoning |
| (none) | — | — | — | — |

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | High | Full molecule rewrite — deletes four mechanisms (overlay stack, scroll-sync, debounce, showColored) and introduces conditional-mount + focus effect + caret helper + tokenize gate in one atomic change; 17 ACs. Mitigated by the plan's 6-cycle-pinned mechanisms and a review checkpoint. |
| 002 | Med | Render-phase set-state-in-render reset is subtle (must be useState-prev, not a ref or passive useEffect — the exact cycle-4/5 grill defect); layer-boundary organism←molecule. Review checkpoint. |
| 003 | Med | CT-fixture scoping landmines (MEMORY): alias tokens.css ENOENT, box-sizing, non-empty baseline seeding. test:ct left UNVERIFIED (pre-existing local-harness mount break) — verified statically. |
| 004 | Med | Same CT-harness constraints as 003; AC-6 immediate-post-switch assertion must read the transient frame, not just settled state. Convergence + review checkpoint. |
| 005 | Low | Single surgical markdown edit. |

**Deferred/noted**:
- `test:ct` Done-When on tasks 003/004 is left UNVERIFIED by design (pre-existing local CT-harness mount break, MEMORY `ct-organism-fixtures-cannot-mount-locally`) — tests are authored + verified statically and live-verified per 018, not run in the local harness. This is a documented deferral, not a coverage gap.
- `verify-contract-chain` reports ORPHAN-PRODUCES / UNSATISFIED-EXPECTS advisories on every task. These are the helper's known literal-match limitation, NOT real breaks: the ORPHAN PRODUCES map to spec ACs the helper cannot see (e.g. 001's "no handleTextareaScroll" → AC-1, "no showColored" → AC-2), and the UNSATISFIED EXPECTS are either existing-codebase state (compose/cx exports, the current overlay) or cross-task chains whose Expects/Produces are worded semantically-equivalent but not byte-identical (002/003 Expects `editing`/`onEditingChange` ← 001 Produces `CodeEditorProps declares editing and onEditingChange`; 004 Expects `body-edit-toggle` ← 002 Produces it; 005 Expects the toggle implemented ← 001/002). The Phase-2 architect explicitly confirmed contract-chain integrity. Documented deferral.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 001 | High risk (full molecule rewrite, 17 ACs) | Conditional-mount textarea XOR pre; tokenize `useMemo` gated `!editing`; focus-on-mount effect; caret helper; overlay/scroll-sync/debounce/showColored deleted; CSS single-layer + `--code-line-h` + no `1.65em`/inline styles |
| 002 | Layer boundary (organism←molecule) + subtle render-phase reset | `useState`-prev render-phase reset (NOT ref, NOT passive useEffect); `body-edit-toggle` + `onMouseDown` preventDefault; editing wired to CodeEditor; none/urlencoded unchanged |
| 004 | Convergence (depends 002) | AC-6 immediate-post-switch preview read; F-002 toggle-while-editing→preview; toggle-entry focus `activeElement`; only-visible testids |
