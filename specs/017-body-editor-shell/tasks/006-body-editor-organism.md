# Task 006: BodyEditor organism + CSS

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002, 003, 009
**Blocks**: 008, 010
**Spec criteria**: AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-12, AC-14, AC-15, AC-16, AC-17, AC-18, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29
**Review checkpoint**: Yes
**Context docs**: specs/017-body-editor-shell/data-model.md, docs/architecture.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/BodyEditor.tsx | Create | Radiogroup + mount-all mode switch + lang-pill + three-layer code area + render-prop urlencoded slot |
| src/renderer/src/components/organisms/BodyEditor.css | Create | `.tk-*` class rules + code-editor/gutter/pre/body-toolbar/body-radio/dot/lang-pill bound to tokens |

## Description

Build the `BodyEditor` organism: a 6-option ARIA radiogroup body-type selector driving a mount-all/hidden-toggle mode switch across three live modes (none, raw, x-www-form-urlencoded) plus three payload-free placeholder discriminants (form-data, binary, GraphQL). Body lives solely in `tab.spec.body` (tabsStore SSOT); BodyEditor reads via a selector and writes an immutable full-`Body` patch via `updateActiveSpec({ body })`. The urlencoded editor is injected as a `renderUrlencoded` **render-prop** (wired at App root, task 008) — BodyEditor must NOT import KVTable or any sibling organism (§2.2). Author BodyEditor.css to match `design/styles.css` §8 exactly.

### Implementation sub-checklist (all required — D5)

- [ ] **Radiogroup**: `role=radiogroup` container + 6 `role=radio` options with `aria-checked` + arrow-key roving focus + visible focus ring, over the design `div + .dot` visuals; defaults to `none` (AC-7, AC-18).
- [ ] **Mode switch**: all 6 mode panels mount-all + `hidden`-toggle by `body.active`; switching toggles visibility, never unmounts (AC-6).
- [ ] **Lang-pill**: button semantics + aria; JSON default; XML/HTML/Text selectable; visible only in raw mode (AC-8).
- [ ] **Three-layer code area**: real `<textarea>` (`value = body.raw.text`, editable, native caret/IME, per-keystroke store write) + aria-hidden `<pre>` overlay + `.gutter`; identical mono metrics, line-height 1.65, padding, tab-size; single scroll source = textarea, `<pre>`+gutter track its `scrollTop/scrollLeft`; no `contenteditable`/`innerHTML`; tokens rendered as escaped JSX children only (XSS-safe).
- [ ] **`<pre>` + gutter TEXT** render from the LIVE `body.raw.text` every keystroke (immediate, plain, no tokenise); gutter node count derives from the live text ⇒ gutter count == pre rendered-line-count by construction (AC-23).
- [ ] **Debounced coloring**: only the `compose(snapshot, lang, validVars)` coloring pass is trailing-debounced (`BODY_HIGHLIGHT_DEBOUNCE_MS`, default 100ms); its spans apply to `<pre>` only when `snapshot === body.raw.text`; while pending, `<pre>` renders live text as plain `var(--text)` (AC-9, AC-10, AC-16, AC-17). Search for an existing debounce helper before hand-rolling (KISS/§3.6).
- [ ] **Render-prop slot**: urlencoded panel renders `props.renderUrlencoded(body.urlencoded.rows, nextRows => write)` bound to `body.urlencoded.rows`.
- [ ] **Re-select early-return**: radio writes `body.active` only, early-returning when `next === body.active`; lang-pill writes `body.raw.lang` only, early-returning when `next === body.raw.lang` (the store no-op guard is reference-based and cannot catch a fresh-but-equal object). Raw-text + urlencoded-rows edits are genuine changes — no guard.
- [ ] **Deferred placeholder**: form-data/binary/graphql render BodyEditor's OWN `<p>Panel not yet available</p>` styled by a BodyEditor.css class matching the muted `request-sub-tabs__empty` treatment — do NOT import anything from RequestSubTabs (§2.2 trap) (AC-15).

## Change Details

- In `src/renderer/src/components/organisms/BodyEditor.tsx` (new):
  - Import `Body`/`RawBody`/`UrlencodedBody`/`BodyType`/`RawLang`/`Row` from `@renderer/lib/tabsStore` (never `requestSpec` — AC-13/§5.2).
  - Import `compose` from `@renderer/lib/jsonTokens`.
  - Props: `{ renderUrlencoded: (rows: readonly Row[], onRowsChange: (r: Row[]) => void) => ReactNode }` — pin this signature exactly (matches KVTable controlled props, task 005, and the App wiring, task 008).
  - Read `body` via a `tabsStore` selector on the active tab; write via `updateActiveSpec({ body })` using the immutable full-`Body` patches (raw text / raw lang / urlencoded rows / active) from data-model.md.
  - Class-based styling only; no inline `style={{...}}`; no Node/Electron imports (AC-29).
  - Add `data-testid` to the built elements the design binding names: `body-code-editor` (code-editor container), `body-toolbar`, `body-radio` (each radio option), `body-lang-pill`, `body-gutter`, `body-pre`.
  - Carry a component contract doc comment (AC-26).
