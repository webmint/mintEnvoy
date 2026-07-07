# Task 005: App compose request pane (KVTable live)

**Feature**: 015-request-sub-tabs
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 003, 004
**Blocks**: None
**Spec criteria**: AC-11, AC-18, AC-20, AC-21
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/App.tsx | Modify | Replace `panes.request` (`<RequestBar/>`) with the composed pane: RequestBar above RequestSubTabs, injecting KVTable into the Params/Headers slots |
| src/renderer/src/__tests__/App.test.tsx | Create | Composed-pane mount smoke test (plan-additive — not in the plan's 3-file test list) |

## Description

Wire the composed request pane into the app (D5), taking KVTable live. Replace the `panes.request` slot in `App.tsx` from a bare `<RequestBar/>` to a fragment stacking `RequestBar` above `RequestSubTabs`, injecting `<KVTable field='params'/>` and `<KVTable field='headers'/>` as the `params`/`headers` slot props from the composition root (org→org wiring stays at the root, §2.2 — RequestSubTabs never imports KVTable). Add a lightweight mount smoke test for the composed pane (R5).

## Change Details

- In `src/renderer/src/App.tsx`:
  - Import `RequestSubTabs` from `@renderer/components/organisms/RequestSubTabs` and `KVTable` from `@renderer/components/organisms/KVTable`.
  - Replace `panes={{ request: <RequestBar /> }}` (App.tsx:23) with:
    `panes={{ request: (<><RequestBar /><RequestSubTabs params={<KVTable field='params' />} headers={<KVTable field='headers' />} /></>) }}`.
  - Change nothing else (Shell/ToastProvider/ToastViewport untouched).
- Create `src/renderer/src/__tests__/App.test.tsx` (Vitest):
  - Render `App` (or the composed request pane), assert `RequestBar` and `RequestSubTabs` both mount and the Params slot renders a `KVTable` (AC-11, AC-18).

## Contracts

### Expects (checked before execution)
- `RequestSubTabs` is exported and accepts `params`/`headers` `ReactNode` slot props (task 003).
- The `.pane-tabs` fidelity CSS + the focus-survives-switch go/no-go CT are green (task 004).
- `KVTable`, `RequestBar`, and `Shell` exist and are importable via `@renderer`.

### Produces (checked after execution)
- `App.tsx` renders the composed request pane: `RequestBar` above `RequestSubTabs`, with `<KVTable field='params'/>` / `field='headers'/>` passed as the `params`/`headers` slot props.
- `App.test.tsx` asserts the composed pane mounts with KVTable live in the Params slot.

## Done When

- [x] `App.tsx` `panes.request` renders `RequestBar` + `RequestSubTabs` with KVTable injected into Params/Headers slots (AC-11, AC-18).
- [x] RequestSubTabs still imports no organism (KVTable injected from the root, §2.2).
- [x] `App.test.tsx` composed-pane smoke test passes.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-06T18:18:03Z
**Files changed**: src/renderer/src/App.tsx, src/renderer/src/__tests__/App.test.tsx
**Contract**: Expects 3/3 | Produces 2/2
**Notes**: App.tsx composes RequestBar + RequestSubTabs with KVTable injected from root (params/headers slots). App.test.tsx smoke: AC-18 ordering (compareDocumentPosition), AC-11 both KVTable slots live. Full renderer Vitest 443/443 — no integration regression (Risk 5).
