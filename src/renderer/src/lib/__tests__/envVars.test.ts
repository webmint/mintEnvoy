import { envVars } from '@renderer/lib/envVars'

describe('envVars', () => {
  it('returns an empty set', () => {
    expect(envVars().size).toBe(0)
  })

  it('returns the SAME reference across calls (stable identity — anti-identity-loop guard)', () => {
    expect(envVars()).toBe(envVars())
  })

  it('the returned set is frozen — a caller cannot mutate the shared sentinel', () => {
    const set = envVars()
    expect(Object.isFrozen(set)).toBe(true)
  })
})
