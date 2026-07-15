/**
 * jsonTokens.ts
 *
 * Renderer-pure, display-only two-pass tokeniser for the body editor.
 *
 * Contract:
 *   - DISPLAY-ONLY: never resolves {{var}} values or serialises the body.
 *   - NO React / DOM / Node / electron imports (renderer-pure, constitution §2.2).
 *   - Fully typed — no `any` (constitution §3.1 strict mode).
 *   - Pure and stateless: same input always produces the same output.
 *
 * Two-pass ordering:
 *   1. JSON structural pass (only when `lang === 'json'`): tokenises JSON text into
 *      `tk-key` / `tk-str` / `tk-num` / `tk-bool` / `tk-null` / `tk-punc` tokens.
 *   2. {{var}} pass (ALL langs): tokenises `{{variable}}` placeholders via
 *      `tokenizeVars`; var-pass-wins — a `{{var}}` region inside a JSON string token
 *      is emitted as `tk-var`, not `tk-str` (AC-9).
 *
 * Degrade paths:
 *   - Empty input → `[]` (no tokens, no throw; AC-16).
 *   - Malformed JSON (lang === 'json') → a single plain segment covering the whole
 *     text, no throw, no error signal (AC-17).
 *   - `text.length > JSON_HIGHLIGHT_MAX_CHARS` → structural pass is skipped
 *     entirely; only the var pass (over plain text) runs (perf ceiling).
 *   - `lang !== 'json'` → structural pass is skipped; only the var pass runs (AC-10).
 */

import { tokenizeVars } from '@renderer/lib/varTokens'
import type { RawLang } from '@renderer/lib/requestSpec'

// ---------------------------------------------------------------------------
// Public constants
// ---------------------------------------------------------------------------

/**
 * Character-count ceiling above which the JSON structural pass is skipped to
 * avoid blocking the render thread on large documents. The `{{var}}` pass
 * (cheap, regex-only) still runs over the raw text; only the expensive
 * character-level JSON scanner is skipped.
 */
export const JSON_HIGHLIGHT_MAX_CHARS = 50_000

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A token segment produced by {@link compose}.
 *
 * Discriminated on `kind`:
 * - `'plain'`   — unstyled text; rendered with the default `var(--text)` colour.
 * - `'tk-key'`  — JSON object key (the string including surrounding quotes).
 * - `'tk-str'`  — JSON string value (including surrounding quotes).
 * - `'tk-num'`  — JSON number literal.
 * - `'tk-bool'` — JSON boolean literal (`true` or `false`).
 * - `'tk-null'` — JSON `null` literal.
 * - `'tk-punc'` — JSON structural punctuation: `{`, `}`, `[`, `]`, `:`, `,`.
 * - `'tk-var'`  — A `{{variable}}` placeholder. `text` is the verbatim raw match
 *                 (e.g. `{{ x }}`); `name` is the trimmed inner text for lookup;
 *                 `known` is true when `name` is in the `validVars` set passed
 *                 to `compose`.
 *
 * All segments are display-only. Callers map `kind` → CSS class / colour token.
 */
export type ComposeToken =
  | { kind: 'plain'; text: string }
  | { kind: 'tk-key'; text: string }
  | { kind: 'tk-str'; text: string }
  | { kind: 'tk-num'; text: string }
  | { kind: 'tk-bool'; text: string }
  | { kind: 'tk-null'; text: string }
  | { kind: 'tk-punc'; text: string }
  | { kind: 'tk-var'; text: string; name: string; known: boolean }

// ---------------------------------------------------------------------------
// Internal types (not exported — ComposeToken is the public interface)
// ---------------------------------------------------------------------------

/**
 * Raw output of the JSON structural scanner — every ComposeToken member except
 * `tk-var`, which is produced only by the subsequent var overlay step.
 */
type JsonToken =
  | { kind: 'plain'; text: string }
  | { kind: 'tk-key'; text: string }
  | { kind: 'tk-str'; text: string }
  | { kind: 'tk-num'; text: string }
  | { kind: 'tk-bool'; text: string }
  | { kind: 'tk-null'; text: string }
  | { kind: 'tk-punc'; text: string }

// ---------------------------------------------------------------------------
// Module-level sentinel — avoids per-call `new Set()` allocation.
// ---------------------------------------------------------------------------
const EMPTY_VALID_VARS: ReadonlySet<string> = new Set<string>()

// ---------------------------------------------------------------------------
// Internal — JSON structural scanner
// ---------------------------------------------------------------------------

/**
 * Scans `text` (caller-validated to be well-formed JSON via `JSON.parse`)
 * and emits a flat list of structural token segments for display colouring.
 *
 * Keys vs values are distinguished by tracking the current context (object
 * vs array) on a stack, plus a `colon-seen` flag to distinguish keys from
 * values within an object.
 */
