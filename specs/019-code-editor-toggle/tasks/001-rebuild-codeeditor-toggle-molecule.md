# Task 001: Rebuild CodeEditor as edit-preview toggle molecule

**Feature**: 019-code-editor-toggle
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 003
**Spec criteria**: AC-1, AC-2, AC-4, AC-5, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-21, AC-22, AC-23
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/CodeEditor.tsx | Modify | Three-layer overlay → conditional-mount edit/preview toggle |
| src/renderer/src/components/molecules/CodeEditor.css | Modify | Drop absolute-overlay stacking; single visible layer |

## Description

Rebuild the CodeEditor molecule from the 018 three-layer overlay (gutter + transparent textarea + aria-hidden pre, scroll-synced) into a design-matched edit/preview toggle that mounts a plain textarea XOR the highlighted pre — never both. **Execute the plan's pinned decisions; do NOT re-derive them** — the plan settled every mechanism across 6 grill cycles. This is one atomic transformation: the overlay deletion and the conditional-mount rewrite are inseparable (deleting `handleTextareaScroll`/`showColored` requires the new single-layer model, and conditional-mount cannot coexist with the both-mounted overlay).

## Change Details

- In `src/renderer/src/components/molecules/CodeEditor.tsx`:
  - Add `editing: boolean` + `onEditingChange: (next: boolean) => void` to `CodeEditorProps`; CodeEditor becomes a controlled molecule (no store awareness).
  - Conditional-mount: render the plain `textarea` when `editing` is true, the highlighted `pre` (testid `body-pre`) when `editing` is false — never both (AC-10). Keep the `body-code-editor` container testid.
  - **Tokenize gate (F-001)**: replace the 100ms debounce `useEffect` + `showColored`/`colored` `useState` with a synchronous `{value,lang}` snapshot-cache `useMemo` that invokes `compose(value, lang, validVars)` ONLY when `!editing` (the pre is the mounted layer). Reuse the existing `colored.snapshot===value` cache idea extended to key on `lang`. Compose runs once per switch-to-preview (AC-14), on first mount (AC-17), and on tab-switch/lang-cycle. Delete the `showColored` derived flag (AC-2) and the `BODY_HIGHLIGHT_DEBOUNCE_MS` debounce.
  - **Focus on edit entry (all paths)**: add a focus-on-mount `useEffect` keyed on `editing` (co-located with the existing effects) that, on the `editing` false→true transition, calls `textareaRef.current?.focus()`. This is the SHARED focus owner for all three entry paths (click / keyboard Enter-Space / toggle). Keyed on `editing` alone — NO `editingViaClick` flag (`focus()` is idempotent). (AC-18)
  - **Caret-at-click**: add a caret-mapping helper — on a preview click, `caretPositionFromPoint` (fallback `caretRangeFromPoint`) on the pre → Range-from-start length → clamp offset to `[0, value.length]`, null hit → end-of-text; stash the offset and apply `setSelectionRange` post-mount. The click path owns ONLY the caret offset; focus itself is the shared effect's job (AC-12, AC-13). Enter/Space on the focusable pre also enters edit (AC-18).
  - **Exits (F-002 half)**: textarea `blur` calls `onEditingChange(false)` (AC-16 blur half — the toggle-activate half lives in task 002).
  - **textarea attrs (AC-15)**: `spellCheck={false}`, no resize, native Tab, `white-space: pre` (horizontal scroll, no soft-wrap).
  - Delete `handleTextareaScroll` (AC-1) and its `onScroll` wiring. The `resetKey` reset stays a plain passive `useEffect` (zeros the persistent pre's scroll on tab-switch); scroll resets to 0 on every toggle via the natural fresh-mount of the swapped layer — NO capture ref, NO restore layout-effect, NO ordering.
  - All token text stays escaped JSX children — never innerHTML (AC-8). `compose()` reused byte-unchanged (AC-5). Malformed JSON degrades to a single plain segment inside `compose()` (AC-4).
  - Classes via `cx()` — no inline `style={{` (AC-23).
- In `src/renderer/src/components/molecules/CodeEditor.css`:
  - Drop the absolute-overlay stacking; both states bind the same `--code-line-h: 20.625px` calc + identical font/padding/box-sizing on the single visible layer (AC-9, AC-19). No `1.65em` em-based row height (AC-22). Horizontal scroll (`white-space: pre`); focusable-preview styling.

## Contracts

### Expects (checked before execution)
- `CodeEditor.tsx` currently renders the three-layer overlay (`handleTextareaScroll`, `showColored`, `colored` useState, debounce useEffect, container `.code-editor` / testid `body-code-editor`, `body-pre`).
- `compose` is exported from `src/renderer/src/lib/jsonTokens.ts` and `cx` from `src/renderer/src/lib/cx.ts`; `isMissingVar` from `varTokens`.

### Produces (checked after execution)
- `CodeEditorProps` declares `editing` and `onEditingChange` in `CodeEditor.tsx`.
- `CodeEditor.tsx` contains no `handleTextareaScroll` and no `showColored`.
- `CodeEditor.tsx` calls `textareaRef.current?.focus()` inside a `useEffect` keyed on `editing`.
- `CodeEditor.tsx` calls `setSelectionRange` and `caretPositionFromPoint` (caret-at-click helper).
- `CodeEditor.tsx` invokes `compose(` inside a `useMemo` (no `setTimeout` debounce remains).
- `CodeEditor.css` contains `--code-line-h` and no `1.65em`.

## Done When

- [x] CodeEditor mounts textarea XOR pre (never both) driven by `editing`; `body-pre` present only in preview, textarea only in edit
- [x] `compose()` runs via a `!editing`-gated `useMemo` (no debounce); `showColored` and `handleTextareaScroll` removed
- [x] Focus-on-mount `useEffect` keyed on `editing` focuses the textarea; caret-at-click helper stashes+applies `setSelectionRange`
- [x] `grep -q 'body-edit' `? N/A — toggle button is task 002; container `body-code-editor` + `body-pre` testids present
- [x] `! grep -q 'handleTextareaScroll'` and `! grep -q 'showColored'` on CodeEditor.tsx pass; `! grep -q '1.65em'` and `! grep -q 'style={{'` pass
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-21T11:14:48Z
**Files changed**: src/renderer/src/components/molecules/CodeEditor.tsx, src/renderer/src/components/molecules/CodeEditor.css
**Contract**: Expects 2/2 | Produces 6/6
**Notes**: Conditional-mount edit/preview toggle; editing/onEditingChange optional to avoid touching BodyEditor (task 002 wires them). Review-repair applied inline (subagent infra stalled): cx() for tk-var class (§4), removed dead tokenSpans fallback, added role=button. Panel clean; perf validVars-stability was premise-false (envVars frozen singleton); qa gaps folded into tasks 003/004.
