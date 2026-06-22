/**
 * Modal.ct.tsx — Playwright Component Tests for the Modal molecule.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so @media queries such as prefers-reduced-motion are evaluated correctly,
 * unlike jsdom which does not support @media evaluation.
 *
 * Covers:
 *   - AC-14: prefers-reduced-motion: reduce disables modal animations
 *             (animation-name is "none" on both overlay and content).
 *   - AC-14: under no-preference, the enter animations are active.
 *   - AC-3:  focus returns to the trigger element after the modal closes
 *             (real browser — Radix FocusScope restores focus correctly).
 *   - AC-6:  focus trap — Tab inside the open modal cycles within the content
 *             and does not escape to body (real browser layout engine).
 *
 * Fixture components are imported from Modal.stories.tsx (Playwright CT requires
 * components to be defined outside the test file).
 */

import { test, expect } from '@playwright/experimental-ct-react'
import { ModalFixture, FocusTrapFixture } from './Modal.stories'

// ---------------------------------------------------------------------------
// AC-14 — prefers-reduced-motion
// ---------------------------------------------------------------------------

test.describe('Modal — AC-14 reduced-motion', () => {
  test('modal overlay and content animations are disabled under prefers-reduced-motion: reduce', async ({
    mount,
    page
  }) => {
    // Emulate reduced-motion BEFORE mounting so the CSS @media rule is active
    // when the browser first evaluates the stylesheet.
    await page.emulateMedia({ reducedMotion: 'reduce' })

    // ModalFixture opens the modal immediately (initialOpen=true)
    await mount(<ModalFixture initialOpen={true} />)

    // Wait for modal overlay and content to appear
    const overlay = page.locator('.modal-overlay').first()
    const content = page.locator('.modal-content').first()
    await expect(overlay).toBeVisible()
    await expect(content).toBeVisible()

    // Under prefers-reduced-motion: reduce, the CSS override sets animation: none
    // on .modal-overlay and .modal-content — so animation-name must be "none".
    const overlayAnim = await overlay.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )
    const contentAnim = await content.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )

    expect(overlayAnim).toBe('none')
    expect(contentAnim).toBe('none')
  })

  test('modal animations run normally under no-preference', async ({ mount, page }) => {
    // Explicitly set no-preference to confirm the baseline animations are present.
    await page.emulateMedia({ reducedMotion: 'no-preference' })

    await mount(<ModalFixture initialOpen={true} />)

    const overlay = page.locator('.modal-overlay').first()
    const content = page.locator('.modal-content').first()
    await expect(overlay).toBeVisible()
    await expect(content).toBeVisible()

    const overlayAnim = await overlay.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )
    const contentAnim = await content.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )

    // The enter keyframes from Modal.css
    expect(overlayAnim).toBe('modal-overlay-in')
    expect(contentAnim).toBe('modal-content-in')
  })
})

// ---------------------------------------------------------------------------
// AC-3 — focus return to trigger (real browser)
// ---------------------------------------------------------------------------

