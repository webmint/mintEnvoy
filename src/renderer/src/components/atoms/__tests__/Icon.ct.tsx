/**
 * Icon.ct.tsx — Playwright Component Tests for the Icon atom.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so @media queries such as prefers-reduced-motion are evaluated correctly,
 * unlike jsdom which does not support @media evaluation.
 *
 * Covers:
 *   - AC-14: prefers-reduced-motion: reduce disables the icon--spin animation
 */
import { test, expect } from '@playwright/experimental-ct-react'
import { Icon } from '@renderer/components/atoms/Icon'

test.describe('Icon — AC-14 reduced-motion', () => {
  test('icon--spin animation is disabled under prefers-reduced-motion: reduce', async ({
    mount,
    page
  }) => {
    // Emulate the reduced-motion media feature before mounting so the
    // CSS @media (prefers-reduced-motion: reduce) rule is in effect.
    await page.emulateMedia({ reducedMotion: 'reduce' })

    const component = await mount(<Icon name="cog" className="icon--spin" />)

    // Retrieve the computed animation-name value from the rendered SVG.
    // Under prefers-reduced-motion: reduce, the Icon.css override sets
    // animation: none, so the computed animation-name must be "none".
    const animationName = await component.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('animation-name')
    })

    expect(animationName).toBe('none')
  })

  test('icon--spin animation runs normally without reduced-motion preference', async ({
    mount,
    page
  }) => {
    // Explicitly use the "no-preference" setting to confirm the baseline.
    await page.emulateMedia({ reducedMotion: 'no-preference' })

    const component = await mount(<Icon name="cog" className="icon--spin" />)

    const animationName = await component.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('animation-name')
    })

    // The spin animation keyframe is named "icon-spin".
    expect(animationName).toBe('icon-spin')
  })
})
