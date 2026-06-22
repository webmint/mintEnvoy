/**
 * nested-overlays.ct.tsx — Playwright Component Tests for AC-12 nested-overlay
 * composition.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so Radix DismissableLayer stacking, focus-trap nesting, and z-order CSS are
 * evaluated correctly — jsdom cannot do focus/Escape-layering reliably.
 *
 * Covers AC-12:
 *   - Escape closes ONLY the topmost overlay (dropdown inside modal → Escape
 *     closes dropdown, modal stays open; second Escape closes modal).
 *   - Focus returns correctly at each Escape step.
 *   - z-order: toast-viewport renders above the modal scrim (z-index comparison).
 *
 * Fixture is imported from nested-overlays.stories.tsx (Playwright CT requires
 * components to be defined outside the test file).
 */

import { test, expect } from '@playwright/experimental-ct-react'
import { NestedOverlayFixture, ReducedMotionComposedFixture } from './nested-overlays.stories'

// ---------------------------------------------------------------------------
// AC-12 — Escape closes only the topmost overlay
// ---------------------------------------------------------------------------

test.describe('NestedOverlays — AC-12 Escape closes topmost overlay only', () => {
  test('Escape on dropdown closes it; modal stays open; second Escape closes modal', async ({
    mount,
    page
  }) => {
    await mount(<NestedOverlayFixture />)

    // Open the modal via the trigger button
    const modalTrigger = page.getByTestId('ct-overlay-modal-trigger')
    await modalTrigger.click()

    // Modal must be visible
    const modalContent = page.locator('.modal-content').first()
    await expect(modalContent).toBeVisible()
    await expect(page.getByTestId('ct-overlay-modal-status')).toHaveText('open')

    // Open the dropdown that lives inside the modal
    const dropdownTrigger = page.getByTestId('ct-overlay-dropdown-trigger')
    await dropdownTrigger.click()

    // Dropdown menu must be visible
    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()
    await expect(page.getByTestId('ct-overlay-dropdown-status')).toHaveText('open')

    // Focus a menu item so Radix DismissableLayer captures the Escape event
    await page.getByRole('menuitem').first().focus()

    // First Escape — should close ONLY the dropdown (topmost layer)
    await page.keyboard.press('Escape')

    // Dropdown must be gone; modal must STILL be open
    await expect(menu).not.toBeVisible()
    await expect(page.getByTestId('ct-overlay-dropdown-status')).toHaveText('closed')
    await expect(modalContent).toBeVisible()
    await expect(page.getByTestId('ct-overlay-modal-status')).toHaveText('open')

    // Second Escape — should close the modal
    await page.keyboard.press('Escape')

    await expect(modalContent).not.toBeVisible()
    await expect(page.getByTestId('ct-overlay-modal-status')).toHaveText('closed')
  })
})

// ---------------------------------------------------------------------------
// AC-12 — focus returns correctly after each Escape step
// ---------------------------------------------------------------------------

