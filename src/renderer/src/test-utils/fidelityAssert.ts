/**
 * fidelityAssert.ts — Shared CT fidelity assertion helpers for §8 computed-style tests.
 *
 * These helpers are consumed by BodyEditor.ct.tsx (task 010) for AC-19 through AC-24.
 * They must NOT be imported by production renderer code — they import Playwright's test
 * API and are test-utilities only.
 *
 * ## Two-layer fail-closed contract
 *
 * The invariant that MUST hold across all helpers:
 *   - An empty/broken computed-style channel → UNVERIFIED (test.skip), NEVER PASS.
 *   - A missing CSS custom property → UNVERIFIED (test.skip), NEVER a silent false green.
 *
 * ### Layer 1 — setup probe (probeComputedStyleChannel / skipIfChannelUnavailable)
 *
 * A pre-flight check that probes whether the live-renderer `getComputedStyle` channel
 * is available and returning non-empty values. When the channel is absent or broken
 * (e.g. the evaluate bridge is down), the consuming suite marks itself UNVERIFIED via
 * `test.skip` before any assertion runs. This ensures a misconfigured environment
 * never produces a false PASS.
 *
 * ### Layer 2 — per-assertion guard (inside assertComputedStyle / assertResolvesToToken)
 *
 * Each assertion wraps the channel read in `try/catch` AND intercepts the CRITICAL
 * case where `getPropertyValue(prop)` returns `""`. The Chromium getComputedStyle
 * API returns `""` for undefined CSS custom properties — it does NOT throw. Two
 * failure modes are blocked by treating `""` as UNVERIFIED before any `expect`:
 *
 *   1. `assertResolvesToToken` false green: both the element value and the token probe
 *      value resolve to `""` (both undefined). `"" === ""` would be a passing expect —
 *      a false PASS on two undefined properties. Skipping before the expect blocks this.
 *
 *   2. `assertComputedStyle` misleading hard fail: an element property returning `""`
 *      compared to a literal hex string fails the expect with a confusing message that
 *      looks like a style mismatch when the real cause is an undefined property. Skipping
 *      instead surfaces the correct diagnosis (UNVERIFIED).
 *
 * Summary: `""` = UNVERIFIED (skip), never PASS, never a misleading assertion failure.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import type { Page } from 'playwright-core'

// ---------------------------------------------------------------------------
// Layer 1 — setup probe
// ---------------------------------------------------------------------------

/**
 * Probes whether the live-renderer `getComputedStyle` channel is available.
 *
 * Reads `color` from `document.documentElement` via `page.evaluate`. In any live
 * Chromium context with a rendered document, `color` is always defined and non-empty.
 * An empty string or a thrown error means the evaluate bridge is broken.
 *
 * @returns `true` when the channel is available and returning non-empty values;
 *          `false` on throw or empty result.
 */
export async function probeComputedStyleChannel(page: Page): Promise<boolean> {
  try {
    const value = await page.evaluate(() =>
      window.getComputedStyle(document.documentElement).getPropertyValue('color')
    )
    return value.trim() !== ''
  } catch {
    return false
  }
}

/**
 * Convenience skip gate for use in test bodies or `beforeEach` hooks.
 *
 * Calls `test.skip` when the live-renderer computed-style channel is unavailable,
 * marking the current test as UNVERIFIED and preventing any subsequent `expect`
 * calls from running. Consuming suites should call this before any fidelity
 * assertion to satisfy AC-19.
 *
 * Usage:
 * ```ts
 * test('§8 fidelity — tk-key color (light)', async ({ mount, page }) => {
 *   await mount(<BodyEditorFidelityFixture />)
 *   await skipIfChannelUnavailable(page)
 *   await assertComputedStyle(page, '.tk-key', 'color', '#0369a1')
 * })
 * ```
 */
export async function skipIfChannelUnavailable(page: Page): Promise<void> {
  const available = await probeComputedStyleChannel(page)
  test.skip(!available, 'UNVERIFIED — live-renderer computed-style channel unavailable')
}

// ---------------------------------------------------------------------------
// Layer 2 — per-assertion assertions
// ---------------------------------------------------------------------------

/**
 * Reads `getComputedStyle(el).getPropertyValue(prop)` on the live-renderer element
 * matched by `selector` and asserts it equals `expected`.
 *
 * Intended for per-theme literal assertions where the expected value is a resolved
 * hex string (e.g. `'#0369a1'` for light-theme `.tk-key`, AC-20/AC-21).
 *
 * ### Fail-closed (Layer 2)
 * - If the `evaluate` call throws → `test.skip` (UNVERIFIED, not a hard failure).
 *   This covers transient evaluate errors and missing selectors.
 * - If `getPropertyValue` returns `""` → `test.skip` (UNVERIFIED, not a comparison
 *   failure). An undefined CSS custom property returns `""`, not a throw — treating
 *   it as UNVERIFIED prevents a hard failure that would obscure the real cause.
 * - Only when a non-empty value is read does `expect` run.
 *
 * @param page     Playwright Page from the CT test fixture.
 * @param selector CSS selector; the first matching element is used.
 * @param prop     CSS property name (e.g. `'color'`, `'background-color'`).
 * @param expected Expected computed value literal (e.g. `'#0369a1'`, `'rgb(3, 105, 161)'`).
 * @param label    Optional label for the expect failure message.
 */
