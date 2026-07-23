# Task 002: Add edit/preview toggle + render-phase reset to BodyEditor

**Feature**: 019-code-editor-toggle
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 004, 005
**Spec criteria**: AC-3, AC-6, AC-7, AC-16, AC-21
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/BodyEditor.tsx | Modify | Own `editing` state, render-phase reset, toggle button, wire CodeEditor |
| src/renderer/src/components/organisms/BodyEditor.css | Modify | Toggle-button styling (toolbar right slot) |

## Description

Give BodyEditor ownership of the ephemeral `editing` boolean and render the edit/preview toggle control, then wire `editing`/`onEditingChange` into the CodeEditor molecule (task 001). **Execute the plan's pinned decisions; do NOT re-derive them.** The none/urlencoded/form-data/binary/graphql panels and the lang-pill behavior stay byte-identical (AC-7).

## Change Details

- In `src/renderer/src/components/organisms/BodyEditor.tsx`:
  - Add `const [editing, setEditing] = useState(false)` (default preview; ephemeral BodyEditor state, NEVER tabsStore — §7).
  - **Render-phase reset (AC-6 return-to-preview)**: add `const [prevTab, setPrevTab] = useState(activeTabId)`; during render, `if (activeTabId !== prevTab) { setPrevTab(activeTabId); setEditing(false) }`. This is React's documented set-state-in-render idiom — atomic with the tab switch, render stays pure, `useState`-seeded prev avoids a spurious first-mount reset. Explicitly NOT a `prevActiveTabId` **ref** written during render and NOT `useEffect(() => setEditing(false), [activeTabId])` (both are the forbidden forms the plan names).
  - **Toggle button (AC-3)**: render a toggle control in the toolbar right slot (beside the lang-pill) with `data-testid="body-edit-toggle"`. Its `onMouseDown` calls `e.preventDefault()` (F-002) so clicking it while editing does not blur the textarea; the single `onClick` owns the flip reading current `editing` (AC-16 toggle half — the blur half is task 001).
  - Pass `editing={editing}` and `onEditingChange={setEditing}` to `<CodeEditor>` at the existing render site (currently :186); keep `resetKey={activeTabId}` and the other props.
  - `handleLangCycle` still cycles `lang` in preview with no editing transition; the radio/urlencoded/placeholder paths are untouched (AC-7).
- In `src/renderer/src/components/organisms/BodyEditor.css`:
  - Add toggle-button styling in the toolbar right slot, class-based via `cx()` (no inline styles).

## Contracts

### Expects (checked before execution)
- `CodeEditor` accepts `editing` and `onEditingChange` props (task 001 Produces).
- `BodyEditor.tsx` subscribes to `activeTabId` via `tabsStore` and renders `<CodeEditor>` in the hidden raw panel with `resetKey={activeTabId}`.
- The toolbar right slot (`div.right`) hosts the `body-lang-pill` button.

### Produces (checked after execution)
- `BodyEditor.tsx` declares `const [editing, setEditing] = useState(false)` and `const [prevTab, setPrevTab] = useState(activeTabId)`.
- `BodyEditor.tsx` contains a render-phase `if (activeTabId !== prevTab)` block calling `setEditing(false)` (no `useEffect` and no ref for this reset).
- `BodyEditor.tsx` contains `body-edit-toggle` and an `onMouseDown` handler calling `preventDefault`.
- `BodyEditor.tsx` passes `editing` and `onEditingChange` to `<CodeEditor>`.

## Done When

- [x] `grep -q 'body-edit-toggle' src/renderer/src/components/organisms/BodyEditor.tsx` passes (AC-3)
- [x] BodyEditor owns `editing` `useState` + `prevTab` `useState` render-phase reset (no ref, no passive useEffect for the reset)
- [x] Toggle `onMouseDown` calls `preventDefault`; `editing`/`onEditingChange` passed to CodeEditor
- [x] none/urlencoded/form-data/binary/graphql + lang-pill behavior unchanged (AC-7)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-21T14:59:02Z
**Files changed**: src/renderer/src/components/organisms/BodyEditor.tsx, src/renderer/src/components/organisms/BodyEditor.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Toggle uses dynamic aria-label; aria-pressed deferred (code-reviewer Medium, non-blocking). AC-21 text not visible in this diff — confirm before task-004 CT.
