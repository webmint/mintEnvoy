/**
 * Tabs.ct.tsx — Playwright Component Tests for the Tabs molecule.
 *
 * These tests run in a real Chromium browser (via @playwright/experimental-ct-react)
 * so focus management, keyboard events, and tabindex are evaluated correctly —
 * unlike jsdom which lacks a layout engine and does not faithfully implement
 * the browser's focus model.
 *
 * Covers:
 *   - AC-7 (a11y):  Structural accessibility assertions — no `aria-controls`
 *                   attribute exists on any tab button (confirming the hand-rolled
 *                   engine does not emit dangling aria-controls), role="tablist",
 *                   role="tab" and aria-selected reflect activeId. These structural
 *                   checks are the authoritative AC-7 guarantee that the hand-rolled
 *                   WAI-ARIA engine is correct in a real browser.
 *                   Note: axe-core is NOT installed in this project and is not used
 *                   by any CT file (Dropdown, Modal, Toast, nested-overlays all use
 *                   structural DOM assertions). The specific concern the hand-rolled
 *                   engine was designed to address — dangling `aria-controls` with
 *                   no mounted panel — is covered by the explicit "NO tab button has
 *                   an aria-controls attribute" test below.
 *   - AC-7 (focus): Roving tabindex single tab-stop — Tab into the strip focuses
 *                   the active/first-enabled tab; exactly one button has tabIndex=0
 *                   at any point.
 *   - AC-6 (focus): Arrow keys move DOM focus AND update selection (aria-selected +
 *                   onChange confirmed via ct-tabs-last-change) in a real browser.
 *   - AC-8:         Actions slot content is visible and NOT inside the tablist
 *                   element in real Chromium.
 *   - AC-9:         Clicking a disabled tab does NOT fire onChange and does NOT
 *                   change aria-selected (confirmed via ct-tabs-last-change).
 *   - AC-10:        No-match activeId and all-disabled strips render with zero
 *                   aria-selected="true" tabs.
 *
 * Fixture components are imported from Tabs.stories.tsx (Playwright CT requires
 * components to be defined outside the test file).
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  TabsFixture,
  TabsActionsFixture,
  TabsNoMatchFixture,
  TabsAllDisabledFixture
} from './Tabs.stories'

// ---------------------------------------------------------------------------
// AC-7 — structural a11y: no aria-controls, correct roles + aria-selected
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-7 structural accessibility (no aria-controls)', () => {
  test('tablist container has role="tablist"', async ({ mount, page }) => {
    await mount(<TabsFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()
  })

  test('each tab button has role="tab"', async ({ mount, page }) => {
    await mount(<TabsFixture />)
    const tabs = page.getByRole('tab')
    // TabsFixture provides 4 tabs (params, headers, body-disabled, auth)
    await expect(tabs).toHaveCount(4)
  })

  test('NO tab button has an aria-controls attribute — hand-rolled engine emits none', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture />)
    // Evaluate on all tab buttons; every one must lack aria-controls.
    // This is the primary guard against the dangling-aria-controls defect
    // that motivated the hand-rolled WAI-ARIA engine (see Tabs.tsx header).
    const ariaControlsValues = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('[role="tab"]'))
      return buttons.map((b) => b.getAttribute('aria-controls'))
    })
    // All values must be null (attribute absent)
    for (const val of ariaControlsValues) {
      expect(val).toBeNull()
    }
  })

  test('active tab has aria-selected="true"; others have aria-selected="false"', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture initialActiveId="params" />)
    const paramsTab = page.getByRole('tab', { name: 'Params' })
    const headersTab = page.getByRole('tab', { name: 'Headers' })

    await expect(paramsTab).toHaveAttribute('aria-selected', 'true')
    await expect(headersTab).toHaveAttribute('aria-selected', 'false')
  })

  test('aria-selected updates when a tab is clicked', async ({ mount, page }) => {
    await mount(<TabsFixture initialActiveId="params" />)

    const headersTab = page.getByRole('tab', { name: 'Headers' })
    await headersTab.click()

    await expect(headersTab).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute(
      'aria-selected',
      'false'
    )
  })
})

// ---------------------------------------------------------------------------
// AC-7 — roving tabindex: exactly one tab-stop, correct button is the stop
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-7 roving tabindex', () => {
  test('exactly one tab has tabIndex=0 on initial mount', async ({ mount, page }) => {
    await mount(<TabsFixture initialActiveId="params" />)
    const zeroStops = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[role="tab"]')).filter(
        (b) => (b as HTMLElement).tabIndex === 0
      ).length
    })
    expect(zeroStops).toBe(1)
  })

  test('the active tab is the single tab-stop', async ({ mount, page }) => {
    await mount(<TabsFixture initialActiveId="params" />)
    const paramsTab = page.getByRole('tab', { name: 'Params' })
    await expect(paramsTab).toHaveAttribute('tabindex', '0')
  })

  test('Tab key into the strip focuses the active tab', async ({ mount, page }) => {
    await mount(<TabsFixture initialActiveId="params" />)

    // Blur any element that may hold focus after mount, then Tab into the strip.
    // Explicitly blurring document.body ensures the test is not brittle to future
    // fixture changes that add preceding focusable elements (mirrors the pre-focus
    // anchor pattern used in Dropdown.ct.tsx keyboard tests).
    await page.evaluate(() => {
      ;(document.activeElement as HTMLElement | null)?.blur()
      document.body.focus()
    })

    await page.keyboard.press('Tab')

    // The only tab-stop in the strip is the active tab (Params); Tab must land here.
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()
  })

  test('tabIndex=0 shifts to the clicked tab after a selection change', async ({ mount, page }) => {
    await mount(<TabsFixture initialActiveId="params" />)

    const headersTab = page.getByRole('tab', { name: 'Headers' })
    await headersTab.click()

    await expect(headersTab).toHaveAttribute('tabindex', '0')
    // Previously active tab must lose the tab-stop
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute('tabindex', '-1')
  })
})

// ---------------------------------------------------------------------------
// AC-6 — keyboard focus movement + selection in a real browser
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-6 keyboard focus movement', () => {
  test('ArrowRight moves DOM focus from first tab to second and fires onChange', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture initialActiveId="params" />)

    // Tab into the strip to land on the active tab
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    await page.keyboard.press('ArrowRight')

    // DOM focus must move to Headers
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeFocused()
    // Selection (aria-selected) must also reflect the move
    await expect(page.getByRole('tab', { name: 'Headers' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
    // onChange must have fired with the new id (recorded by the fixture)
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('headers')
  })

  test('ArrowRight skips a disabled tab in the middle and fires onChange', async ({
    mount,
    page
  }) => {
    // headers → [body disabled] → auth
    await mount(<TabsFixture initialActiveId="headers" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeFocused()

    await page.keyboard.press('ArrowRight')

    // Body is disabled; focus AND selection must land on Auth
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Auth' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('auth')
  })

  test('ArrowLeft moves DOM focus backward, skips disabled, and fires onChange', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture initialActiveId="auth" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()

    await page.keyboard.press('ArrowLeft')

    // auth ← skip body (disabled) → headers
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Headers' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('headers')
  })

  test('ArrowRight wraps from the last enabled tab to the first enabled tab', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture initialActiveId="auth" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()

    await page.keyboard.press('ArrowRight')

    // auth is the last enabled tab; wrapping goes to params (first enabled)
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('params')
  })

  test('ArrowLeft from the first enabled tab wraps focus to the last enabled tab', async ({
    mount,
    page
  }) => {
    // Mirrors the ArrowRight-wrap test above but in the opposite direction.
    await mount(<TabsFixture initialActiveId="params" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    await page.keyboard.press('ArrowLeft')

    // params is the first enabled tab; wrapping backward goes to auth (last enabled,
    // skipping body which is disabled)
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Auth' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('auth')
  })

  test('Home key moves focus to the first enabled tab and fires onChange', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture initialActiveId="auth" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()

    await page.keyboard.press('Home')

    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('params')
  })

  test('End key moves focus to the last enabled tab and fires onChange', async ({
    mount,
    page
  }) => {
    await mount(<TabsFixture initialActiveId="params" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    await page.keyboard.press('End')

    // auth is the last enabled tab (body is disabled)
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Auth' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('auth')
  })
})

// ---------------------------------------------------------------------------
// AC-8 — actions slot outside the tablist in real Chromium
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-8 actions slot', () => {
  test('actions slot content is visible on screen', async ({ mount, page }) => {
    await mount(<TabsActionsFixture />)
    await expect(page.getByTestId('ct-tabs-add-btn')).toBeVisible()
  })

  test('actions slot content is NOT inside the role="tablist" element', async ({ mount, page }) => {
    await mount(<TabsActionsFixture />)

    const isInsideTablist = await page.evaluate(() => {
      const tablist = document.querySelector('[role="tablist"]')
      const btn = document.querySelector('[data-testid="ct-tabs-add-btn"]')
      return tablist !== null && btn !== null && tablist.contains(btn)
    })

    expect(isInsideTablist).toBe(false)
  })

  test('clicking a tab in the actions fixture fires onChange and updates aria-selected', async ({
    mount,
    page
  }) => {
    await mount(<TabsActionsFixture />)

    const twoTab = page.getByRole('tab', { name: 'Two' })
    await twoTab.click()

    await expect(twoTab).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('ct-tabs-actions-last-change')).toHaveText('two')
  })
})

// ---------------------------------------------------------------------------
// AC-9 — disabled tab: click does NOT fire onChange, aria-selected unchanged
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-9 disabled tab behaviour', () => {
  test('clicking a disabled tab does not change selection or fire onChange', async ({
    mount,
    page
  }) => {
    // TabsFixture: params (active), headers, body (DISABLED), auth
    await mount(<TabsFixture initialActiveId="params" />)

    // Attempt to click the disabled "Body" tab
    const bodyTab = page.getByRole('tab', { name: 'Body' })
    // force:true bypasses Playwright's "element is disabled" actionability guard
    // so the click event actually reaches the DOM (the component's JS guard must
    // then prevent the call — the native `disabled` attribute blocks most paths,
    // but this verifies no JS leakage).
    await bodyTab.click({ force: true })

    // onChange must NOT have fired — last-change remains empty
    await expect(page.getByTestId('ct-tabs-last-change')).toHaveText('')
    // Original selection must be unchanged
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute('aria-selected', 'true')
    await expect(bodyTab).toHaveAttribute('aria-selected', 'false')
  })
})

// ---------------------------------------------------------------------------
// AC-10 — no-selection guard: no-match activeId + all-disabled tabs
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-10 no-selection guard', () => {
  test('no tab has aria-selected="true" when activeId matches no descriptor', async ({
    mount,
    page
  }) => {
    // TabsNoMatchFixture passes activeId="nonexistent-id" — no tab matches.
    await mount(<TabsNoMatchFixture />)

    const selectedCount = await page.evaluate(() => {
      return document.querySelectorAll('[role="tab"][aria-selected="true"]').length
    })
    expect(selectedCount).toBe(0)
  })

  test('no tab has aria-selected="true" when all tabs are disabled', async ({ mount, page }) => {
    // TabsAllDisabledFixture: both tabs are disabled — no enabled tab can be active.
    await mount(<TabsAllDisabledFixture />)

    const selectedCount = await page.evaluate(() => {
      return document.querySelectorAll('[role="tab"][aria-selected="true"]').length
    })
    expect(selectedCount).toBe(0)
  })

  test('all-disabled strip has no tab-stop (no tabIndex=0)', async ({ mount, page }) => {
    await mount(<TabsAllDisabledFixture />)

    const zeroStops = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[role="tab"]')).filter(
        (b) => (b as HTMLElement).tabIndex === 0
      ).length
    })
    // No enabled tab exists → roving tabindex has no candidate → zero tab-stops
    expect(zeroStops).toBe(0)
  })
})
