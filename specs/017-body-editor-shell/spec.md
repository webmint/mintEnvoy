# Spec: body-editor-shell

**Date**: 2026-07-10
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Add a request-body editor shell — the BodyEditor organism — to the request panel's Body sub-tab. A 6-option body-type radio selector (none, form-data, x-www-form-urlencoded, raw, binary, GraphQL) drives a mode switch with three live modes (none = empty region; raw = a JSON-default functional lang-pill toolbar over a hand-rolled textarea/<pre>/gutter code area with two-pass {{var}}+JSON highlighting; x-www-form-urlencoded = the existing KVTable). Body becomes a store-owned discriminated union on type in RequestSpec, and design/reference.html §8 visual fidelity is mandatory.

## 2. Current State

The Body sub-tab is not yet editable. RequestSubTabs (src/renderer/src/components/organisms/RequestSubTabs.tsx) mounts Params and Headers via named slot props (:76-82) but has no body slot — the Body tabpanel falls through to the shared 'Panel not yet available' emptyState. RequestSpec.body is currently a FLAT descriptor { lang: string; type: string; text: string } (src/renderer/src/lib/requestSpec.ts:82), seeded blank as { lang: '', type: '', text: '' } by makeBlankRequest (:124, seed at :131); .body has zero readers beyond that seed. Reuse seams already exist and were fit-checked: tabsStore.updateActiveSpec(patch: Partial<RequestSpec>) shallow-merges with an equality no-op guard (tabsStore.ts:160 signature and :340 body); varTokens.tokenizeVars returns VarSegment[] (plain/var) display-only; KVTable emits Row[] (Row at requestSpec.ts:32); RequestSubTabs uses the house mount-all + hidden-toggle panel pattern. No BodyEditor, radio-group, lang-pill, code-editor, or JSON syntax tokenizer exists yet. design/reference.html + design/styles.css section 8 pin the DOM classes (body-toolbar, body-radio with dot, lang-pill, code-editor grid 36px 1fr, gutter, pre) and every value, including the tk-star token vocabulary.

## 3. Desired Behavior

The Body sub-tab shall render the BodyEditor organism. The body-type radio selector shall expose six options and default to none; selecting a type shall switch the visible mode panel while keeping all panels mounted (hidden-toggled). Raw mode shall show a functional lang-pill (JSON default; XML/HTML/Text selectable) above a hand-rolled code area whose gutter line-count and pre line-count stay equal and share one scrollTop; the code area shall apply a two-pass highlight — a {{var}} pass (var(--accent)) plus a JSON syntax pass (.tk-key/str/num/bool/null/punc) — with the var pass winning inside JSON strings. Non-JSON raw languages shall receive only the .tk-var pass (no structural highlighting). x-www-form-urlencoded mode shall mount KVTable emitting Row[]. form-data, binary, and GraphQL shall render a shared neutral 'Panel not yet available' placeholder. Body shall be a discriminated union on type (lang/text only on raw; Row[] on urlencoded/form-data), written to the active tab's RequestSpec via updateActiveSpec({ body }); the union type shall reach BodyEditor via a tabsStore re-export, never a direct requestSpec import. Switching body-type away and back shall preserve each mode's value from the spec. Malformed JSON shall degrade to plain var(--text) with no throw and no error UI. The body-type selector shall be an ARIA radiogroup (role=radiogroup/role=radio, aria-checked, arrow-key roving focus) over the design's div+dot visuals. §8 fidelity shall be asserted from a LIVE renderer computed-style channel; a CT assertComputedStyle/assertResolvesToToken helper + live-renderer channel is built in this feature so those assertions run.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| varTokens var pass | src/renderer/src/lib/varTokens.ts | reuse tokenizeVars for raw code-area {{var}} highlighting; language-agnostic; validVars-∅ selector applied by caller |
| KVTable urlencoded | src/renderer/src/components/organisms/KVTable.tsx | mount for x-www-form-urlencoded mode; emits Row[] |
| RequestSubTabs body slot | src/renderer/src/components/organisms/RequestSubTabs.tsx | host; add a body slot prop + wire the body key (currently falls to emptyState L241); BodyEditor mounts here; deferred-mode placeholder mirrors this empty-state |
| tabsStore updateActiveSpec | src/renderer/src/lib/tabsStore.ts | body write path: updateActiveSpec({body}) shallow-merge; no direct requestSpec import from BodyEditor |
| requestSpec Body union migration | src/renderer/src/lib/requestSpec.ts | migrate body flat {lang,type,text} (L82) -> discriminated union; update makeBlankRequest seed (L131); Row (L32) reused for urlencoded/form-data rows |
| BodyEditor organism (new) | src/renderer/src/components/organisms | greenfield BodyEditor.tsx: body-type radio + mode switch + code-editor/gutter/pre + lang-pill; no existing BodyEditor/radio-group/lang-pill/code-editor found |
| syntax tokenizer (new lib) | src/renderer/src/lib | greenfield JSON syntax tokenizer module (.tk-key/str/num/bool/null/punc); lib never imports components; no existing syntax tokenizer found |
| internal:src/renderer/src/lib/varTokens.ts | src/renderer/src/lib/varTokens.ts | internal — existing {{variable}} tokeniser (var pass); pure, renderer-only, returns VarSegment[] plain/var; directly reusable for the raw code-area var pass |
| internal:src/renderer/src/components/organisms/KVTable.tsx | src/renderer/src/components/organisms/KVTable.tsx | internal — existing key-value editor emitting Row[]; reuse verbatim for x-www-form-urlencoded mode |
| internal:src/renderer/src/components/organisms/RequestSubTabs.tsx | src/renderer/src/components/organisms/RequestSubTabs.tsx | internal — host sub-tab shell; mount-all + hidden-toggle; shared 'Panel not yet available' empty-state (L241) — the pattern the deferred body-modes placeholder mirrors; BodyEditor mounts in the body slot |
| internal:src/renderer/src/lib/tabsStore.ts | src/renderer/src/lib/tabsStore.ts | internal — store write seam (Partial<RequestSpec> shallow-merge + dirty + equality no-op); BodyEditor emits body via updateActiveSpec({body}) |
| internal:src/renderer/src/lib/requestSpec.ts | src/renderer/src/lib/requestSpec.ts | internal — Body type home; CURRENTLY FLAT {lang,type,text} (L82), NOT a union; Row type (L32) is the actual KV row shape (user called it KVRow). Union migration lands here |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The JSON syntax tokenizer shall exist as a renderer-pure module under src/renderer/src/lib.
  > Verification: ls src/renderer/src/lib | grep -Eiq 'token|syntax'
