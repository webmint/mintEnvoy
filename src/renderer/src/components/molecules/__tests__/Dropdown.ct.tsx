/**
 * Dropdown.ct.tsx — Playwright Component Tests for the Dropdown molecule.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so pointer-event dispatch, keyboard focus management, and @media queries are
 * evaluated correctly — unlike jsdom which lacks a layout engine.
 *
 * Covers:
 *   - AC-2:  Keyboard navigation — ArrowDown / ArrowUp / Home / End move focus
 *            between menu items (real Chromium, Radix handles the logic).
 *   - AC-4:  Click-outside closes the menu; Escape closes the menu.
 *   - AC-3:  Focus returns to the trigger element after the menu closes.
 *   - AC-5:  Edge-aware positioning — menu content stays within the viewport
 *            when the trigger is near a viewport edge (Radix avoidCollisions).
 *   - AC-14: prefers-reduced-motion: reduce disables the dropdown animation.
 *
 * Fixture components are imported from Dropdown.stories.tsx (Playwright CT
 * requires components to be defined outside the test file).
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  DropdownFixture,
  DropdownEdgeFixture,
  DropdownKeyboardFixture,
  DropdownEdgeTopFixture
} from './Dropdown.stories'

// ---------------------------------------------------------------------------
// AC-2 — keyboard navigation (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-2 keyboard navigation', () => {
  /**
   * For keyboard navigation tests, open the menu via keyboard (focus trigger →
   * Enter) so Radix registers the keyboard manager and auto-focuses the first
   * item before the first arrow key press.  Clicking the trigger via pointer
   * does NOT guarantee Radix focuses the first item immediately; keyboard-open
   * does (Radix calls `focusFirst` synchronously on keyboard-open — AC-2).
   */

  test('ArrowDown moves focus from the first item to the second', async ({ mount, page }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    // Focus trigger and open via keyboard → Radix focuses first item
    await page.getByTestId('ct-dropdown-trigger').focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('menu')).toBeVisible()

    // Wait for Radix to settle focus on the first item (useEffect timing)
    await expect(page.getByRole('menuitem').first()).toBeFocused()

    // ArrowDown moves from first item to the second (AC-2)
    await page.keyboard.press('ArrowDown')

    // Guard: wait for focus to settle on Item B before reading the label,
    // preventing the evaluate from firing before Radix completes the move.
    const itemB = page.getByRole('menuitem').nth(1)
    await expect(itemB).toBeFocused()

    const focusedLabel = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      return (
        el?.querySelector('.dropdown-item__label')?.textContent?.trim() ??
        el?.textContent?.trim() ??
        null
      )
    })
    expect(focusedLabel).toBe('Item B')
  })

  test('ArrowUp moves focus from the second item to the first', async ({ mount, page }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    await page.getByTestId('ct-dropdown-trigger').focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('menu')).toBeVisible()
    await expect(page.getByRole('menuitem').first()).toBeFocused()

    // Move down to Item B, confirm focus landed, then ArrowUp back to Item A
    await page.keyboard.press('ArrowDown')
    const itemB = page.getByRole('menuitem').nth(1)
    await expect(itemB).toBeFocused()

    await page.keyboard.press('ArrowUp')

    // Wait for focus to settle on the first item before reading the label (AC-2)
    const firstItem = page.getByRole('menuitem').first()
    await expect(firstItem).toBeFocused()

    const focusedLabel = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      return (
        el?.querySelector('.dropdown-item__label')?.textContent?.trim() ??
        el?.textContent?.trim() ??
        null
      )
    })
    // ArrowUp from Item B returns focus to Item A (AC-2)
    expect(focusedLabel).toBe('Item A')
  })

  test('End key moves focus to the last enabled item', async ({ mount, page }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    await page.getByTestId('ct-dropdown-trigger').focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('menu')).toBeVisible()
    await expect(page.getByRole('menuitem').first()).toBeFocused()

    await page.keyboard.press('End')

    // Guard: assert focus settled on Item B before reading the label (matches the
    // defensive pattern used in the Home-key test — prevents a race where the
    // evaluate fires before Radix finishes moving focus).
    const itemB = page.getByRole('menuitem').nth(1)
    await expect(itemB).toBeFocused()

    const focusedLabel = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      return (
        el?.querySelector('.dropdown-item__label')?.textContent?.trim() ??
        el?.textContent?.trim() ??
        null
      )
    })
    // DropdownFixture items: Item A, Item B, Disabled (disabled).
    // End should land on the last enabled item: "Item B".
    expect(focusedLabel).toBe('Item B')
  })

  test('Home key moves focus to the first item from the second', async ({ mount, page }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    await page.getByTestId('ct-dropdown-trigger').focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('menu')).toBeVisible()
    await expect(page.getByRole('menuitem').first()).toBeFocused()

    // Move down to Item B (confirmed reachable via ArrowDown), then Home (AC-2)
    await page.keyboard.press('ArrowDown')
    await expect(page.getByRole('menuitem').nth(1)).toBeFocused()

    await page.keyboard.press('Home')

    // Wait for focus to settle on the first item before evaluating (AC-2)
    const firstItem = page.getByRole('menuitem').first()
    await expect(firstItem).toBeFocused()

    const focusedLabel = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      return (
        el?.querySelector('.dropdown-item__label')?.textContent?.trim() ??
        el?.textContent?.trim() ??
        null
      )
    })
    // Home from Item B jumps focus back to Item A (AC-2)
    expect(focusedLabel).toBe('Item A')
  })
})