- In `src/renderer/src/components/organisms/BodyEditor.css` (new):
  - Author ALL `.tk-*` class rules: `.tk-key/.tk-str/.tk-num/.tk-bool` bind via `var(--tk-key/str/num/bool)` (the tokens land in task 009); `.tk-null → var(--text-faint)`, `.tk-punc → var(--text-muted)`, `.tk-var → var(--accent)` (AC-22).
  - Author `.code-editor` (grid `36px 1fr`, `font-family: var(--font-mono)`, `font-size: 12.5px`, `line-height: 1.65`), `.code-editor .gutter`, `.code-editor pre`, `.code-editor .gutter > div { height: calc(1.65em) }`, `.body-toolbar`, `.body-radio` (+ `:hover`, `.active`, `.dot`, `.active .dot`), `.body-toolbar .right`, `.lang-pill` — matching `design/styles.css` §8 values exactly (AC-24).
  - Do NOT redefine the `--tk-*` tokens here (they are owned by tokens.css, task 009); only bind to them.

## Contracts

### Expects (checked before execution)
- `Body`/`RawBody`/`UrlencodedBody`/`BodyType`/`RawLang`/`Row` are re-exported from `tabsStore` (task 002).
- `compose(text, lang, validVars)` is exported from `jsonTokens` (task 003).
- `--tk-key/--tk-str/--tk-num/--tk-bool` tokens exist in `tokens.css` (task 009).
- `updateActiveSpec({ body })` accepts a `Partial<RequestSpec>` on `tabsStore`.

### Produces (checked after execution)
- `BodyEditor.tsx` exports `BodyEditor` with the pinned `renderUrlencoded: (rows: readonly Row[], onRowsChange: (r: Row[]) => void) => ReactNode` prop.
- The 6-option `role=radiogroup`/`role=radio`/`aria-checked` selector defaults to `none`; mode panels mount-all + `hidden`-toggle by `body.active`.
- Body writes go through `updateActiveSpec({ body })`; radio + lang-pill early-return on an equal value.
- The `<pre>` + gutter render from the live `body.raw.text`; only `compose()` coloring is debounced via `BODY_HIGHLIGHT_DEBOUNCE_MS`.
- BodyEditor imports zero sibling organisms; the deferred placeholder is BodyEditor's own markup.
- The built elements carry the `data-testid`s named in `design-manifest.json` (`body-code-editor`, `body-toolbar`, `body-radio`, `body-lang-pill`, `body-gutter`, `body-pre`).
- `BodyEditor.css` binds `.tk-*`/code-editor/gutter/pre/toolbar/radio/lang-pill to tokens matching styles.css §8.

## Done When

- [x] `BodyEditor.tsx` exists and exports `BodyEditor` (AC-5).
- [x] Selecting a radio option switches the visible panel while all panels stay mounted (AC-6); six options present, default none (AC-7).
- [x] Raw mode shows a functional lang-pill defaulting to JSON with XML/HTML/Text selectable (AC-8).
- [x] JSON raw text renders the two-pass highlight (var-pass-wins); non-JSON renders var-pass-only; empty renders zero tokens; malformed degrades to plain — none throw (AC-9, AC-10, AC-16, AC-17).
- [x] Body edits write via `updateActiveSpec({ body })` (AC-12); switching type away and back restores each mode's value from the store (AC-14).
- [x] form-data/binary/graphql render BodyEditor's own neutral placeholder with no RequestSubTabs import (AC-15).
- [x] Selector exposes `role=radiogroup`/`role=radio`/`aria-checked`/arrow-key roving focus over div+dot (AC-18).
- [x] `.tk-*` classes + code-editor grid 36px 1fr + gutter/pre bind to tokens matching styles.css §8; `.tk-null/punc/var` resolve to `var(--text-faint/--text-muted/--accent)` (AC-22, AC-23, AC-24).
- [x] BodyEditor carries a contract doc comment (AC-26); no `console.log`/`debugger` (AC-27); class-based, no inline styles, no Node/Electron imports (AC-29).
- [x] BodyEditor passes type-check and lint before completion (AC-28).
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-14T10:07:51Z
**Files changed**: src/renderer/src/components/organisms/BodyEditor.tsx, src/renderer/src/components/organisms/BodyEditor.css
**Contract**: Expects 4/4 | Produces 7/7
**Notes**: New BodyEditor organism: 6-option ARIA radiogroup (roving focus), mount-all/hidden-toggle switch, three-layer code area (textarea+aria-hidden pre overlay+gutter, XSS-safe escaped tokens), debounced compose() coloring (BODY_HIGHLIGHT_DEBOUNCE_MS=100, plain-degrade while typing), render-prop urlencoded slot (no KVTable import), own placeholder for form-data/binary/graphql. CSS matches styles.css section 8 verbatim, .tk-* bound to --tk-*/--text-*/--accent, all 6 data-testids. 1 review-panel repair round (removed dead lang-cycle guard + deduped textarea CSS). qa's 6 forward test gaps recorded in task 010 brief. Deviations: React.JSX.Element return type (tsconfig no global JSX); implementing agent stalled twice on 600s watchdog before succeeding.
