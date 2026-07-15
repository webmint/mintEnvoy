# Data Model: body-editor-shell

**Date**: 2026-07-10 (revised — grill-revision run)
**Scope**: The one CHANGED domain entity — `RequestSpec.body` migrates from a flat descriptor to a **tagged record with always-present retained sub-records**. This supersedes the earlier single-slot discriminated-union design, which grill Finding F-001 (High, confirmed) proved could not satisfy AC-14 (a single-variant union erases the prior mode's value on switch). The revised shape keeps every value-bearing mode's value in the store simultaneously with a single source of truth.

## Changed Entity

### `RequestSpec.body` (flat → tagged record)

**Before** (`src/renderer/src/lib/requestSpec.ts:82`):

```ts
body: { lang: string; type: string; text: string }
```

**After** — a tagged record whose `active` field is the mode discriminant and whose `raw`/`urlencoded` sub-records persist independent of `active`:

```ts
export type BodyType = 'none' | 'raw' | 'urlencoded' | 'form-data' | 'binary' | 'graphql'
export type RawLang = 'json' | 'xml' | 'html' | 'text'

/** Retained raw-mode draft; persists across mode switches (AC-14). */
export interface RawBody {
  lang: RawLang
  text: string
}

/** Retained urlencoded-mode draft; persists across mode switches (AC-14). */
export interface UrlencodedBody {
  rows: Row[]
}

/**
 * Request body. `active` is the discriminant (which mode the selector shows);
 * `raw` and `urlencoded` are always-present retained sub-records so every
 * entered mode's value survives a mode switch with the store as the single
 * source of truth (AC-14). form-data / binary / graphql are payload-free
 * values of `active` — their mode implementations are §6 Out of Scope.
 */
export interface Body {
  active: BodyType
  raw: RawBody
  urlencoded: UrlencodedBody
}
```

`RequestSpec.body` field type changes to `Body`. **`isRawBody` is removed** — the earlier design copied the `Auth`/`isBearerAuth` guard, but a tagged record needs no narrowing to reach `body.raw`/`body.urlencoded` (both always present). Mode dispatch reads `body.active`.

### Discriminant + sub-record table

| `active` value | Reads which sub-record | Carries | Exercised by AC |
|----------------|------------------------|---------|-----------------|
| `none` | — (empty region) | nothing | AC-4 (seed), AC-7 (default), AC-6 |
| `raw` | `body.raw` (`lang`, `text`) | code text + selected language | AC-8, AC-9, AC-10, AC-16, AC-17 |
| `urlencoded` | `body.urlencoded` (`rows`) | KV rows (reuses existing `Row`) | AC-11 |
| `form-data` | — (payload-free) | nothing | AC-7, AC-14, AC-15 |
| `binary` | — (payload-free) | nothing | AC-7, AC-14, AC-15 |
| `graphql` | — (payload-free) | nothing | AC-7, AC-14, AC-15 |

`RawLang` = `'json' | 'xml' | 'html' | 'text'` — `json` is the seeded default (AC-8); `xml`/`html`/`text` selectable. `Row` is the existing shape (`requestSpec.ts:32`) — reused verbatim, not redefined.

**Why not a discriminated union?** A `type`-discriminated union holds exactly one variant's payload, so switching mode overwrites the prior mode's value → AC-14 unsatisfiable (grill F-001). Always-present sub-records retain every value-bearing mode's value at once. AC-4 ("valid … value of type none") = `body.active === 'none'`; AC-12 ("write the discriminated-union body via `updateActiveSpec` with a body patch") is unchanged — `active` is the discriminant, the patch is still a single `{ body }`.

### Seed change

`makeBlankRequest()` (`requestSpec.ts:124`, body seed at `:131`):

```ts
// before
body: { lang: '', type: '', text: '' }
// after
body: { active: 'none', raw: { lang: 'json', text: '' }, urlencoded: { rows: [] } }
```

Sub-records are seeded (never absent), so no nullable branch exists — reads are unconditional.

## Write path (tabsStore SSOT)

Every edit is an immutable full-`Body` patch via `updateActiveSpec({ body })`:

| Edit | Patch |
|------|-------|
| raw text | `{ body: { ...body, raw: { ...body.raw, text: next } } }` |
| raw lang | `{ body: { ...body, raw: { ...body.raw, lang: next } } }` |
| urlencoded rows | `{ body: { ...body, urlencoded: { rows: next } } }` |
| mode switch | `{ body: { ...body, active: next } }` (discriminant only; both sub-records carried forward → AC-14) |

**Dirty semantics**: the store's no-op guard is REFERENCE equality (`patch[k] === tab.spec[k]`, `tabsStore.ts:344`). Each edit builds a fresh `body` object, so a real edit flips `dirty` correctly. Re-selecting an already-active control would build a fresh-but-equal object and spuriously flip `dirty` — the reference guard cannot catch it. This applies to BOTH the **radio** (`{ body: { ...body, active: next } }`) and the **lang-pill** (`{ body: { ...body, raw: { ...body.raw, lang: next } } }`). **General rule (D2/D5): every BodyEditor control that writes a fresh `body` early-returns when its next value equals the current stored value** — `BodyEditor` early-returns when `next === body.active` (radio) and when `next === body.raw.lang` (lang-pill), emitting no write. Urlencoded-rows and raw-text edits are genuine content changes (a fresh array / string reflects a real edit) — **exempt, no guard** (guarding them would suppress real dirty flips). (Grill F2.)

**Highlight scheduling** (grill F3, refined cycle-3): the raw `<textarea>` is store-controlled (`value = body.raw.text`, per-keystroke write → AC-14 + single SSOT). The aria-hidden `<pre>` overlay and the gutter render their TEXT from the LIVE `body.raw.text` every keystroke (plain-text render is O(n)-cheap, no tokenise) — so typed chars are visible immediately (the `<pre>` is the sole visible text layer under the `color:transparent` textarea) and the gutter stays aligned. ONLY the expensive `compose()` coloring pass is debounced (`BODY_HIGHLIGHT_DEBOUNCE_MS`, default 100ms): its token spans apply to the `<pre>` only when the debounced snapshot === the live text (typing paused); while the snapshot is stale the `<pre>` renders the live text as plain `var(--text)` segments (the same plain-degrade path D6 uses above the >50k ceiling). So `compose()` runs off-keystroke on the trailing edge — never synchronously per keystroke (spec §7 constraint 3b) — WITHOUT the visible text lagging. The gutter node count derives from the LIVE `body.raw.text` ⇒ gutter count == pre rendered-line-count by construction (AC-23, now with no transient divergence — grill F3 cycle-3).

## Validation / Invariants

- `raw.lang`/`raw.text` live ONLY under `body.raw`; `rows` ONLY under `body.urlencoded`. The only representable illegal state (which `active` value is live vs which sub-record is shown) is resolved by `active` — there is no cross-field constraint to violate. Illegal-state *minimization* (not elimination) is the deliberate trade for AC-14 retention, per the grill `must_satisfy` directive.
- Narrow `KVTable` props via `'rows' in props`; narrow nothing to reach `body.raw`/`body.urlencoded`; never a cast (constitution §3.1).
- Round-trip safe: every field is a JSON primitive/array/plain-object, so `JSON.parse(JSON.stringify(body))` deep-equals `body` (preserves the `RequestSpec` invariant).
- `form-data`/`binary`/`graphql` are payload-free `active` values: no in-scope AC writes or persists their rows, and §6 marks their mode implementations Out of Scope. A future feature adds e.g. `formData: { rows }` as that feature's own migration.

## Migration blast radius

`.body.text` / `.body.lang` / `.body.type` has **no PRODUCTION reader beyond the `makeBlankRequest` seed** (verified) — the type change is production-consumer-free. But the blast radius is NOT zero: **≥1 existing test must be reseeded** — `src/renderer/src/lib/__tests__/tabsStore.test.ts:232` asserts the old seed shape `expect(spec.body).toEqual({ lang: '', type: '', text: '' })` and MUST be rewritten to the tagged-record seed (listed in the plan's File Impact table). Migrate first and let the type-checker enumerate every access site once the record lands (spec §9 risk 3/6, sequenced first) — do NOT present the enumeration's outcome as pre-verified zero. (Grill F1 corrected the earlier false "ZERO readers / consumer-free including tests" claim.)

## Re-export (consumption path)

`tabsStore.ts` re-exports `Body`, `RawBody`, `UrlencodedBody`, `BodyType`, `RawLang`, and `Row` so `BodyEditor` imports them from `@renderer/lib/tabsStore` — never from `requestSpec` directly (AC-13 / constitution §5.2: requestSpec stays component-invisible). `isRawBody` is no longer exported (removed).
