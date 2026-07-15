/**
 * requestSpec.ts
 *
 * Renderer-only domain model for an HTTP request specification.
 *
 * This module:
 *   - has NO node / electron imports (renderer-only, constitution §2.1/§2.3, AC-10)
 *   - exports plain, JSON-serializable types only — no class instances, Symbols,
 *     or functions on the data shape (actions live on the store, never here)
 *   - exports a type guard (isBearerAuth) and a seed factory (makeBlankRequest)
 *   - is strict-mode compatible: no `any`, no casts (constitution §3.1)
 *
 * Usage:
 *   import { makeBlankRequest, isBearerAuth } from './requestSpec'
 *
 *   const spec = makeBlankRequest()
 *   if (isBearerAuth(spec.auth)) {
 *     console.log(spec.auth.token)
 *   }
 */

import type { HttpMethod } from './httpMethods'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A single query-param or request-header row.
 * Both `params[]` and `headers[]` on RequestSpec share this shape.
 */
export interface Row {
  /** Whether the row participates in the request (UI checkbox). */
  enabled: boolean
  /** Param or header name; may be an empty string for a blank row. */
  key: string
  /** Param or header value; stored verbatim. */
  value: string
  /** Free-text note; not sent with the request. */
  description: string
}

// ---------------------------------------------------------------------------
// Body types
// ---------------------------------------------------------------------------

/** Discriminant for which body mode the selector shows. */
export type BodyType = 'none' | 'raw' | 'urlencoded' | 'form-data' | 'binary' | 'graphql'

/** Language hint for the raw body editor. */
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
 * values of `active` — their mode implementations are Out of Scope.
 */
export interface Body {
  active: BodyType
  raw: RawBody
  urlencoded: UrlencodedBody
}

// ---------------------------------------------------------------------------
// Auth types
// ---------------------------------------------------------------------------

/**
 * No-auth variant of the Auth discriminated union.
 * Signals that no authentication header should be derived.
 */
export type NoneAuth = { type: 'none' }

/**
 * Bearer-token auth variant of the Auth discriminated union.
 * The token is stored verbatim; template interpolation is out of scope here.
 */
export interface BearerAuth {
  type: 'bearer'
  /** Bearer token value; stored verbatim (e.g. `'{{apiKey}}'` is a literal string). */
  token: string
}

/**
 * Discriminated union covering the two auth variants in scope.
 * Narrowed at runtime via `isBearerAuth`.
 */
export type Auth = NoneAuth | BearerAuth

/**
 * Full HTTP-request definition bound to a single tab.
 * Every field is a JSON primitive, array, or plain object — the value is
 * round-trip safe: `JSON.parse(JSON.stringify(spec))` deep-equals `spec`.
 */
export interface RequestSpec {
  /** HTTP method; one of the values in `METHODS` from `httpMethods.ts`. */
  method: HttpMethod
  /** Request URL; stored verbatim (un-interpolated template). */
  url: string
  /** Display name shown in the tab strip; may be empty. */
  name: string
  /** Query parameters appended to the URL. */
  params: Row[]
  /** Request headers. Auth is NOT mirrored here; no Authorization row is derived. */
  headers: Row[]
  /** Request body; `active` is the mode discriminant, `raw`/`urlencoded` are always present. */
  body: Body
  /** Authentication config; narrowed via `isBearerAuth`. */
  auth: Auth
}

// ---------------------------------------------------------------------------
// Type guard
// ---------------------------------------------------------------------------

/**
 * Narrows `auth` to `BearerAuth` when `auth.type === 'bearer'`.
 * Uses a literal-type comparison — never `any` or a cast.
 *
 * @param auth - The Auth union value to narrow.
 * @returns `true` if `auth` is a `BearerAuth`, enabling access to `auth.token`.
 */
export function isBearerAuth(auth: Auth): auth is BearerAuth {
  return auth.type === 'bearer'
}

// ---------------------------------------------------------------------------
// Seed factory
// ---------------------------------------------------------------------------

/**
 * Canonical blank Body seed. Single source of truth shared with BodyEditor's
 * fallback (BLANK_BODY in BodyEditor.tsx imports this via tabsStore re-export).
 * Values are primitives and empty arrays — safe to reference in read-only
 * contexts; makeBlankRequest freshens BOTH nested sub-objects (a fresh `raw`
 * and a fresh `urlencoded.rows`) so no blank tab aliases this singleton.
 */
export const BLANK_BODY: Body = {
  active: 'none',
  raw: { lang: 'json', text: '' },
  urlencoded: { rows: [] }
}

/**
 * Creates a fresh blank RequestSpec with canonical seed defaults.
 *
 * A new object is constructed on every call — arrays and nested objects are
 * never shared between calls, so two blank tabs can never alias the same
 * headers or params arrays. `body` spreads BLANK_BODY and freshens BOTH nested
 * sub-objects (`raw` and `urlencoded`) so no blank tab aliases BLANK_BODY.raw.
 *
 * Seed defaults:
 *   - method:  `'GET'`
 *   - url:     `''`
 *   - name:    `''`
 *   - params:  `[]`
 *   - headers: `[{ enabled: true, key: 'Accept', value: 'application/json', description: '' }]`
 *   - body:    `{ active: 'none', raw: { lang: 'json', text: '' }, urlencoded: { rows: [] } }`
 *   - auth:    `{ type: 'bearer', token: '{{apiKey}}' }` (literal string, not interpolated)
 *
 * @returns A new `RequestSpec` initialised with the canonical blank-tab defaults.
 */
export function makeBlankRequest(): RequestSpec {
  return {
    method: 'GET',
    url: '',
    name: '',
    params: [],
    headers: [{ enabled: true, key: 'Accept', value: 'application/json', description: '' }],
    body: { ...BLANK_BODY, raw: { ...BLANK_BODY.raw }, urlencoded: { rows: [] } },
    auth: { type: 'bearer', token: '{{apiKey}}' }
  }
}
