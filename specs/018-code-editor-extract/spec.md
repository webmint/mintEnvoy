# Spec: code-editor-extract

**Date**: 2026-07-16
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Extract the raw-mode code editor currently inlined in BodyEditor into a standalone, reusable CodeEditor molecule, and single-source its line-box height so gutter numbers stay aligned to code rows at any line count. The JSON syntax highlighting already lives in a reusable lib (jsonTokens.compose()) and is reused unchanged; the extraction relocates only the editor UI (gutter + aria-hidden highlighted pre + transparent textarea overlay) and preserves every existing behavior and the token/grid/gutter fidelity contract.

## 2. Current State

The raw-mode code editor is inline in BodyEditor.tsx:296-327 (a .code-editor grid of gutter divs + a .code-editor-content wrapper holding an aria-hidden <pre> overlay beneath a transparent <textarea> scroll source). Its state lives in the same component: a BODY_HIGHLIGHT_DEBOUNCE_MS=100 trailing debounce runs compose(body.raw.text, body.raw.lang, envVars()) into a colored snapshot, showColored gates token spans vs a plain-degrade span (AC-23 live/debounced split), gutterDivs/tokenSpans are useMemo'd, and scroll-sync mirrors textarea scroll onto the pre via refs. The gutter alignment is ALREADY correct: BodyEditor.css:30 pins .gutter>div to height:calc(12.5px * 1.65)=20.625px (NOT 1.65em), and BodyEditor.ct.tsx already guards it with expect(gutterHeight).toBe('20.625px'). The buggy height:calc(1.65em) form survives only in the design/styles.css:1208 reference. The line-box height is duplicated as literals — .code-editor sets font-size:12.5px (BodyEditor.css:23) and the gutter re-derives 12.5px*1.65 — with no single shared unit, and tokens.css defines none. BodyEditor is rendered by App.tsx:70 (render-prop wiring for the urlencoded slot) inside the RequestSubTabs body sub-tab slot. The JSON tokenizer (jsonTokens.ts compose(), lib/) is already a reusable exported lib; its named second consumer 'response-body' does not exist as a component.

## 3. Desired Behavior

A new reusable CodeEditor lives at src/renderer/src/components/molecules/CodeEditor.tsx (+ CodeEditor.css), self-contained: it owns compose()+debounce+colored state and exposes props value/lang/onChange/validVars. It renders the same three-layer overlay (aria-hidden highlighted pre under a transparent textarea, single scroll container) and gutter, reusing jsonTokens.compose() unchanged. ONE shared line-box unit — a local CSS var --code-line-h scoped to CodeEditor — drives the row height of the textarea, the pre lines, AND the gutter divs (never 1.65em on the gutter), so all three grids share one absolute 20.625px line box and numbers stay aligned at any line count. BodyEditor's raw slot (296-327) is replaced by a <CodeEditor> consumer. Existing data-testids (body-code-editor, body-gutter, body-pre) are preserved so current CTs stay green. All preserved behaviors: mount-all/hidden mode switch, none/urlencoded modes, mode strip, AC-17 malformed degrade, AC-23 live/debounced split, cross-mode retention, XSS-safe escaped-children render, and the token color/grid/gutter fidelity contract (T7a) unchanged.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| CodeEditor (new molecule) | src/renderer/src/components/molecules/CodeEditor.tsx, src/renderer/src/components/molecules/CodeEditor.css | Create new — extracted three-layer overlay editor + gutter; owns compose()+debounce; --code-line-h shared line-box var drives textarea/pre/gutter rows |
| BodyEditor (consumer) | src/renderer/src/components/organisms/BodyEditor.tsx, src/renderer/src/components/organisms/BodyEditor.css | Raw slot (296-327) + editor state/CSS removed; renders <CodeEditor> instead; body-* testids preserved on CodeEditor |
| CodeEditor tests | src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx | Create new — relocate + extend AC-23 guard to assert textarea/pre/gutter row heights all equal 20.625px; fidelity via computed-style channel |
| BodyEditor tests (adjust) | src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx, src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx | Fidelity/alignment ACs move to CodeEditor CT; BodyEditor CT retains integration + body-* testid assertions |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The BodyEditor component shall no longer declare the inline three-layer code-area overlay markup.
  > Verification: ! grep -q 'code-editor-content' src/renderer/src/components/organisms/BodyEditor.tsx
- [x] **AC-9**: The renderer shall provide a reusable CodeEditor component module in the molecules tier.
  > Verification: test -f src/renderer/src/components/molecules/CodeEditor.tsx
- [x] **AC-10**: The renderer shall provide a CodeEditor stylesheet co-located with the component.
  > Verification: test -f src/renderer/src/components/molecules/CodeEditor.css

### 5.2 Behavior preservation

