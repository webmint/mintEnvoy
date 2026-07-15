# Task 008: App composition — wire BodyEditor into the body slot

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 005, 006, 007
**Blocks**: None
**Spec criteria**: AC-11, AC-13
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/App.tsx | Modify | Pass `body={<BodyEditor renderUrlencoded={…KVTable…} />}` into RequestSubTabs |

## Description

Wire `BodyEditor` into the `RequestSubTabs` `body` slot at the App composition root, injecting the controlled `KVTable` through BodyEditor's `renderUrlencoded` render-prop. App is the sanctioned cross-organism composer (§2.2) — this is the ONLY place KVTable and BodyEditor meet. This is the convergence task where the pinned `renderUrlencoded` signature (task 006) and KVTable's controlled props (task 005) must line up.

## Change Details

- In `src/renderer/src/App.tsx`:
  - Import `BodyEditor` from `@renderer/components/organisms/BodyEditor`.
  - Add a `body` prop to the existing `<RequestSubTabs params={…} headers={…} />`: `body={<BodyEditor renderUrlencoded={(rows, onRowsChange) => <KVTable rows={rows} onRowsChange={onRowsChange} />} />}`.
  - Keep the existing `params`/`headers` `<KVTable field=… />` wiring unchanged.
  - Note (carried from task 005 review): the urlencoded controlled `KVTable` must drive rows purely through `onRowsChange` → the body write path, never through `tabsStore.updateActiveSpec` directly. The AC-11 negative-arm assertion (spy that `updateActiveSpec` is not called on a controlled-mode edit) is owned by task 011's CT regression.

## Contracts

### Expects (checked before execution)
- `BodyEditor` exports a `renderUrlencoded: (rows: readonly Row[], onRowsChange: (r: Row[]) => void) => ReactNode` prop (task 006).
- `RequestSubTabs` accepts a `body?: ReactNode` slot (task 007).
- `KVTable` accepts the controlled `{ rows, onRowsChange }` arm (task 005).

### Produces (checked after execution)
- `App.tsx` passes `body={<BodyEditor renderUrlencoded={(rows, onRowsChange) => <KVTable rows={rows} onRowsChange={onRowsChange} />} />}` to `RequestSubTabs`.
- The existing `params`/`headers` field-mode wiring is unchanged.

## Done When

- [x] The Body sub-tab renders `BodyEditor`, and its urlencoded mode mounts the controlled `KVTable` (AC-11).
- [x] `BodyEditor` receives body types only via the `tabsStore` re-export path (no direct requestSpec import anywhere in the wiring) (AC-13).
- [x] The composition type-checks (the `renderUrlencoded` signature matches KVTable's controlled props).
- [x] params/headers behavior is unchanged.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-14T10:12:31Z
**Files changed**: src/renderer/src/App.tsx
**Contract**: Expects 3/3 | Produces 2/2
**Notes**: Wired BodyEditor into RequestSubTabs body slot at App root; renderUrlencoded render-prop injects controlled KVTable. renderUrlencoded<->KVTable controlled-props signatures converge cleanly (no cast). params/headers unchanged; no requestSpec/store import in App (AC-13). Panel clean iteration 0.
