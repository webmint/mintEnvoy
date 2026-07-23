# Spec: code-editor-toggle

**Date**: 2026-07-19
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Replace the raw-mode CodeEditor's overlay edit mechanism with a design-matched edit/preview toggle. An 'editing' boolean (owned by BodyEditor) gates the render so the code area shows EITHER a plain textarea (editing) OR the highlighted pre (preview) — never both mounted — and the JSON tokenizer runs once on the switch-to-preview transition instead of on every keystroke. A visible toggle button plus click-to-edit (caret placed at the clicked character) drive the state, shedding the transparent-textarea/absolute-pre stack, the textarea->pre scroll sync, the per-keystroke debounce, and the colored-during-edit snapshot.

## 2. Current State

The raw-mode code area is the CodeEditor molecule (src/renderer/src/components/molecules/CodeEditor.tsx:55), consumed only by BodyEditor (src/renderer/src/components/organisms/BodyEditor.tsx:186; all other references are test fixtures). It always mounts BOTH layers together: an aria-hidden highlighted <pre> (CodeEditor.tsx:170-181) absolutely positioned behind a transparent <textarea> scroll source (CodeEditor.tsx:183-190; CodeEditor.css:63-110). A 100ms trailing debounce re-runs compose() into a colored snapshot on every [value,lang,resetKey] change (CodeEditor.tsx:95-101); showColored (CodeEditor.tsx:124) gates token spans vs a plain-degrade span; handleTextareaScroll (CodeEditor.tsx:106) mirrors textarea scroll onto the pre via ref. The shared line-box --code-line-h: calc(12.5px*1.65)=20.625px (CodeEditor.css:9) binds the gutter row (CodeEditor.css:27), pre (CodeEditor.css:78), and textarea (CodeEditor.css:107). compose() (src/renderer/src/lib/jsonTokens.ts:344) uses a JSON.parse pre-validation as the malformed-JSON degrade-to-plain detector (jsonTokens.ts:363-366). CodeEditor props are value/lang/onChange/validVars/resetKey (CodeEditor.tsx:31-45); resetKey (=activeTabId) resets scroll and invalidates the snapshot on tab switch (CodeEditor.tsx:75-88). BodyEditor's toolbar right slot currently holds only the lang-pill (BodyEditor.tsx). Feature 018 established this editor; its CT co-reads pre+textarea line-box in one mounted state (CodeEditor.ct.tsx:57).

## 3. Desired Behavior

The CodeEditor accepts an 'editing' boolean prop (plus onEditingChange) owned by BodyEditor. WHILE editing=false the code area renders ONLY the highlighted pre (preview); WHILE editing=true it renders ONLY a plain textarea (spellCheck off, resize none, native undo/selection/IME, native Tab key, white-space:pre with horizontal scroll and no soft-wrap). The two layers are never mounted simultaneously; only the visible layer carries its data-testid (body-pre in preview, the textarea in edit). Edit is entered by (a) clicking the preview — caret placed at the clicked character, clamped to the nearest character for out-of-bounds clicks — or (b) activating the toggle button, or (c) focusing the preview region and pressing Enter/Space. Edit is left (edit->preview) on textarea blur OR toggle-button activation. compose() runs exactly once on each switch-to-preview transition, never per keystroke. The gutter tracks whichever layer is visible within one scroll container and all rows stay on the 20.625px --code-line-h line-box. The code area first mounts in preview, and a request-tab switch (resetKey change) resets it to preview. A visible toggle button (edit/preview) sits in the BodyEditor toolbar. The debounced re-tokenize effect, the colored-during-edit snapshot path, and the textarea->pre scroll-sync handler are removed. jsonTokens.compose() (incl. its malformed-JSON degrade-to-plain) is reused byte-unchanged; none/urlencoded body modes are unchanged.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| CodeEditor (molecule) | src/renderer/src/components/molecules/CodeEditor.tsx, src/renderer/src/components/molecules/CodeEditor.css | Add editing/onEditingChange props; conditionally mount textarea XOR pre; tokenize once on switch-to-preview; add click-to-edit (caret-at-click, clamped) + preview focus/Enter entry; remove scroll-sync handler, debounced re-tokenize effect, colored-during-edit snapshot; CSS drops absolute-overlay stacking, keeps --code-line-h line-box + horizontal-scroll on the single visible layer |
| BodyEditor (organism, consumer + state owner) | src/renderer/src/components/organisms/BodyEditor.tsx, src/renderer/src/components/organisms/BodyEditor.css | Own the editing boolean (default preview; reset to preview on activeTabId change); render the edit/preview toggle button in the toolbar and wire it + pass editing/onEditingChange to CodeEditor |
| CodeEditor tests | src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx, src/renderer/src/components/molecules/__tests__/CodeEditor.stories.tsx | Split the AC-12/13/21 line-box co-read into edit-state and preview-state reads; add toggle/click-to-edit/caret/entry coverage; drop the live/debounced (018 AC-23) colored-during-edit assertions |
| BodyEditor tests | src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx, src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx | Cover the toggle button + editing-state ownership + reset-to-preview-on-tab-switch; adjust testid assertions to only-visible-layer |
| Docs | docs/architecture.md | Update the CodeEditor molecule description from three-layer overlay to edit/preview toggle (editing prop, tokenize-on-preview) |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The CodeEditor shall not declare a textarea-to-pre scroll-synchronisation handler.
  > Verification: ! grep -q 'handleTextareaScroll' src/renderer/src/components/molecules/CodeEditor.tsx
