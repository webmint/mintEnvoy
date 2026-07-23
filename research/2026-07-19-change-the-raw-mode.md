# Research: Change the raw-mode CodeEditor molecule from an overlay (transparent textarea over highlighted pre, per-keystroke re-tokenization) to a design-matched edit/preview toggle that renders either a plain textarea (editing) or the highlighted pre (preview), tokenizing once on switch-to-preview.


**Date**: 2026-07-19
**Topic**: Change the raw-mode CodeEditor molecule from an overlay (transparent textarea over highlighted pre, per-keystroke re-tokenization) to a design-matched edit/preview toggle that renders either a plain textarea (editing) or the highlighted pre (preview), tokenizing once on switch-to-preview.
**Mode**: Enhancement
**Verdict**: Feasible with caveats

## Summary

The raw-mode CodeEditor overlay (transparent textarea over an absolute aria-hidden pre, per-keystroke debounced compose(), textarea->pre scroll-sync, colored-during-edit snapshot) exists only to color text WHILE typing; the design accepts plain-while-editing, so it can be replaced by an 'editing' boolean that mounts exactly one layer — plain textarea in edit, tokenized pre in preview — calling compose() once on switch-to-preview. State is owned by BodyEditor (the sole real consumer at BodyEditor.tsx:186; every other CodeEditor reference is a test fixture): entered via preview-click (caret placed at the clicked char) and the separate toggle button, left on textarea blur or the button. The shared 20.625px line-box (--code-line-h at CodeEditor.css:9), the byte-unchanged compose lib + its malformed-JSON degrade-to-plain (jsonTokens.ts:344/366), the data-testids (now only-visible-layer), and the resetKey scroll/snapshot-invalidation all carry over. Remaining uncertainty: caret-at-click has no setSelectionRange canonical in the repo (0 hits), so a click-coordinate->char-offset mapping is likely new code (runtime-probe pinned), and the CT AC-12/13/21 line-box test co-reads pre+textarea in one mounted state and must be split per toggle state.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | The raw-mode CodeEditor uses an overlay edit mechanism (transparent textarea stacked over an aria-hidden highlighted pre, per-keystroke debounced re-tokenization, a colored snapshot shown while editing, textarea->pre scroll sync) that diverges from the design's edit/preview toggle and carries avoidable complexity (dual-layer scroll sync, debounce timing, live-vs-snapshot coloring). Change it to a design-matched editing-state toggle. |
| Affected area | src/renderer/src/components/molecules/CodeEditor.tsx (molecule — edit/preview render + click-to-edit handler) and src/renderer/src/components/organisms/BodyEditor.tsx (organism — owns the editing boolean, hosts the separate toggle button that also flips editing). Editing is entered two ways: clicking the preview (CodeEditor) and via the toggle button (BodyEditor). |
| Repro / Current | In the request Body editor raw/JSON mode: the code area always mounts the textarea+pre overlay together; typing re-runs compose() on a BODY_HIGHLIGHT_DEBOUNCE_MS debounce and repaints colored token spans live; scrolling the textarea drives the pre via handleTextareaScroll; switching request tabs (resetKey change) resets inner scroll and invalidates the colored snapshot. |
| Desired | An 'editing' boolean gates the render: editing=true shows a plain textarea (spellCheck off, resize none, native undo/selection/IME, native Tab, white-space:pre with horizontal scroll, no soft-wrap); editing=false shows the highlighted pre (preview). Never both mounted. Transitions: enter edit via (a) clicking the preview — caret MUST be placed at the clicked character position — or (b) the toggle button; leave edit (edit->preview) on BOTH textarea blur AND the toggle button. compose() tokenization runs ONCE on the switch-to-preview transition, not per keystroke. Gutter tracks whichever layer is visible within one scroll container. No colored-during-edit snapshot; no textarea->pre scroll sync. |
| Scope | feature-wide |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| CodeEditor molecule — component to restructure (overlay -> editing-toggle) | src/renderer/src/components/molecules/CodeEditor.tsx:55 | The memo'd component holding both layers; gains an 'editing' prop and conditionally mounts textarea XOR pre. | primary |
| Per-keystroke debounced re-tokenize effect (to remove) | src/renderer/src/components/molecules/CodeEditor.tsx:97 | setTimeout(compose, BODY_HIGHLIGHT_DEBOUNCE_MS) on [value,lang,resetKey]; replaced by a single compose() on edit->preview transition. | primary |
| Textarea->pre scroll-sync handler (to remove) | src/renderer/src/components/molecules/CodeEditor.tsx:106 | handleTextareaScroll copies scrollTop/Left to preRef; obsolete once only one layer is mounted (wired at JSX onScroll line 183). | primary |
| showColored gate — colored-during-edit path (to remove) | src/renderer/src/components/molecules/CodeEditor.tsx:124 | const showColored = colored!==null && colored.snapshot===value; the live-vs-debounced coloring path replaced by a plain textarea in edit + tokenized pre in preview. | primary |
| Overlay CSS — absolute pre behind transparent textarea (to restructure) | src/renderer/src/components/molecules/CodeEditor.css:63 | code-editor-content overflow:hidden with pre position:absolute inset:0 (69) + textarea transparent (92); the toggle keeps line-box+padding but drops the stacked-overlay/scroll-sync layout. | primary |
| Shared line-box unit — must survive | src/renderer/src/components/molecules/CodeEditor.css:9 | --code-line-h: calc(12.5px*1.65)=20.625px, single source bound by gutter row (27), pre (78), textarea (107); both toggle states must keep binding it. | primary |
| BodyEditor consumer — owns editing state + hosts toggle button | src/renderer/src/components/organisms/BodyEditor.tsx:186 | Sole real consumer; passes resetKey/value/lang/onChange/validVars. Gains an editing boolean + toggle button (toolbar right, near lang-pill) and passes editing/onEditingChange to CodeEditor. | primary |
| JSON tokenizer compose lib — reused byte-unchanged | src/renderer/src/lib/jsonTokens.ts:344 | compose() incl. the malformed-JSON degrade-to-plain catch (line ~366) is called ONCE on switch-to-preview; unchanged. | primary |
| canonical-pattern search — caret-at-click placement | (none) | no canonical pattern found project-wide for setSelectionRange/caretPositionFromPoint; click-to-edit caret mapping (click coords -> char offset -> textarea focus+selection) is new code, justified. | primary |
| canonical mount-all hidden-toggle idiom (runner-up frame) | src/renderer/src/components/organisms/BodyEditor.tsx:171 | canonical pattern — reusable: hidden={body.active!==...} keeps all panels mounted and toggles CSS visibility; this is the runner-up frame's reuse candidate (keep both layers mounted). | runner-up |
| CT contract co-reads pre+textarea line-box simultaneously (runner-up falsifier check) | src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx:57 | AC-12/13/21 reads gutter(69)+pre(79)+textarea(89) line-heights in ONE mounted state; this is a measurement convenience, NOT a hard both-mounted requirement (user: only visible layer carries testid), so it does NOT confirm the runner-up 'keep both mounted' frame — the test must be split into edit-state and preview-state reads. | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: The overlay architecture (transparent textarea over an absolute aria-hidden pre, per-keystroke debounced compose, textarea->pre scroll-sync, colored-during-edit snapshot) exists solely to show live syntax highlighting WHILE typing. The design accepts plain-while-editing, so that entire dual-layer machinery is unnecessary: an 'editing' boolean can gate a single visible layer (plain textarea in edit, tokenized pre in preview), tokenizing once on switch-to-preview. State is owned in BodyEditor (entered via preview click with caret-at-click, and via the separate toggle button; left via textarea blur or the button).

