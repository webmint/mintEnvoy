import { compose, JSON_HIGHLIGHT_MAX_CHARS } from '@renderer/lib/jsonTokens'
import type { ComposeToken } from '@renderer/lib/jsonTokens'

// ---------------------------------------------------------------------------
// Helpers — build expected segments without repeating shape literals.
// ---------------------------------------------------------------------------
const plain = (text: string): ComposeToken => ({ kind: 'plain', text })
const tkKey = (text: string): ComposeToken => ({ kind: 'tk-key', text })
const tkStr = (text: string): ComposeToken => ({ kind: 'tk-str', text })
const tkNum = (text: string): ComposeToken => ({ kind: 'tk-num', text })
const tkBool = (text: string): ComposeToken => ({ kind: 'tk-bool', text })
const tkNull = (): ComposeToken => ({ kind: 'tk-null', text: 'null' })
const tkPunc = (text: string): ComposeToken => ({ kind: 'tk-punc', text })
const tkVar = (text: string, name: string, known = false): ComposeToken => ({
  kind: 'tk-var',
  text,
  name,
  known
})

// Kinds that the JSON structural pass produces.
const STRUCTURAL_KINDS: ReadonlyArray<ComposeToken['kind']> = [
  'tk-key',
  'tk-str',
  'tk-num',
  'tk-bool',
  'tk-null',
  'tk-punc'
]