- [x] **AC-2**: The CT fidelity assertion helpers assertComputedStyle and assertResolvesToToken shall exist in the renderer test utilities.
  > Verification: grep -rlE 'assertComputedStyle|assertResolvesToToken' src/renderer/src
- [x] **AC-5**: The BodyEditor organism shall exist as a component file under src/renderer/src/components/organisms.
  > Verification: test -f src/renderer/src/components/organisms/BodyEditor.tsx

### 5.2 Behavior preservation

- [x] **AC-3**: WHILE a sub-tab other than Body is active, the RequestSubTabs shell shall render that sub-tab's content unchanged.
- [x] **AC-4**: The makeBlankRequest factory shall return a RequestSpec whose body is a valid discriminated-union value of type none.

### 5.3 Behavior change

- [x] **AC-6**: WHEN the user selects a body-type radio option, the BodyEditor shall switch the visible mode panel while keeping all mode panels mounted.
- [x] **AC-7**: The body-type selector shall present six options — none, form-data, x-www-form-urlencoded, raw, binary, and GraphQL — and shall default to none.
- [x] **AC-8**: WHILE raw mode is active, the BodyEditor shall render a functional lang-pill that defaults to JSON and lets the user select XML, HTML, or Text above the code area.
- [x] **AC-9**: WHILE the raw language is JSON, the code area shall apply a two-pass highlight of a variable pass rendered as var(--accent) and a JSON syntax pass, with the variable pass winning inside JSON strings.
- [x] **AC-10**: WHILE the raw language is not JSON, the code area shall apply only the variable pass and no structural syntax highlighting.
- [x] **AC-11**: WHILE x-www-form-urlencoded mode is active, the BodyEditor shall mount the KVTable editor emitting Row arrays.
- [x] **AC-12**: WHEN the body value changes, the BodyEditor shall write the discriminated-union body to the active tab RequestSpec via updateActiveSpec with a body patch.
- [x] **AC-13**: The discriminated-union Body type shall reach the BodyEditor through a tabsStore re-export rather than a direct requestSpec import.
- [x] **AC-14**: WHEN the user switches the body-type away and back, the BodyEditor shall restore each mode's prior value from the RequestSpec.
- [x] **AC-15**: WHILE the selected body type is form-data or binary or GraphQL, the BodyEditor shall render the shared neutral Panel not yet available placeholder.
- [x] **AC-16**: WHILE the raw text is empty, the code area shall render an empty editor with zero highlight tokens and shall not throw.
- [x] **AC-17**: IF the raw JSON text is malformed, THEN the code area shall degrade to plain var(--text) text without throwing and without any error UI.
- [x] **AC-18**: The body-type selector shall expose ARIA radiogroup semantics of role radiogroup, role radio, aria-checked, and arrow-key roving focus over the design div-and-dot visuals.
- [x] **AC-19**: IF the live-renderer computed-style channel is unavailable, THEN the section 8 fidelity acceptance criteria shall be reported UNVERIFIED and never PASS.
- [x] **AC-20**: WHILE data-theme is light and the live-renderer computed-style channel is available, the code area shall compute the tk-key color as #0369a1 and tk-str as #15803d and tk-num as #b45309 and tk-bool as #be185d.
- [x] **AC-21**: WHILE data-theme is dark and the live-renderer computed-style channel is available, the code area shall compute the tk-key color as #7dd3fc and tk-str as #86efac and tk-num as #fcd34d and tk-bool as #f0abfc.
- [x] **AC-22**: The code area shall resolve the tk-null token to var(--text-faint) and tk-punc to var(--text-muted) and tk-var to var(--accent) in both themes.
- [x] **AC-23**: WHILE the live-renderer computed-style channel is available, the BodyEditor shall keep the gutter row height equal to the computed line-height of the pre element and the gutter node count equal to the rendered line count and a single shared scrollTop.
- [x] **AC-24**: The code area shall match design reference section 8 as a code-editor grid of 36px and 1fr with a gutter column and a pre column bound to the generated design tokens.