// ---------------------------------------------------------------------------
// AC-4 — dismiss: Escape and click-outside (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-4 dismiss', () => {
  test('Escape key closes the menu', async ({ mount, page }) => {
    // Start closed; open via trigger click
    await mount(<DropdownFixture initialOpen={false} />)

    const trigger = page.getByTestId('ct-dropdown-trigger')
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Focus a menu item so Escape reaches DismissableLayer
    await page.getByRole('menuitem').first().focus()
    await page.keyboard.press('Escape')

    await expect(menu).not.toBeVisible()
  })

  test('clicking outside the menu closes it', async ({ mount, page }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    const trigger = page.getByTestId('ct-dropdown-trigger')
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Click below the menu panel so the pointer lands outside both the trigger
    // and the dropdown content.  The CT viewport is 1280×720 by default; clicking
    // at the bottom-right corner is safely outside both elements.
    const vp = page.viewportSize() ?? { width: 1280, height: 720 }
    await menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))
    // Macrotask-boundary readiness floor: guarantees Radix DismissableLayer's
    // setTimeout(0)-deferred pointerdown listener has fired (not a fixed delay).
    await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))
    await page.mouse.click(vp.width - 10, vp.height - 10)

    await expect(menu).not.toBeVisible()
  })

  test('clicking outside closes the menu under reduced-motion (macrotask-floor only)', async ({
    mount,
    page
  }) => {
    // Reduced-motion disables the entry animation, so getAnimations() returns []
    // and the animation-completion await no-ops — this proves the setTimeout(0)
    // macrotask-boundary floor alone arms Radix's dismiss listener (spec §9 Risk-1).
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await mount(<DropdownFixture initialOpen={false} />)

    const trigger = page.getByTestId('ct-dropdown-trigger')
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    const vp = page.viewportSize() ?? { width: 1280, height: 720 }
    await menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))
    // Macrotask-boundary readiness floor: guarantees Radix DismissableLayer's
    // setTimeout(0)-deferred pointerdown listener has fired (not a fixed delay).
    await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))
    await page.mouse.click(vp.width - 10, vp.height - 10)

    await expect(menu).not.toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// AC-3 — focus return to trigger (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-3 focus return', () => {
  test('focus returns to the trigger button after the menu closes via Escape', async ({
    mount,
    page
  }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    const trigger = page.getByTestId('ct-dropdown-trigger')
    await trigger.focus()
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Close via Escape
    await page.keyboard.press('Escape')
    await expect(menu).not.toBeVisible()

    // Radix FocusScope returns focus to the DropdownMenu.Trigger element (AC-3)
    await expect(trigger).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// AC-3 — focus return after click-outside (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-3 focus return after click-outside', () => {
  test('focus returns to the trigger button after the menu closes via click-outside', async ({
    mount,
    page
  }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    const trigger = page.getByTestId('ct-dropdown-trigger')
    // Focus trigger first so Radix can track it for focus-return
    await trigger.focus()
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Click at a safe coordinate well outside the trigger and menu panel.
    // The CT default viewport is 1280×720; clicking at (640, 600) is safely
    // below the menu which opens near the top-left of the viewport.
    await menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))
    // Macrotask-boundary readiness floor: guarantees Radix DismissableLayer's
    // setTimeout(0)-deferred pointerdown listener has fired (not a fixed delay).
    await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))
    await page.mouse.click(640, 600)

    // Menu must close
    await expect(menu).not.toBeVisible()

    // Radix FocusScope must return focus to the trigger (AC-3)
    await expect(trigger).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// AC-2 — keyboard item activation: Enter and Space (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-2 keyboard item activation', () => {
  test('pressing Enter on a focused item activates it and closes the menu', async ({
    mount,
    page
  }) => {
    // DropdownKeyboardFixture starts closed so we open via keyboard, causing Radix
    // to register keyboard-manager mode and auto-focus the first item on open.
    await mount(<DropdownKeyboardFixture />)

    const trigger = page.getByTestId('ct-kb-trigger')
    await trigger.focus()
    // Press Enter on the trigger to open the menu in keyboard mode
    await page.keyboard.press('Enter')

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Radix keyboard-open auto-focuses the first item; wait for it to settle
    await expect(page.getByRole('menuitem').first()).toBeFocused()

    // ArrowDown to the second item ("second"), then activate with Enter
    await page.keyboard.press('ArrowDown')
    await expect(page.getByRole('menuitem').nth(1)).toBeFocused()

    await page.keyboard.press('Enter')

    // Menu must close after activation
    await expect(menu).not.toBeVisible()

    // The fixture records which item was selected
    await expect(page.getByTestId('ct-kb-last-selected')).toHaveText('second')
  })

  test('pressing Space on a focused item activates it and closes the menu', async ({
    mount,
    page
  }) => {
    // Open via keyboard so Radix auto-focuses the first item (same pattern as Enter test).
    await mount(<DropdownKeyboardFixture />)

    const trigger = page.getByTestId('ct-kb-trigger')
    await trigger.focus()
    await page.keyboard.press('Enter')

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Wait for Radix to settle focus on the first item
    await expect(page.getByRole('menuitem').first()).toBeFocused()

    // Activate the first item with Space
    await page.keyboard.press(' ')

    // Menu must close after activation
    await expect(menu).not.toBeVisible()

    // First item ("first") must have been recorded as selected
    await expect(page.getByTestId('ct-kb-last-selected')).toHaveText('first')
  })
})