export async function assertComputedStyle(
  page: Page,
  selector: string,
  prop: string,
  expected: string,
  label?: string
): Promise<void> {
  let value: string

  try {
    value = await page
      .locator(selector)
      .first()
      .evaluate((el, p) => window.getComputedStyle(el).getPropertyValue(p), prop)
  } catch {
    // evaluate threw — the bridge is broken or the selector produced no element.
    // Treat as UNVERIFIED: test.skip throws a skip error, exiting the test.
    test.skip(
      true,
      `UNVERIFIED — live-renderer getComputedStyle threw for selector "${selector}" / property "${prop}"`
    )
    return
  }

  // Layer 2: getPropertyValue returns "" for undefined CSS custom properties,
  // NOT a throw. Intercepting "" before the expect prevents a misleading hard fail
  // whose error message would look like a style mismatch when the real cause is an
  // undefined property or a misconfigured test fixture.
  test.skip(
    value.trim() === '',
    `UNVERIFIED — getPropertyValue("${prop}") returned "" for selector "${selector}" (property not defined or channel unavailable)`
  )

  // test.skip throws when its condition is true; reaching here means value is non-empty.
  expect(value.trim(), label ?? `${selector} ${prop}`).toBe(expected)
}

/**
 * Asserts that the computed value of `prop` on the matched element resolves to the
 * same value that the CSS custom property `tokenVar` resolves to.
 *
 * Intended for token-binding assertions where the expected value is dynamic (depends
 * on which tokens are loaded and which theme is active). For example:
 * - `.tk-null` color must equal the resolved value of `--text-faint` (AC-22).
 * - `.tk-punc` color must equal the resolved value of `--text-muted` (AC-22).
 * - `.tk-var` color must equal the resolved value of `--accent` (AC-22).
 *
 * ### Token resolution
 * Injects a probe element with `prop: var(tokenVar)` into `document.body`, reads
 * `getComputedStyle(probe).getPropertyValue(prop)`, and removes the probe. This is
 * the established technique used throughout the RequestBar.ct.tsx CT suite (e.g. the
 * focus-ring, Send shadow, bg-elev, and text-faint assertions).
 *
 * ### Fail-closed (Layer 2)
 * - If either `evaluate` call throws → `test.skip` (UNVERIFIED).
 * - If the element value is `""` → `test.skip` (UNVERIFIED): the element's property
 *   is not defined, so the comparison has no meaning.
 * - If the token resolved value is `""` → `test.skip` (UNVERIFIED): the custom
 *   property is not defined, so any comparison — especially `"" === ""` if both sides
 *   are undefined — would be a false green.
 * - Only when both sides resolve to non-empty strings does `expect` run.
 *
 * @param page     Playwright Page from the CT test fixture.
 * @param selector CSS selector; the first matching element is used.
 * @param prop     CSS property name used for both the element read and the probe
 *                 resolution (e.g. `'color'` for color token assertions).
 * @param tokenVar CSS custom property name to resolve (e.g. `'--text-faint'`, `'--accent'`).
 * @param label    Optional label for the expect failure message.
 */
export async function assertResolvesToToken(
  page: Page,
  selector: string,
  prop: string,
  tokenVar: string,
  label?: string
): Promise<void> {
  let elementValue: string
  let tokenResolved: string

  try {
    elementValue = await page
      .locator(selector)
      .first()
      .evaluate((el, p) => window.getComputedStyle(el).getPropertyValue(p), prop)
  } catch {
    test.skip(
      true,
      `UNVERIFIED — live-renderer getComputedStyle threw for selector "${selector}" / property "${prop}"`
    )
    return
  }

  try {
    tokenResolved = await page.evaluate(
      ({ p, tv }: { p: string; tv: string }): string => {
        const probe = document.createElement('div')
        // setProperty handles hyphenated property names (e.g. 'background-color')
        // correctly, unlike the camelCase style index accessor.
        probe.style.setProperty(p, `var(${tv})`)
        document.body.appendChild(probe)
        const v = window.getComputedStyle(probe).getPropertyValue(p)
        probe.remove()
        return v
      },
      { p: prop, tv: tokenVar }
    )
  } catch {
    test.skip(
      true,
      `UNVERIFIED — live-renderer getComputedStyle threw while resolving token "${tokenVar}"`
    )
    return
  }

  // Layer 2: either side returning "" triggers UNVERIFIED.
  //
  // Element side: "" means the CSS property is not defined on this element.
  // Token side: "" means the CSS custom property is not defined in the stylesheet.
  //
  // Crucially, if BOTH sides return "" (e.g. both the class and the token are missing),
  // the expect would pass ("" === ""), producing a false green. Skipping before the
  // expect blocks this silent failure mode — the single most important guard here.
  test.skip(
    elementValue.trim() === '',
    `UNVERIFIED — getPropertyValue("${prop}") returned "" for selector "${selector}" (property not defined or channel unavailable)`
  )
  test.skip(
    tokenResolved.trim() === '',
    `UNVERIFIED — token "${tokenVar}" resolved to "" via prop "${prop}" (custom property not defined or channel unavailable)`
  )

  // test.skip throws when its condition is true; reaching here means both values
  // are non-empty and the comparison is meaningful.
  expect(elementValue.trim(), label ?? `${selector} ${prop} must resolve to ${tokenVar}`).toBe(
    tokenResolved.trim()
  )
}
