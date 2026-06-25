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
  /** HTTP method (e.g. `'GET'`, `'POST'`). */
  method: string
  /** Request URL; stored verbatim (un-interpolated template). */
  url: string
  /** Display name shown in the tab strip; may be empty. */
  name: string
  /** Query parameters appended to the URL. */
  params: Row[]
  /** Request headers. Auth is NOT mirrored here; no Authorization row is derived. */
  headers: Row[]
  /** Request body descriptor. */
  body: { lang: string; type: string; text: string }
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
 * Creates a fresh blank RequestSpec with canonical seed defaults.
 *
 * A new object is constructed on every call — arrays and nested objects are
 * never shared between calls, so two blank tabs can never alias the same
 * headers or params arrays.
 *
 * Seed defaults:
 *   - method:  `'GET'`
 *   - url:     `''`
 *   - name:    `''`
 *   - params:  `[]`
 *   - headers: `[{ enabled: true, key: 'Accept', value: 'application/json', description: '' }]`
 *   - body:    `{ lang: '', type: '', text: '' }`
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
    body: { lang: '', type: '', text: '' },
    auth: { type: 'bearer', token: '{{apiKey}}' }
  }
}
