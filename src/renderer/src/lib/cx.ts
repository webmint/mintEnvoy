/**
 * cx — lightweight className merge utility.
 *
 * Joins an arbitrary number of class tokens into a single space-separated
 * string, filtering out any falsy values (false, null, undefined, empty string).
 * Replaces the open-coded `[...].filter(Boolean).join(' ')` idiom used across
 * Icon, Dropdown, and Modal.
 *
 * @example
 * ```ts
 * cx('foo', condition && 'bar', undefined) // → "foo bar"
 * cx('a', false, null, 'b')               // → "a b"
 * ```
 *
 * @param classes - Zero or more class tokens. Falsy values are ignored.
 * @returns A single space-separated class string (never has leading/trailing spaces).
 */
export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}