### 5.4 CI / pipeline

N/A — Renderer-only feature; no CI workflow, pipeline, or build-config changes.

### 5.5 Hooks / gates

- [x] **AC-25**: WHERE the feature has a design/reference.html, the design-token provenance check and the runtime design-auditor gate shall apply to the BodyEditor.

### 5.6 Documentation

- [x] **AC-26**: The BodyEditor organism and the JSON syntax tokenizer and the Body discriminated union shall each carry documentation comments describing their contract.

### 5.7 Hygiene

- [x] **AC-27**: The changed renderer files shall contain no debug logging calls or debugger statements.
  > Verification: test -z "$(grep -rnE 'console\.log|debugger' src/renderer/src/components/organisms/BodyEditor.tsx 2>/dev/null)"
- [x] **AC-28**: The BodyEditor and JSON tokenizer shall pass type-check and lint before task completion.
  > Verification: npm run typecheck && eslint --cache src/renderer/src
- [x] **AC-29**: The renderer body-editor code shall use class-based styling with no inline styles and shall import no Node or Electron APIs.
  > Verification: ! grep -rnE 'style=\{\{|from .electron.|require\(.electron.\)' src/renderer/src/components/organisms/BodyEditor.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Send-time concerns — body serialization, percent-encoding, Content-Type derivation, and variable VALUE resolution — are owned by the send path, not the editor.
- NOT included: Structure-aware syntax highlighting for XML, HTML, and Text; only JSON receives structural highlighting while all raw languages receive the {{var}} pass. — F-2026-07-10-request-body-editor-shell-with-a-body-type-selector-plus-8
- NOT included: Third-party code editors (Monaco / CodeMirror 6); the editor is hand-rolled to keep the design-anchor computed-style diff valid. CodeMirror 6 is a documented future fallback only. — F-2026-07-10-request-body-editor-shell-with-a-body-type-selector-plus-7
- NOT included: Editor niceties — multi-cursor, folding, autocomplete, bracket matching, format/beautify, and JSON validation/lint UI.
- NOT included: form-data, binary, and GraphQL mode implementations — placeholder slot only in this feature.
- NOT included: Response-body rendering; a separate task that will reuse the same tokenizer lib and .tk-* vocabulary.

## 7. Technical Constraints