**Confidence**: Confirmed

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Keep both textarea and pre mounted at all times and toggle only their CSS visibility (display/hidden), reusing BodyEditor's mount-all/hidden-toggle idiom, instead of conditionally mounting exactly one layer. |
| Falsifier | A hard requirement to preserve textarea scroll/selection state across edit<->preview toggles (only a keep-mounted layer survives it), OR the design/test contract permitting both pre and textarea in the DOM simultaneously. |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| A single CodeEditor with an 'editing' prop that conditionally mounts textarea XOR pre inside the existing 36px+1fr grid is sufficient; gutter/line-box alignment holds because both layers already bind var(--code-line-h) and the gutter column is independent of which content layer is mounted. | Unmounting one layer changes the content column's height or scroll such that the gutter rows drift from the visible layer, or scroll position is lost unexpectedly on toggle. | yes |
| The caret-at-click requirement is the real complexity center (no setSelectionRange/caretPositionFromPoint canonical exists project-wide), needing a click-coordinate -> character-offset mapping before focusing the textarea. | Native textarea focus after mounting already lands the caret at the clicked character without manual coordinate mapping (e.g. by making the textarea itself the click target rather than the pre). | yes |
| Keeping both textarea and pre mounted and toggling only CSS visibility (BodyEditor's hidden-toggle idiom) would satisfy the design equally well. | The explicit requirement 'renders EITHER textarea OR pre, never both' plus 'only the visible layer carries its testid' rules out a both-mounted approach; runner-up disproved. | no |

## Recommended Verify Step

| Sub-field | Value |
|---|---|
| probe | In edit mode, click the preview at a known mid-line character; log textarea.selectionStart after focus. |
| reproduction | Open raw/JSON body in preview state, click a character in the middle of a line to enter edit mode. |
| discriminator | if selectionStart == clicked char offset -> native click-through/mapping suffices (H-B benign); if it lands at 0 or text end -> a manual click-coordinate->char-offset mapping is required before focus (H-B confirmed). |

## Approaches (HOW to change)

### Editing-state conditional-mount toggle (state in BodyEditor)
- **Description**: Add an 'editing' boolean (owned by BodyEditor, passed with an onEditingChange callback to CodeEditor); CodeEditor conditionally MOUNTS the plain textarea XOR the tokenized pre inside the existing 36px+1fr grid, calling compose() once on the edit->preview transition. Delete the scroll-sync handler, the debounced re-tokenize effect, and the colored-during-edit snapshot.
- **Addresses hypothesis**: A, B
- **Does NOT cover**: C
- **Pros**: Matches the design/requirement exactly — renders EITHER layer, never both; Net simplification (KISS): removes overlay stacking, scroll-sync, debounce, and live-vs-snapshot coloring; One compose() per preview switch instead of per keystroke (perf win); only-visible-layer data-testids satisfied by construction
- **Cons**: caret-at-click needs a new click-coordinate->char-offset mapping (no setSelectionRange canonical); CT AC-12/13/21 line-box test must be split into edit-state and preview-state reads; textarea scroll/selection is not preserved across a toggle unless explicitly captured/restored
- **Complexity**: Med

### Keep-both-mounted CSS visibility toggle (runner-up)
- **Description**: Keep both textarea and pre mounted at all times and toggle only their CSS visibility, reusing BodyEditor's hidden-toggle idiom (BodyEditor.tsx:171). compose() could still run once on entering preview.
- **Addresses hypothesis**: C
- **Does NOT cover**: A, B
- **Pros**: Reuses the existing mount-all hidden-toggle canonical at BodyEditor.tsx:171; Preserves textarea scroll/selection across toggles for free; CT AC-12/13/21 line-box co-read keeps passing unchanged
- **Cons**: VIOLATES the explicit requirement: renders EITHER textarea OR pre, NEVER both, and only the visible layer carries its testid; Keeps the dual-layer complexity the change is meant to shed (aria-hidden pre stays in DOM); Does not match the design intent (design expresses a single pre-based preview)
- **Complexity**: Low

**Recommended approach**: Editing-state conditional-mount toggle (state in BodyEditor) — Option 1 wins on the one non-negotiable the brief states outright: at any instant the DOM must contain just one of the two surfaces, and its test hook must be the sole marker attached. Option 2 retains a dormant second surface and is excluded by that rule. Every must-not-regress item is honored — the 20.625 px row metric stays a shared constant in either state, the colouring helper is reused unmodified and fires one time on return to preview, the reset scalar's scroll-and-discard signal is kept, and the empty and form-encoded paths are untouched. Two questions stay unresolved and are logged below: retaining the viewport scroll over a state switch, and where the insertion point lands on entry from a pointer press.

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| §6.3 Search Before Building | Reuse checked: mount-all hidden-toggle canonical at BodyEditor.tsx:171 exists but is rejected (requirement forbids both-mounted); caret-at-click has no setSelectionRange canonical (0 hits project-wide) → new coord->offset mapping justified; compose lib (jsonTokens.ts:344) reused byte-unchanged. |
| §3.6 Simplicity & Reuse (KISS/DRY) | Enables the change: deleting the overlay stack, scroll-sync handler, debounce effect, and colored-during-edit snapshot is a net simplification; compose() reused rather than reimplemented. |
| §6.1 Minimal Changes | Change confined to CodeEditor.tsx, CodeEditor.css, BodyEditor.tsx (+ tests); no ripple — CodeEditor's only non-test consumer is BodyEditor.tsx:186. |
| §2.2 Renderer Tier Organization | Editing state owned by the BodyEditor organism and flows to the CodeEditor molecule via props; preserves CodeEditor's existing 'holds NO tabsStore awareness' contract. |
| §3.4 Testing Requirements | CT AC-12/13/21 co-reads pre+textarea line-box in one mounted state (CodeEditor.ct.tsx:57) and must be split into edit-state + preview-state reads; CT harness is broken locally (verify statically / live-verify per 018 memory). |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Med | 3 source files (CodeEditor.tsx render+state, CodeEditor.css overlay->single-layer, BodyEditor.tsx editing state+toggle button) plus CT/story updates; ~net deletion of overlay/scroll-sync/debounce offset by caret-mapping addition. |
| Risk | Med | Line-box (20.625px) alignment must hold in BOTH toggle states; gutter must track the visible layer in one scroll container; caret-at-click mapping correctness; scroll-position preservation across toggle. |
| Verify cost | Med | Runtime caret-placement probe + edit/preview toggle behavior; CT AC-12/13/21 split; CT harness broken locally so lean on live-verify + static checks. |

## Open Uncertainties

- [NEEDS CLARIFICATION: desired — Confirm the click-to-edit insertion-point behavior (does native focus land the caret at the pressed character, or is a click-coordinate mapping needed) before designing.]
- [NEEDS CLARIFICATION: desired — Confirm whether viewport/scroll offset must be retained across an edit<->preview state switch, or may reset.]

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "The raw-mode CodeEditor uses an overlay edit mechanism (transparent textarea stacked over an aria-hidden highlighted pre, per-keystroke debounced re-tokenization, a colored snapshot shown while editing, textarea->pre scroll sync) that diverges from the design's edit/preview toggle and carries avoidable complexity (dual-layer scroll sync, debounce timing, live-vs-snapshot coloring). Change it to a design-matched editing-state toggle. — An 'editing' boolean gates the render: editing=true shows a plain textarea (spellCheck off, resize none, native undo/selection/IME, native Tab, white-space:pre with horizontal scroll, no soft-wrap); editing=false shows the highlighted pre (preview). Never both mounted. Transitions: enter edit via (a) clicking the preview — caret MUST be placed at the clicked character position — or (b) the toggle button; leave edit (edit->preview) on BOTH textarea blur AND the toggle button. compose() tokenization runs ONCE on the switch-to-preview transition, not per keystroke. Gutter tracks whichever layer is visible within one scroll container. No colored-during-edit snapshot; no textarea->pre scroll sync."

Research reference: research/2026-07-19-change-the-raw-mode.md
Key facts:
- Mode: Enhancement
- Symptom: The raw-mode CodeEditor uses an overlay edit mechanism (transparent textarea stacked over an aria-hidden highlighted pre, per-keystroke debounced re-tokenization, a colored snapshot shown while editing, textarea->pre scroll sync) that diverges from the design's edit/preview toggle and carries avoidable complexity (dual-layer scroll sync, debounce timing, live-vs-snapshot coloring). Change it to a design-matched editing-state toggle.
- Desired: An 'editing' boolean gates the render: editing=true shows a plain textarea (spellCheck off, resize none, native undo/selection/IME, native Tab, white-space:pre with horizontal scroll, no soft-wrap); editing=false shows the highlighted pre (preview). Never both mounted. Transitions: enter edit via (a) clicking the preview — caret MUST be placed at the clicked character position — or (b) the toggle button; leave edit (edit->preview) on BOTH textarea blur AND the toggle button. compose() tokenization runs ONCE on the switch-to-preview transition, not per keystroke. Gutter tracks whichever layer is visible within one scroll container. No colored-during-edit snapshot; no textarea->pre scroll sync.
- Recommended approach: Editing-state conditional-mount toggle (state in BodyEditor)
- Hypothesis addressed: A, B
- Hypotheses NOT covered: C
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
