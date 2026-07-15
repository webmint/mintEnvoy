import { makeBlankRequest, BLANK_BODY } from '@renderer/lib/requestSpec'

// ---------------------------------------------------------------------------
// makeBlankRequest — per-call independence of nested body sub-objects.
//
// makeBlankRequest spreads the canonical BLANK_BODY but must freshen BOTH nested
// sub-objects (`raw` and `urlencoded`) so two blank tabs never alias the same
// object — a shared reference would let one tab's in-place mutation corrupt the
// other tab (and BLANK_BODY itself).
// ---------------------------------------------------------------------------
describe('makeBlankRequest — blank Body is fully de-aliased', () => {
  it('two calls return independent body.raw objects (not the same reference)', () => {
    const a = makeBlankRequest()
    const b = makeBlankRequest()
    expect(a.body.raw).not.toBe(b.body.raw)
    expect(a.body.urlencoded.rows).not.toBe(b.body.urlencoded.rows)
  })

  it('body.raw is not the BLANK_BODY.raw singleton reference', () => {
    const spec = makeBlankRequest()
    expect(spec.body.raw).not.toBe(BLANK_BODY.raw)
    expect(spec.body.urlencoded.rows).not.toBe(BLANK_BODY.urlencoded.rows)
  })

  it('mutating a blank spec.body.raw does not leak into BLANK_BODY or another spec', () => {
    const a = makeBlankRequest()
    a.body.raw.text = 'mutated'
    a.body.raw.lang = 'xml'
    const b = makeBlankRequest()
    expect(b.body.raw.text).toBe('')
    expect(b.body.raw.lang).toBe('json')
    expect(BLANK_BODY.raw.text).toBe('')
    expect(BLANK_BODY.raw.lang).toBe('json')
  })

  it('values still match the canonical seed', () => {
    const spec = makeBlankRequest()
    expect(spec.body).toEqual({ active: 'none', raw: { lang: 'json', text: '' }, urlencoded: { rows: [] } })
  })
})
