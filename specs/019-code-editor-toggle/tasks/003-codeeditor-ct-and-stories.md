# Task 003: CodeEditor CT + stories (toggle/caret/focus/recolor)

**Feature**: 019-code-editor-toggle
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: None
**Spec criteria**: AC-4, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-17, AC-18, AC-19
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx | Modify | Toggle/caret/focus/recolor CTs; split line-box co-read |
| src/renderer/src/components/molecules/__tests__/CodeEditor.stories.tsx | Modify | Edit/preview fixtures; single-layer mount |

## Description

Author Playwright component tests + stories for the rebuilt CodeEditor molecule (task 001). Drive the molecule in isolation via the `editing` prop from a fixture — no BodyEditor needed. Drop the 018 colored-during-edit assertions.

## CT Harness Constraints (carry-forward — MEMORY lessons; violating these fails the CT build under a misleading exit 0)

1. Import `tokens.css` via the global `playwright/index.tsx`, NOT a direct `@renderer/styles/tokens.css` alias import in the fixture (the alias resolves to `src/renderer/src` while tokens live at `src/renderer/styles` → ENOENT fails the whole CT build).
2. Reproduce the full styling context: production `className` scope + any `data-mstyle`/token attributes so line-box reads are real (not content-box defaults).
3. Scope `box-sizing: border-box` to the fixture via an inline `<style>` — do NOT global-import `base.css` (breaks screenshot baselines).
4. For any no-reflow / line-box baseline, seed with a NON-empty value (empty→filled conflates mount with the measured change → false regression).
5. Height-bound the fixture so the single-layer panel actually overflows before asserting `scrollTop`.
6. Leave the `test:ct` Done-When UNVERIFIED — the local CT harness cannot mount (pre-existing break); verify statically + live-verify per 018 rather than burning repair rounds.

## Change Details

- In `CodeEditor.ct.tsx`:
  - F-001 recolor: first-mount preview is colored (AC-17); lang-cycle-in-preview recolors; NO recolor on keystroke-in-edit (AC-14 — compose runs once per switch-to-preview, not per keystroke).
  - Conditional-mount: assert textarea XOR pre — `editing=false` mounts `body-pre` and NOT the textarea; `editing=true` mounts the textarea and NOT `body-pre` (AC-10, AC-11 only-visible-layer testids).
  - Caret-at-click: click a preview character → enter edit + caret at the clicked offset (AC-12); click past end-of-line/below-text → caret clamped to nearest character (AC-13).
  - Keyboard entry focus: focus the preview `pre`, press Enter → assert `document.activeElement === textareaRef.current` (AC-18 keyboard entry focuses the textarea).
  - Line-box: split the AC-9 co-read into an edit-state (textarea) read and a preview-state (pre) read; both equal the shared `--code-line-h` line-box height.
  - **AC-4 (carry-forward from task-001 qa review)**: malformed-JSON degrade CT — with `editing=false` and a malformed-JSON `value`, assert `body-pre` renders a single plain `<span>` with NO `.tk-*` token spans, IMMEDIATELY on mount (the new synchronous `useMemo` model — NOT the deleted debounce-timed arrival the old CT at CodeEditor.ct.tsx assumed). MEMORY `jsontokens-jsonparse-is-ac17-detector`: this exercises the JSON.parse degrade boundary.
  - **AC-15 (carry-forward)**: textarea-attribute CT — with `editing=true`, assert `textarea.spellcheck === false`, `getComputedStyle(textarea).resize === 'none'`, and `getComputedStyle(textarea).whiteSpace === 'pre'` (guards the horizontal-scroll/no-soft-wrap contract against a regression to `pre-wrap`).
  - **AC-19 (carry-forward)**: assert the gutter tracks the visible layer within one scroll container (gutter present + row-aligned per state).
  - **G-1 stale-CT rewrite (carry-forward — REQUIRED)**: the existing CodeEditor.ct.tsx tests that assert 018-era behavior WILL fail against the new model and MUST be rewritten, not just left: the resetKey re-arm test (asserts `setColored(null)`+debounce detach/reattach — neither exists now; `useMemo` is synchronous so `.tk-key` is present from first render) and the scroll-reset test (drives `handleTextareaScroll` on both pre+textarea from one mount — `handleTextareaScroll` is deleted and only one layer mounts). Rewrite both for the conditional-mount model.
  - **AC-14 framing (carry-forward — G-4)**: a Playwright CT CANNOT read the `useMemo` invocation count without implementation binding. Assert the BEHAVIORAL evidence — `.tk-*` spans absent while `editing=true` (pre unmounted) and present after switching to preview — do NOT claim "exactly once" in an assertion the CT cannot prove; the once-per-transition guarantee is a code-review property, not a CT one.
  - **Assertion-formula constraints (carry-forward — G-7/G-8)**: for the focus assertions, locate the textarea by its accessible name — `page.getByLabel('Request body')` / `await expect(...).toBeFocused()` — NEVER `document.activeElement === textareaRef.current` (an internal React ref inaccessible from CT). The textarea has NO data-testid by design; do NOT add one — locate it by role/aria-label. AC-11 edit-state check = `body-pre` NOT attached AND `getByLabel('Request body')` attached.
  - **Caret-CT font precondition (carry-forward — G-5)**: `caretPositionFromPoint` maps a click coordinate against the RENDERED font metrics; the AC-12/13 caret CT must first assert the monospace font (JetBrains Mono) is loaded in the harness (MEMORY `fontsource-vite-relative-url` — the project had CT font-load failures), else the predicted `selectionStart` is calibrated to a fallback font and the test is flaky/wrong.
