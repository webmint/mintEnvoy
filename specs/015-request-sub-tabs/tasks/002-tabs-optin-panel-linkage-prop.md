# Task 002: Tabs opt-in panel-linkage prop

**Feature**: 015-request-sub-tabs
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 003
**Spec criteria**: AC-5, AC-14, AC-20, AC-21
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/Tabs.tsx | Modify | Add an opt-in `linkPanels` prop that emits the tab's DOM `id` + `aria-controls` on the `role="tab"` button; OFF by default → byte-identical to the current contract |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | Add on-path assertions (id + aria-controls emitted) + an off-path assertion (no id/aria-controls when the prop is absent) |

## Description

Route B (D10, user-approved): the Tabs molecule renders `role="tab"` buttons with no DOM `id` and deliberately no `aria-controls` (Tabs.tsx:370), so a tabpanel cannot link back to its tab (AC-14). Add a minimal, opt-in `linkPanels` boolean prop that, when set, emits `id={`tab-${tab.id}`}` and `aria-controls={`panel-${tab.id}`}` on the tab button — in BOTH render branches (closable=false and closable=true). When the prop is absent/false the output is byte-identical to today (no `id`, no `aria-controls`), preserving the selection-only contract (AC-5). This mirrors the backward-compatible-extension pattern already used for `closable`/`onClose` (feature-004).

## Change Details

- In `src/renderer/src/components/molecules/Tabs.tsx`:
  - Add `linkPanels?: boolean` to `TabsProps` with a doc comment explaining the opt-in id/aria-controls emission and the byte-identical-when-off guarantee (AC-5).
  - In the `closable=false` button branch (~Tabs.tsx:544) add `id={linkPanels ? `tab-${tab.id}` : undefined}` and `aria-controls={linkPanels ? `panel-${tab.id}` : undefined}`.
  - In the `closable=true` button branch (~Tabs.tsx:605) apply the identical two attributes.
  - Do not change any other attribute, the roving-tabindex logic, or the keyboard engine.
- In `src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx`:
  - With `linkPanels`, assert a tab button has `id="tab-<id>"` and `aria-controls="panel-<id>"`.
  - Without the prop, assert the tab button has no `id` and no `aria-controls` (off-path unchanged, AC-5).

## Change Details Notes

The panel-side `id="panel-<key>"` and `aria-labelledby="tab-<key>"` are owned by RequestSubTabs (003); this task supplies only the tab-side half so the two resolve to the same id namespace (`tab-<key>` / `panel-<key>`).

## Contracts

### Expects (checked before execution)
- `TabsProps` and the two `role="tab"` button render branches exist in `Tabs.tsx`; neither currently emits `id` or `aria-controls`.

### Produces (checked after execution)
- `TabsProps` declares a `linkPanels` (boolean) prop.
- Both button branches emit `id={`tab-${tab.id}`}` + `aria-controls={`panel-${tab.id}`}` when `linkPanels` is set, and neither attribute when it is absent.
- `Tabs.ct.tsx` asserts both the on-path (attrs present) and off-path (attrs absent) behavior.

## Done When

- [x] `linkPanels` prop exists on `TabsProps` and is documented.
- [x] Both tab-button branches emit `id`/`aria-controls` only when `linkPanels` is set.
- [x] Off-path CT proves no `id`/`aria-controls` when the prop is absent (AC-5 byte-identical).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-06T10:52:14Z
**Files changed**: src/renderer/src/components/molecules/Tabs.tsx, src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx
**Contract**: Expects 1/1 | Produces 3/3
**Notes**: Added CT fixtures in Tabs.stories.tsx (3rd file — fixture source for the CT). Tabs CT run green in main thread. Repair leg fixed 2 stale JSDoc aria-controls comments.