// ---------------------------------------------------------------------------
// AC-5 — edge-aware positioning (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-5 edge-aware positioning', () => {
  test('menu content stays within viewport when trigger is near a viewport edge', async ({
    mount,
    page
  }) => {
    // Use a small viewport so the bottom-right trigger is close to both edges
    await page.setViewportSize({ width: 600, height: 400 })

    await mount(<DropdownEdgeFixture />)

    // Click the near-edge trigger to open the menu
    const trigger = page.getByTestId('ct-edge-trigger')
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Assert the menu content bounding rect lies fully within the viewport.
    // Radix avoidCollisions flips / shifts the menu as needed (AC-5).
    // Playwright BoundingBox is { x, y, width, height }; derive edges manually.
    const box = await menu.boundingBox()
    expect(box).not.toBeNull()

    const left = box!.x
    const top = box!.y
    const right = box!.x + box!.width
    const bottom = box!.y + box!.height

    const viewportWidth = page.viewportSize()?.width ?? 0
    const viewportHeight = page.viewportSize()?.height ?? 0

    // Allow 1 px of subpixel rounding tolerance
    expect(left).toBeGreaterThanOrEqual(-1)
    expect(top).toBeGreaterThanOrEqual(-1)
    expect(right).toBeLessThanOrEqual(viewportWidth + 1)
    expect(bottom).toBeLessThanOrEqual(viewportHeight + 1)
  })

  test('menu content stays within viewport when trigger is near the TOP-LEFT edge', async ({
    mount,
    page
  }) => {
    // Small viewport to make collision avoidance engage on the top/left edges
    await page.setViewportSize({ width: 600, height: 400 })

    await mount(<DropdownEdgeTopFixture />)

    const trigger = page.getByTestId('ct-edge-top-trigger')
    await trigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Assert the menu bounding rect lies fully within the viewport.
    // Radix avoidCollisions shifts/flips the menu away from the top-left edge.
    const box = await menu.boundingBox()
    expect(box).not.toBeNull()

    const left = box!.x
    const top = box!.y
    const right = box!.x + box!.width
    const bottom = box!.y + box!.height

    const viewportWidth = page.viewportSize()?.width ?? 0
    const viewportHeight = page.viewportSize()?.height ?? 0

    // Allow 1 px of subpixel rounding tolerance
    expect(left).toBeGreaterThanOrEqual(-1)
    expect(top).toBeGreaterThanOrEqual(-1)
    expect(right).toBeLessThanOrEqual(viewportWidth + 1)
    expect(bottom).toBeLessThanOrEqual(viewportHeight + 1)
  })
})

