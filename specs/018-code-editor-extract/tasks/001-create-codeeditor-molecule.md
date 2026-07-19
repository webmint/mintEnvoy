# Task 001: create-codeeditor-molecule

**Feature**: 018-code-editor-extract
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 003
**Spec criteria**: AC-2, AC-3, AC-5, AC-6, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-17, AC-19, AC-20, AC-21
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/CodeEditor.tsx | Create | Self-contained three-layer overlay editor extracted from BodyEditor |
| src/renderer/src/components/molecules/CodeEditor.css | Create | Code-area CSS with a single `--code-line-h` line-box var |

## Description

Create a new reusable `CodeEditor` molecule that owns the three-layer overlay (gutter + aria-hidden `<pre>` + transparent `<textarea>`, single scroll source) currently inlined in BodyEditor (BodyEditor.tsx:296-327 + its state at 82-246). CodeEditor is self-contained: it owns the `compose()` 100ms trailing debounce, the colored snapshot state, the `gutterDivs`/`tokenSpans` memos, and the onScroll sync. It exposes props `{value, lang, onChange, validVars, resetKey?}`. The scroll-reset + `setColored(null)` invalidation effect AND the compose-debounce re-arm effect are keyed on the `resetKey` prop — a verbatim port of BodyEditor.tsx:104-114 and 122-128, swapping the `activeTabId` dep for `resetKey` (D5). CodeEditor holds NO tabsStore/activeTabId awareness — `resetKey` is an opaque scalar the consumer supplies. Reuse `jsonTokens.compose()` by import, byte-unchanged.

CodeEditor.css moves the code-area/overlay rules out of BodyEditor.css and single-sources the line-box height: define `--code-line-h: calc(12.5px * 1.65)` (= 20.625px) and drive the textarea, the `<pre>` lines, AND the `.gutter > div` rows from that one var — never `1.65em` on the gutter. Keep the `.tk-*` token colors, the `.code-editor` grid geometry, and the overlay padding/box-sizing/font exactly as in the T7a contract.

## Change Details

- In `src/renderer/src/components/molecules/CodeEditor.tsx`:
  - Export `CodeEditor` (memo-wrapped) with props type `{ value: string; lang: RawLang; onChange: (v: string) => void; validVars: ReadonlySet<string>; resetKey?: string | number }`.
  - Port the colored/debounce state, `showColored`, `lineCount`, `gutterDivs`, `tokenSpans`, `handleTextareaScroll`, and the three-layer render (`.code-editor` grid → `.gutter` + `.code-editor-content` → `<pre>` + `<textarea>`).
  - Port BodyEditor.tsx:104-114 (scroll-reset + `setColored(null)`) and 122-128 (debounce re-arm) with `resetKey` substituted for `activeTabId` in the dep arrays; call `compose(value, lang, validVars)`.
  - Keep `data-testid` values `body-code-editor` (grid), `body-gutter`, `body-pre` unchanged.
  - Import `compose` from `@renderer/lib/jsonTokens` and `isMissingVar` from `@renderer/lib/varTokens` via the `@renderer` alias; import only lib/ + atoms, never `organisms/` or `tabsStore`.
- In `src/renderer/src/components/molecules/CodeEditor.css`:
  - Add `.code-editor { --code-line-h: calc(12.5px * 1.65); … }`; set the `.gutter > div`, `<pre>` line, and textarea row heights from `var(--code-line-h)`.
  - Move the `.tk-*`, `.code-editor-content`, overlay pre/textarea, and focus-ring rules verbatim from BodyEditor.css.

## Contracts

### Expects (checked before execution)
- `BodyEditor.tsx` lines 296-327 hold the inline `.code-editor` three-layer overlay markup.
- `compose` is an exported function in `src/renderer/src/lib/jsonTokens.ts`.

### Produces (checked after execution)
- `CodeEditor` is exported from `src/renderer/src/components/molecules/CodeEditor.tsx` with props including `value`, `lang`, `onChange`, `validVars`, and optional `resetKey`.
- `CodeEditor` calls `compose(` from `@renderer/lib/jsonTokens` and never redefines a tokenizer.
- A `useEffect` in `CodeEditor.tsx` lists `resetKey` in its dependency array and resets scroll + calls `setColored(null)`; a second `useEffect` lists `resetKey` and re-schedules `compose`.
- `CodeEditor.css` defines `--code-line-h` and applies `var(--code-line-h)` to the gutter, pre, and textarea rows; the file contains no `1.65em`.
- `data-testid="body-code-editor"`, `data-testid="body-gutter"`, and `data-testid="body-pre"` appear in `CodeEditor.tsx`.
- `CodeEditor.tsx` contains no import from `@renderer/components/organisms` and no `tabsStore` import.

## Done When

- [x] `CodeEditor.tsx` + `CodeEditor.css` exist under `molecules/` and render the three-layer overlay from props.
- [x] `--code-line-h` single-sources the gutter/pre/textarea row height (20.625px); no `1.65em` on the gutter.
- [x] `resetKey`-keyed reset + re-arm effects present; `compose()` reused byte-unchanged.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-17T06:26:56Z
**Files changed**: src/renderer/src/components/molecules/CodeEditor.tsx, src/renderer/src/components/molecules/CodeEditor.css
**Contract**: Expects 2/2 | Produces 6/6
**Notes**: Faithful three-layer overlay extraction. compose() reused byte-unchanged; resetKey substituted for activeTabId in both effects. --code-line-h single-sources gutter/pre/textarea row height (no 1.65em). qa flagged 3 test-coverage gaps (AC-2 degrade, .tk-var.missing, AC-3 tie-break) accepted-deferred to Task 003 per convention. aria-label kept verbatim per spec.
