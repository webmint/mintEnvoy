# Discovery: Request-body editor shell with a body-type selector plus three text-only modes (none, raw with {{variable}}-highlighted code area defaulting to JSON, and x-www-form-urlencoded via the existing key-value editor), emitting {type,lang,text} to the active tab RequestSpec through the store, with mandatory design/reference.html visual fidelity.

**Date**: 2026-07-10
**Topic**: Request-body editor shell with a body-type selector plus three text-only modes (none, raw with {{variable}}-highlighted code area defaulting to JSON, and x-www-form-urlencoded via the existing key-value editor), emitting {type,lang,text} to the active tab RequestSpec through the store, with mandatory design/reference.html visual fidelity.
**Verdict**: Worth pursuing

## Summary

A request-body editor shell (BodyEditor organism) with a 6-option body-type radio selector and three live text-only modes — none, raw (JSON-default lang pill over a hand-rolled textarea/<pre>/gutter code area with two-pass {{var}}+JSON highlighting), and x-www-form-urlencoded (existing KVTable) — with form-data/binary/GraphQL rendered as the house 'Panel not yet available' placeholder. Every reuse seam the feature assumes already exists in-repo and fits: varTokens.tokenizeVars, KVTable (Row[]), RequestSubTabs (host + mount-all/hidden-toggle + shared empty-state), and tabsStore.updateActiveSpec. Overall fit is Good; the one belief-vs-reality gap is that RequestSpec.body is currently FLAT {lang,type,text}, not the discriminated union the design needs — but that migration is essentially consumer-free (zero readers beyond the seed) so its blast radius is Low. Recommended direction: model Body as a discriminated union owned by the store as the single source of truth, mount all mode panels and toggle by hidden (automatic round-trip), and hand-roll the code editor + JSON tokenizer so the design-anchor computed-style diff stays valid (Monaco/CodeMirror are correctly rejected). Primary risk is not integration but the anti-false-green fidelity gate: the .tk-* literal-hex assertions need a live-renderer computed-style channel, an OPEN dev-lane dependency that must report UNVERIFIED (never PASS) when absent.

## Prior Art

| Reference | Kind | Relevance | Source |
|---|---|---|---|
| varTokens.tokenizeVars | pattern | internal — existing {{variable}} tokeniser (var pass); pure, renderer-only, returns VarSegment[] plain/var; directly reusable for the raw code-area var pass | internal:src/renderer/src/lib/varTokens.ts |
| KVTable organism | pattern | internal — existing key-value editor emitting Row[]; reuse verbatim for x-www-form-urlencoded mode | internal:src/renderer/src/components/organisms/KVTable.tsx |
| RequestSubTabs shell + empty-slot pattern | pattern | internal — host sub-tab shell; mount-all + hidden-toggle; shared 'Panel not yet available' empty-state (L241) — the pattern the deferred body-modes placeholder mirrors; BodyEditor mounts in the body slot | internal:src/renderer/src/components/organisms/RequestSubTabs.tsx |
| tabsStore.updateActiveSpec | pattern | internal — store write seam (Partial<RequestSpec> shallow-merge + dirty + equality no-op); BodyEditor emits body via updateActiveSpec({body}) | internal:src/renderer/src/lib/tabsStore.ts |
| requestSpec.RequestSpec.body + Row | pattern | internal — Body type home; CURRENTLY FLAT {lang,type,text} (L82), NOT a union; Row type (L32) is the actual KV row shape (user called it KVRow). Union migration lands here | internal:src/renderer/src/lib/requestSpec.ts |
| react-simple-code-editor | library | canonical textarea-over-<pre> overlay technique reference; validates the hand-rolled approach (transparent textarea, CSS-Grid alignment, single scroll source). NOT adopted as a dep — used as a pattern reference only; matches design §8 .code-editor grid | https://github.com/react-simple-code-editor/react-simple-code-editor |
| CSS-Tricks: editable textarea with syntax-highlighted code | pattern | documents transparent-textarea + highlighted-pre grid overlay + caret-color + scroll-sync — the three-layer alignment invariant in constraints | https://css-tricks.com/creating-an-editable-textarea-that-supports-syntax-highlighted-code/ |

