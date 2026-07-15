# Feature Summary — Body Editor Shell (017)

**Verdict**: APPROVED (see `verification.md`) · **Status**: Complete

## What was built

The request panel's **Body** sub-tab is now editable. A six-option body-type selector (None · form-data · x-www-form-urlencoded · raw · binary · GraphQL) drives a mode switch: **raw** mode gives a syntax-highlighted code editor (JSON by default, with an XML/HTML/Text language pill) that colors both `{{variables}}` and JSON structure as you type; **x-www-form-urlencoded** mode reuses the existing key-value table; **None** shows an empty region; and form-data / binary / GraphQL show a neutral "Panel not yet available" placeholder. Each request tab remembers its own body — switching body-type away and back, or switching request tabs, preserves what you entered.

## Changes

- **Body data model** — the request body became a typed discriminated union (`{ active, raw, urlencoded }`) owned by the tab store, replacing the old flat `{ lang, type, text }` shape; blank tabs seed a fully de-aliased body.
- **BodyEditor organism** — new component: a 6-option ARIA radiogroup (roving arrow-key focus) + a mount-all/hidden-toggle mode switch + a hand-rolled gutter/textarea/`<pre>` code area with a language pill.
- **JSON syntax highlighting** — new renderer-pure `jsonTokens.ts` tokenizer: a two-pass `compose()` that overlays a `{{var}}` pass on a JSON structural pass (var wins inside strings), degrades malformed JSON to plain text with no throw, and skips structural highlighting for non-JSON languages.
- **urlencoded reuse** — KVTable gained a controlled/field discriminated-prop mode so the body editor drives it with `rows` + `onRowsChange` without duplicating the table.
- **Wiring** — RequestSubTabs gained a `body` slot; App mounts BodyEditor (with a memoized urlencoded KVTable) into it; Body types reach BodyEditor via a `tabsStore` re-export (never a direct `requestSpec` import).
- **Design-fidelity test infra** — new `fidelityAssert.ts` CT helper (`assertComputedStyle` / `assertResolvesToToken`) with a fail-closed live-renderer computed-style channel; `--tk-*` per-theme tokens added to `tokens.css`.
- **Post-review fixes** — highlight re-arms on same-body request-tab switch (`activeTabId` added to the debounce deps) and inner scroll offsets reset on tab switch (scroll-bleed guard), each with regression CTs.

## Files changed

54 files, **+7177 / −68**.

- `src/` (25 files) — `components/organisms/BodyEditor.{tsx,css}` (new), `KVTable.{tsx,css}`, `RequestSubTabs.{tsx,css}`, `atoms/EmptyPanel.{tsx,css}` (new), `App.tsx`; `lib/jsonTokens.ts` (new), `varTokens.ts`, `requestSpec.ts`, `tabsStore.ts`; `test-utils/fidelityAssert.ts` (new); `styles/tokens.css`; plus CT/stories/unit tests.
- `specs/` (27) + `discover/` (2) — feature planning + pipeline artifacts.

## Key decisions

- **D1 — Body as a tagged record** (`{ active, raw, urlencoded }`) so `raw` and `urlencoded` sub-records retain their values across mode switches (AC-14).
- **D2 — Store-owned round-trip** — body lives only in `tab.spec.body`; BodyEditor reads via a `tabsStore` selector and writes via `updateActiveSpec`; the store is the single source of retained values.
- **D3 — urlencoded reuses KVTable** via a discriminated prop union rather than a second table (the reuse crux).
- **D4 — Body types reach BodyEditor through a `tabsStore` re-export**, keeping `requestSpec` component-invisible (§5.2).
- **D5 — Composition**: `role=radiogroup`/`role=radio` + roving focus over the design's div+dot visuals, on the proven mount-all/hidden panel pattern.
- **D6 — Renderer-pure JSON tokenizer** with a pure `compose()`; imports nothing renderer-external.
- **D7 — CT fidelity by computed-style, not pixel-diff** (the reference renders SF on macOS); assertions fail closed when the live channel is unavailable.

## Acceptance criteria

29 / 29 **PASS** (verified by code reading, `tests` mode — authoritative status from `verification.md`).

- AC-1 … AC-29: ✅ PASS — body model, BodyEditor organism, mode switch, ARIA radiogroup + roving focus, lang-pill cycle, two-pass highlight, malformed-JSON degrade, cross-mode value retention, gutter/scroll sync, §8 computed-style fidelity (light + dark tokens), and no-inline-style / no-renderer-external-import constraints.

## Known follow-ups (non-blocking, from `review.md`)

Advisory findings that ride outside the verdict gate — real, not shipped-broken, worth a future pass:

- **Design fidelity**: `.body-toolbar` height 40px vs reference 45px (reference has extra action buttons out of this feature's scope); `.code-editor pre` horizontal padding drift.
- **Accessibility**: gutter missing `aria-hidden` (screen reader announces line numbers); lang-pill focus-ring contrast 2.17:1 below WCAG 2.4.11 (3:1); KVTable grid semantics; two responsive-wrap issues at ≤720px width.
