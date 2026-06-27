/**
 * Divider.ct.tsx — Playwright Component Tests for the Divider molecule.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so pointer capture, real layout dimensions, focus management, and keyboard
 * events are evaluated correctly — unlike jsdom which lacks a layout engine
 * and does not faithfully implement the browser's focus model or pointer capture.
 *
 * ## Test surface
 *
 * - Divider pointer drag: real-browser drag via mouse events; pointer release
 *   outside window still commits (pointer capture); role=separator ARIA.
 * - Divider keyboard: ArrowKey/Home/End resize + aria-valuenow update.
 * - Pane divider px→ratio: real container height → correct ratio conversion.
 * - Pointer-release-outside: pointer capture semantics (CT-only).
 *
 * Fixture components are imported from Divider.stories.tsx (Playwright CT requires
 * components to be defined outside the test file).
 */

import { test, expect } from '@playwright/experimental-ct-react'
import { DividerFixture, PaneDividerFixture } from './Divider.stories'

// ---------------------------------------------------------------------------
// Divider — role="separator" structural ARIA
// ---------------------------------------------------------------------------

test.describe('Divider — structural ARIA (real browser)', () => {
  test('has role="separator"', async ({ mount, page }) => {
    await mount(<DividerFixture />)
    await expect(page.getByRole('separator')).toBeVisible()
  })

  test('has aria-orientation matching the orientation prop', async ({ mount, page }) => {
    await mount(<DividerFixture orientation="vertical" />)
    await expect(page.getByRole('separator')).toHaveAttribute('aria-orientation', 'vertical')
  })

  test('has aria-valuenow reflecting initial value', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={300} />)
    await expect(page.getByRole('separator')).toHaveAttribute('aria-valuenow', '300')
  })

  test('has aria-valuemin and aria-valuemax', async ({ mount, page }) => {
    await mount(<DividerFixture min={200} max={520} />)
    const separator = page.getByRole('separator')
    await expect(separator).toHaveAttribute('aria-valuemin', '200')
    await expect(separator).toHaveAttribute('aria-valuemax', '520')
  })

  test('aria-valuenow updates after keyboard commit', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={300} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('ArrowRight')

    // Default keyboard step = 8, so 300 + 8 = 308
    await expect(separator).toHaveAttribute('aria-valuenow', '308')
  })
})

// ---------------------------------------------------------------------------
// Divider — keyboard resize in real browser
// ---------------------------------------------------------------------------

test.describe('Divider — keyboard resize (real browser)', () => {
  test('ArrowRight increases value by keyboard step and commits', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={300} min={200} max={520} keyboardStep={8} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('ArrowRight')

    // Committed value updates the fixture display
    await expect(page.getByTestId('ct-divider-committed')).toHaveText('308')
  })

  test('ArrowLeft decreases value by keyboard step and commits', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={300} min={200} max={520} keyboardStep={8} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('ArrowLeft')

    await expect(page.getByTestId('ct-divider-committed')).toHaveText('292')
  })

  test('Home commits exact min bound', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={300} min={200} max={520} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('Home')

    await expect(page.getByTestId('ct-divider-committed')).toHaveText('200')
    // aria-valuenow reflects the new value
    await expect(separator).toHaveAttribute('aria-valuenow', '200')
  })

  test('End commits exact max bound', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={300} min={200} max={520} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('End')

    await expect(page.getByTestId('ct-divider-committed')).toHaveText('520')
    await expect(separator).toHaveAttribute('aria-valuenow', '520')
  })

  test('ArrowRight at max is clamped to max', async ({ mount, page }) => {
    await mount(<DividerFixture initialValue={520} min={200} max={520} keyboardStep={8} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('ArrowRight')

    await expect(page.getByTestId('ct-divider-committed')).toHaveText('520')
  })

  test('wrong-axis arrow keys are no-ops for vertical divider', async ({ mount, page }) => {
    await mount(<DividerFixture orientation="vertical" initialValue={300} />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('ArrowUp')
    await page.keyboard.press('ArrowDown')

    // Value unchanged
    await expect(page.getByTestId('ct-divider-committed')).toHaveText('300')
  })

  test('separator is focusable (tabIndex=0)', async ({ mount, page }) => {
    await mount(<DividerFixture />)

    await page.evaluate(() => {
      document.body.focus()
    })
    await page.keyboard.press('Tab')

    await expect(page.getByRole('separator')).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// Divider — pointer drag in real browser
// ---------------------------------------------------------------------------

test.describe('Divider — pointer drag (real browser)', () => {
  test('dragging right increases committed value', async ({ mount, page }) => {
    await mount(<DividerFixture orientation="vertical" initialValue={300} min={200} max={520} />)

    const separator = page.getByRole('separator')
    const box = await separator.boundingBox()
    expect(box).not.toBeNull()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      await page.mouse.move(cx, cy)
      await page.mouse.down()
      await page.mouse.move(cx + 50, cy)
      await page.mouse.up()
    }

    // Committed value should have increased by ~50px
    const committedText = await page.getByTestId('ct-divider-committed').textContent()
    expect(Number(committedText)).toBeGreaterThan(300)
    expect(Number(committedText)).toBeLessThanOrEqual(520)
  })

  test('dragging left decreases committed value', async ({ mount, page }) => {
    await mount(<DividerFixture orientation="vertical" initialValue={350} min={200} max={520} />)

    const separator = page.getByRole('separator')
    const box = await separator.boundingBox()
    expect(box).not.toBeNull()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      await page.mouse.move(cx, cy)
      await page.mouse.down()
      await page.mouse.move(cx - 50, cy)
      await page.mouse.up()
    }

    const committedText = await page.getByTestId('ct-divider-committed').textContent()
    expect(Number(committedText)).toBeLessThan(350)
    expect(Number(committedText)).toBeGreaterThanOrEqual(200)
  })

  test('drag past max bound is clamped to max', async ({ mount, page }) => {
    await mount(<DividerFixture orientation="vertical" initialValue={500} min={200} max={520} />)

    const separator = page.getByRole('separator')
    const box = await separator.boundingBox()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      await page.mouse.move(cx, cy)
      await page.mouse.down()
      // Drag far beyond max
      await page.mouse.move(cx + 500, cy)
      await page.mouse.up()
    }

    const committedText = await page.getByTestId('ct-divider-committed').textContent()
    expect(Number(committedText)).toBe(520)
  })

  test('drag past min bound is clamped to min', async ({ mount, page }) => {
    await mount(<DividerFixture orientation="vertical" initialValue={220} min={200} max={520} />)

    const separator = page.getByRole('separator')
    const box = await separator.boundingBox()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      await page.mouse.move(cx, cy)
      await page.mouse.down()
      // Drag far beyond min
      await page.mouse.move(cx - 500, cy)
      await page.mouse.up()
    }

    const committedText = await page.getByTestId('ct-divider-committed').textContent()
    expect(Number(committedText)).toBe(200)
  })
})

