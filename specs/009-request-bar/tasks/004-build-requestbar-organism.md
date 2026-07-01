# Task 004: build-requestbar-organism

**Feature**: 009-request-bar
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001, 002, 003
**Blocks**: 005, 006
**Spec criteria**: AC-1, AC-3, AC-6, AC-7, AC-8, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-23, AC-28, AC-29, AC-30
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File                                                                | Action | Description               |
| ------------------------------------------------------------------- | ------ | ------------------------- |
| src/renderer/src/components/organisms/RequestBar.tsx                | Create | the RequestBar organism   |
| src/renderer/src/components/organisms/RequestBar.css                | Create | token-bound layout styles |
| src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx | Create | Vitest unit tests         |

## Description

Build the flat `RequestBar` organism: layout `[method ▾][URL][Send]` plus Save and Share, bound to the active tab's RequestSpec. Mirror the established renderer patterns — TabBar's per-field zustand selectors + stable action refs, the 001 Dropdown molecule for the method selector, the 005 `.method/.{METHOD}` color convention, and Shell Effect 4's `document` keydown shape for the global shortcuts. Renderer-only, `@renderer` alias, zero inline styles.

## Change Details

- Create `src/renderer/src/components/organisms/RequestBar.tsx`:
  - Props: `onSend?: (intent: { tabId: string; method: HttpMethod; url: string }) => void` (default no-op). Type `HttpMethod` imported from `@renderer/lib/httpMethods` — do NOT import `requestSpec` (constitution §5.2). Document the prop type (AC-23).
  - Read via per-field selectors: `activeTabId`, and the active tab's `method`, `url`, `dirty` (derive active tab from `tabs` + `activeTabId`, mirror TabBar). Stable action refs for `updateActiveSpec` + `markClean` (AC-11).
  - Method selector: controlled 001 `Dropdown` (local `useState` open-state driving `open`/`onOpenChange`); trigger is a button styled `.method {METHOD}` showing the current method; `items` from `METHODS`, each `onSelect` → `updateActiveSpec({ method })` (AC-7). Trigger's accessible name is the visible method text only — no redundant `aria-label` (AC-23 / spec Q-1).
  - URL field: controlled single-line `<input value={url} onChange={e => updateActiveSpec({ url: e.target.value })}>` (AC-8); no remount key so method changes don't touch the url buffer/caret (AC-18).
  - `canSend = url.trim() !== ''` derived once; consumed by the Send button `disabled`, the click handler, and the ⌘↵ handler (AC-12). Send click: if `canSend`, call `onSend({ tabId: activeTabId, method, url })` — no HTTP (AC-13).
  - Save button: `if (dirty) markClean(activeTabId)` else no-op (AC-14, AC-15). Share button: rendered token-styled in its final slot, `disabled`/no-op stub (AC-19). Icons via the Icon atom.
  - One `useEffect` registering a `document` keydown: ⌘↵ → the Send path (same `canSend` guard); ⌘S → `e.preventDefault()` then the Save path; read live state via `tabsStore.getState()` (no stale closure); empty deps; cleanup on unmount (AC-16, AC-17). Acts on the active tab regardless of focus.
- Create `src/renderer/src/components/organisms/RequestBar.css`:
  - Semantic classes bound to `tokens.css` custom properties; zero inline styles (AC-28). `[method ▾][URL][Send/Save/Share]` row; the URL input is single-line with horizontal overflow scroll and the method pill + actions do not reflow/grow with url length (AC-20).
- Create `src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx`:
  - Reset the tabsStore singleton via `tabsStore.setState({tabs,activeTabId})` in `beforeEach` (mirror TabBar.test.tsx); use the `@renderer/__tests__/fixtures/requestSpec` `makeTab` fixture.
  - Cover: trim guard (empty/whitespace url → Send disabled, no onSend), method-switch leaves url unchanged, Save markClean-when-dirty / no-op-when-clean, per-tab render isolation on activeTabId change.
- RequestBar must NOT write `document.documentElement.dataset.mstyle` — Shell remains the sole writer (AC-6).

## Contracts

### Expects (checked before execution)

- `METHODS` + `HttpMethod` exported from `lib/httpMethods` (task 001).
- `tabsStore.updateActiveSpec(patch)` exists (task 002); `tabsStore.markClean(tabId)` exists (pre-existing state).
- constitution §4 admits a spec-edit subscriber (task 003).
- `Dropdown` (controlled, `open`/`onOpenChange`/`trigger`/`items`) + `Icon` atom + `cx` + `tokens.css` exist.

### Produces (checked after execution)

- `src/renderer/src/components/organisms/RequestBar.tsx` exports `RequestBar` with an `onSend?` prop typed against `HttpMethod` + primitives (no `requestSpec` import).
- RequestBar writes method/url only through `updateActiveSpec` and Save only through `markClean`.
- `RequestBar.css` exists with token-bound classes and no inline styles in the tsx.
- `RequestBar.test.tsx` covers trim guard, method-switch independence, Save dirty/no-op, per-tab isolation.

## Done When

- [x] RequestBar renders `[method ▾][URL][Send/Save/Share]` and binds to the active tab's method+url
- [x] Send disabled on empty-after-trim url; fires `onSend` otherwise; Save markClean/no-op; Share disabled stub
- [x] ⌘↵ Send / ⌘S Save act on the active tab regardless of focus; ⌘S calls preventDefault
- [x] No `requestSpec` import and no Node/Electron import in RequestBar.tsx; no inline styles
- [x] `npx vitest run src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx` passes
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-28T11:15:36Z
**Files changed**: src/renderer/src/components/organisms/RequestBar.tsx, src/renderer/src/components/organisms/RequestBar.css, src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx
**Contract**: Expects 4/4 | Produces 4/4
**Notes**: RequestBar organism: per-field primitive selectors (no §9 over-render), controlled URL input + method Dropdown via updateActiveSpec, Send/Save/Share, ⌘↵/⌘S via onSendRef+empty-deps document keydown. 23 unit tests. 1 autonomous review-repair round (perf over-render + listener churn + 3 test gaps + JSDoc). Icons: chevronDown/send/save/share.
