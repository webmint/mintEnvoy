# Task 007: Create TabBar organism

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002, 004
**Blocks**: 008, 009
**Spec criteria**: AC-3, AC-24, AC-25, AC-26, AC-9, AC-10
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/TabBar.tsx | Create | Strip composing Tabs; store→TabDescriptor mapping; label/dirty/`+` wiring |
| src/renderer/src/components/organisms/TabBar.css | Create | Tokens-bound semantic classes; reduced-motion-gated; no inline styles |

## Description

Create the `TabBar` organism — the working-tabs strip that composes the (now closable) Tabs primitive and binds it to `tabsStore`. Map `tabsStore.tabs` → `TabDescriptor[]` and wire the store's lifecycle actions to the primitive's events. Subscribe via **per-field selectors** (`tabs` and `activeTabId` separately) and pull actions as stable references — never a whole-store read (§4, matches the 003 Shell pattern).

Dependency direction: TabBar (organism) imports the Tabs **molecule** + `tabsStore`/`requestSpec` from `lib` (downward only) via the `@renderer` alias — never a sibling organism, never reaching back into `lib` from a component the wrong way (§2.3, Risk 2).

Label precedence per tab: `spec.name` when non-empty, else `method + ' ' + url` when `url` is non-empty, else the literal `'Untitled'` — rendered verbatim, no interpolation (AC-25), CSS-ellipsis truncated. The dirty marker renders alongside the label via the primitive's `badge` slot without replacing the label text (AC-26). The `+` new-tab control rides the existing `actions` slot (no Tabs contract change for `+`). Activating a tab → `selectActive`; the ✕ → `close`; the `+` → `newBlank` (AC-24).

## Change Details

- In `src/renderer/src/components/organisms/TabBar.tsx` (new):
  - Import `Tabs` (+ `TabDescriptor`) from `@renderer/components/molecules/Tabs` and `tabsStore` from `@renderer/lib/tabsStore`.
  - Subscribe with per-field selectors: `const tabs = tabsStore((s) => s.tabs)`, `const activeTabId = tabsStore((s) => s.activeTabId)`; pull `selectActive`/`close`/`newBlank` as stable action references.
  - Map each `Tab` → `TabDescriptor`: `id` = `tab.id`; `label` via the name→method+url→`Untitled` precedence (verbatim); `badge` set to a dirty marker only when `tab.dirty` (alongside label, not replacing it — AC-26).
  - Render `<Tabs closable onClose={close} onChange={selectActive} activeId={activeTabId} tabs={descriptors} actions={<button onClick={newBlank}>+</button>} aria-label="Open request tabs" />` (route ✕→close, tab activate→selectActive, +→newBlank — AC-24).
  - JSDoc the component. Renderer-only, no `electron`/`node:` import (AC-10), no inline `style={{...}}` (AC-9).
- In `src/renderer/src/components/organisms/TabBar.css` (new):
  - Tokens-bound semantic classes (color/bg/border/text vars, radius/font scales; per-method color for any method marker). CSS-ellipsis truncation for the label. Reduced-motion-gated transitions. No inline styles.

## Contracts

### Expects (checked before execution)
- `tabsStore` (task 002) exposes the `tabs`/`activeTabId` state + `selectActive`/`close`/`newBlank` actions for per-field selector subscription. (`openFromCollection` is NOT consumed here.)
- The closable/onClose Tabs contract (task 004) is present (`TabsProps.closable`, `TabsProps.onClose`).
- The Tabs molecule's `badge` slot and `actions` slot exist (feature 002, unchanged contract).

### Produces (checked after execution)
- `src/renderer/src/components/organisms/TabBar.tsx` exports `TabBar` and `src/renderer/src/components/organisms/TabBar.css` exists with tokens-bound classes (AC-3).
- TabBar composes `Tabs` with `closable`, routing activate→`selectActive`, ✕→`close`, +→`newBlank` (AC-24).
- Label precedence name→method+url→`Untitled` rendered verbatim (AC-25); dirty marker via `badge` slot alongside the label (AC-26).
- TabBar imports only the Tabs molecule + `lib` (downward), never a sibling organism (§2.3, Risk 2).

## Done When

- [x] `TabBar.tsx` + `TabBar.css` exist; styling is tokens-bound with no inline styles (AC-3, AC-9)
- [x] per-field selectors (`tabs`, `activeTabId`) + stable action refs; no whole-store read
- [x] activate→`selectActive`, ✕→`close`, +→`newBlank` wired through the primitive (AC-24)
- [x] label precedence name→method+url→`Untitled`, verbatim + ellipsis-truncated (AC-25)
- [x] dirty marker via `badge` slot alongside label, not replacing it (AC-26)
- [x] imports only Tabs molecule + lib (downward), never a sibling organism; `@renderer` alias; no `node:`/`electron` (AC-10, §2.3)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T06:26:44Z
**Files changed**: src/renderer/src/components/organisms/TabBar.tsx, src/renderer/src/components/organisms/TabBar.css, src/renderer/src/components/molecules/Tabs.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: TabBar organism: per-field tabsStore selectors + stable action refs, closable Tabs composition, label precedence name->method+url->Untitled, dirty marker via badge slot, + new-tab. Imports only Tabs molecule + lib (no sibling organism, Risk 2). Panel repair: React.JSX->{JSX} import (organism convention); removed dead .tabs__badge--dirty from Tabs.css + fixed TabBar.css comment + added real .tabbar .tabs__badge accent-dot rule. Tabs suite 52/52.
