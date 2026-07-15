/**
 * varTokens.ts
 *
 * Renderer-only, display-only tokeniser for `{{variable}}` placeholders.
 *
 * This module:
 *   - is DISPLAY-ONLY — it NEVER resolves or substitutes variable values
 *     (resolution is intentionally out of scope; AC-12).
 *   - has NO React / DOM / Node / electron imports (renderer-pure, constitution §2.1/§2.3).
 *   - is fully typed — no `any` (constitution §3.1 strict mode).
 *   - is field-agnostic — the caller decides which cells to tokenise.
 *     Key text and value text tokenise independently (same function, called per cell).
 *   - is pure and stateless; repeated calls with the same input always produce
 *     the same output.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A segment produced by {@link tokenizeVars}.
 *
 * Discriminated on `kind`:
 * - `'plain'` — literal text with no variable reference; `text` is the raw string.
 * - `'var'`   — a `{{name}}` placeholder:
 *               - `name` is the trimmed inner text (for `validVars` lookup).
 *               - `raw` is the verbatim matched `{{...}}` text (for faithful display,
 *                 preserving any interior whitespace such as `{{ x }}`).
 *               The `name` is NEVER resolved — callers use it for display / highlighting only.
 */
export type VarSegment =
  | { kind: 'plain'; text: string }
  | { kind: 'var'; name: string; raw: string }

/**
 * Returns true when a `{{var}}` placeholder should be styled as "missing" —
 * i.e. the env-var set is loaded (non-empty) AND the var name is unknown.
 *
 * When `validVars` is empty (pre-load state), all var tokens render as neutral
 * `.var` highlights and none are flagged `.missing`. This prevents false
 * "missing" noise before the env store is populated.
 *
 * Centralises the `size > 0 && !known` gate so BodyEditor and KVTable both
 * derive the flag from a single source of truth (§3.6 DRY).
 *
 * @param known     - Whether the var name is present in `validVars`.
 *                    For ComposeToken tk-var callers this is `token.known`;
 *                    for VarSegment callers compute `validVars.has(seg.name)`.
 * @param validVars - The current set of known variable names.
 */
export function isMissingVar(known: boolean, validVars: ReadonlySet<string>): boolean {
  return validVars.size > 0 && !known
}

// ---------------------------------------------------------------------------
// Tokeniser
// ---------------------------------------------------------------------------

/**
 * Tokenises `text` into an ordered sequence of plain-text and variable-placeholder
 * segments for display-only highlighting of `{{variable}}` syntax.
 *
 * **Parsing rules**
 * - **Non-greedy / shortest match**: `{{a}}{{b}}` → two var segments (`a` and `b`),
 *   not one segment spanning `a}}{{b`.
 * - **Empty `{{}}`** → emitted as a plain-text segment (the literal four-character
 *   string `{{}}`). A var requires a non-empty inner run after trimming.
 * - **Unclosed `{{name`** (no matching `}}`) → emitted as plain text.
 * - **Trimmed name**: `{{ x }}` → var segment with `name === 'x'`.
 * - **Unrestricted names**: dots, dashes, and Unicode code points are all valid
 *   (e.g. `{{user.id}}`, `{{user-id}}`, `{{café}}`). Names are any non-`}}`
 *   run, trimmed, non-empty.
 * - **Empty input** (`""`) → returns `[]`.
 * - **Independent tokenisation**: the function is stateless; two separate calls
 *   never share state.
 *
 * @param text - The raw string to tokenise.
 * @returns An ordered array of {@link VarSegment} objects. May be empty.
 */
export function tokenizeVars(text: string): VarSegment[] {
  const segments: VarSegment[] = []

  // Non-greedy `.*?` ensures {{a}}{{b}} yields two distinct var segments rather
  // than one segment whose inner spans `a}}{{b`.
  // The `s` (dotAll) flag lets `.` match newlines inside a placeholder name.
  // The pattern is defined locally so each call gets its own `lastIndex` — no
  // shared state between calls.
  const pattern = /\{\{(.*?)\}\}/gs

  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    const fullMatch = match[0]
    const inner = match[1]
    const matchStart = match.index

    // Emit any plain text that precedes this match.
    if (matchStart > lastIndex) {
      segments.push({ kind: 'plain', text: text.slice(lastIndex, matchStart) })
    }

    const name = inner.trim()

    if (name.length > 0) {
      // Non-empty trimmed inner → valid var placeholder.
      // `raw` preserves the verbatim matched text (e.g. `{{ x }}`) so the
      // overlay renders character-identical content to the backing input.
      segments.push({ kind: 'var', name, raw: fullMatch })
    } else {
      // Empty {{}} → treat the entire token as plain text (the literal `{{}}`).
      segments.push({ kind: 'plain', text: fullMatch })
    }

    lastIndex = matchStart + fullMatch.length
  }

  // Emit any trailing plain text that follows the last match (or the whole
  // string if no match was found).
  if (lastIndex < text.length) {
    segments.push({ kind: 'plain', text: text.slice(lastIndex) })
  }

  return segments
}
