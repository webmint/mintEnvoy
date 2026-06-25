/**
 * Shared test fixtures for RequestSpec and Tab.
 *
 * Centralises the `makeSpec` and `makeTab` helpers so test files across the
 * project can share the same canonical factories instead of duplicating them.
 */
import { makeBlankRequest } from '@renderer/lib/requestSpec'
import type { RequestSpec } from '@renderer/lib/requestSpec'
import type { Tab } from '@renderer/lib/tabsStore'

/**
 * Build a partial RequestSpec merged over a blank seed.
 * Keeps test data DRY without resorting to `any`.
 *
 * @param overrides - Fields to override on the blank-request seed.
 * @returns A fully-typed RequestSpec with sensible defaults.
 */
export function makeSpec(overrides: Partial<RequestSpec> = {}): RequestSpec {
  return { ...makeBlankRequest(), ...overrides }
}

/**
 * Build a Tab fixture with sensible defaults and optional overrides.
 * Every field is explicitly typed — no `any`.
 *
 * @param id           - The unique tab identifier.
 * @param specOverrides  - Fields to override on the blank-request seed spec.
 * @param tabOverrides   - Fields to override on the tab (excluding id and spec).
 * @returns A fully-typed Tab with `collectionRequestId: null` and `dirty: false` by default.
 */
export function makeTab(
  id: string,
  specOverrides: Partial<RequestSpec> = {},
  tabOverrides: Partial<Omit<Tab, 'id' | 'spec'>> = {}
): Tab {
  return {
    id,
    collectionRequestId: null,
    spec: makeSpec(specOverrides),
    dirty: false,
    ...tabOverrides
  }
}
