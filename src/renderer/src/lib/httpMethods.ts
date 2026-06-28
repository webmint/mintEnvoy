/**
 * httpMethods.ts
 *
 * Single source of truth for the HTTP method list and its derived type.
 *
 * This module:
 *   - imports NOTHING (no components, stores, Node, or Electron) (constitution §2.2/AC-29)
 *   - exports a readonly tuple `METHODS` — the order IS the dropdown display order
 *   - exports `HttpMethod`, the union type derived from that tuple
 *   - is strict-mode compatible: no `any`, no casts (constitution §3.1)
 *
 * Usage:
 *   import { METHODS, HttpMethod } from './httpMethods'
 *
 *   const method: HttpMethod = 'GET'
 *   METHODS.forEach(m => console.log(m))
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Ordered list of supported HTTP methods.
 *
 * The array order determines the display order in method-selection dropdowns
 * throughout the UI. Do not reorder without checking all consumers.
 */
export const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'] as const

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Union of all supported HTTP method strings, derived from `METHODS`.
 *
 * Narrowing `string` to this type ensures only valid method values reach the
 * network layer and allows exhaustive switching on method in consumers.
 *
 * @example
 *   const method: HttpMethod = 'GET'   // valid
 *   const bad: HttpMethod = 'TRACE'    // TS error — not in METHODS
 */
export type HttpMethod = (typeof METHODS)[number]