## Integration Surface

| Touchpoint | Module/file | Why touched |
|---|---|---|
| varTokens var pass | src/renderer/src/lib/varTokens.ts | reuse tokenizeVars for raw code-area {{var}} highlighting; language-agnostic; validVars-∅ selector applied by caller |
| KVTable urlencoded | src/renderer/src/components/organisms/KVTable.tsx | mount for x-www-form-urlencoded mode; emits Row[] |
| RequestSubTabs body slot | src/renderer/src/components/organisms/RequestSubTabs.tsx | host; add a body slot prop + wire the body key (currently falls to emptyState L241); BodyEditor mounts here; deferred-mode placeholder mirrors this empty-state |
| tabsStore updateActiveSpec | src/renderer/src/lib/tabsStore.ts | body write path: updateActiveSpec({body}) shallow-merge; no direct requestSpec import from BodyEditor |
| requestSpec Body union migration | src/renderer/src/lib/requestSpec.ts | migrate body flat {lang,type,text} (L82) -> discriminated union; update makeBlankRequest seed (L131); Row (L32) reused for urlencoded/form-data rows |
| BodyEditor organism (new) | src/renderer/src/components/organisms | greenfield BodyEditor.tsx: body-type radio + mode switch + code-editor/gutter/pre + lang-pill; no existing BodyEditor/radio-group/lang-pill/code-editor found |
| syntax tokenizer (new lib) | src/renderer/src/lib | greenfield JSON syntax tokenizer module (.tk-key/str/num/bool/null/punc); lib never imports components; no existing syntax tokenizer found |

## Fit Assessment

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|---|---|---|---|---|
| varTokens var pass | reuse lib/varTokens.ts for the raw var pass | tokenizeVars exists, pure, renderer-only, returns VarSegment[] (plain/var, name+raw); no validVars/missing concept (caller applies ∅-selector) — exactly the seam described | Low | none |
| KVTable urlencoded | reuse existing key-value editor for urlencoded | KVTable exists and emits Row[]; row type is Row (requestSpec.ts:32), not a distinct KVRow — naming reconciliation only | Low | none |
| RequestSubTabs body slot | BodyEditor mounts into the Body sub-tab; deferred modes mirror sub-tab empty-slot | RequestSubTabs mounts params/headers via slot props; body currently falls to shared emptyState (L241). Must add a body slot prop + wire it. Mount-all+hidden-toggle already the house pattern (supports round-trip) | Low | add body slot prop to RequestSubTabs |
| tabsStore updateActiveSpec | emit body via store to active-tab RequestSpec; no direct requestSpec import | updateActiveSpec(Partial<RequestSpec>) exists with shallow-merge + dirty + equality no-op; exact seam | Low | none |
| requestSpec Body union migration | Body union type home = requestSpec.ts (type-only import, store re-export) | body is CURRENTLY FLAT {lang,type,text} (L82), not a union. Migration required. But .body.text/lang/type has ZERO consumers beyond makeBlankRequest seed -> consumer-free migration, LOW blast radius. Union stays JSON-round-trip-safe | Low | change RequestSpec.body to union; update makeBlankRequest seed to {type:none} |
| BodyEditor organism (new) | BodyEditor as new organism reusing seams | no existing BodyEditor/radio-group/lang-pill/code-editor — greenfield, but design/reference.html + styles.css §8 fully specify DOM+values (grid 36px 1fr, gutter, pre, .tk-*) | Medium | none |
| syntax tokenizer (new lib) | new lib/ syntax tokenizer, lib never imports components | no existing syntax tokenizer; greenfield JSON-only tokenizer; token vocabulary fixed by styles.css (.tk-key/str/num/bool/null/punc); scope bounded to JSON | Medium | none |

