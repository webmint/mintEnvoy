import { resolveIcon } from '@renderer/lib/icons-glue'
import { ICONS } from '@renderer/components/atoms/icons'

const FALLBACK_MARKUP = '<path d="M8 2l6 6-6 6-6-6 6-6z"/>'

describe('resolveIcon', () => {
  it('returns the exact fallback entry for an unknown name', () => {
    const entry = resolveIcon('__nope__')
    expect(entry.name).toBe('unknown')
    expect(entry.markup).toBe(FALLBACK_MARKUP)
  })

  it('returns the fallback entry for every edge-case input', () => {
    const edgeInputs = ['', '   ', 'SEND', 'undefined']
    for (const input of edgeInputs) {
      const entry = resolveIcon(input)
      expect(entry.name).toBe('unknown')
      expect(typeof entry.markup).toBe('string')
    }
  })

  it('never throws for any string input', () => {
    const inputs = ['', '   ', 'SEND', 'Send', '__unknown__', 'null', 'undefined']
    for (const input of inputs) {
      expect(() => resolveIcon(input)).not.toThrow()
    }
  })

  it('is case-sensitive: SEND does not match the lowercase send key', () => {
    // 'send' is a valid icon name; 'SEND' (uppercase) is not
    expect(resolveIcon('SEND').name).toBe('unknown')
  })

  it('rejects prototype keys — Object.hasOwn guards against toString, valueOf, etc.', () => {
    const entry = resolveIcon('toString')
    expect(entry.name).toBe('unknown')
    expect(typeof entry.markup).toBe('string')
    expect(entry.markup).toBe(FALLBACK_MARKUP)
  })

  it('resolves a known icon name to its markup', () => {
    const entry = resolveIcon('send')
    expect(entry.name).toBe('send')
    expect(entry.markup).toBe(ICONS.send)
  })

  it('resolves every icon in the ICONS registry', () => {
    const names = Object.keys(ICONS) as Array<keyof typeof ICONS>
    for (const name of names) {
      const entry = resolveIcon(name)
      expect(entry.name).toBe(name)
      expect(entry.markup).toBe(ICONS[name])
    }
  })

  it('returns the fallback for null-ish coerced to string', () => {
    // Callers passing String(null) or String(undefined) should still get a safe fallback.
    expect(() => resolveIcon(String(null))).not.toThrow()
    expect(resolveIcon(String(null)).name).toBe('unknown')
  })
})