// ---------------------------------------------------------------------------
// AC-14 — prefers-reduced-motion (real Chromium)
// ---------------------------------------------------------------------------

test.describe('Dropdown — AC-14 reduced-motion', () => {
  test('dropdown content animation is disabled under prefers-reduced-motion: reduce', async ({
    mount,
    page
  }) => {
    // Emulate reduced-motion BEFORE mounting so the CSS @media rule is active
    // when the browser first evaluates the stylesheet.
    await page.emulateMedia({ reducedMotion: 'reduce' })

    await mount(<DropdownFixture initialOpen={true} />)

    const content = page.locator('.dropdown-content').first()
    await expect(content).toBeVisible()

    const animationName = await content.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )

    // Under prefers-reduced-motion: reduce the CSS override sets animation: none
    expect(animationName).toBe('none')
  })

  test('dropdown animation runs normally under no-preference', async ({ mount, page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' })

    await mount(<DropdownFixture initialOpen={true} />)

    const content = page.locator('.dropdown-content').first()
    await expect(content).toBeVisible()

    const animationName = await content.evaluate((el) =>
      window.getComputedStyle(el).getPropertyValue('animation-name')
    )

    // The enter keyframe from Dropdown.css
    expect(animationName).toBe('dropdown-content-in')
  })
})

// ---------------------------------------------------------------------------
// Task 004 — Dropdown panel computed-style fidelity (real Chromium)
// ---------------------------------------------------------------------------

/**
 * Computed-style fidelity suite for the Dropdown panel (Task 003 restyling).
 *
 * jsdom cannot resolve CSS custom properties (color-mix, token references) or
 * compute box-shadow shorthands — Chromium is required for all assertions here.
 *
 * Styling context (project memory ct-fidelity-fixture-scoping):
 *   - `tokens.css` is imported globally for all CT tests via playwright/index.tsx.
 *   - The fixture host needs no data-mstyle attribute for Dropdown tests since
 *     none of the dropdown panel rules depend on [data-mstyle].
 *   - `box-sizing: border-box` is already declared on `.dropdown-item` in
 *     Dropdown.css, so no fixture-level inline <style> is needed for padding
 *     assertions (project memory ct-borderbox-harness-import-breaks-screenshots).
 *
 * Dismiss gate (project memory ct-radix-dismiss-arm-race):
 *   Applied in tests that require opening then closing the dropdown.  Tests
 *   that mount with `initialOpen={true}` skip the gate (no open animation races
 *   a dismiss action).
 */