- [x] **AC-2**: IF the raw text is not valid JSON, THEN the system shall render it as a single plain segment without throwing.
- [x] **AC-3**: WHEN a {{var}} placeholder appears inside a JSON string or key, the system shall let the variable overlay win the tie-break.
- [x] **AC-4**: WHILE an inactive body-mode panel is hidden, the system shall preserve that panel's DOM-local scroll and caret state.
- [x] **AC-5**: The system shall insert all highlighted token text as escaped children and never via innerHTML.
- [x] **AC-6**: WHEN the active request tab switches, the system shall reset the code-area scroll offset and invalidate the colored snapshot.
- [x] **AC-7**: WHILE the none or urlencoded body mode is active, the system shall behave identically to the pre-extraction BodyEditor.
- [x] **AC-8**: The system shall preserve the body-code-editor, body-gutter, and body-pre data-testids on the extracted editor.
- [x] **AC-11**: WHEN a user edits raw JSON in the CodeEditor, the system shall produce syntax highlighting by reusing the existing jsonTokens compose lib unchanged.

### 5.3 Behavior change

- [x] **AC-12**: The CodeEditor shall define one shared line-box unit that sets the row height of the textarea, the highlighted pre lines, and the gutter divs.
- [x] **AC-13**: IF a consumer overrides the code font metrics, THEN the gutter, pre, and textarea rows shall remain equal in height.
- [x] **AC-14**: WHEN a consumer mounts the CodeEditor with value, lang, onChange, and validVars props, the system shall render a self-contained editor that owns its own compose debounce and colored state.
- [x] **AC-15**: The CodeEditor shall reside in the molecules tier so an organism can consume it without a sibling-organism import.
- [x] **AC-16**: WHILE the live-renderer computed-style channel is unavailable, the system shall mark fidelity assertions UNVERIFIED rather than PASS.
- [x] **AC-17**: The system shall keep the tk-* token colors, the code-editor grid, and the gutter geometry unchanged from the T7a fidelity contract.
- [x] **AC-21**: The gutter, pre, and textarea rows shall each compute to the same absolute line-box height derived from the code font-size times its line-height.
  > Verification: grep -q 'code-line-h' src/renderer/src/components/molecules/CodeEditor.css

### 5.4 CI / pipeline

N/A — No CI/pipeline change — pure renderer component extraction; existing test jobs cover it

### 5.5 Hooks / gates

N/A — No hooks/gates change — no new git hooks, pre-commit, or CI gates introduced

### 5.6 Documentation

- [x] **AC-18**: The documentation shall describe CodeEditor as a reusable molecule and BodyEditor as its consumer.

### 5.7 Hygiene

- [x] **AC-19**: The renderer shall pass type-check and lint after the extraction.
  > Verification: npm run typecheck && eslint --cache src/renderer/src/components/molecules/CodeEditor.tsx
- [x] **AC-20**: The CodeEditor stylesheet shall not use an em-based row height on the gutter.
  > Verification: ! grep -q '1.65em' src/renderer/src/components/molecules/CodeEditor.css

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Building the response-body / JSON response viewer as a second CodeEditor consumer — that component does not exist yet — F-2026-07-16-fix-gutter-line-misalignment-1
- NOT included: Fixing the stale height:calc(1.65em) rule in design/styles.css — it is the design reference mockup, not shipped app code — F-styles-3
- NOT included: Promoting the line-box height to a global design token in design/tokens.json — the metric is component-internal; a local --code-line-h var is used instead — F-tokens-2
- NOT included: Resolving {{var}} values — the tokeniser stays display-only (var overlay, no resolution)

## 7. Technical Constraints

- Must follow: Search before building (Key Rules #12)
- Must follow: SOLID, DRY, KISS (Key Rules #11)
- Must follow: Minimal changes / never modify outside scope (Key Rules #3, Never #5)
- Must follow: test-utils/fidelityAssert helpers are test-only and must not be imported by production renderer code; CodeEditor CT consumes them, CodeEditor.tsx does not
- Must not break: The compose() JSON.parse pre-validation is the malformed-JSON degrade detector — it must not be removed or bypassed during extraction
- Must follow constitution §2.2: Organisms compose molecules/atoms and never import a sibling organism; CodeEditor lives in molecules so BodyEditor (and a future response-body organism) may consume it
- Must follow constitution §3.6: Simplicity & Reuse: reuse the existing jsonTokens compose lib rather than re-implement a tokenizer for the extracted editor
- Must follow constitution §2.3: All intra-renderer imports use the @renderer alias; the CodeEditor import in BodyEditor and its lib imports must follow it

## 8. Open Questions

- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Overlay pixel-grid alignment (textarea over pre) is fidelity-sensitive; the shared line-box refactor could shift row height if the var value differs from 20.625px. Mount-all hidden-panel scroll preservation and the AC-23 debounce split must survive the move | Med | Med | tbd via /plan |
| Overlay pixel-grid desync (transparent textarea over highlighted pre) during the move | Med | High | Preserve identical padding/box-sizing/font on textarea+pre; assert row-height equality + tk-* colors via the live-renderer computed-style channel (fidelityAssert) |
| CodeEditor CT green-but-wrong because the fixture omits the full styling context | Med | Med | Reproduce tokens.css import + data-mstyle + production className scope in the CT fixture (alias-trap lesson) |
| Static/CT fidelity reports CLEAN yet layout drift persists | Low | Med | DOM-verify gutter, pre, AND textarea computed row heights are all equal, not just the gutter guard |
