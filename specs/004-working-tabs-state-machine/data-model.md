# Data Model: working-tabs-state-machine

All entities are NEW, renderer-only, in-memory, and plain-serializable (no class instances / Symbols / functions on the data shape — only the store wrapper holds actions). Defined in `src/renderer/src/lib/requestSpec.ts` (domain types + seed factory + guards) and consumed by `src/renderer/src/lib/tabsStore.ts` (slice).

## Entities

### Row

A single param or header row (params[] and headers[] share this shape).

| Field       | Type    | Required | Description                                  |
| ----------- | ------- | -------- | -------------------------------------------- |
| enabled     | boolean | yes      | Whether the row participates (UI checkbox)   |
| key         | string  | yes      | Param/header name (may be empty for a blank) |
| value       | string  | yes      | Param/header value (stored verbatim)         |
| description | string  | yes      | Free-text note                               |

### Auth (discriminated union on `type`)

Exactly two members in scope; the union is intentionally extensible (other variants owned by the out-of-scope auth-panel task).

| Variant  | Shape                              | Description                                   |
| -------- | ---------------------------------- | --------------------------------------------- |
| none     | `{ type: 'none' }`                 | No auth                                        |
| bearer   | `{ type: 'bearer'; token: string }`| Bearer token; token stored verbatim (no interp)|

Narrowed via a type guard (`isBearerAuth(auth): auth is BearerAuth`), never via `any`/casts.

### RequestSpec

The full HTTP-request definition bound to a tab.

| Field   | Type                                   | Required | Description                                      |
| ------- | -------------------------------------- | -------- | ------------------------------------------------ |
| method  | string                                 | yes      | HTTP method (seed default `'GET'`)               |
| url     | string                                 | yes      | Request URL; stored verbatim (un-interpolated template) |
| name    | string                                 | yes      | Display name (may be empty)                      |
| params  | Row[]                                  | yes      | Query params                                     |
| headers | Row[]                                  | yes      | Request headers (auth is NOT mirrored here)      |
| body    | `{ lang: string; type: string; text: string }` | yes | Request body descriptor                |
| auth    | Auth                                   | yes      | Discriminated-union auth                         |

### Tab

A slice-owned wrapper pairing a RequestSpec with tab-local state.

| Field              | Type             | Required | Description                                                                                          |
| ------------------ | ---------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| id                 | string           | yes      | Unique tab id (`crypto.randomUUID()`); per-tab surrogate key — NOT a collection identity             |
| collectionRequestId | string \| null  | yes      | Source collection-request identity, set when the tab was opened from a collection; `null` for new-blank. This is the field AC-13's id-first dedupe matches on (distinct from `id`). |
| spec               | RequestSpec      | yes      | The request this tab edits                                                                            |
| dirty              | boolean          | yes      | Unsaved-edits flag; cleared by markClean                                                             |

### OpenFromCollectionInput (the typed `openFromCollection` argument)

The slice does NOT build the collection identity itself (the collection-list trigger site is §6 out of scope); it accepts and stores one supplied by the caller.

| Field              | Type        | Required | Description                                                              |
| ------------------ | ----------- | -------- | ----------------------------------------------------------------------- |
| collectionRequestId | string     | yes      | Stable identity of the collection request being opened (matched by dedupe leg 1) |
| spec               | RequestSpec | yes      | The request payload to seed the tab with                                |

### TabsState (zustand slice shape)

| Field        | Type     | Required | Description                          |
| ------------ | -------- | -------- | ------------------------------------ |
| tabs         | Tab[]    | yes      | Open tabs; **array order IS tab order** |
| activeTabId  | string   | yes      | id of the active tab                 |

Actions (live on the store, not on the serializable data): `openFromCollection(input: OpenFromCollectionInput)`, `newBlank()`, `close(tabId)`, `selectActive(tabId)`, `markClean(tabId)`.

## Relationships

- TabsState → Tab: one-to-many (the open tab list; order significant).
- Tab → RequestSpec: one-to-one embedded (Option A "flat array with embedded spec"; no separate spec registry).
- RequestSpec → Row: one-to-many for both `params` and `headers`.
- RequestSpec → Auth: one-to-one discriminated union.

## Validation / Invariants

- **Never-zero**: `tabs.length >= 1` always; `close` on the last tab spawns a fresh seeded GET before removal completes.
- **Active validity**: `activeTabId` always references a tab present in `tabs`; after `close` of the active tab, it points to the right neighbor (else left). **Closing a NON-active tab leaves `activeTabId` unchanged** — the previously-active tab stays active (the neighbor-selection logic is scoped strictly to the active-tab-closed branch). Pinned by a dedicated slice unit test.
- **Seed defaults (makeBlankRequest)**: `method='GET'`, `url=''`, `name=''`, `body={lang:'',type:'',text:''}`, `params=[]`, `headers=[{enabled:true,key:'Accept',value:'application/json',description:''}]`, `auth={type:'bearer',token:'{{apiKey}}'}` (the `{{apiKey}}` literal verbatim; Accept value reproduced from the prototype SEED at `design/reference.html:13485`). A new Tab wrapping this seed has `dirty=false`.
- **Auth never mirrored**: no `Authorization` row is derived into `headers[]` (auth→wire-header derivation is out of scope).
- **Dedupe (two-leg)**: `openFromCollection(input)` matches an existing tab by `input.collectionRequestId === tab.collectionRequestId` first (leg 1, both non-null), then falls through to exact verbatim non-empty `url` equality (leg 2); an empty `url` never matches (blank tabs stay distinct). A new tab opened from a collection stores `input.collectionRequestId` on its `Tab` so the next open can match leg 1.
- **Serializable**: every field above is a JSON primitive / array / plain object — `JSON.parse(JSON.stringify(spec))` deep-equals `spec` (the Q-2 contract test pins this for the out-of-scope persistence task).