- [x] **AC-2**: The CodeEditor shall not declare a debounced colored-snapshot state for the editing surface.
  > Verification: ! grep -q 'showColored' src/renderer/src/components/molecules/CodeEditor.tsx
- [x] **AC-3**: The BodyEditor shall provide an edit/preview toggle control carrying a stable data-testid.
  > Verification: grep -q 'body-edit-toggle' src/renderer/src/components/organisms/BodyEditor.tsx

### 5.2 Behavior preservation

- [x] **AC-4**: IF the raw text is not valid JSON, THEN the CodeEditor shall render it as a single plain segment without throwing.
- [x] **AC-5**: The CodeEditor shall reuse the existing jsonTokens compose library unchanged for syntax highlighting.
- [x] **AC-6**: WHEN the active request tab switches, the CodeEditor shall reset the code-area scroll offset and return to preview.
- [x] **AC-7**: WHILE the none or urlencoded body mode is active, the BodyEditor shall behave identically to its pre-change behavior.
- [x] **AC-8**: The CodeEditor shall insert all highlighted token text as escaped children and never via innerHTML.
- [x] **AC-9**: The CodeEditor shall keep the gutter, the preview, and the edit textarea rows on one shared line-box height in both states.

### 5.3 Behavior change

- [x] **AC-10**: WHILE editing is false the CodeEditor shall render only the preview pre, and while editing is true it shall render only the plain textarea, never mounting both together.
- [x] **AC-11**: The CodeEditor shall expose only the currently visible layer data-testid, namely body-pre in preview and the textarea in edit.
- [x] **AC-12**: WHEN the user clicks the preview, the CodeEditor shall enter edit mode and place the caret at the clicked character.
- [x] **AC-13**: IF a preview click lands past the end of a line or below the text, THEN the CodeEditor shall clamp the caret to the nearest character.
- [x] **AC-14**: WHEN the CodeEditor switches to preview, the system shall run the tokenizer exactly once for that transition rather than per keystroke.
- [x] **AC-15**: WHILE editing is true, the textarea shall disable spellcheck, disable resize, keep the Tab key native, and wrap with white-space pre giving horizontal scroll and no soft-wrap.
- [x] **AC-16**: WHEN the textarea loses focus or the toggle control is activated, the CodeEditor shall leave edit mode and return to preview.
- [x] **AC-17**: WHEN a request raw code area first mounts, the CodeEditor shall start in preview.
- [x] **AC-18**: WHERE the user operates by keyboard, the preview shall be focusable and Enter or Space shall enter edit mode.
- [x] **AC-19**: WHILE either layer is visible, the gutter shall track that layer within one scroll container.

### 5.4 CI / pipeline

N/A — No CI/pipeline change — pure renderer component change covered by existing vitest + playwright CT jobs

### 5.5 Hooks / gates

N/A — No new git hooks, pre-commit, or CI gates introduced