**Overall fit**: Good
**Effort estimate**: Medium
**Rationale**: Fit is Good. Every reuse seam the user believed exists actually exists and matches: varTokens.tokenizeVars (var pass), KVTable (Row[] emitter), RequestSubTabs (host + mount-all/hidden-toggle + shared 'Panel not yet available' empty-state at L241), tabsStore.updateActiveSpec (Partial<RequestSpec> write path). One belief-vs-reality mismatch: the user's inputs_outputs assumes a discriminated-union Body, but RequestSpec.body is CURRENTLY FLAT {lang,type,text} (requestSpec.ts:82) — a migration, not a green-field add. Blast radius is LOW: .body.text/lang/type has ZERO consumers beyond the makeBlankRequest seed, so the union swap + seed update is essentially consumer-free and stays JSON-round-trip-safe. Minor naming reconciliation: the KV row type is Row (requestSpec.ts:32), not KVRow. Remaining work is greenfield-but-fully-design-specified: BodyEditor organism (radio + mode-switch + textarea/pre/gutter code-editor + lang-pill) and a JSON syntax tokenizer lib — no existing BodyEditor/radio-group/lang-pill/code-editor/syntax-tokenizer found, but design/reference.html + styles.css §8 pin the DOM and every value. Third-party editors (Monaco/CodeMirror) are correctly rejected: they render their own DOM/theming, defeating the design-anchor computed-style diff (verify-green-but-drifted, the 009->010->B3 mode). The textarea-over-<pre> overlay is the canonical hand-rolled technique. Effort Medium driven by the two greenfield UI/lib pieces, not by integration risk.

## Design Options

### Option A: Union-in-spec, store-owned, mount-all panels
- **Shape**:
```
Body becomes a discriminated union on type in requestSpec.ts; the store (tabsStore) is the single source of truth. BodyEditor reads body from the active spec and writes each mode's variant via updateActiveSpec({body}); all mode panels are always-mounted and toggled by the hidden attr (round-trip is free — state lives in the spec, not the component).
```
- **Pros**:
  - Illegal states unrepresentable (lang/text only on raw; rows on urlencoded/form-data)
  - Round-trip preservation is automatic — no rehydrate logic
  - Matches the house mount-all/hidden-toggle pattern (RequestSubTabs)
  - Store stays single source of truth (constitution §5.2 / §2.2)
  - Decoupled: BodyEditor never imports requestSpec data
- **Cons**:
  - Requires the flat->union body migration in requestSpec.ts + seed
  - Every mode writes a full union variant on change
- **Complexity**: Med

### Option B: Flat {type,lang,text} + text-encoded KV (minimal migration)
- **Shape**:
```
Keep RequestSpec.body flat; add only a type discriminator and serialize urlencoded/form-data rows into the text field at edit time, parsing back on render.
```
- **Pros**:
  - No type migration — smallest diff to requestSpec.ts
- **Cons**:
  - Lossy round-trip: encoded text cannot represent disabled-but-present rows, row order, or duplicates
  - Var literals {{var}} mangled — pre-encoding braces is wrong, leaving them raw is not encoded
  - Parse-back every render; over-generalizes raw (text) onto KV (rows)
  - Contradicts inputs_outputs — the user already reasoned this shape out as incorrect
- **Complexity**: Low

### Option C: Union-in-spec + component-owned per-mode draft state
- **Shape**:
```
Body is a union in the spec, but BodyEditor holds local React state per mode and syncs to the store on blur/debounce rather than on every edit.
```
- **Pros**:
  - Fewer store writes per keystroke
- **Cons**:
  - Dual source of truth (local draft vs spec) -> sync bugs
  - Round-trip needs manual rehydrate on mode switch
  - Dirty-flag timing becomes ambiguous
  - Contradicts store-as-single-source-of-truth (§5.2)
- **Complexity**: Med