test.describe('NestedOverlays — AC-12 focus return at each close', () => {
  test('focus returns to dropdown trigger after Escape closes dropdown; then to modal trigger after modal closes', async ({
    mount,
    page
  }) => {
    await mount(<NestedOverlayFixture />)

    // Open modal — focus the trigger first so Radix FocusScope captures it as the
    // return-focus target (same pattern as the Dropdown CT focus-return test).
    const modalTrigger = page.getByTestId('ct-overlay-modal-trigger')
    await modalTrigger.focus()
    await modalTrigger.click()
    await expect(page.locator('.modal-content').first()).toBeVisible()

    // Open dropdown via click (pointer-open; focus is on dropdown trigger before click)
    const dropdownTrigger = page.getByTestId('ct-overlay-dropdown-trigger')
    await dropdownTrigger.focus()
    await dropdownTrigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Focus a menu item so Escape reaches DismissableLayer
    await page.getByRole('menuitem').first().focus()

    // Escape: dropdown closes → focus should return to the dropdown trigger (AC-3 / AC-12)
    await page.keyboard.press('Escape')
    await expect(menu).not.toBeVisible()
    await expect(dropdownTrigger).toBeFocused()

    // Escape: modal closes → focus should return to the modal trigger button
    await page.keyboard.press('Escape')
    await expect(page.locator('.modal-content').first()).not.toBeVisible()

    // Radix Dialog FocusScope returns focus to the element that was focused before
    // the modal opened.  We clicked modalTrigger — verify focus returns there.
    await expect(modalTrigger).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// AC-12 — single-layer Escape: only modal open, no dropdown
// ---------------------------------------------------------------------------

test.describe('NestedOverlays — AC-12 single-modal Escape closes modal and returns focus', () => {
  test('Escape with only the modal open closes it and returns focus to its trigger', async ({
    mount,
    page
  }) => {
    await mount(<NestedOverlayFixture />)

    // Focus the trigger before clicking so Radix Dialog can record the return-focus target
    const modalTrigger = page.getByTestId('ct-overlay-modal-trigger')
    await modalTrigger.focus()
    await modalTrigger.click()

    const modalContent = page.locator('.modal-content').first()
    await expect(modalContent).toBeVisible()
    await expect(page.getByTestId('ct-overlay-modal-status')).toHaveText('open')

    // Dropdown is NOT opened — this is the single-layer (modal-only) case
    await expect(page.getByTestId('ct-overlay-dropdown-status')).toHaveText('closed')

    // Press Escape — topmost (and only) overlay is the modal, so it must close
    await page.keyboard.press('Escape')

    await expect(modalContent).not.toBeVisible()
    await expect(page.getByTestId('ct-overlay-modal-status')).toHaveText('closed')

    // Focus must return to the modal trigger (Radix Dialog FocusScope behaviour)
    await expect(modalTrigger).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// Composed reduced-motion: Modal + Toast both disable animations simultaneously
// ---------------------------------------------------------------------------

test.describe('NestedOverlays — composed reduced-motion (Modal + Toast)', () => {
  test('both modal-content/modal-overlay and toast have animation-name:none under prefers-reduced-motion:reduce', async ({
    mount,
    page
  }) => {
    // Emulate reduced-motion BEFORE mounting so the CSS @media rule applies to
    // all stylesheets from the first paint.
    await page.emulateMedia({ reducedMotion: 'reduce' })

    // ReducedMotionComposedFixture opens the modal and fires a toast immediately.
    await mount(<ReducedMotionComposedFixture />)

    // Both the modal content panel and the toast must be in the DOM.
    const modalContent = page.locator('.modal-content').first()
    const modalOverlay = page.locator('.modal-overlay').first()
    const toastLi = page.locator('li.toast').first()

    await expect(modalContent).toBeVisible()
    await expect(modalOverlay).toBeVisible()
    await expect(toastLi).toBeVisible()

    // Assert all three elements have animation disabled.
    const modalContentAnim = await modalContent.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )
    const modalOverlayAnim = await modalOverlay.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )
    const toastAnim = await toastLi.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )

    expect(modalContentAnim).toBe('none')
    expect(modalOverlayAnim).toBe('none')
    expect(toastAnim).toBe('none')
  })

  test('both modal-content/modal-overlay and toast have active keyframe animations under no-preference', async ({
    mount,
    page
  }) => {
    // Explicitly set no-preference to confirm the baseline animations are present —
    // proving that suppression is media-query-conditional, not unconditional.
    await page.emulateMedia({ reducedMotion: 'no-preference' })

    await mount(<ReducedMotionComposedFixture />)

    const modalContent = page.locator('.modal-content').first()
    const modalOverlay = page.locator('.modal-overlay').first()
    const toastLi = page.locator('li.toast').first()

    await expect(modalContent).toBeVisible()
    await expect(modalOverlay).toBeVisible()
    await expect(toastLi).toBeVisible()

    const modalContentAnim = await modalContent.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )
    const modalOverlayAnim = await modalOverlay.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )
    const toastAnim = await toastLi.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )

    // Under no-preference, each element's enter keyframe must be active (NOT 'none').
    expect(modalContentAnim).toBe('modal-content-in')
    expect(modalOverlayAnim).toBe('modal-overlay-in')
    expect(toastAnim).toBe('toast-slide-in')
  })
})

// ---------------------------------------------------------------------------
// AC-12 — z-order: toast renders above the modal scrim
// ---------------------------------------------------------------------------

test.describe('NestedOverlays — AC-12 toast renders above modal scrim', () => {
  test('toast-viewport z-index is greater than modal-overlay z-index', async ({ mount, page }) => {
    await mount(<NestedOverlayFixture />)

    // Open modal so the overlay is in the DOM
    await page.getByTestId('ct-overlay-modal-trigger').click()
    await expect(page.locator('.modal-content').first()).toBeVisible()

    // Fire a toast from inside the modal
    await page.getByTestId('ct-overlay-toast-btn').click()

    // Wait for the toast to appear in the viewport
    const toastItem = page.locator('li.toast').first()
    await expect(toastItem).toBeVisible()

    // Compare z-index values: toast-viewport must be above modal-overlay
    const zOrder = await page.evaluate(() => {
      const viewport = document.querySelector('.toast-viewport')
      const overlay = document.querySelector('.modal-overlay')
      if (!viewport || !overlay) return { viewportZ: null, overlayZ: null }
      return {
        viewportZ: parseInt(window.getComputedStyle(viewport).zIndex, 10),
        overlayZ: parseInt(window.getComputedStyle(overlay).zIndex, 10)
      }
    })

    expect(zOrder.viewportZ).not.toBeNull()
    expect(zOrder.overlayZ).not.toBeNull()
    // Guard against `auto` or missing z-index producing NaN — a NaN comparison
    // always returns false and would make the greater-than assertion vacuously pass.
    expect(Number.isFinite(zOrder.viewportZ)).toBe(true)
    expect(Number.isFinite(zOrder.overlayZ)).toBe(true)
    // Toast viewport sits above modal overlay (Toast.css: 2147483647 > Modal.css: 900)
    expect(zOrder.viewportZ!).toBeGreaterThan(zOrder.overlayZ!)
  })
})