// ---------------------------------------------------------------------------
// Empty input
// ---------------------------------------------------------------------------
describe('compose — empty input', () => {
  it('empty string → [] (AC-16)', () => {
    expect(compose('', 'json')).toEqual([])
  })

  it('empty string with non-json lang → []', () => {
    expect(compose('', 'xml')).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// Malformed JSON (AC-17)
// ---------------------------------------------------------------------------
describe('compose — malformed JSON (AC-17)', () => {
  it('{ "a": } → single plain segment, no throw', () => {
    const text = '{ "a": }'
    expect(compose(text, 'json')).toEqual([plain(text)])
  })

  it('{unclosed → single plain segment', () => {
    const text = '{"key": '
    expect(compose(text, 'json')).toEqual([plain(text)])
  })

  it('bare identifier (not valid JSON) → single plain segment', () => {
    const text = 'notjson'
    expect(compose(text, 'json')).toEqual([plain(text)])
  })

  it('does not throw on malformed JSON', () => {
    expect(() => compose('{ bad json }', 'json')).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Non-JSON lang — var pass only (AC-10)
// ---------------------------------------------------------------------------
describe('compose — non-JSON lang (AC-10)', () => {
  it('xml lang: no structural tokens emitted', () => {
    const result = compose('<foo>hello</foo>', 'xml')
    for (const token of result) {
      expect(STRUCTURAL_KINDS).not.toContain(token.kind)
    }
  })

  it('xml lang with {{bar}}: tk-var token emitted, no structural tokens', () => {
    const text = '<foo>{{bar}}</foo>'
    const result = compose(text, 'xml')
    for (const token of result) {
      expect(STRUCTURAL_KINDS).not.toContain(token.kind)
    }
    expect(result.some(t => t.kind === 'tk-var' && (t as { name: string }).name === 'bar')).toBe(true)
  })

  it('text lang: plain text emitted as plain segment, no structural tokens', () => {
    const text = 'hello world'
    const result = compose(text, 'text')
    expect(result).toEqual([plain('hello world')])
  })

  it('html lang with {{name}}: var pass produces tk-var', () => {
    const text = '<h1>{{name}}</h1>'
    const result = compose(text, 'html')
    expect(result.some(t => t.kind === 'tk-var')).toBe(true)
    expect(result.find(t => t.kind === 'tk-var')).toEqual(tkVar('{{name}}', 'name'))
  })

  it('padded var name {{  greeting  }} in non-JSON lang: name trimmed, text verbatim', () => {
    // Guards the trim path for the var pass outside of JSON strings.
    const result = compose('{{  greeting  }}', 'text')
    expect(result).toEqual([tkVar('{{  greeting  }}', 'greeting')])
  })
})

// ---------------------------------------------------------------------------
// Perf ceiling — above JSON_HIGHLIGHT_MAX_CHARS
// ---------------------------------------------------------------------------
describe('compose — perf ceiling', () => {
  it('text.length > JSON_HIGHLIGHT_MAX_CHARS → no structural tokens (uses constant, not literal)', () => {
    // Build a string that is exactly one character above the ceiling.
    // Content does not need to be valid JSON — structural pass is never reached.
    const longText = 'x'.repeat(JSON_HIGHLIGHT_MAX_CHARS + 1)
    const result = compose(longText, 'json')
    for (const token of result) {
      expect(STRUCTURAL_KINDS).not.toContain(token.kind)
    }
  })

  it('text.length === JSON_HIGHLIGHT_MAX_CHARS → structural pass DOES run (valid JSON)', () => {
    // At exactly the ceiling, structural pass should still be attempted.
    // "null" is 4 characters, well under 50 000; pad to exactly the threshold
    // with surrounding whitespace which JSON.parse accepts on valid JSON values.
    // We just verify structural tokens are present (tk-null).
    const padding = ' '.repeat(JSON_HIGHLIGHT_MAX_CHARS - 4)
    const atThreshold = padding + 'null'
    expect(atThreshold.length).toBe(JSON_HIGHLIGHT_MAX_CHARS)
    const result = compose(atThreshold, 'json')
    expect(result.some(t => t.kind === 'tk-null')).toBe(true)
  })

  it('long non-json text above threshold: var pass still runs', () => {
    const base = 'hello {{x}} world'
    const longText = base.repeat(Math.ceil((JSON_HIGHLIGHT_MAX_CHARS + 1) / base.length))
    const result = compose(longText, 'json')
    // Should have tk-var tokens (var pass ran) but no structural tokens.
    expect(result.some(t => t.kind === 'tk-var')).toBe(true)
    for (const token of result) {
      expect(STRUCTURAL_KINDS).not.toContain(token.kind)
    }
  })
})

// ---------------------------------------------------------------------------
// var-pass-wins inside JSON strings (AC-9)
// ---------------------------------------------------------------------------
describe('compose — var-pass-wins inside JSON strings (AC-9)', () => {
  it('JSON string value containing {{x}} → {{x}} region is tk-var, surrounding text is tk-str', () => {
    const text = '{"key": "hello {{x}} world"}'
    const result = compose(text, 'json')

    // The {{x}} region must be a tk-var token.
    const varToken = result.find(t => t.kind === 'tk-var')
    expect(varToken).toEqual(tkVar('{{x}}', 'x'))

    // The surrounding string portions must be tk-str (not merged into one token).
    const strTokens = result.filter(t => t.kind === 'tk-str')
    const strTexts = strTokens.map(t => t.text)
    expect(strTexts.some(t => t.includes('hello'))).toBe(true)
    expect(strTexts.some(t => t.includes('world'))).toBe(true)

    // Sanity: the key "key" must be a tk-key token.
    expect(result.some(t => t.kind === 'tk-key' && t.text === '"key"')).toBe(true)
  })

  it('JSON key containing {{dynamic}} → {{dynamic}} region is tk-var, surrounding quotes are tk-key', () => {
    const text = '{"{{dynamic}}": 1}'
    const result = compose(text, 'json')
    expect(result.some(t => t.kind === 'tk-var' && (t as { name: string }).name === 'dynamic')).toBe(true)
    // The surrounding quotes must be tk-key tokens, not collapsed into the var.
    expect(result.some(t => t.kind === 'tk-key' && t.text === '"')).toBe(true)
  })

  it('JSON string value with NO {{var}}: emitted as a single tk-str (fast path)', () => {
    const text = '{"key": "plain string"}'
    const result = compose(text, 'json')
    expect(result.some(t => t.kind === 'tk-var')).toBe(false)
    expect(result.some(t => t.kind === 'tk-str' && t.text === '"plain string"')).toBe(true)
  })

  it('multiple {{vars}} inside a JSON string all become tk-var tokens', () => {
    const text = '{"msg": "{{greeting}} {{name}}"}'
    const result = compose(text, 'json')
    const varTokens = result.filter(t => t.kind === 'tk-var')
    expect(varTokens).toHaveLength(2)
    expect(varTokens[0]).toEqual(tkVar('{{greeting}}', 'greeting'))
    expect(varTokens[1]).toEqual(tkVar('{{name}}', 'name'))
  })

  it('known validVars sets known:true on matching tk-var tokens', () => {
    const text = '{"v": "{{known}} {{unknown}}"}'
    const result = compose(text, 'json', new Set(['known']))
    const varTokens = result.filter(t => t.kind === 'tk-var') as Array<{
      kind: 'tk-var'
      text: string
      name: string
      known: boolean
    }>
    const knownToken = varTokens.find(t => t.name === 'known')
    const unknownToken = varTokens.find(t => t.name === 'unknown')
    expect(knownToken?.known).toBe(true)
    expect(unknownToken?.known).toBe(false)
  })

  it('tk-var.text carries the full verbatim raw — full toEqual on the token shape', () => {
    // Pins that text === the full braced literal (not just name), and known defaults to false.
    const text = '{"key": "hello {{x}} world"}'
    const result = compose(text, 'json')
    const varToken = result.find(t => t.kind === 'tk-var')
    expect(varToken).toEqual({ kind: 'tk-var', text: '{{x}}', name: 'x', known: false })
  })

  it('padded var name {{ x }} inside JSON string: name is trimmed, text is verbatim raw', () => {
    // Guards against a broken/absent trim: name must be 'x', not '  x  ' or ' x '.
    const result = compose('{"v": "{{ x }}"}', 'json')
    const varToken = result.find(t => t.kind === 'tk-var')
    expect(varToken).toEqual({ kind: 'tk-var', text: '{{ x }}', name: 'x', known: false })
  })

  it('empty {{}} inside JSON string: NOT a tk-var (tokenizeVars treats it as plain)', () => {
    // {{}} has empty inner text after trim → plain literal per tokenizeVars contract.
    const text = '{"v": "{{}}"}'
    const result = compose(text, 'json')
    expect(result.some(t => t.kind === 'tk-var')).toBe(false)
    // The {{}} content must appear inside a tk-str token.
    const strTokens = result.filter(t => t.kind === 'tk-str')
    expect(strTokens.some(t => t.text.includes('{{}}'))).toBe(true)
  })

  it('known defaults to false when validVars is omitted', () => {
    const result = compose('{"v": "{{myVar}}"}', 'json')
    const varToken = result.find(t => t.kind === 'tk-var') as
      | { kind: 'tk-var'; text: string; name: string; known: boolean }
      | undefined
    expect(varToken).toBeDefined()
    expect(varToken?.known).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// JSON structural tokenisation (well-formed JSON)
// ---------------------------------------------------------------------------
describe('compose — JSON structural tokens', () => {
  it('simple object: keys, values, punctuation all tokenised', () => {
    const result = compose('{"a": 1}', 'json')
    expect(result).toEqual([
      tkPunc('{'),
      tkKey('"a"'),
      tkPunc(':'),
      plain(' '),
      tkNum('1'),
      tkPunc('}')
    ])
  })

  it('boolean and null literals', () => {
    const result = compose('[true, false, null]', 'json')
    expect(result).toContainEqual(tkBool('true'))
    expect(result).toContainEqual(tkBool('false'))
    expect(result).toContainEqual(tkNull())
  })

  it('nested object: inner keys are classified as tk-key', () => {
    const result = compose('{"outer": {"inner": 2}}', 'json')
    const keys = result.filter(t => t.kind === 'tk-key').map(t => t.text)
    expect(keys).toContain('"outer"')
    expect(keys).toContain('"inner"')
  })

  it('array of strings: elements are tk-str, not tk-key', () => {
    const result = compose('["a", "b"]', 'json')
    const strTokens = result.filter(t => t.kind === 'tk-str')
    expect(strTokens.map(t => t.text)).toContain('"a"')
    expect(strTokens.map(t => t.text)).toContain('"b"')
    expect(result.some(t => t.kind === 'tk-key')).toBe(false)
  })

  it('top-level string value: tk-str (not tk-key)', () => {
    const result = compose('"hello"', 'json')
    expect(result).toEqual([tkStr('"hello"')])
  })

  it('top-level number: tk-num', () => {
    const result = compose('42', 'json')
    expect(result).toEqual([tkNum('42')])
  })

  it('negative number: tk-num', () => {
    const result = compose('-3.14', 'json')
    expect(result).toEqual([tkNum('-3.14')])
  })
})
