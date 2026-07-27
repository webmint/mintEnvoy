# Summary: 019-code-editor-toggle

**Verdict**: APPROVED (see `verification.md`) · **Status**: Complete

## What was built

The raw request-body editor was rebuilt from a three-layer highlight overlay into an **edit/preview toggle**. By default the code area shows a syntax-highlighted, read-only preview; clicking it (or the new toggle control, or pressing Enter/Space) drops into a plain textarea for editing, and blurring or toggling returns to the highlighted preview. Only one layer is ever in the DOM at a time, highlighting is computed synchronously on switch-to-preview, and the editor behaves like a familiar code editor (Postman/CodeMirror-style): caret-at-click entry, a borderless editing surface, and horizontal scroll for long lines.

## Changes

- **Rebuild CodeEditor as an edit/preview toggle molecule** — conditional-mount textarea XOR highlighted `<pre>` (never both); synchronous `{value,lang}`-snapshot tokenizer gated to preview; caret-at-click, keyboard entry, and focus-on-mount.
- **BodyEditor owns the toggle + return-to-preview** — an ephemeral `editing` state, a toolbar toggle control, and a render-phase reset that returns to preview atomically on a request-tab switch.
- **Component tests + stories** rewritten for the new model (CodeEditor + BodyEditor), retiring the stale 018-era debounce/scroll-sync tests.
- **Docs** — `architecture.md` now describes the CodeEditor as an edit/preview toggle with tokenize-on-switch-to-preview.
- **Post-review UX fixes** (found via live Chrome DevTools MCP testing): whole-area click-to-edit so an empty/short body isn't a dead zone; edit textarea grows to full content height (`rows={lineCount}`) so no line is clipped; a borderless editor while editing (caret is the focus indicator) with a keyboard-only focus ring on the preview; an inset focus ring + 12px right gutter so nothing is clipped at the window edge; toggle `aria-pressed` + text-based accessible name, and a `.lang-pill` focus ring.

## Files changed

`33 files changed, +3550 / -1036` (assembled feature diff), of which the source surface is 8 files:

- `src/renderer/src/components/molecules/CodeEditor.{tsx,css}` — the rebuilt toggle molecule.
- `src/renderer/src/components/organisms/BodyEditor.{tsx,css}` — toggle ownership, render-phase reset, toolbar control.
- `src/renderer/src/components/molecules/__tests__/CodeEditor.{ct,stories}.tsx` + `.../organisms/__tests__/BodyEditor.{ct,stories}.tsx` — CT + fixtures for the new model.
- `docs/architecture.md` — CodeEditor clause updated.

The remaining changes are feature-planning artifacts under `specs/` and `research/`.

## Key decisions

- **Conditional mount (textarea XOR pre), no overlay** — the single mounted layer replaces the old three-layer transparent-textarea overlay; the caret is native and highlighting never fights the input.
- **`editing` owned by BodyEditor, never the store** — ephemeral UI state passed down as `editing`/`onEditingChange`, keeping the CodeEditor a controlled molecule.
- **Return-to-preview via set-state-in-render** — the tab-switch reset uses React's set-state-in-render idiom (not a `useEffect` and not a ref), so `editing` resets to false atomically with the tab switch (no stale edit frame).
- **Tokenize on switch-to-preview, no debounce** — a `{value,lang}`-snapshot `useMemo` gated to preview runs the tokenizer once per switch-to-preview, never per keystroke; the old debounced colored-snapshot state is gone.
- **Toggle-exit race handled with `onMouseDown` preventDefault** — clicking the toggle while editing suppresses the textarea blur so the single `onClick` flips cleanly to preview instead of bouncing back to edit.
- **Single-layer shared line-box CSS** — one `--code-line-h` custom property single-sources the gutter, preview, and textarea row height (no em-based gutter height).

## Deviations from plan

- Task 002 initially shipped a dynamic toggle `aria-label` and deferred `aria-pressed` (non-blocking); the `/review` accessibility pass surfaced it and it was fixed post-review (`aria-pressed` + text-based accessible name, WCAG 2.5.3-compliant).
- The 12px right gutter (Postman-parity, user-approved) is an intentional deviation from `design/reference.html` (`padding-right: 0`); it is recorded in `review.md`'s design-fidelity section and left to be declared or reverted.

## Acceptance criteria

All 23 verified PASS (code-read; `tests` mode — the CT suite is not locally runnable due to the pre-existing harness mount break):

- [x] AC-1 … AC-23 — **23/23 PASS** (per `verification.md`): no scroll-sync handler (AC-1), no debounced snapshot / synchronous useMemo (AC-2), toggle control (AC-3), malformed-JSON degrade (AC-4), jsonTokens reused unchanged (AC-5), tab-switch scroll+preview reset (AC-6), none/urlencoded unchanged (AC-7), escaped JSX children / no innerHTML (AC-8), shared line-box (AC-9), conditional mount (AC-10), only-visible testid (AC-11), caret-at-click + clamp (AC-12/13), tokenize-once-per-preview (AC-14), textarea attrs (AC-15), blur/toggle exit (AC-16), starts-in-preview (AC-17), keyboard entry (AC-18), gutter tracks layer (AC-19), docs updated (AC-20), type-check + lint (AC-21), no em gutter height (AC-22), no inline toggle styles (AC-23).
