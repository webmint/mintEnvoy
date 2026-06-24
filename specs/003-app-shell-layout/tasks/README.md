# Tasks: 003-app-shell-layout

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/003-app-shell-layout/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/003-app-shell-layout/plan.md
**Generated**: 2026-06-23
**Total tasks**: 11

## Dependency Graph

```
001 (settings-store) ──→ 002 (divider) ──→ 003 (sidebar) ──┐
                     ├──────────────────→ 004 (panesplit) ─┤
                     └──→ 005 (titlebar) ──────────────────┤
                          006 (statusbar) ─────────────────┤
                                                           ├──→ 007 (shell-composition) ──→ 008 (shell-behaviors) ──→ 009 (wire-shell-into-app) ──→ 011 (shell-tests)
                                                                                                                  └──────────────────────────────────→ 011
010 (set-window-minwidth)   [independent — no deps]
```

## Task Index

| #   | Title                                   | Agent             | Depends on         | Status   |
| --- | --------------------------------------- | ----------------- | ------------------ | -------- |
| 001 | create-settings-store                   | frontend-engineer | None               | Complete |
| 002 | create-divider                          | frontend-engineer | 001                | Complete |
| 003 | create-sidebar                          | frontend-engineer | 001, 002           | Complete |
| 004 | create-panesplit                        | frontend-engineer | 001, 002           | Complete |
| 005 | create-titlebar                         | frontend-engineer | 001                | Complete |
| 006 | create-statusbar                        | frontend-engineer | None               | Complete |
| 007 | shell-composition-and-store-dom-effects | frontend-engineer | 003, 004, 005, 006 | Complete |
| 008 | shell-behaviors-resize-cmdb-focus       | frontend-engineer | 007                | Complete |
| 009 | wire-shell-into-app                     | frontend-engineer | 008                | Complete |
| 010 | set-window-minwidth                     | frontend-engineer | None               | Complete |
| 011 | shell-tests                             | qa-engineer       | 008, 009           | Complete |

## Additions to Spec

- `src/main/index.ts` (BrowserWindow `minWidth`, task 010) — discovered during planning; NOT in spec §4 Affected Areas. A main-process window-config change (main's responsibility per constitution §2.1) required so the renderer's static 200-520px sidebar clamp + AC-17 no-overflow are jointly satisfiable at runtime. The feature is otherwise renderer-only.

## Contract Chain

`verify-contract-chain` exits 2 with **advisory-only** findings (every line is self-labelled `advisory`). The chain is intact: each `Expects` traces either to an upstream `Produces` (the helper's literal string-matcher cannot confirm cross-task semantic matches — e.g. 002 expects the `SIDEBAR_MIN`/clamp-helper exports that 001 produces, worded differently) or to verified existing-codebase state (`zustand`, `cx()`, `toastStore.ts`, the `App.tsx` `<ToastProvider>`/`<ToastViewport>` substrate); each `Produces` feeds a downstream `Expects` or a spec AC (the helper cannot see ACs). `verify-ac-coverage` passes (17/17). No real orphan or unsatisfied dependency — the exit 2 is the matcher's known blind spot, not a decomposition defect.

## Risk Assessment

| Task | Risk | Reason                                                                                                                                                                                                                |
| ---- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 002  | Med  | Hand-rolled WAI-ARIA separator + rAF/pointer-capture drag is the highest-skill task; a11y/perf correctness (per plan §9 derisk) — covered by 011 CT suite + a design-auditor pass at /review.                         |
| 008  | Med  | Three AC-bearing behaviors (window-resize re-clamp AC-17, global Cmd-B AC-5, cross-organism focus-return / grill F3); the focus-coordination is the one open grill gap, pinned to the `toggleRef` contract (005→008). |
| 009  | Med  | App.tsx root edit must PRESERVE the `<ToastProvider>`/`<ToastViewport>` substrate (grill F2) — dropping it silently breaks every `toast()` (Radix has no throwing guard). Regression-tested in 011.                   |
| 010  | Low  | One-line main-process window option; runtime guarantee for AC-17 (jsdom/CT cannot enforce OS minWidth).                                                                                                               |
| 007  | Low  | 4-way composition convergence + slot contract that 009/011 bind to; structural, decisions already settled in plan.                                                                                                    |

## Review Checkpoints

| Before Task | Reason                                                                           | What to Review                                                                                                                                                                                  |
| ----------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 007         | Convergence (depends on 4 tasks) + establishes the slot contract 009/011 bind to | Shell composes the four organisms; typed named slots render arbitrary children; store→`<html>` data-attr effect + CSS-var write correct; `toggleRef` created + passed to Titlebar               |
| 008         | High-risk behaviors                                                              | Window-resize re-clamp via store actions (no overflow, AC-17); global Cmd-B preventDefault + toggle (AC-5); on-collapse focus moves to the Titlebar toggle (grill F3); all listeners cleaned up |
| 009         | High-risk integration + layer boundary (grill F2)                                | `<Shell>` mounts INSIDE the preserved `<ToastProvider>`/`<ToastViewport>`; PrimitivesDemo stays dev-gated + unmounted; `@renderer` alias used                                                   |
| 011         | Convergence (depends on 008 + 009) — AC-verification surface                     | Interaction + CT suites cover AC-4/5/6/7/9/16/17; toast-still-renders regression; Tabs-in-slot decoupling proof; store reset between cases                                                      |

## Specialist Consultation

| Specialist | Sub-question                                                                                                                  | Input summary                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Verdict  | Cites                                                                                                                                                            |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| architect  | Atomicity/bundling, dependency ordering/direction, contract-chain integrity, agent fit on design-decision tasks (001/002/007) | Split original 007 into 007 (composition+slots+store→DOM) and 008 (resize+Cmd-B+focus); keep 006 separate; resolve the action name to a single `toggleSidebar()`; pin the grill-F3 focus contract as a named `toggleRef` (005 produces → 008 expects); make 002 clamp internally before onCommit; note 011 tests AC-17 as JS clamp math only (010 is the runtime guarantee). Graph acyclic + correctly directed; agents on 001/002/007 correct; 010→backend-engineer correct. | accepted | specs/003-app-shell-layout/plan.md (Key Design Decisions); src/main/index.ts:9; src/renderer/src/lib/toastStore.ts; specs/003-app-shell-layout/grill.md (F2, F3) |
