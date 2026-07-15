import { tokenizeVars, isMissingVar } from '@renderer/lib/varTokens'
import type { VarSegment } from '@renderer/lib/varTokens'

// ---------------------------------------------------------------------------
// Helpers — build expected segments without repeating shape literals.
// ---------------------------------------------------------------------------
const plain = (text: string): VarSegment => ({ kind: 'plain', text })
const varSeg = (name: string, raw: string): VarSegment => ({ kind: 'var', name, raw })

// ---------------------------------------------------------------------------
// isMissingVar — missing-var gate
// ---------------------------------------------------------------------------
describe('isMissingVar', () => {
  it('empty validVars → false regardless of known (pre-load neutral state)', () => {
    expect(isMissingVar(true, new Set())).toBe(false)
    expect(isMissingVar(false, new Set())).toBe(false)
  })

  it('non-empty validVars + known=true → false (var is recognised, not missing)', () => {
    expect(isMissingVar(true, new Set(['x', 'y']))).toBe(false)
  })

  it('non-empty validVars + known=false → true (env loaded, var is absent)', () => {
    expect(isMissingVar(false, new Set(['x', 'y']))).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Core parsing rules
// ---------------------------------------------------------------------------
describe('tokenizeVars — parsing rules', () => {
  it('single {{a}} → one var segment', () => {
    expect(tokenizeVars('{{a}}')).toEqual([varSeg('a', '{{a}}')])
  })

  it('adjacent {{a}}{{b}} → two var segments (non-greedy, not one spanning a}}{{b)', () => {
    expect(tokenizeVars('{{a}}{{b}}')).toEqual([varSeg('a', '{{a}}'), varSeg('b', '{{b}}')])
  })

  it('nested {{a{{b}}}} → shortest match gives var name "a{{b" plus trailing plain "}}"', () => {
    // Non-greedy regex finds the FIRST closing }} at position 6-7,
    // so the match is {{a{{b}} (inner: a{{b), leaving }} as plain text.
    expect(tokenizeVars('{{a{{b}}}}')).toEqual([varSeg('a{{b', '{{a{{b}}'), plain('}}')])
  })

  it('empty {{}} → plain literal "{{}}" (var requires non-empty inner)', () => {
    expect(tokenizeVars('{{}}')).toEqual([plain('{{}}')])
  })

  it('unclosed {{abc with no closing }} → plain text', () => {
    expect(tokenizeVars('{{abc')).toEqual([plain('{{abc')])
  })

  it('{{ x }} → var with trimmed name "x"', () => {
    expect(tokenizeVars('{{ x }}')).toEqual([varSeg('x', '{{ x }}')])
  })

  it('whitespace-only {{   }} → plain literal (trim-then-check, not raw-truthy check)', () => {
    expect(tokenizeVars('{{   }}')).toEqual([plain('{{   }}')])
  })
})

// ---------------------------------------------------------------------------
// Name character rules — dots, dashes, unicode
// ---------------------------------------------------------------------------
describe('tokenizeVars — name character rules', () => {
  it('unicode name {{café}} → var segment with name "café"', () => {
    expect(tokenizeVars('{{café}}')).toEqual([varSeg('café', '{{café}}')])
  })

  it('dot name {{user.id}} → var segment with name "user.id"', () => {
    expect(tokenizeVars('{{user.id}}')).toEqual([varSeg('user.id', '{{user.id}}')])
  })

  it('dash name {{user-id}} → var segment with name "user-id"', () => {
    expect(tokenizeVars('{{user-id}}')).toEqual([varSeg('user-id', '{{user-id}}')])
  })
})

// ---------------------------------------------------------------------------
// Mixed / plain / empty inputs
// ---------------------------------------------------------------------------
describe('tokenizeVars — mixed and edge inputs', () => {
  it('mixed plain+var: "a{{b}}c" → [plain a, var b, plain c]', () => {
    expect(tokenizeVars('a{{b}}c')).toEqual([plain('a'), varSeg('b', '{{b}}'), plain('c')])
  })

  it('multiple vars interleaved: "a{{b}}c{{d}}e" → 5 segments alternating plain/var/plain/var/plain', () => {
    expect(tokenizeVars('a{{b}}c{{d}}e')).toEqual([
      plain('a'),
      varSeg('b', '{{b}}'),
      plain('c'),
      varSeg('d', '{{d}}'),
      plain('e')
    ])
  })

  it('plain-only "hello" → [plain "hello"]', () => {
    expect(tokenizeVars('hello')).toEqual([plain('hello')])
  })

  it('empty string "" → [] (locked decision: empty input produces no segments)', () => {
    expect(tokenizeVars('')).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// Independence — two different inputs tokenise without shared state
// ---------------------------------------------------------------------------
describe('tokenizeVars — field-agnostic independence', () => {
  it('key text and value text tokenise independently', () => {
    // Simulate a table row: key cell and value cell are tokenised separately.
    const keySegments = tokenizeVars('{{key}}')
    const valueSegments = tokenizeVars('Hello {{name}}, welcome!')

    // Key result must not be polluted by the value call (and vice versa).
    expect(keySegments).toEqual([varSeg('key', '{{key}}')])
    expect(valueSegments).toEqual([
      plain('Hello '),
      varSeg('name', '{{name}}'),
      plain(', welcome!')
    ])
  })

  it('repeated calls on the same input produce identical results (stateless)', () => {
    const input = '{{a}}middle{{b}}'
    const first = tokenizeVars(input)
    const second = tokenizeVars(input)
    expect(first).toEqual(second)
  })
})

// ---------------------------------------------------------------------------
// Raw-preservation — desync fix regression lock
// ---------------------------------------------------------------------------
describe('tokenizeVars — raw field preservation', () => {
  it('padded token {{ x }} preserves raw verbatim while name is trimmed (desync fix lock)', () => {
    // name must be trimmed for validVars lookup; raw must be verbatim for overlay display.
    expect(tokenizeVars('{{ x }}')[0]).toEqual({ kind: 'var', name: 'x', raw: '{{ x }}' })
  })
})
