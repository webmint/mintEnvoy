/**
 * icons-glue.ts
 *
 * Lookup bridge between the project icon set and consumer code.
 * Import this module — not icons.ts directly — whenever you need to resolve
 * an icon name that may be user-supplied, stored, or otherwise unvalidated.
 *
 * This module:
 *   - has NO node / electron imports (renderer-only, constitution §4)
 *   - imports icon data only from atoms/icons via the @renderer alias (constitution §2.3)
 *   - never throws on an unknown name (constitution §3.2)
 */
import { ICONS, type IconName } from '@renderer/components/atoms/icons'

/**
 * The shape returned by resolveIcon for every call — known or unknown.
 * `name` is the canonical IconName (or 'unknown' for the fallback).
 * `markup` is the raw inner SVG markup string ready for dangerouslySetInnerHTML.
 */
export type IconEntry = {
  /** The canonical icon name, or 'unknown' when the input was not found. */
  name: IconName | 'unknown'
  /**
   * Raw inner SVG markup string (path / circle / rect elements).
   * Render inside an <svg viewBox="0 0 16 16"> with stroke="currentColor"
   * fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}.
   */
  markup: string
}

/**
 * Placeholder icon used when resolveIcon receives an unrecognised name.
 * Renders as a small diamond shape — visually distinct, always safe to display.
 */
const FALLBACK_ENTRY: IconEntry = Object.freeze({
  name: 'unknown',
  markup: '<path d="M8 2l6 6-6 6-6-6 6-6z"/>'
})

/**
 * Resolve an icon name to its IconEntry (markup + canonical name).
 *
 * Safe by contract: NEVER throws for any input, including null, undefined,
 * empty string, or a name not present in the icon set.  Unknown names return
 * FALLBACK_ENTRY (a diamond placeholder) so the UI always has something to
 * render without a try/catch at the call site.
 *
 * @param name - Any string; only values that match an IconName yield the real icon.
 * @returns    IconEntry with the resolved markup, or the fallback for unknown names.
 *
 * @example
 *   const { markup } = resolveIcon('send')  // known icon
 *   const { markup } = resolveIcon('__nope__')  // → fallback diamond, no throw
 */
/**
 * Type guard that narrows an arbitrary string to IconName using Object.hasOwn,
 * which — unlike the `in` operator — checks only own (non-prototype) keys.
 * This prevents prototype-key collisions such as resolveIcon('toString').
 */
function isIconName(n: string): n is IconName {
  return Object.hasOwn(ICONS, n)
}

export function resolveIcon(name: string): IconEntry {
  if (isIconName(name)) {
    return {
      name,
      markup: ICONS[name]
    }
  }
  return FALLBACK_ENTRY
}
