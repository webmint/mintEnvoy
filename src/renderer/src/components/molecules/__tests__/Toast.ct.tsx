/**
 * Toast.ct.tsx — Playwright Component Tests for the Toast molecule.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so @media queries such as prefers-reduced-motion are evaluated correctly,
 * unlike jsdom which does not support @media evaluation.
 *
 * Covers:
 *   - AC-14: prefers-reduced-motion: reduce disables the toast-slide-in animation.
 *   - AC-14: under no-preference, the slide-in animation is active.
 *   - Variant rendering: info, success, warning, and error variants each render
 *     with the expected icon aria-label and message text in real Chromium.
 *
 * Fixture components are imported from Toast.stories.tsx (Playwright CT requires
 * components to be defined outside the test file).
 */
import { test, expect } from '@playwright/experimental-ct-react'
import { ToastWithSeededMessage } from './Toast.stories'

// ---------------------------------------------------------------------------
// AC-14 — prefers-reduced-motion
// ---------------------------------------------------------------------------

test.describe('Toast — AC-14 reduced-motion', () => {
  test('toast-slide-in animation is disabled under prefers-reduced-motion: reduce', async ({
    mount,
    page
  }) => {
    // Emulate reduced-motion BEFORE mounting so the CSS @media rule is active
    // when the browser first evaluates the stylesheet.
    await page.emulateMedia({ reducedMotion: 'reduce' })

    // The fixture enqueues a toast via useEffect inside the browser context.
    await mount(<ToastWithSeededMessage message="Reduced-motion test" />)

    // Wait for the <li> toast root to appear in the viewport
    const toastLi = page.locator('li.toast').first()
    await expect(toastLi).toBeVisible()

    // Under prefers-reduced-motion: reduce, the CSS override sets animation: none
    // on .toast — so the computed animation-name must be "none".
    const animationName = await toastLi.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('animation-name')
    })

    expect(animationName).toBe('none')
  })

  test('toast-slide-in animation runs normally under no-preference', async ({ mount, page }) => {
    // Explicitly use no-preference to confirm the baseline animation is present.
    await page.emulateMedia({ reducedMotion: 'no-preference' })

    await mount(<ToastWithSeededMessage message="Motion-allowed test" />)

    const toastLi = page.locator('li.toast').first()
    await expect(toastLi).toBeVisible()

    const animationName = await toastLi.evaluate((el) => {
      return window.getComputedStyle(el).getPropertyValue('animation-name')
    })

    // The slide-in keyframe is named "toast-slide-in" in Toast.css.
    expect(animationName).toBe('toast-slide-in')
  })
})

// ---------------------------------------------------------------------------
// Variant rendering — icon + message in real Chromium
// Each variant maps to a specific icon aria-label (see VARIANT_LABEL in Toast.tsx)
// ---------------------------------------------------------------------------

test.describe('Toast — variant rendering', () => {
  test('info variant renders with Info icon and message', async ({ mount, page }) => {
    await mount(<ToastWithSeededMessage message="Info toast" variant="info" />)

    const toastLi = page.locator('li.toast--info').first()
    await expect(toastLi).toBeVisible()
    // Message text is present
    await expect(toastLi.getByText('Info toast')).toBeVisible()
    // Icon carries the variant aria-label (role="img" set by Icon when label is provided)
    await expect(toastLi.getByRole('img', { name: 'Info' })).toBeVisible()
  })

  test('success variant renders with Success icon and message', async ({ mount, page }) => {
    await mount(<ToastWithSeededMessage message="Success toast" variant="success" />)

    const toastLi = page.locator('li.toast--success').first()
    await expect(toastLi).toBeVisible()
    await expect(toastLi.getByText('Success toast')).toBeVisible()
    await expect(toastLi.getByRole('img', { name: 'Success' })).toBeVisible()
  })

  test('warning variant renders with Warning icon and message', async ({ mount, page }) => {
    await mount(<ToastWithSeededMessage message="Warning toast" variant="warning" />)

    const toastLi = page.locator('li.toast--warning').first()
    await expect(toastLi).toBeVisible()
    await expect(toastLi.getByText('Warning toast')).toBeVisible()
    await expect(toastLi.getByRole('img', { name: 'Warning' })).toBeVisible()
  })

  test('error variant renders with Error icon and message', async ({ mount, page }) => {
    await mount(<ToastWithSeededMessage message="Error toast" variant="error" />)

    const toastLi = page.locator('li.toast--error').first()
    await expect(toastLi).toBeVisible()
    await expect(toastLi.getByText('Error toast')).toBeVisible()
    await expect(toastLi.getByRole('img', { name: 'Error' })).toBeVisible()
  })
})
