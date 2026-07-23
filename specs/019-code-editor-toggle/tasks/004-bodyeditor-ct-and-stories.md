# Task 004: BodyEditor CT + stories (toggle/AC-6/focus)

**Feature**: 019-code-editor-toggle
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-6, AC-11, AC-16
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx | Modify | Toggle/AC-6/focus CTs |
| src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx | Modify | Reflect toggle-state rendering |

## Description

Author Playwright component tests + stories for the BodyEditor toggle + render-phase reset (task 002). These prove the organism-level behaviors that the molecule CT (task 003) cannot: the toggle button, the F-002 preventDefault exit, the toggle-entry focus, and the AC-6 tab-switch-while-editing atomic reset.

## CT Harness Constraints (carry-forward — MEMORY lessons; violating these fails the CT build under a misleading exit 0)

1. Import `tokens.css` via the global `playwright/index.tsx`, NOT a direct `@renderer/styles/tokens.css` alias import in the fixture (the alias resolves to `src/renderer/src` while tokens live at `src/renderer/styles` → ENOENT fails the whole CT build).
2. Reproduce the full styling context: production `className` scope + any `data-mstyle`/token attributes so line-box reads are real (not content-box defaults).
3. Scope `box-sizing: border-box` to the fixture via an inline `<style>` — do NOT global-import `base.css` (breaks screenshot baselines).
4. For any no-reflow / line-box baseline, seed with a NON-empty value (empty→filled conflates mount with the measured change → false regression).
5. Height-bound the fixture so the single-layer panel actually overflows before asserting `scrollTop`.
6. Leave the `test:ct` Done-When UNVERIFIED — the local CT harness cannot mount (pre-existing break); verify statically + live-verify per 018 rather than burning repair rounds.

## Change Details

- In `BodyEditor.ct.tsx`:
  - Toggle button + editing ownership: `body-edit-toggle` present in the toolbar right slot.
  - F-002 CT: enter edit, click the toggle while editing → lands in preview (the preventDefault suppresses the blur-then-click double-fire that would bounce back to edit).
  - Toggle-resets-scroll CT: toggle, then assert the freshly-mounted layer reads `scrollTop === 0` (height-bounded fixture per constraint 5).
  - Toggle-entry focus CT: from preview, click `body-edit-toggle` → assert `document.activeElement` is the mounted textarea (toggle entry focuses the textarea despite F-002 `preventDefault` — AC-18/AC-16 path).
  - AC-6 tab-switch-while-editing CT: enter edit (textarea mounted), change `activeTabId`, then in the IMMEDIATE post-switch read assert `body-pre` is mounted and the textarea is NOT — proving the same-commit editing reset (no intermediate edit-mode frame; the forbidden passive-`useEffect` form would commit `editing=true`/textarea for the new tab first).
  - Only-visible-layer testid assertions at the organism level (AC-11).
  - **AC-16 blur-exit CT (carry-forward from task-001 qa review — G-6)**: a STANDALONE blur exit, isolated from the toggle path — enter edit mode, then remove focus from the textarea by clicking an unrelated element (NOT the toggle), and assert `body-pre` is mounted (returned to preview). The F-002 toggle CT alone does not isolate the blur handler (the toggle's mousedown+click also fires `onEditingChange(false)`), so a bug calling `onEditingChange(true)` in the blur handler would slip through without this dedicated test.
  - **Assertion-formula constraint (carry-forward — G-7)**: locate the textarea by accessible name (`getByLabel('Request body')` / `toBeFocused()`), never by an internal `textareaRef`.
- In `BodyEditor.stories.tsx`:
  - Reflect toggle-state rendering (preview vs edit).

## Contracts

### Expects (checked before execution)
- BodyEditor renders `body-edit-toggle` with an `onMouseDown` preventDefault handler and owns `editing`/`prevTab` state (task 002 Produces).
- BodyEditor passes `editing`/`onEditingChange` to CodeEditor.

### Produces (checked after execution)
- `BodyEditor.ct.tsx` asserts clicking the toggle while editing lands in preview (F-002).
- `BodyEditor.ct.tsx` asserts `document.activeElement` is the textarea after a toggle-button entry.
- `BodyEditor.ct.tsx` asserts the immediate post-tab-switch read is `body-pre` (not textarea) when a tab switch occurs while editing (AC-6).
- `BodyEditor.stories.tsx` reflects preview vs edit toggle state.

## Done When

- [x] CTs authored for F-002 toggle-while-editing→preview, toggle-resets-scroll, toggle-entry focus (`activeElement`), AC-6 tab-switch-while-editing immediate preview, only-visible testids
- [x] Stories reflect toggle-state rendering
- [ ] `test:ct` run left UNVERIFIED (pre-existing local-harness mount break) — verified statically per the CT Harness Constraints _(unverified — see Completion Notes)_
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-22T08:55:13Z
**Files changed**: src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx, src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: Rewrote BodyEditor.ct for edit/preview toggle model; deleted 3 018-era tests (debounce/page.clock, 2x handleTextareaScroll sync, setColored re-arm). Added AC-3/AC-11/AC-16-18 focus/F-002/blur-exit/toggle-scroll/AC-6. Rewrote AC-14/isolation/onChange/scroll-reset/mixed/AC-4 for conditional-mount. Stories: +RawJsonToggleFixture, -orphaned ScrollHFixture, fixed stale debounce JSDoc. Authored main-thread (subagents stall on CT work; code-reviewer died 2x). Panel converged iter2: 2 code-reviewer Highs were analysis errors (onClick misread idempotent; store-mutation) refuted + closed with clarifying comments. test:ct UNVERIFIED (harness mount break).
