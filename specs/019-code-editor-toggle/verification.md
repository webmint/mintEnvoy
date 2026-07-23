# Feature Verification — 019-code-editor-toggle — 2026-07-22

**Feature**: specs/019-code-editor-toggle
**Date**: 2026-07-22
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | CodeEditor.tsx has no `handleTextareaScroll` function and no scroll-sync useEffect between textarea and pre; the only scroll-related useEffect resets both refs to (0,0) on `resetKey` change (line ~121-130). |
| AC-2 | PASS (code) | No `setColored`, no `debounce`, no colored-snapshot state in CodeEditor.tsx. Tokenisation is a synchronous `useMemo` (`tokenResult`, line ~235-238) gated on `!editing`; no useState for the token result. |
| AC-3 | PASS (code) | BodyEditor.tsx renders `<button … data-testid="body-edit-toggle" … onClick={() => setEditing((v) => !v)}>` (line ~641-655); data-testid is a string literal — stable, not dynamic. |
| AC-4 | PASS (code) | `compose()` from jsonTokens is called unconditionally on any value; the component doc header states "If the raw text is not valid JSON, then CodeEditor shall render it as a single plain segment without throwing" and no try/catch wrapping is needed here — that guarantee lives inside `compose()` itself, which is reused unchanged (AC-5). No throwing path is introduced in CodeEditor. |
| AC-5 | PASS (code) | CodeEditor.tsx imports `compose` from `@renderer/lib/jsonTokens` (line ~57) and calls it as `compose(value, lang, validVars)` (line ~237) with no wrapper, monkey-patching, or modification. |
| AC-6 | PASS (code) | BodyEditor.tsx uses a render-phase state-in-render idiom: when `activeTabId !== prevTab`, it calls `setPrevTab(activeTabId)` and `setEditing(false)` (lines ~534-537), resetting to preview on tab switch. `resetKey={activeTabId}` propagates to CodeEditor for scroll reset. |
| AC-7 | PASS (code) | BodyEditor.tsx uses mount-all/hidden-toggle: `none` and `urlencoded` panels remain mounted with `hidden` attribute; their render logic (radio group, handleUrlencodedRowsChange, renderUrlencoded render-prop) is unchanged. No conditional logic was modified for these modes. |
| AC-8 | PASS (code) | Token spans are rendered as `<span …>{t.text}</span>` JSX children (lines ~250-267 of tokenSpans useMemo); no `dangerouslySetInnerHTML` or `innerHTML` assignment appears anywhere in CodeEditor.tsx. The file-level doc comment explicitly states "All token text is inserted as escaped JSX children — no innerHTML (AC-8)". |
| AC-9 | PASS (code) | CodeEditor.css defines `--code-line-h: calc(12.5px * 1.65)` on `.code-editor`; `.code-editor .gutter > div { height: var(--code-line-h); }` and `.code-editor-content > pre, .code-editor-content > textarea { line-height: var(--code-line-h); }` — all three layers share a single CSS custom property. |
| AC-10 | PASS (code) | CodeEditor.tsx render uses `{editing ? (<textarea …/>) : (<pre …/>)}` inside `.code-editor-content` (lines ~293-321) — a ternary conditional mount; never both elements present simultaneously. |
| AC-11 | PASS (code) | `data-testid="body-pre"` is on the `<pre>` element only (preview branch). The `<textarea>` has no `data-testid`. The container has `data-testid="body-code-editor"` (always present). Only the visible layer's testid (`body-pre`) is exposed; textarea has none. |
| AC-12 | PASS (code) | `handlePreviewClick` (line ~197-200) calls `computeCaretOffset(e.clientX, e.clientY)`, stashes the result in `pendingCaretOffset.current`, then calls `onEditingChange?.(true)`. The focus-on-mount effect (line ~136-145) then applies `setSelectionRange(offset, offset)` after the textarea mounts. |
| AC-13 | PASS (code) | `computeCaretOffset` (line ~155-186) returns `value.length` on a null hit (click below text) and clamps via `Math.max(0, Math.min(charOffset, value.length))` at line ~185; the comment on `handlePreviewClick` explicitly references "(AC-13)". |
| AC-14 | PASS (code) | `tokenResult` useMemo is gated `!editing ? compose(…) : null` (line ~235-238); while editing, the `<pre>` is unmounted so the memo is unreachable during keystrokes. `compose()` runs once on the `editing` false→true transition and whenever `{value, lang}` changes while in preview. |
| AC-15 | PASS (code) | The `<textarea>` has `spellCheck={false}` (line ~305) and no `resize` prop (CSS sets `resize: none` in CodeEditor.css line ~446). `white-space: pre` is set on `.code-editor-content > textarea` in CSS (line ~416). No explicit Tab override — native Tab behavior is preserved. |
| AC-16 | PASS (code) | `handleTextareaBlur` calls `onEditingChange?.(false)` (line ~214-216) on `onBlur`. The toggle button in BodyEditor calls `setEditing((v) => !v)` (line ~653) and uses `onMouseDown={(e) => e.preventDefault()}` to prevent blur-before-click race. |
| AC-17 | PASS (code) | CodeEditor prop `editing` defaults to `false` (line ~104: `editing = false`); BodyEditor initialises `const [editing, setEditing] = useState(false)` (line ~522). First mount starts in preview. |
| AC-18 | PASS (code) | The `<pre>` has `tabIndex={0}` (focusable) and `onKeyDown={handlePreviewKeyDown}`; `handlePreviewKeyDown` (line ~206-211) triggers `onEditingChange?.(true)` on `e.key === 'Enter'` or `e.key === ' '`. |
| AC-19 | PASS (code) | Both `<pre>` and `<textarea>` share `overflow: auto` inside `.code-editor-content` (CSS line ~417) with `--code-line-h` as the single line-height; the gutter is a parallel grid column with matching `height: var(--code-line-h)` per row. CSS grid (`grid-template-columns: 36px 1fr`) keeps gutter and content layer in one shared row. |
| AC-20 | PASS (code) | The embedded docs clause (docs/architecture.md line 30) explicitly states: "CodeEditor — domain-agnostic self-contained edit/preview toggle code editor … highlighting runs synchronously on switch-to-preview via a `{value,lang}` snapshot-cache `useMemo` (gated to preview, so it never recomputes per keystroke)". Both required doc elements are present. |
| AC-21 | PASS (code) | CodeEditor.tsx uses strict TypeScript throughout — typed props interface, explicit `React.JSX.Element` return, typed refs (`useRef<HTMLPreElement>`, `useRef<HTMLTextAreaElement>`), typed event handlers. No type suppressions (`@ts-ignore`, `as any`) are visible. No obvious lint violations (no console.log, no unused imports visible, no missing keys). Type-suite confirms separately. |
| AC-22 | PASS (code) | CodeEditor.css uses `height: var(--code-line-h)` (a calc-px value) on `.code-editor .gutter > div` (line ~368), NOT an em-based value. The comment at that line explicitly explains the reasoning: "An em-based value here would resolve against the gutter's 11.5px font (~18.975px) and drift". |
| AC-23 | PASS (code) | The CodeEditor component's JSX uses `data-editing={editing}` (a data attribute, not an inline style) on the container. Toggle states are controlled via CSS selectors `.code-editor[data-editing='false']` in CodeEditor.css. No `style={{…}}` prop is present on any element in CodeEditor.tsx for toggle-state presentation. |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/019-code-editor-toggle/review.md
**Scope creep**: none detected
**Leftover artifacts** _(advisory — does not block the verdict)_: 26 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

0 confirmed | 0 contested | 1 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 26 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