// ---------------------------------------------------------------------------
// Divider — pointer release outside window (pointer capture semantics)
//
// This test is CT-only: jsdom has no pointer capture semantics.
// We verify that releasing the pointer outside the component still commits
// (pointer capture ensures events are routed to the element even if mouse
// has moved outside the viewport).
// ---------------------------------------------------------------------------

test.describe('Divider — pointer release outside window (pointer capture)', () => {
  test('releasing pointer outside viewport after drag still commits the value', async ({
    mount,
    page
  }) => {
    await mount(<DividerFixture orientation="vertical" initialValue={300} min={200} max={520} />)

    const separator = page.getByRole('separator')
    const box = await separator.boundingBox()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      // Start drag
      await page.mouse.move(cx, cy)
      await page.mouse.down()
      // Move significantly right
      await page.mouse.move(cx + 80, cy)
      // Release outside viewport by moving past viewport width first
      // Playwright clamps to the viewport, so we use the far right edge
      const viewportSize = page.viewportSize()
      if (viewportSize) {
        await page.mouse.move(viewportSize.width + 10, cy)
      }
      await page.mouse.up()
    }

    // Value must have been committed (not remain at 300)
    const committedText = await page.getByTestId('ct-divider-committed').textContent()
    // At minimum, the drag progress before leaving should have been committed
    expect(Number(committedText)).toBeGreaterThan(300)
  })
})

// ---------------------------------------------------------------------------
// Pane divider — px→ratio conversion in real browser
// ---------------------------------------------------------------------------

test.describe('PaneSplit — px→ratio conversion (real browser)', () => {
  test('pane divider drag uses container height for ratio conversion', async ({ mount, page }) => {
    await mount(<PaneDividerFixture />)

    const separator = page.getByRole('separator')
    const containerBox = await page.locator('[data-testid="ct-pane-container"]').boundingBox()
    expect(containerBox).not.toBeNull()

    if (!containerBox) return

    const box = await separator.boundingBox()
    expect(box).not.toBeNull()

    if (box && containerBox) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      // Drag down by 40px on a 400px container → ratio +0.1
      await page.mouse.move(cx, cy)
      await page.mouse.down()
      await page.mouse.move(cx, cy + 40)
      await page.mouse.up()
    }

    const committedText = await page.getByTestId('ct-pane-divider-committed').textContent()
    const committed = Number(committedText)

    // With 400px height, 40px drag → +0.1 ratio; start 0.5 → ~0.6
    // Allow some tolerance for container height being 400px
    expect(committed).toBeGreaterThan(0.5)
    expect(committed).toBeLessThanOrEqual(0.85)
    // Critically, must NOT be start + 40 (the bug) — that would be 40.5, clamped to 0.85
    // The bug path would always hit the max bound; the fixed path would be near 0.6
    expect(committed).toBeLessThan(0.8)
  })

  test('pane divider keyboard ArrowDown commits paneRatio + 0.02', async ({ mount, page }) => {
    await mount(<PaneDividerFixture />)

    const separator = page.getByRole('separator')
    await separator.focus()
    await page.keyboard.press('ArrowDown')

    // 0.5 + 0.02 = 0.52
    const committedText = await page.getByTestId('ct-pane-divider-committed').textContent()
    const committed = Number(committedText)
    expect(committed).toBeCloseTo(0.52, 2)
  })
})