### 5.6 Documentation

- [x] **AC-20**: The documentation shall describe the CodeEditor as an edit/preview toggle whose highlighting runs on switch-to-preview.

### 5.7 Hygiene

- [x] **AC-21**: The renderer shall pass type-check and lint after the change.
  > Verification: npm run typecheck && eslint --cache src/renderer/src/components/molecules/CodeEditor.tsx
- [x] **AC-22**: The CodeEditor stylesheet shall not use an em-based gutter row height.
  > Verification: ! grep -q '1.65em' src/renderer/src/components/molecules/CodeEditor.css
- [x] **AC-23**: The CodeEditor component shall not use inline element styles for the toggle states.
  > Verification: ! grep -q 'style={{' src/renderer/src/components/molecules/CodeEditor.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Any third-party editor engine (CodeMirror, Monaco, etc.) — the edit surface stays a native textarea — F-2026-07-19-change-the-raw-mode-6
- NOT included: Auto-indent, bracket/quote auto-close, multi-cursor, find/replace, and paste-and-format
- NOT included: Syntax highlighting while typing — plain-while-editing is the accepted tradeoff (colored only in preview) — F-spec-2
- NOT included: Changing the jsonTokens compose library or its token vocabulary — reused byte-unchanged — F-constitution-2
- NOT included: Any other CodeEditor consumer (response-body viewer, GraphQL variables) — none exists; BodyEditor is the sole consumer

## 7. Technical Constraints

- Must follow: §6.3 Search Before Building
- Must follow: §3.6 Simplicity & Reuse (KISS/DRY)
- Must follow: §6.1 Minimal Changes
- Must follow: §2.2 Renderer Tier Organization
- Must follow: §3.4 Testing Requirements
- Must follow: Editing is ephemeral UI state owned by BodyEditor local component state, never a tabsStore domain field (raw text still round-trips through updateActiveSpec unchanged)
- Must follow: Commits follow Conventional Commits and include the Co-Authored-By: Claude attribution trailer
- Must not break: compose()'s JSON.parse pre-validation is the malformed-JSON degrade-to-plain detector — it must not be removed or bypassed

## 8. Open Questions

- **Q-1**: Caret-at-click implementation: whether native textarea focus already lands the caret at the clicked character, or a click-coordinate to character-offset mapping is required (research runtime-probe pinned; either satisfies AC-12).
- **Q-2**: Whether textarea scroll/selection must be retained across an edit->preview->edit round trip within the same tab, or may reset (research open uncertainty).
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior — the overlay behaviors to change (per-keystroke debounce, scroll-sync, colored-during-edit snapshot) are determined by the settled requirement (remove them; plain-while-editing accepted tradeoff)
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes — the two breaks (018 AC-23 live/debounced coloring removed; only-visible-layer testid contract) are user-accepted in research; no downstream non-test consumer of CodeEditor exists besides BodyEditor
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration — pure renderer component change; no migration/config/infra surface

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Line-box (20.625px) alignment must hold in BOTH toggle states; gutter must track the visible layer in one scroll container; caret-at-click mapping correctness; scroll-position preservation across toggle. | Med | Med | tbd via /plan |
| Conditional-mount does not preserve textarea scroll/selection across a toggle; display:none/unmount loses scrollTop and focus() can re-clobber it | Med | Med | Decide scroll retention in /plan (Q-2); if required, capture scrollTop/selection at switch and restore after mount with focus({preventScroll:true}) |
| CodeEditor/BodyEditor Playwright CT cannot mount in the local harness (pre-existing break) | High | Med | Verify statically + live-verify per 018; leave test:ct Done-When UNVERIFIED rather than burning repair rounds; reproduce tokens.css import + data-mstyle + production className scope in fixtures |
| CT AC-12/13/21 line-box co-read of pre+textarea in one state breaks once only one layer mounts at a time | High | Low | Split the line-box assertion into an edit-state read (textarea) and a preview-state read (pre); both must equal the shared line-box height |
| Line-box row height could drift between the edit and preview states if the single mounted layer inherits different metrics | Med | Med | Both states bind the same --code-line-h var + identical font/padding/box-sizing; DOM-verify equal row heights per state |
