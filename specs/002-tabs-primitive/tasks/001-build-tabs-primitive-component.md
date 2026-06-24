# Task 001: build-tabs-primitive-component

**Feature**: 002-tabs-primitive
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 003
**Spec criteria**: AC-1, AC-2, AC-3, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md (Renderer UI Primitives Layer)

## Files

| File                                           | Action | Description                                                                        |
| ---------------------------------------------- | ------ | ---------------------------------------------------------------------------------- |
| src/renderer/src/components/molecules/Tabs.tsx | Create | The hand-rolled, controlled, selection-only Tabs primitive + exported types        |
| src/renderer/src/components/molecules/Tabs.css | Create | Sibling token-bound BEM stylesheet; no inline styles; prefers-reduced-motion guard |

## Description

Build the `Tabs` primitive: a controlled, horizontal-only, selection-only tab-strip that renders a row of tab buttons from a flat descriptor array and emits `onChange(id)` on click or keyboard selection. Per the approved plan's Key Design Decision, the accessibility engine is **hand-rolled** (`role="tablist"` containing `role="tab"` buttons with manual roving tabindex) — NOT a Radix Tabs wrapper, because Radix `Tabs.Trigger` emits a dangling `aria-controls` with no `Tabs.Content` mounted, which fails AC-7. The component veneer mirrors the established `Dropdown` molecule (flat descriptor-array API, `cx()` BEM classes, `import './Tabs.css'`, JSDoc citing each AC, exported types) — only the a11y engine differs. Renderer-only: pure React + `cx`, no Node/electron imports, no Radix import.

## Change Details

- In `src/renderer/src/components/molecules/Tabs.tsx`:
  - Export an interface `TabDescriptor` with fields: `id: string`, `label: string`, `badge?: string | number`, `disabled?: boolean`.
  - Export an interface `TabsProps`: `tabs: TabDescriptor[]`, `activeId: string`, `onChange: (id: string) => void`, `actions?: React.ReactNode`, optional `className`/`'aria-label'` as needed.
  - Export a function component `Tabs` that renders a `role="tablist"` container with one `role="tab"` button per descriptor; mark the tab whose `id === activeId` with `aria-selected="true"` (others `aria-selected="false"`).
  - Roving tabindex: exactly one tab is the tab-stop (`tabIndex={0}`) — the active tab, or the first enabled tab when no tab matches `activeId`; all others `tabIndex={-1}`.
  - Keyboard (automatic activation): ArrowLeft/ArrowRight move selection to the previous/next ENABLED tab with wrap-around; Home/End jump to the first/last enabled tab; each movement calls `onChange(id)` with the newly selected tab's id and moves focus to it.
  - Click: clicking an enabled tab calls `onChange(id)` exactly once; clicking the already-active tab still calls `onChange` (controlled — caller decides to no-op).
  - Disabled-skip: disabled tabs are rendered (with `aria-disabled`/`disabled`), are skipped by arrow/Home/End navigation, and never invoke `onChange` on click or keyboard.
  - Render-no-selection guard: when `activeId` matches no enabled tab (no match / empty `tabs` / all disabled), render with no `aria-selected="true"` tab and auto-select nothing.
  - Actions slot: when `actions` is supplied, render it right-aligned at the end of the strip, OUTSIDE the `role="tablist"` element.
  - Compose class names with `cx()` from `@renderer/lib/cx`; import the stylesheet via `import './Tabs.css'`.
  - JSDoc on the module, the exported types, and the component, citing the ACs each satisfies (mirror the Dropdown.tsx JSDoc style).
- In `src/renderer/src/components/molecules/Tabs.css`:
  - Define semantic BEM classes (e.g. `tabs`, `tabs__list`, `tabs__tab`, `tabs__tab--active`, `tabs__tab--disabled`, `tabs__badge`, `tabs__actions`) bound to existing `src/renderer/styles/tokens.css` CSS custom properties.
  - No inline styles anywhere in the component. Gate any transition behind `@media (prefers-reduced-motion: reduce)`.

## Contracts

### Expects (checked before execution)

- `cx` is exported from `src/renderer/src/lib/cx.ts` and importable via `@renderer/lib/cx`.
- CSS custom properties exist in `src/renderer/styles/tokens.css` for the strip's colors/spacing.
- `src/renderer/src/components/molecules/` exists with `Dropdown.tsx` present as the wrapper/JSDoc precedent.

### Produces (checked after execution)

- `Tabs.tsx` exports `Tabs`, `TabDescriptor`, and `TabsProps`.
- `Tabs.tsx` renders a `role="tablist"` element containing `role="tab"` buttons, with `aria-selected` tied to `activeId`.
- `Tabs.tsx` imports `cx` from `@renderer/lib/cx` and `import './Tabs.css'`, and contains no `electron`/`node:` imports and no Radix import.
- `Tabs.css` defines the `tabs__tab` (and `tabs__tab--active`) semantic class selectors bound to `tokens.css` custom properties, with no inline-style reliance.

## Done When

- [x] `Tabs.tsx` and `Tabs.css` exist under `src/renderer/src/components/molecules/`
- [x] `Tabs` exports `TabDescriptor`, `TabsProps`, and the `Tabs` component, all with JSDoc (AC-11)
- [x] Tablist/tab roles + aria-selected + roving tabindex render per activeId; keyboard Arrow/Home/End wrap + disabled-skip; click fires onChange once; no-selection guard holds (AC-5,6,7,9,10)
- [x] Actions slot renders right-aligned outside the tablist when supplied (AC-8)
- [x] No inline `style={{...}}` in `Tabs.tsx`; no `electron`/`node:` import (AC-14, AC-15)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T05:41:02Z
**Files changed**: src/renderer/src/components/molecules/Tabs.tsx, src/renderer/src/components/molecules/Tabs.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Hand-rolled tablist per plan (no Radix). Review repair: aria-disabled string->boolean, removed dead margin-left CSS. qa Info for task 002: no-selection keeps tabIndex=0 on first enabled tab.