function scanJsonTokens(text: string): JsonToken[] {
  const tokens: JsonToken[] = []
  // Stack of contexts: 'object' when inside {}, 'array' when inside [].
  const contextStack: Array<'object' | 'array'> = []
  // True when the next string token should be classified as a key.
  let expectKey = false
  let i = 0

  while (i < text.length) {
    const ch = text[i]

    // Whitespace — emitted as plain; preserves original formatting in the overlay.
    if (ch === ' ' || ch === '\t' || ch === '\r' || ch === '\n') {
      const start = i
      while (i < text.length) {
        const c = text[i]
        if (c !== ' ' && c !== '\t' && c !== '\r' && c !== '\n') break
        i++
      }
      tokens.push({ kind: 'plain', text: text.slice(start, i) })
      continue
    }

    // Double-quoted string — scan until the first unescaped closing quote.
    if (ch === '"') {
      const start = i
      i++
      while (i < text.length) {
        if (text[i] === '\\') {
          i += 2 // skip the backslash and the escaped character
        } else if (text[i] === '"') {
          i++
          break
        } else {
          i++
        }
      }
      // Classify: key when we are in an object and haven't seen ':' yet.
      if (expectKey) {
        tokens.push({ kind: 'tk-key', text: text.slice(start, i) })
      } else {
        tokens.push({ kind: 'tk-str', text: text.slice(start, i) })
      }
      expectKey = false
      continue
    }

    // Number — optional leading minus, integer part, optional fraction, optional exponent.
    if (ch === '-' || (ch >= '0' && ch <= '9')) {
      const start = i
      if (ch === '-') i++
      while (i < text.length && text[i] >= '0' && text[i] <= '9') i++
      if (i < text.length && text[i] === '.') {
        i++
        while (i < text.length && text[i] >= '0' && text[i] <= '9') i++
      }
      if (i < text.length && (text[i] === 'e' || text[i] === 'E')) {
        i++
        if (i < text.length && (text[i] === '+' || text[i] === '-')) i++
        while (i < text.length && text[i] >= '0' && text[i] <= '9') i++
      }
      tokens.push({ kind: 'tk-num', text: text.slice(start, i) })
      expectKey = false
      continue
    }

    // JSON keyword literals.
    if (text.startsWith('true', i)) {
      tokens.push({ kind: 'tk-bool', text: 'true' })
      i += 4
      expectKey = false
      continue
    }
    if (text.startsWith('false', i)) {
      tokens.push({ kind: 'tk-bool', text: 'false' })
      i += 5
      expectKey = false
      continue
    }
    if (text.startsWith('null', i)) {
      tokens.push({ kind: 'tk-null', text: 'null' })
      i += 4
      expectKey = false
      continue
    }

    // Structural punctuation — push, update context stack and expectKey accordingly.
    if (ch === '{') {
      tokens.push({ kind: 'tk-punc', text: ch })
      contextStack.push('object')
      expectKey = true // the first token inside an object is a key
      i++
      continue
    }
    if (ch === '}') {
      tokens.push({ kind: 'tk-punc', text: ch })
      contextStack.pop()
      expectKey = false
      i++
      continue
    }
    if (ch === '[') {
      tokens.push({ kind: 'tk-punc', text: ch })
      contextStack.push('array')
      expectKey = false // arrays hold values, not keys
      i++
      continue
    }
    if (ch === ']') {
      tokens.push({ kind: 'tk-punc', text: ch })
      contextStack.pop()
      expectKey = false // symmetric with '}' — closing punctuators never precede a key
      i++
      continue
    }
    if (ch === ':') {
      tokens.push({ kind: 'tk-punc', text: ch })
      expectKey = false // colon separates key from value; next is a value
      i++
      continue
    }
    if (ch === ',') {
      tokens.push({ kind: 'tk-punc', text: ch })
      // After a comma: next string is a key only when we are inside an object.
      const ctx = contextStack[contextStack.length - 1]
      expectKey = ctx === 'object'
      i++
      continue
    }

    // Fallback: unknown character — emit as a single plain segment.
    // Should not occur after JSON.parse validates the input, but included for safety.
    tokens.push({ kind: 'plain', text: ch })
    i++
  }

  return tokens
}

// ---------------------------------------------------------------------------
// Internal — var overlay inside a single JSON string token
// ---------------------------------------------------------------------------

/**
 * Overlays the `{{var}}` pass on one JSON string token (key or value).
 *
 * `rawStr` is the full string token text including the surrounding double
 * quotes. When no `{{var}}` placeholders are present, the original token is
 * returned unchanged (fast path). When at least one placeholder is found, the
 * token is split: surrounding quote characters are emitted as `tk-str`/`tk-key`
 * segments and `{{name}}` regions are emitted as `tk-var` tokens
 * (var-pass-wins, AC-9).
 */