test.describe('Modal — AC-3 focus return', () => {
  test('focus returns to the Dialog.Trigger element after the modal is closed via the inner close button', async ({
    mount,
    page
  }) => {
    // Start with modal closed so we can click the Radix Dialog.Trigger to open it.
    // We use ct-modal-trigger (the element wrapped by Dialog.Trigger asChild) so
    // Radix tracks it and restores focus to it when the modal closes (AC-3).
    await mount(<ModalFixture initialOpen={false} />)

    // The Dialog.Trigger button (wrapped by Radix via asChild)
    const dialogTrigger = page.getByTestId('ct-modal-trigger')
    await dialogTrigger.focus()
    await dialogTrigger.click()

    // Modal should now be open
    const content = page.locator('.modal-content').first()
    await expect(content).toBeVisible()

    // Close via the inner close button inside the modal
    const innerClose = page.getByTestId('ct-inner-btn')
    await innerClose.click()

    // Wait for modal to close — poll until content is gone rather than a fixed timeout
    await expect(content).not.toBeVisible()

    // Radix FocusScope restores focus to the Dialog.Trigger element on close (AC-3)
    await expect(dialogTrigger).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// AC-11 — click-outside closes the modal (real browser)
// ---------------------------------------------------------------------------

test.describe('Modal — AC-11 click outside closes modal', () => {
  test('clicking the overlay scrim fires onOpenChange(false) and the dialog closes', async ({
    mount,
    page
  }) => {
    await mount(<ModalFixture initialOpen={true} />)

    const overlay = page.locator('.modal-overlay').first()
    const content = page.locator('.modal-content').first()
    await expect(overlay).toBeVisible()
    await expect(content).toBeVisible()

    // Click the top-left corner of the viewport — well outside the centered
    // content panel on any viewport size.  `force: true` bypasses Playwright's
    // actionability checks (the overlay covers the full viewport, so Playwright
    // would otherwise consider a click at x:5,y:5 as "inside" a covering element)
    // and ensures the event reaches the overlay's DismissableLayer wiring.
    await page.mouse.click(5, 5)

    // Radix DismissableLayer fires onOpenChange(false); ModalFixture calls setOpen(false)
    // which removes the portal — wait for content to disappear
    await expect(content).not.toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// AC-6 — focus trap inside modal (real browser)
// ---------------------------------------------------------------------------

test.describe('Modal — AC-6 focus trap', () => {
  /**
   * Exercises the BOUNDARY of the Radix FocusScope trap using FocusTrapFixture,
   * which renders three focusable elements (input, button, close-button) plus
   * the built-in close X icon inside the modal.
   *
   * Boundary assertions:
   *   1. Tab from the last body-element wraps to the first body-element.
   *   2. Shift+Tab from the first body-element wraps to the last focusable
   *      element inside the modal (which may be the close X or ct-trap-last,
   *      depending on DOM order — the key invariant is that focus stays INSIDE).
   */
  test('Tab wraps from last to first focusable element inside the modal trap', async ({
    mount,
    page
  }) => {
    await mount(<FocusTrapFixture />)

    const content = page.locator('.modal-content').first()
    await expect(content).toBeVisible()

    // Focus the LAST body-element we control — ct-trap-last
    const lastBtn = page.getByTestId('ct-trap-last')
    await lastBtn.focus()
    await expect(lastBtn).toBeFocused()

    // Press Tab — Radix FocusScope wraps focus back to the first focusable
    // element inside the modal (the built-in close X or ct-trap-first depending
    // on DOM order).  The critical invariant: focus must NOT leave the modal.
    await page.keyboard.press('Tab')

    const focusedAfterTab = await page.evaluate(() => {
      const active = document.activeElement
      const modal = document.querySelector('.modal-content')
      if (!active || !modal) return { inside: false, id: null }
      return { inside: modal.contains(active), id: (active as HTMLElement).dataset.testid ?? null }
    })

    expect(focusedAfterTab.inside).toBe(true)

    // The first focusable in our fixture body is ct-trap-first (input).
    // Radix may focus the close X before it depending on DOM order; either way
    // focus must have wrapped to a DIFFERENT element than ct-trap-last.
    expect(focusedAfterTab.id).not.toBe('ct-trap-last')
  })

  test('Shift+Tab from first focusable wraps to last element inside the modal trap', async ({
    mount,
    page
  }) => {
    await mount(<FocusTrapFixture />)

    const content = page.locator('.modal-content').first()
    await expect(content).toBeVisible()

    // Focus the FIRST body-element we control — ct-trap-first (input)
    const firstInput = page.getByTestId('ct-trap-first')
    await firstInput.focus()
    await expect(firstInput).toBeFocused()

    // Press Shift+Tab — focus wraps backward to the last focusable in the trap
    await page.keyboard.press('Shift+Tab')

    // Focus must remain inside .modal-content and must not be on ct-trap-first
    const focusedAfterShiftTab = await page.evaluate(() => {
      const active = document.activeElement
      const modal = document.querySelector('.modal-content')
      if (!active || !modal) return { inside: false, id: null }
      return { inside: modal.contains(active), id: (active as HTMLElement).dataset.testid ?? null }
    })

    expect(focusedAfterShiftTab.inside).toBe(true)
    expect(focusedAfterShiftTab.id).not.toBe('ct-trap-first')
  })
})