- Must satisfy NFR (see discovery report constraints dimension): CONFIRMED — Fidelity (mandatory): semantic classes bound to tokens.css; .tk-key/str/num/bool assert LITERAL per-theme hex (:root + [data-theme=dark]); .tk-null/punc/var assert resolves-to-token; gutter<->line alignment (.gutter>div height calc(1.65em), one div/line). No cruft: no data-om-*, __OmT, inline-style, tweaks-panel residue. Layering: lib/ never imports components; Body union import type-only; validVars/highlight spans render-only, never persisted; no wire-format/Content-Type logic in editor (send-time). ADDED (reference silent on edit mechanism -> B4 underspecified-deviate): 1) Editable surface = real <textarea>, highlight <pre> aria-hidden presentation-only, NO contenteditable (native caret + SR; IME/composition safety; caret<->highlight alignment). 2) Three-layer alignment invariant (supersedes gutter<->line): textarea+pre+gutter share identical mono metrics + line-height 1.65 + padding + tab-size; single scroll source (pre+gutter track textarea scrollTop/Left). 3) Highlight perf ceiling (behavior not mechanism): above size/line threshold syntax pass SKIPPED -> pre degrades to plain var(--text); no full-body synchronous tokenise per keystroke (debounce/off-keystroke); bounded gutter node count; threshold = plan-level tunable w/ stated default, not a magic constant. 4) Max body = routing not hard cap: no artificial raw-text limit; large payloads via binary fileRef, never raw buffer. 5) XSS-safe render: tokens as escaped JSX children ONLY; never dangerouslySetInnerHTML/innerHTML of raw body text. 6) a11y on div controls (.body-radio, .lang-pill are divs) DEVIATE-from-underspecified (B1/B4): role=radiogroup/radio + aria-checked + arrow-key nav + visible focus ring; lang-pill = button semantics + aria.
- Must satisfy NFR (non-goal boundary from scoping session): Out of scope: CONFIRMED out: form-data/binary/graphql mode implementations — deferred-mode placeholder slot only (mirrors functional_scope: none/raw/urlencoded live now). Send-time concerns — serialization, percent-encoding, Content-Type derivation, variable VALUE resolution: T10a/main not editor. Third-party editors — Monaco rejected; CodeMirror 6 documented future fallback, out. Editor niceties — multi-cursor, folding, autocomplete, bracket matching. .tk-var.missing strikethrough — default MATCH neutral .tk-var only; missing-state = opt-in DEVIATE, out. DECISION real syntax tokenizer for XML/HTML/Text = OUT (design-grounded: styles.css ships only JSON token vocab .tk-key/str/num/bool/null/punc; no .tk-tag/attr/comment class exists -> a real XML/HTML tokenizer invents classes the fidelity contract cannot check). JSON syntax tokenizer IN; XML/HTML/Text render plain (var(--text)). CARVE (NOT out): var pass .tk-var for {{var}} applies to ALL raw langs incl text/XML/HTML — {{var}} highlighting is language-agnostic (varTokens), not JSON-specific; non_goal is structure-aware coloring for non-JSON, not any highlighting. ADDITIONAL out: Response-body rendering (§11 response pane = separate task, reuses same .tk-*/tokenizer lib but T7 = request-body only). Format/Beautify/prettify (no control in export; .body-toolbar .right holds lang-pill only). Gutter interactivity (presentational, line-numbers only; no click-to-select/breakpoint). JSON validation UI (no error markers/lint squiggles/invalid-JSON UI; malformed input degrades to plain, never throws).
- Must follow constitution §constitution.md: §2.2 Renderer Tier Organization (organisms flow downward only; no sibling-tier imports)
- Must follow constitution §constitution.md: §5.2 Domain Invariants (requestSpec stays a pure data module — never imported by components)
- Must follow constitution §constitution.md: §3.1 Type Safety (strict mode, no any, narrow don't cast)
- Must follow constitution §constitution.md: §2.1/§2.3 Renderer purity (no Node/Electron; @renderer alias)
- Must follow constitution §constitution.md: §4 Prefer design tokens over literal style values

## 8. Open Questions

- **hq-1**: user-supplied mechanism/placement guesses (confirm via Phase 2 fit-check): reuse existing key-value editor component + its tokenise/validVars-∅-selector seam; emit body via store to active-tab RequestSpec (no direct requestSpec import); neutral 'not yet available' placeholder mirrors existing sub-tab empty-slot pattern  [blocking]
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Spike the three-layer alignment (textarea/<pre>/gutter) + scroll-sync in BOTH themes before building any mode — proves the hardest fidelity invariant early | Med | Med | address before implementation; see derisk plan |
| Prototype the CT assertComputedStyle / assertResolvesToToken helper against the .tk-* hex table + live-renderer channel; this is the OPEN dev-lane dependency behind the anti-false-green gate | Med | Med | address before implementation; see derisk plan |
| Do the flat->union body migration first and let the type-checker enumerate every narrowing site — confirms the zero-consumer / Low-blast-radius assumption empirically | Med | Med | address before implementation; see derisk plan |
| Write a {{var}}-inside-JSON-string fixture and pin the var-pass-wins tie-break before wiring the two-pass tokenizer | Med | Med | address before implementation; see derisk plan |
| add body slot prop to RequestSubTabs | High | High | must resolve before implementation |
| change RequestSpec.body to union | High | High | must resolve before implementation |
| update makeBlankRequest seed to {type:none} | High | High | must resolve before implementation |