test.describe('Dropdown — fidelity (Task 004)', () => {
  /**
   * Asserts that the open panel (.dropdown-content) carries the correct
   * computed box-shadow, inter-item gap, border-radius, and background.
   *
   *   - box-shadow: must resolve to the --shadow-lg token value
   *   - row-gap: 1px (the vertical flex column's inter-item gap)
   *   - border-top-left-radius: --radius-md (9px in the light theme)
   *   - background-color: --bg-elev (elevated white surface)
   *
   * All expected values are resolved at runtime via probe elements —
   * the test stays correct if token hex or numeric values change.
   */
  test('open panel: box-shadow resolves to --shadow-lg, 1px row-gap, --radius-md border-radius, --bg-elev background', async ({
    mount,
    page
  }) => {
    // Mount pre-opened so no animation race against the style read
    await mount(<DropdownFixture initialOpen={true} />)

    const content = page.locator('.dropdown-content').first()
    await expect(content).toBeVisible()

    // Probe expected token values at runtime — avoids hardcoding resolved px/rgb
    const [shadowLgValue, bgElvRgb, radiusMd] = await page.evaluate(() => {
      // box-shadow probe: inject a div with `box-shadow: var(--shadow-lg)` and
      // read back Chromium's serialized form — the same technique used for the
      // Send-button shadow assertions in RequestBar.ct.tsx.
      const probeShadow = document.createElement('div')
      probeShadow.style.boxShadow = 'var(--shadow-lg)'
      document.body.appendChild(probeShadow)
      const shadow = window.getComputedStyle(probeShadow).boxShadow
      probeShadow.remove()

      const probeBg = document.createElement('div')
      probeBg.style.backgroundColor = 'var(--bg-elev)'
      document.body.appendChild(probeBg)
      const bg = window.getComputedStyle(probeBg).backgroundColor
      probeBg.remove()

      // --radius-md is a plain px value — read directly from :root
      const radius = window
        .getComputedStyle(document.documentElement)
        .getPropertyValue('--radius-md')
        .trim()

      return [shadow, bg, radius]
    })

    const [boxShadow, rowGap, borderRadius, backgroundColor] = await content.evaluate((el) => {
      const s = window.getComputedStyle(el)
      return [s.boxShadow, s.rowGap, s.borderTopLeftRadius, s.backgroundColor]
    })

    expect(boxShadow, 'panel box-shadow must equal --shadow-lg').toBe(shadowLgValue)
    // 1px inter-item gap (vertical flex column, not row-gap separately)
    expect(rowGap, 'panel row-gap must be 1px (inter-item gap)').toBe('1px')
    expect(borderRadius, 'panel border-radius must equal --radius-md (9px)').toBe(radiusMd)
    expect(backgroundColor, 'panel background must equal --bg-elev').toBe(bgElvRgb)
  })

  /**
   * Asserts that `.dropdown-item` has exactly `padding: 6px 8px` (the reference
   * .menu-item treatment from design/styles.css).
   *
   * Dropdown.css declares `padding: 6px 8px` and `box-sizing: border-box` on
   * `.dropdown-item`, so `getComputedStyle` returns the correct inner-padding
   * even though the CT harness defaults to content-box for the host document
   * (project memory ct-borderbox-harness-import-breaks-screenshots).
   */
  test('.dropdown-item padding is 6px 8px (reference .menu-item treatment)', async ({
    mount,
    page
  }) => {
    await mount(<DropdownFixture initialOpen={true} />)

    const firstItem = page.getByRole('menuitem').first()
    await expect(firstItem).toBeVisible()

    const [paddingTop, paddingRight, paddingBottom, paddingLeft] = await firstItem.evaluate(
      (el) => {
        const s = window.getComputedStyle(el)
        return [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft]
      }
    )

    expect(paddingTop, 'item padding-top').toBe('6px')
    expect(paddingRight, 'item padding-right').toBe('8px')
    expect(paddingBottom, 'item padding-bottom').toBe('6px')
    expect(paddingLeft, 'item padding-left').toBe('8px')
  })

  /**
   * Asserts that a `[data-highlighted]` menu item's background resolves to
   * the `--bg-hover` token (AC-2 keyboard/pointer highlight parity).
   *
   * Radix sets `data-highlighted` on the focused menu item for both keyboard
   * navigation and pointer hover.  This test opens via keyboard so Radix
   * auto-focuses the first item (and sets data-highlighted on it), then reads
   * the computed backgroundColor after the 80ms transition completes.
   *
   * Transition completion gate: `.dropdown-item` has `transition: background-color
   * 80ms ease`.  After `await expect(firstItem).toBeFocused()` confirms focus,
   * `el.getAnimations().map(a => a.finished)` waits for ALL running CSS
   * transitions (Chromium exposes them via the Web Animations API) to resolve
   * before reading the computed style — the same technique used by the Radix
   * dismiss-gate pattern in the rest of this file.
   */
  test('[data-highlighted] .dropdown-item background resolves to --bg-hover (AC-2 highlight)', async ({
    mount,
    page
  }) => {
    await mount(<DropdownFixture initialOpen={false} />)

    // Open via keyboard so Radix registers keyboard-manager and auto-focuses
    // the first item, applying data-highlighted to it.
    await page.getByTestId('ct-dropdown-trigger').focus()
    await page.keyboard.press('Enter')

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // Wait for Radix to settle focus — the first item must carry data-highlighted
    const firstItem = page.getByRole('menuitem').first()
    await expect(firstItem).toBeFocused()

    // Wait for the 80ms background-color CSS transition to finish before reading
    // the computed value — prevents reading a mid-interpolation result.
    // Chromium exposes CSS transitions via el.getAnimations() (Web Animations API),
    // so Promise.all + a.finished covers both CSS animations and CSS transitions.
    await firstItem.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))

    // Probe --bg-hover to get Chromium's serialized rgb() form
    const bgHoverRgb = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.backgroundColor = 'var(--bg-hover)'
      document.body.appendChild(probe)
      const rgb = window.getComputedStyle(probe).backgroundColor
      probe.remove()
      return rgb
    })

    const highlightedBg = await firstItem.evaluate(
      (el) => window.getComputedStyle(el).backgroundColor
    )

    expect(highlightedBg, '[data-highlighted] item background must equal --bg-hover').toBe(
      bgHoverRgb
    )
  })

  /**
   * Visual regression baseline for the open Dropdown panel.
   *
   * This is a DELIBERATE rebaseline (Task 004): the panel styling changed in
   * Tasks 001-003 (box-shadow, gap, border-radius rebind) and the old baseline
   * no longer matches. The test regenerates an authoritative baseline for the
   * current design-fidelity-correct panel.
   *
   * Radix two-step dismiss gate is NOT needed here — the panel is mounted
   * pre-opened (no dismiss action in this test).
   *
   * PRIMARY fidelity proof: the computed-style assertions above.
   * This screenshot gates against FUTURE visual regressions.
   */
  test('open panel visual regression screenshot (Task 004 rebaseline)', async ({ mount, page }) => {
    // Emulate reduced-motion so the panel is fully rendered (no mid-animation
    // opacity/scale from the dropdown-content-in keyframe).
    await page.emulateMedia({ reducedMotion: 'reduce' })

    await mount(<DropdownFixture initialOpen={true} />)

    const content = page.locator('.dropdown-content').first()
    await expect(content).toBeVisible()

    await expect(content).toHaveScreenshot('dropdown-panel-fidelity.png', {
      maxDiffPixelRatio: 0.01,
      threshold: 0.1,
      animations: 'disabled'
    })
  })
})
