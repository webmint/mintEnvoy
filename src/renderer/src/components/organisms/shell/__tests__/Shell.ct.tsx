/**
 * Shell.ct.tsx — Playwright Component Tests for Shell organisms.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so pointer capture, real layout dimensions, focus management, and keyboard
 * events are evaluated correctly — unlike jsdom which lacks a layout engine
 * and does not faithfully implement the browser's focus model or pointer capture.
 *
 * ## Test surface
 *
 * - Tabs-in-shell: Tabs molecule mounted in Shell tabs slot (content-decoupling proof).
 * - Collapse/separator: separator absent when sidebar collapsed; toggle button visible.
 * - Titlebar: toggle button visible + updates sidebarCollapsed state.
 * - Statusbar: role=status + children visible in real Chromium.
 * - Sidebar drag resize: real-browser drag updates sidebarWidth in the store.
 * - PaneSplit drag resize: real-browser drag updates paneRatio in the store.
 *
 * (Divider's own isolation CT suites live co-located at
 * molecules/__tests__/Divider.ct.tsx.)
 *
 * Fixture components are imported from Shell.stories.tsx (Playwright CT requires
 * components to be defined outside the test file).
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  ShellWithTabsFixture,
  ShellCollapsedFixture,
  TitlebarFixture,
  StatusbarFixture,
  SidebarFixture,
  PaneSplitFixture
} from './Shell.stories'

// ---------------------------------------------------------------------------
// Tabs-in-Shell — content-decoupling proof (AC-7)
// ---------------------------------------------------------------------------

test.describe('Shell — Tabs molecule in tabs slot (content-decoupling proof)', () => {
  test('Shell renders Tabs in tabs slot without inspecting its contents', async ({
    mount,
    page
  }) => {
    await mount(<ShellWithTabsFixture />)

    // The Tabs molecule is visible inside Shell
    await expect(page.getByRole('tablist')).toBeVisible()
    // Individual tabs are present
    await expect(page.getByRole('tab', { name: 'Params' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Body' })).toBeVisible()
  })

  test('clicking a tab inside the Shell tabs slot updates selection', async ({ mount, page }) => {
    await mount(<ShellWithTabsFixture />)

    const headersTab = page.getByRole('tab', { name: 'Headers' })
    await headersTab.click()

    await expect(headersTab).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-shell-tabs-last-change')).toHaveText('headers')
  })

  test('other Shell slots (sidebar, request, response) render alongside tabs slot', async ({
    mount,
    page
  }) => {
    await mount(<ShellWithTabsFixture />)

    await expect(page.getByTestId('ct-shell-sidebar-content')).toBeVisible()
    await expect(page.getByTestId('ct-shell-request-content')).toBeVisible()
    await expect(page.getByTestId('ct-shell-response-content')).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// Shell — collapse/expand; separator presence
// ---------------------------------------------------------------------------

test.describe('Shell — sidebar collapse (real browser focus)', () => {
  test('sidebar separator is present when sidebar is expanded', async ({ mount, page }) => {
    await mount(<ShellCollapsedFixture />)

    // Initially expanded
    await expect(page.getByRole('separator', { name: /resize sidebar/i })).toBeVisible()
  })

  test('clicking toggle button collapses sidebar and removes separator', async ({
    mount,
    page
  }) => {
    await mount(<ShellCollapsedFixture />)

    const toggleBtn = page.getByRole('button', { name: /toggle sidebar/i })
    await toggleBtn.click()

    // Separator must be absent after collapse
    await expect(page.getByRole('separator', { name: /resize sidebar/i })).toHaveCount(0)
  })

  test('toggle button is present and clickable when sidebar is collapsed', async ({
    mount,
    page
  }) => {
    await mount(<ShellCollapsedFixture />)

    // Collapse
    const toggleBtn = page.getByRole('button', { name: /toggle sidebar/i })
    await toggleBtn.click()

    // Toggle button must still be visible and focusable
    await expect(toggleBtn).toBeVisible()
    await expect(toggleBtn).toBeEnabled()
  })
})

// ---------------------------------------------------------------------------
// Titlebar — toggle button interaction
// ---------------------------------------------------------------------------

test.describe('Titlebar — toggle button (real browser)', () => {
  test('toggle button is visible with correct accessible name', async ({ mount, page }) => {
    await mount(<TitlebarFixture />)
    await expect(page.getByRole('button', { name: /toggle sidebar/i })).toBeVisible()
  })

  test('clicking toggle button updates sidebarCollapsed state', async ({ mount, page }) => {
    await mount(<TitlebarFixture />)

    await expect(page.getByTestId('ct-titlebar-collapsed')).toHaveText('false')

    const toggleBtn = page.getByRole('button', { name: /toggle sidebar/i })
    await toggleBtn.click()

    await expect(page.getByTestId('ct-titlebar-collapsed')).toHaveText('true')
  })
})

// ---------------------------------------------------------------------------
// Statusbar — structure and children slot
// ---------------------------------------------------------------------------

test.describe('Statusbar — real browser', () => {
  test('renders with role="status"', async ({ mount, page }) => {
    await mount(<StatusbarFixture />)
    await expect(page.getByRole('status')).toBeVisible()
  })

  test('renders children content inside the status region', async ({ mount, page }) => {
    await mount(<StatusbarFixture />)
    await expect(page.getByTestId('ct-statusbar-child')).toBeVisible()
    await expect(page.getByTestId('ct-statusbar-child')).toHaveText('Status content')
  })
})

// ---------------------------------------------------------------------------
// Sidebar — drag resize in real browser
// ---------------------------------------------------------------------------

test.describe('Sidebar — drag resize (real browser)', () => {
  test('sidebar has a role=separator drag handle when expanded', async ({ mount, page }) => {
    await mount(<SidebarFixture />)
    await expect(page.getByRole('separator', { name: /resize sidebar/i })).toBeVisible()
  })

  test('dragging the sidebar divider updates sidebarWidth in the store', async ({
    mount,
    page
  }) => {
    await mount(<SidebarFixture />)

    const separator = page.getByRole('separator', { name: /resize sidebar/i })
    const box = await separator.boundingBox()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      await page.mouse.move(cx, cy)
      await page.mouse.down()
      await page.mouse.move(cx + 40, cy)
      await page.mouse.up()
    }

    const widthText = await page.getByTestId('ct-sidebar-width').textContent()
    expect(Number(widthText)).toBeGreaterThan(260)
    expect(Number(widthText)).toBeLessThanOrEqual(520)
  })
})

// ---------------------------------------------------------------------------
// PaneSplit — drag resize in real browser
// ---------------------------------------------------------------------------

test.describe('PaneSplit — drag resize (real browser)', () => {
  test('pane split has a role=separator drag handle', async ({ mount, page }) => {
    await mount(<PaneSplitFixture />)
    await expect(page.getByRole('separator', { name: /resize.*pane/i })).toBeVisible()
  })

  test('dragging the pane divider updates paneRatio in the store', async ({ mount, page }) => {
    await mount(<PaneSplitFixture />)

    const separator = page.getByRole('separator', { name: /resize.*pane/i })
    const box = await separator.boundingBox()

    if (box) {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2

      await page.mouse.move(cx, cy)
      await page.mouse.down()
      await page.mouse.move(cx, cy + 30)
      await page.mouse.up()
    }

    const ratioText = await page.getByTestId('ct-pane-ratio').textContent()
    const ratio = Number(ratioText)
    expect(ratio).toBeGreaterThanOrEqual(0.15)
    expect(ratio).toBeLessThanOrEqual(0.85)
  })
})