**Recommended option**: Union-in-spec, store-owned, mount-all panels — This is the only option that makes illegal body states unrepresentable and gets round-trip preservation for free by keeping the discriminated-union Body in internal:src/renderer/src/lib/requestSpec.ts with the store (internal:src/renderer/src/lib/tabsStore.ts) as single source of truth — extending the existing seams rather than building new state. The existing flat body at internal:src/renderer/src/lib/requestSpec.ts (L82) must migrate to the union, but that existing implementation does NOT cover the discriminated-union requirement, and the migration is consumer-free (zero readers of .body.text/lang/type beyond makeBlankRequest), so it is Low-risk. It reuses internal:src/renderer/src/lib/varTokens.ts, internal:src/renderer/src/components/organisms/KVTable.tsx, and internal:src/renderer/src/lib/tabsStore.ts verbatim, and honours the constitution: BodyEditor injects KVTable as a slot prop (no sibling-organism import, §2.2) and receives the Body type via a tabsStore re-export (requestSpec stays component-invisible, §5.2). Option B is rejected as lossy; Option C duplicates the source of truth.

## Build vs Buy

| Build | Buy/Adopt |
|---|---|
| Hand-roll the code editor (transparent textarea over a highlighted <pre> + gutter, CSS-Grid aligned, single scroll source — the canonical react-simple-code-editor technique) and a small JSON-only syntax tokenizer lib; reuse varTokens for the var pass. | Adopt Monaco or CodeMirror 6 as the raw editor. |

**Recommendation**: Build — Buy is rejected on fidelity grounds: Monaco/CodeMirror render their own DOM and theming, which defeats the design-anchor computed-style diff against reference.html (the verify-green-but-drifted failure, 009->010->B3). The design already ships the exact editor DOM (§8 .code-editor grid 36px 1fr, .gutter, pre, full .tk-* vocabulary), so hand-rolling is a values-copy, not novel design. CodeMirror 6 remains a documented FUTURE fallback strictly if folding/multi-cursor are ever needed — a re-decision, not part of this build.

## Derisk Plan

1. Spike the three-layer alignment (textarea/<pre>/gutter) + scroll-sync in BOTH themes before building any mode — proves the hardest fidelity invariant early
2. Prototype the CT assertComputedStyle / assertResolvesToToken helper against the .tk-* hex table + live-renderer channel; this is the OPEN dev-lane dependency behind the anti-false-green gate
3. Do the flat->union body migration first and let the type-checker enumerate every narrowing site — confirms the zero-consumer / Low-blast-radius assumption empirically
4. Write a {{var}}-inside-JSON-string fixture and pin the var-pass-wins tie-break before wiring the two-pass tokenizer

## Constitution Constraints

| Rule | Impact |
|---|---|
| §2.2 Renderer Tier Organization (organisms flow downward only; no sibling-tier imports) | BodyEditor (organism) must NOT import KVTable (sibling organism). Inject the urlencoded editor as a slot prop — the house pattern RequestSubTabs already uses to receive params/headers panels. Constrains BodyEditor's composition API. |
| §5.2 Domain Invariants (requestSpec stays a pure data module — never imported by components) | The discriminated-union Body type must reach BodyEditor via a tabsStore re-export, not a direct requestSpec import; requestSpec stays component-invisible. Enables the union-in-spec option without breaking the invariant. |
| §3.1 Type Safety (strict mode, no any, narrow don't cast) | The discriminated-union Body aligns with this — narrowing on type replaces casts and removes illegal states; write-path stays fully typed via updateActiveSpec(Partial<RequestSpec>). |
| §2.1/§2.3 Renderer purity (no Node/Electron; @renderer alias) | The new JSON syntax tokenizer lib must be renderer-pure with no React/DOM/Node imports (mirrors varTokens.ts) and sit at the leaf lib layer — lib never imports components. |
| §4 Prefer design tokens over literal style values | The .tk-key/str/num/bool LITERAL per-theme hex is a DELIBERATE, design-grounded exception (styles.css ships literal hex, not tokens, for these four); assert literal hex per theme. .tk-null/punc/var stay token-based (resolves-to-token) per the general rule. |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied mechanism/placement guesses (confirm via Phase 2 fit-check): reuse existing key-value editor component + its tokenise/validVars-∅-selector seam; emit body via store to active-tab RequestSpec (no direct requestSpec import); neutral 'not yet available' placeholder mirrors existing sub-tab empty-slot pattern]