- In `CodeEditor.stories.tsx`:
  - Add edit-state and preview-state fixtures; single-layer mount.

## Contracts

### Expects (checked before execution)
- CodeEditor exposes `body-code-editor` container, `body-pre` (preview), and the textarea (edit) testids, and a focus-on-mount effect keyed on `editing` (task 001 Produces).
- CodeEditor accepts `editing`/`onEditingChange` props.

### Produces (checked after execution)
- `CodeEditor.ct.tsx` asserts the textarea (located via `getByLabel('Request body')` / `toBeFocused()`, never an internal ref) is focused after keyboard-Enter entry.
- `CodeEditor.ct.tsx` asserts only the visible layer's testid is present per `editing` state.
- `CodeEditor.ct.tsx` asserts a single compose per switch-to-preview (no per-keystroke recolor).
- `CodeEditor.stories.tsx` exports an edit-state and a preview-state fixture.

## Done When

- [x] CTs authored for F-001 recolor, caret/clamp, keyboard-Enter focus (`activeElement`), only-visible-layer testids (AC-10/11), line-box split
- [x] Stories export edit + preview fixtures (single-layer mount)
- [ ] `test:ct` run left UNVERIFIED (pre-existing local-harness mount break) — verified statically per the CT Harness Constraints _(unverified — see Completion Notes)_
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-22T07:30:03Z
**Files changed**: src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx, src/renderer/src/components/molecules/__tests__/CodeEditor.stories.tsx
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: Rewrote CT+stories for conditional-mount/synchronous CodeEditor; retired 3 stale 018-era tests. 18 tests covering AC-4/6/9/10/11/12/13/14/15/16/17/18/19. Authored in main thread (dispatched qa-engineer + code-reviewer stalled on 600s watchdog). Panel converged iter2 after 2 repair rounds (AC-14 no-op-tokeniser + AC-19 edit-gutter gaps; AC-14 function-poll disambiguation). test:ct UNVERIFIED — local CT harness mount break (MEMORY ct-organism-fixtures-cannot-mount-locally); verified statically. Carry-forward: assertMonoFontLoaded depends on CT-harness font load (MEMORY fontsource-vite-relative-url).