function overlayVarsInJsonString(
  rawStr: string,
  kind: 'tk-str' | 'tk-key',
  validVars: ReadonlySet<string>
): ComposeToken[] {
  // Guard: too short to contain both quotes and content.
  if (rawStr.length < 2) return [{ kind, text: rawStr }]

  // Extract the content between the surrounding double quotes.
  const inner = rawStr.slice(1, rawStr.length - 1)
  const varSegs = tokenizeVars(inner)

  // Fast path: no var placeholders — return the original token unchanged.
  if (!varSegs.some(s => s.kind === 'var')) {
    return [{ kind, text: rawStr }]
  }

  // Slow path: split the string token so var regions become tk-var.
  const out: ComposeToken[] = []
  out.push({ kind, text: '"' }) // opening quote
  for (const seg of varSegs) {
    if (seg.kind === 'var') {
      out.push({ kind: 'tk-var', text: seg.raw, name: seg.name, known: validVars.has(seg.name) })
    } else {
      out.push({ kind, text: seg.text })
    }
  }
  out.push({ kind, text: '"' }) // closing quote
  return out
}

// ---------------------------------------------------------------------------
// Internal — var-pass-only conversion (non-JSON langs + degrade paths)
// ---------------------------------------------------------------------------

/**
 * Runs `tokenizeVars` on `text` and converts the output to `ComposeToken[]`.
 * Used for non-JSON langs (AC-10) and for the perf-ceiling degrade path.
 * `'var'` segments become `tk-var`; `'plain'` segments stay `plain`.
 */
function varPassOnly(text: string, validVars: ReadonlySet<string>): ComposeToken[] {
  return tokenizeVars(text).map((seg): ComposeToken => {
    if (seg.kind === 'var') {
      return { kind: 'tk-var', text: seg.raw, name: seg.name, known: validVars.has(seg.name) }
    }
    return { kind: 'plain', text: seg.text }
  })
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * compose(text, lang, validVars?)
 *
 * Two-pass display-only tokeniser for the body code area.
 *
 * **Pass 1 — JSON structural** (only when `lang === 'json'` AND
 * `text.length <= JSON_HIGHLIGHT_MAX_CHARS`):
 *   Emits `tk-key`, `tk-str`, `tk-num`, `tk-bool`, `tk-null`, `tk-punc`, and
 *   `plain` (whitespace) tokens from a character-level scanner.
 *
 * **Pass 2 — `{{var}}` overlay** (all langs):
 *   `tokenizeVars` is run on the content of each JSON string/key token (Pass 1)
 *   or on the raw text (non-JSON / degrade paths). `{{name}}` regions inside
 *   JSON strings take precedence over the enclosing `tk-str`/`tk-key` token —
 *   var-pass-wins (AC-9).
 *
 * **Degrade paths**:
 *   - Empty input → `[]` (AC-16).
 *   - Malformed JSON → `[{ kind: 'plain', text }]`, no throw (AC-17).
 *   - `text.length > JSON_HIGHLIGHT_MAX_CHARS` → structural pass skipped (perf ceiling).
 *   - `lang !== 'json'` → structural pass skipped; var pass only (AC-10).
 *
 * @param text      - Raw body text to tokenise for display.
 * @param lang      - Body language hint; only `'json'` activates the structural pass.
 * @param validVars - Known variable names for `tk-var` `known` flag. Optional;
 *                    defaults to an empty set (all vars reported as unknown).
 * @returns An ordered array of {@link ComposeToken} segments, possibly empty.
 *          Never throws.
 */
export function compose(
  text: string,
  lang: RawLang | string,
  validVars?: ReadonlySet<string>
): ComposeToken[] {
  // Empty input → zero tokens (AC-16).
  if (text.length === 0) return []

  const vars = validVars ?? EMPTY_VALID_VARS

  // Non-JSON lang or above the perf ceiling: skip the expensive structural pass.
  // The var pass has no size ceiling by design — it is a single regex sweep and
  // far cheaper than JSON.parse + the character-level scanner (AC-10 + perf ceiling).
  if (lang !== 'json' || text.length > JSON_HIGHLIGHT_MAX_CHARS) {
    return varPassOnly(text, vars)
  }

  // JSON structural pass + var overlay.
  // JSON.parse validates syntax first; any error is caught and degrades below.
  let jsonTokens: JsonToken[]
  try {
    JSON.parse(text) // Validation only — result is discarded; tokenisation uses our own scanner.
    jsonTokens = scanJsonTokens(text)
  } catch {
    // Malformed JSON: JSON.parse threw a SyntaxError. Return a single plain segment
    // covering the whole text (AC-17). This catch IS the error-handling path — not an
    // empty catch; returning here is the intentional degrade.
    return [{ kind: 'plain', text }]
  }

  // Apply the var overlay to each structural token.
  const result: ComposeToken[] = []
  for (const token of jsonTokens) {
    if (token.kind === 'tk-str' || token.kind === 'tk-key') {
      // Var-pass-wins inside JSON strings (AC-9): split the string token around
      // any {{var}} placeholders found in its content.
      result.push(...overlayVarsInJsonString(token.text, token.kind, vars))
    } else {
      // Whitespace and non-string structural tokens pass through unchanged.
      result.push(token)
    }
  }

  return result
}
