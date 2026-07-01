# Task 005: add-requestbar-component-test

**Feature**: 009-request-bar
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004
**Blocks**: None
**Spec criteria**: AC-30
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                                              | Action | Description               |
| ----------------------------------------------------------------- | ------ | ------------------------- |
| src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx | Create | Playwright component test |

## Description

Add the real-browser Playwright CT for RequestBar — the focus/keyboard/fidelity layer the jsdom unit test cannot cover. Targets the layout, the disabled-Send state, the ⌘↵/⌘S shortcuts, the method-dropdown open+dismiss, and per-tab isolation. Apply the two project CT lessons: the Radix dismiss arm-race two-step gate and full styling-context fixture scoping.

## Change Details

- Create `src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx` (mirror the existing `Dropdown.ct.tsx` / `Tabs.ct.tsx` shape):
  - Fixture mounts RequestBar with the full styling context: import `tokens.css` and set `data-mstyle` on the host element (per the CT-fidelity-fixture-scoping lesson) so the method pill resolves its color.
  - Cover: `[method ▾][URL][Send]` layout renders; Send is disabled with an empty url and enabled after typing; ⌘↵ triggers the send path and ⌘S triggers save (preventDefault — native save does not fire); the method Dropdown opens and an outside click dismisses it using the two-step gate (await `el.getAnimations()` finished, then yield one `setTimeout(0)` macrotask before `page.mouse.click`); switching the active tab swaps method+url with no bleed.

## Contracts

### Expects (checked before execution)

- `RequestBar` is exported from `src/renderer/src/components/organisms/RequestBar.tsx` (task 004) with its `onSend` prop.

### Produces (checked after execution)

- `RequestBar.ct.tsx` exists and exercises layout, disabled Send, ⌘↵/⌘S, method-dropdown dismiss (two-step gate), and per-tab isolation.

## Done When

- [x] CT covers layout, disabled-Send, ⌘↵/⌘S, dropdown open+dismiss, per-tab isolation
- [x] Outside-click dismiss applies the Radix two-step readiness gate (no immediate `mouse.click`)
- [x] Fixture imports tokens.css and sets data-mstyle on the host
- [x] The RequestBar CT suite passes (`playwright test`)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-28T12:12:13Z
**Files changed**: src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx, src/renderer/src/components/organisms/**tests**/RequestBar.stories.tsx
**Contract**: Expects 1/1 | Produces 1/1
**Notes**: RequestBar Playwright CT (7 tests: layout, disabled-Send, ⌘↵/⌘S, Radix dropdown dismiss two-step gate, per-tab isolation, AC-20 overflow-no-reflow). ADDITION: RequestBar.stories.tsx fixture file (required by the established CT pattern, per Dropdown.stories.tsx). 1 review-repair round (AC-20 CT + order-independent store reset + §5.2 shared-fixture import + CT-4 comment). test-only setState confirmed as established convention.
