# Task 003: RequestSubTabs organism

**Feature**: 015-request-sub-tabs
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001, 002
**Blocks**: 004, 005
**Spec criteria**: AC-1, AC-3, AC-5, AC-6, AC-9, AC-10, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-25, AC-26
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/RequestSubTabs.tsx | Create | The container/switcher organism: composes Tabs, derives read-only badges, owns 6 mounted tabpanels + shared empty-state, wires tabpanel ARIA, defensive reads |
| src/renderer/src/components/organisms/__tests__/RequestSubTabs.test.tsx | Create | Vitest interaction: switch, badge derivation (count + 99+ + auth `•`), external setActiveSubTab, invalid-key normalization, no-active-tab empty region |

## Description

Create the `RequestSubTabs` organism (D1/D3/D6/D7/D8/D9). It composes the `Tabs` molecule for the fixed 6-sub-tab strip (Params, Auth, Headers, Body, Tests, Code), self-subscribes the active tab's `activeSubTab` (normalized) + active `spec` ref, derives 3 read-only badges, and owns all 6 tabpanels mounted at once and toggled via the `hidden` attribute so KVTable panel state survives a switch. Params/Headers panels arrive as named slot props (`params`/`headers`); the other 4 render ONE shared muted empty-state. It never mutates the RequestSpec and imports no organism / no unbuilt panel.

## Change Details

- Create `src/renderer/src/components/organisms/RequestSubTabs.tsx`:
  - Props: `{ params?: ReactNode; headers?: ReactNode }` — exactly two named slot props (NOT a `Record<SubTabKey, ReactNode>`); absent → the shared empty-state renders in that slot. Export the component with a doc comment (AC-19).
  - `import './RequestSubTabs.css'`. Import `Tabs`, `TabDescriptor` from the molecule; import `tabsStore`, `SubTabKey`, `VALID_KEYS` from `@renderer/lib/tabsStore` (alias, §2.3). Do NOT import KVTable or any `AuthPanel/BodyEditor/TestsPanel/CodePanel` (AC-24 `updateActiveSpec` never called, AC-25 no unbuilt-panel import, AC-23 no electron/node).
  - Per-field selectors: `activeTabId`; the active tab's `activeSubTab` read normalized `VALID_KEYS.includes(v) ? v : 'params'` (AC-16); the active tab's `spec` ref via a selector mirroring KVTable's `rows` selector (returns the spec ref — no new object per render, AC-26); `setActiveSubTab` action ref.
  - Badge derivation via `useMemo` over the spec ref: `params` = `spec.params.length` (omit when 0), `headers` = `spec.headers.length` (omit when 0), each clamped `n > 99 ? '99+' : n` (AC-15); `auth` = the literal `'•'` (U+2022) when `spec.auth.type !== 'none'`, else omit; Body/Tests/Code never badged.
  - Build 6 `TabDescriptor`s (`id` = the `SubTabKey`, `label` = human title, `badge` = derived-or-undefined), none `disabled` (AC-13). Render `<Tabs closable={false} linkPanels activeId={activeSubTab} onChange={(k) => setActiveSubTab(activeTabId, k as SubTabKey)} className='pane-tabs' tabs={descriptors} aria-label='Request sub-tabs' />` (AC-5, AC-6 keyboard delegated to Tabs).
  - Render 6 tabpanels, one per key, each: `role='tabpanel'`, `id={`panel-${key}`}`, `aria-labelledby={`tab-${key}`}`, `aria-controls={`tab-${key}`}` linking to its tab, `aria-selected={key === activeSubTab}`, and `hidden={key !== activeSubTab}` (AC-9, AC-14). Params panel content = `params` prop; Headers = `headers` prop; the other 4 (and any absent prop) = the shared empty-state element.
  - Shared empty-state: ONE muted element (class bound to `--text-muted`) reading "Panel not yet available" (AC-12) — internal JSX, not a per-panel personalization.
  - Focus preservation: a `useLayoutEffect` that refocuses the last-focused element in a panel on re-show (reuse the focus-restore pattern in Tabs.tsx:428-436) so literal input focus survives the `hidden` toggle (R6, AC-9).
  - No-active-tab guard: when `activeTabId` resolves to no tab, render a neutral empty region without throwing (AC-17).
  - No inline `style={{...}}` (AC-22) — all styling via `RequestSubTabs.css` classes.
- Create `src/renderer/src/components/organisms/__tests__/RequestSubTabs.test.tsx` (Vitest):
  - Clicking a sub-tab calls `setActiveSubTab` and shows that panel / hides others (AC-6, AC-9).
  - Badge shows params/headers counts, `99+` above 99 (AC-15), auth `•` when auth set, nothing when `type==='none'`.
  - An external `setActiveSubTab` write updates the visible panel identically to a click (AC-10).
  - An invalid stored `activeSubTab` normalizes to `params` (AC-16); no active tab renders an empty region, no throw (AC-17).

## Contracts

### Expects (checked before execution)
- `SubTabKey`, `VALID_KEYS`, `Tab.activeSubTab`, and `setActiveSubTab` are exported from `tabsStore.ts` (task 001).
- `Tabs` accepts a `linkPanels` prop that emits `id="tab-<id>"` + `aria-controls="panel-<id>"` on the tab button (task 002).
- `Tabs` + `TabDescriptor` (with `badge`) exist in the molecule.

### Produces (checked after execution)
- `RequestSubTabs` is exported from `RequestSubTabs.tsx`, accepting `params`/`headers` `ReactNode` slot props.
- The component renders a `<Tabs className='pane-tabs' linkPanels ... />` plus 6 `role='tabpanel'` nodes, each with `id="panel-<key>"`, `aria-labelledby="tab-<key>"`, `aria-selected`, and `hidden` toggling.
- Badge derivation appears in source: `spec.params.length` / `spec.headers.length` with a `> 99` `'99+'` clamp and the `'•'` auth marker.
- `RequestSubTabs.tsx` contains no `updateActiveSpec` call, no `electron`/`node:` import, no inline `style={{`, and no `AuthPanel|BodyEditor|CodePanel|TestsPanel` import.
- `RequestSubTabs.test.tsx` covers switch, badges, external write, normalization, and no-active-tab.

## Done When

- [x] `RequestSubTabs` renders the 6-tab strip via composed `Tabs` and 6 `hidden`-toggled tabpanels with correct ARIA.
- [x] Badges derive read-only (counts + 99+ + auth `•`) and update on spec change (AC-26).
- [x] Params/Headers slots render the `params`/`headers` props; the other 4 share one muted empty-state (AC-12).
- [x] Defensive reads pass: invalid key → `params` (AC-16); no active tab → empty region no throw (AC-17).
- [x] Source has no `updateActiveSpec` (AC-24), no electron/node import (AC-23), no inline style (AC-22), no unbuilt-panel import (AC-25).
- [x] `RequestSubTabs.test.tsx` passes.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-06T12:08:24Z
**Files changed**: src/renderer/src/components/organisms/RequestSubTabs.tsx, src/renderer/src/components/organisms/RequestSubTabs.css, src/renderer/src/components/organisms/__tests__/RequestSubTabs.test.tsx
**Contract**: Expects 3/3 | Produces 5/5
**Notes**: Created empty RequestSubTabs.css placeholder (task 004 fills). 36 Vitest tests. aria-selected on tabpanel kept per AC-14 (user Stage-A decision; non-standard WAI-ARIA but harmless). QA test gaps (n=99 boundary, auth empty-state, disabled-absent) closed in repair leg.