## Recommendation

**Action**: Proceed to /specify for the BodyEditor shell + none/raw/urlencoded modes, carrying the union-in-spec design, the per-feature MATCH/DEVIATE dispositions (radio option set, lang-pill language set, var-missing state), and the anti-false-green fidelity gate as explicit ACs.
**Next**: Run /specify with the distilled topic; spec the flat->union migration as task one.

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

~~~
/specify "Request-body editor shell (BodyEditor organism): body-type radio selector + none/raw/urlencoded modes, raw = JSON-default lang pill over a hand-rolled textarea/pre/gutter code area with two-pass {{var}}+JSON highlighting, urlencoded = KVTable; Body as a store-owned discriminated union; design/reference.html §8 fidelity mandatory."

Discovery reference: discover/2026-07-10-request-body-editor-shell-with-a-body-type-selector-plus.md
Key facts:
- Functional scope: BodyEditor shell = body-type radio selector (none, form-data, x-www-form-urlencoded, raw, binary, GraphQL) driving a mode switch. Three modes live now: none (empty region), raw (lang-pill toolbar JSON default over a hand-rolled <pre>/gutter code area with two-pass {{variable}} + syntax highlight), x-www-form-urlencoded (mount existing KVTable emitting KVRow[]). form-data/binary/GraphQL = shared neutral 'not yet available' placeholder. Body is a discriminated union on type (lang/text only on raw; urlencoded/form-data carry KVRow[]); mutations write the union to the active tab RequestSpec via store updateActiveSpec, NOT a flat {type,lang,text}.
- Users: mintEnvoy end user (developer authoring an HTTP request) editing the request body in the request panel Body sub-tab. Single consumer surface. No component reads BodyEditor directly — downstream (serializer/send) reads the body shape from RequestSpec via the store, decoupled from the editor component.
- Success criteria: Three AC groups (fidelity, behavioral, robustness/a11y) confirmed. TIGHTENING 1 — .tk-* HEX TABLE (from styles.css), not prose: light .tk-key #0369a1 / .tk-str #15803d / .tk-num #b45309 / .tk-bool #be185d; dark .tk-key #7dd3fc / .tk-str #86efac / .tk-num #fcd34d / .tk-bool #f0abfc; both .tk-null resolves var(--text-faint), .tk-punc resolves var(--text-muted), .tk-var resolves var(--accent) (no dark override, theme-invariant). Assert literal hex per active theme for key/str/num/bool; resolves-to-token for null/punc/var; do NOT run resolves-to-token on the hex four. TIGHTENING 2 — anti-false-green gate (load-bearing): fidelity ACs PASS ONLY when auditor reads computed-style from a LIVE renderer; if the renderer/computed-style channel is unavailable (DevTools-MCP absent) fidelity ACs report UNVERIFIED never PASS (skipped != green; false-green is the known drift root cause). Phrase AC as gate not mechanism. TIGHTENING 3 — gutter<->line EQUALITY: computed height of .code-editor .gutter>div == computed line-height of .code-editor pre (1.65 x font-size); gutter node count == rendered line count; pre and gutter share one scrollTop (no independent drift). ADDITIONS: empty/initial raw state renders empty .code-editor, zero tokens, no throw; union round-trip — switching body-type away and back preserves per-mode value from RequestSpec (raw text kept, urlencoded rows kept) via mount-all + toggle-visibility (not unmount). SCOPE DISCIPLINE: only non-JSON highlighting criterion is '.tk-var works across all raw langs'; NO criterion asserts XML/HTML/Text structural highlighting (in non_goals); malformed JSON degrades to plain var(--text), no throw, no error UI. OPEN dependency (not a criterion): CT assertComputedStyle/assertResolvesToToken helper + live-renderer infra are OPEN dev-lane items; if unavailable at build time fidelity ACs stay UNVERIFIED per Tightening 2.
- Recommended option: Union-in-spec, store-owned, mount-all panels
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
~~~

