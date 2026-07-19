# Task 002: wire-bodyeditor-consumer

**Feature**: 018-code-editor-extract
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 004, 005
**Spec criteria**: AC-1, AC-4, AC-6, AC-7, AC-19
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/BodyEditor.tsx | Modify | Replace inline raw editor with `<CodeEditor>`; remove editor state/effects/memos |
| src/renderer/src/components/organisms/BodyEditor.css | Modify | Remove relocated code-area/overlay rules |

## Description

Refactor BodyEditor to consume the new `CodeEditor` molecule. Replace the inline three-layer overlay in the raw slot (BodyEditor.tsx:296-327) with `<CodeEditor resetKey={activeTabId} value={body.raw.text} lang={body.raw.lang} onChange={…} validVars={validVars} />`. Remove from BodyEditor: the colored/debounce state, the `preRef`/`textareaRef` refs, the two `activeTabId`-keyed effects (104-114 reset, 122-128 re-arm), `handleTextareaScroll`, `handleTextChange`'s inline body if now trivial, `lineCount`/`gutterDivs`/`tokenSpans` memos, and the `compose`/`isMissingVar` imports if no longer used. Keep the toolbar, body-type radiogroup, lang-pill, and the mount-all/hidden six-panel structure (none/urlencoded/form-data/binary/graphql) exactly as before. Remove the relocated `.code-editor*`/`.tk-*`/overlay rules from BodyEditor.css; keep `.body-toolbar`, `.body-radio*`, `.lang-pill` styles.

## Change Details

- In `src/renderer/src/components/organisms/BodyEditor.tsx`:
  - Import `CodeEditor` from `@renderer/components/molecules/CodeEditor`.
  - Replace the raw panel's inner `.code-editor` markup with `<CodeEditor resetKey={activeTabId} … />`; the `onChange` calls the existing `setRaw({ ...body.raw, text })`.
  - Delete the colored state, refs, the two `activeTabId` effects, scroll handler, and the code-area memos now owned by CodeEditor.
  - Leave the radiogroup, lang-pill, mount-all `hidden` panels, and urlencoded render-prop slot untouched.
- In `src/renderer/src/components/organisms/BodyEditor.css`:
  - Remove the `.code-editor`, `.code-editor .gutter`, `.code-editor pre`, `.code-editor-content*`, `.tk-*`, and code-area focus rules (now in CodeEditor.css).
  - Keep toolbar/radio/lang-pill rules.

## Contracts

### Expects (checked before execution)
- `CodeEditor` is exported from `src/renderer/src/components/molecules/CodeEditor.tsx` with a `resetKey` prop (Task 001 Produces).

### Produces (checked after execution)
- `BodyEditor.tsx` imports `CodeEditor` from `@renderer/components/molecules/CodeEditor`.
- `BodyEditor.tsx` renders `<CodeEditor` with a `resetKey={activeTabId}` attribute in the raw slot.
- `BodyEditor.tsx` no longer contains a `.code-editor` inline overlay, a `preRef`, or a `useEffect` whose dependency array is `[activeTabId]`.
- `BodyEditor.tsx` retains the body-type `role="radiogroup"`, the `lang-pill`, and the six `hidden`-toggled mode panels.
- `BodyEditor.css` no longer contains a `.code-editor` rule.

## Done When

- [x] BodyEditor raw slot renders `<CodeEditor resetKey={activeTabId} …>`; inline overlay + the two `activeTabId` effects removed.
- [x] none/urlencoded/mode-strip/mount-all behavior unchanged.
- [x] Relocated code-area CSS removed from BodyEditor.css.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-17T07:14:22Z
**Files changed**: src/renderer/src/components/organisms/BodyEditor.tsx, src/renderer/src/components/organisms/BodyEditor.css
**Contract**: Expects 1/1 | Produces 5/5
**Notes**: BodyEditor delegates raw slot to <CodeEditor resetKey={activeTabId}>. Removed inline overlay + editor state/effects/memos + compose/isMissingVar imports; radiogroup/lang-pill/6 mount-all panels + none/urlencoded unchanged. BodyEditor.css stripped of .code-editor*/.tk-* rules. qa test-scope gaps (prop-wiring, lang-drift, testid contract) accepted-deferred to Task 003/004 per spec §4. onChange kept inline per perf (imperceptible, non-regression); useCallback fix noted for optional future polish.
