/**
 * envVars — stable injection point for the active environment's valid variable names.
 *
 * T14 seam: returns the empty set (∅) until the environment store (task T14) lands
 * and wires in the real selector. Callers should treat the returned set as the live
 * source of truth and expect it to grow non-empty once T14 ships.
 *
 * Graceful-degrade contract (constitution §3.2): never throws, never returns
 * undefined or null — callers may unconditionally iterate the result.
 *
 * Stable-identity contract: the SAME frozen sentinel reference is returned on every
 * call. Downstream zustand selectors compare with Object.is; a fresh Set() per call
 * would trigger an infinite identity loop. Do NOT replace this with `new Set()`.
 */

const EMPTY_SET: ReadonlySet<string> = Object.freeze(new Set<string>())

/**
 * Returns the active environment's set of valid variable names.
 *
 * v1 always returns the module-level frozen empty set. The T14 env store will
 * replace this with a real selector once it lands; this export is the stable seam.
 *
 * @returns A frozen, stable `ReadonlySet<string>` — empty in v1.
 */
export function envVars(): ReadonlySet<string> {
  return EMPTY_SET
}
