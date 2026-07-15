/**
 * RequestSubTabs.ct.tsx — Playwright Component Tests for the RequestSubTabs organism.
 *
 * These tests run in a real Chromium browser via @playwright/experimental-ct-react,
 * covering concerns jsdom cannot exercise:
 *
 *   - AC-6:  Arrow/Home/End keyboard navigation moves the active sub-tab
 *            (delegated to the Tabs molecule; exercised end-to-end here).
 *   - AC-9:  Focus-survives-switch (R1 GO/NO-GO gate) — a focused input in
 *            the Params panel retains DOM identity, value, and panel scrollTop
 *            after a sub-tab switch and switch-back. Relies on the
 *            useLayoutEffect + lastFocusedInPanel wiring in RequestSubTabs.tsx.
 *   - AC-8:  A→B→A per-request-tab state — switching request tabs A→B→A
 *            preserves each tab's independently stored activeSubTab.
 *   - AC-27: Per-theme computed-style fidelity — resolves every §6 property
 *            (overflow, height, border-faint separator, tab color/font-size/
 *            font-weight, active box-shadow neutralization, active underline
 *            ::after height+color, inactive badge bg/color/font-size/radius/
 *            padding/weight, active badge accent wash) under BOTH light and
 *            dark themes against the hardcoded §6 token-resolved values from
 *            design/styles.css. Asserts numeric computed styles, NOT screenshots
 *            (Risk R3: a sub-1% color change must not stay within tolerance).
 *   - AC-14: a11y — each tabpanel's aria-labelledby resolves to its tab button
 *            id (linkPanels-emitted "tab-<key>") confirming the AC-14 linkage.
 *
 * Fixture components are imported from RequestSubTabs.stories.tsx — Playwright
 * experimental-ct-react requires that mounted components be defined in a
 * separate file from the test file.
 *
 * Token → rgb() map (light theme, :root in tokens.css):
 *   --text-muted   #6c6c75  → rgb(108, 108, 117)
 *   --text         #18181b  → rgb(24, 24, 27)
 *   --accent       #10b981  → rgb(16, 185, 129)
 *   --bg-active    #e8e6e3  → rgb(232, 230, 227)
 *   --border-faint #f0efed  → rgb(240, 239, 237)
 *   --accent-soft  color-mix(in oklab, …) → resolved dynamically in browser
 *
 * Token → rgb() map (dark theme, [data-theme='dark'] in tokens.css):
 *   --text-muted   #a1a1aa  → rgb(161, 161, 170)
 *   --text         #f4f4f5  → rgb(244, 244, 245)
 *   --accent       #10b981  → rgb(16, 185, 129) (unchanged between themes)
 *   --bg-active    #25252a  → rgb(37, 37, 42)
 *   --border-faint #1c1c1f  → rgb(28, 28, 31)
 *   --accent-soft  color-mix(in oklab, …) → resolved dynamically in browser
 *
 * NOTE: do NOT run `npm run test:ct` in the agent — it stalls the watchdog
 * on long silent output. The orchestrator runs the CT suite in the main thread.
 */

import { test, expect } from '@playwright/experimental-ct-react'

// Non-component imports must be in a SEPARATE statement from fixture components.
// Playwright CT's Babel transform only replaces an import's specifiers with
// importRef objects when EVERY specifier in that statement is used as a JSX
// element. Mixing exports in one statement prevents the transform and causes a
// "cannot be mounted" runtime error.

import {
  RequestSubTabsStoreResetFixture,
  RequestSubTabsBasicFixture,
  RequestSubTabsTwoRequestTabsFixture,
  RequestSubTabsFidelityFixture,
  RequestSubTabsScrollLeakFixture,
  RequestSubTabsWithKVTableFixture,
  RequestSubTabsWithBodyFixture,
  RequestSubTabsWithBodyRawFixture,
  RequestSubTabsWithAllSlotsFixture
} from './RequestSubTabs.stories'

// ---------------------------------------------------------------------------
// Setup — reset store state before every test
// ---------------------------------------------------------------------------

/**
 * Before each test:
 * 1. Mount RequestSubTabsStoreResetFixture, wait for its readiness signal, then
 *    unmount. Ensures every test starts from the same known store state.
 * 2. Remove any data-theme attribute so tests that don't set a theme explicitly
 *    use the light theme (:root tokens).
 */
test.beforeEach(async ({ mount, page }) => {
  const resetFixture = await mount(<RequestSubTabsStoreResetFixture />)
  await page.waitForSelector('[data-testid="ct-rst-store-reset-done"]', { state: 'attached' })
  await resetFixture.unmount()

  await page.evaluate(() => {
    document.documentElement.removeAttribute('data-theme')
  })
})

// ---------------------------------------------------------------------------
// AC-6 — Keyboard navigation moves the active sub-tab
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — AC-6 keyboard navigation (delegated to Tabs)', () => {
  test('ArrowRight moves focus from Params to Auth and selects Auth', async ({ mount, page }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    // Blur any initially focused element, then Tab into the strip.
    await page.evaluate(() => {
      ;(document.activeElement as HTMLElement | null)?.blur()
      document.body.focus()
    })
    await page.keyboard.press('Tab')

    // Tab key lands on the active tab (Params, roving tabindex=0).
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    await page.keyboard.press('ArrowRight')

    // DOM focus and selection move to Auth (next enabled sub-tab).
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Auth' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute(
      'aria-selected',
      'false'
    )
  })

  test('ArrowLeft moves focus backward from Auth to Params', async ({ mount, page }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    await page.evaluate(() => {
      ;(document.activeElement as HTMLElement | null)?.blur()
      document.body.focus()
    })
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Move forward to Auth first.
    await page.keyboard.press('ArrowRight')
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Auth' })).toHaveAttribute('aria-selected', 'true')

    // ArrowLeft must move backward to Params.
    await page.keyboard.press('ArrowLeft')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('tab', { name: 'Auth' })).toHaveAttribute('aria-selected', 'false')
  })

  test('End key moves focus to Code (last sub-tab) from Params', async ({ mount, page }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    await page.evaluate(() => {
      ;(document.activeElement as HTMLElement | null)?.blur()
      document.body.focus()
    })
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    await page.keyboard.press('End')

    // All 6 sub-tabs are enabled (AC-13); End lands on the last one.
    await expect(page.getByRole('tab', { name: 'Code' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Code' })).toHaveAttribute('aria-selected', 'true')
  })

  test('Home key moves focus to Params (first sub-tab) from Code', async ({ mount, page }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    await page.evaluate(() => {
      ;(document.activeElement as HTMLElement | null)?.blur()
      document.body.focus()
    })
    await page.keyboard.press('Tab')
    // Move to the last sub-tab first.
    await page.keyboard.press('End')
    await expect(page.getByRole('tab', { name: 'Code' })).toBeFocused()

    await page.keyboard.press('Home')

    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()
    await expect(page.getByRole('tab', { name: 'Params' })).toHaveAttribute('aria-selected', 'true')
  })
})

// ---------------------------------------------------------------------------
// AC-9 — Focus-survives-switch (R1 GO/NO-GO gate)
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — AC-9 focus-survives-switch (R1 gate)', () => {
  /**
   * Primary R1 gate: the SAME DOM node retains focus + value after the
   * sub-tab switches away from Params and back. Relies on the
   * useLayoutEffect + lastFocusedInPanel wiring in RequestSubTabs.tsx.
   * A failure here blocks task 005 (App wiring of the pane live).
   */
  test('input in Params panel retains focus + value after switch-to-Headers and switch-back', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsBasicFixture />)
    const input = page.getByTestId('ct-rst-params-input')
    await expect(input).toBeVisible()

    // Focus the input; this fires onFocus on the Params panel div, recording
    // the input as the last focused element for the 'params' sub-tab.
    await input.click()
    await expect(input).toBeFocused()

    // Capture the value before switching (defaultValue="hello").
    const valueBefore = await input.inputValue()

    // Switch to Headers sub-tab: focus moves to the Headers tab button; the
    // Params panel gets the hidden attribute, blurring the input.
    await page.getByRole('tab', { name: 'Headers' }).click()
    // Sanity: input is inside the now-hidden panel — not focused.
    const paramsPanel = page.locator('#panel-params')
    await expect(paramsPanel).toHaveAttribute('hidden')

    // Switch back to Params: useLayoutEffect fires, finds the recorded input,
    // and calls savedEl.focus() synchronously before the browser paints.
    await page.getByRole('tab', { name: 'Params' }).click()

    // Same DOM node is focused (identity preserved — no remount).
    await expect(input).toBeFocused()

    // Value must not have been reset (input is always-mounted, never remounted).
    await expect(input).toHaveValue(valueBefore)
  })

  test('panel scrollTop is preserved at non-zero after sub-tab switch and switch-back', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByTestId('ct-rst-params-input')).toBeVisible()

    // Focus the input to record it in lastFocusedInPanel.
    await page.getByTestId('ct-rst-params-input').click()

    // Scroll the panel to 50px — the fixture's 600px spacer ensures the panel
    // has enough overflow. A non-zero scrollTop makes the assertion non-vacuous.
    // No scroll-event dispatch needed: handleSubTabChange captures scrollTop
    // synchronously at switch time before the state update hides the panel.
    await page.evaluate(() => {
      const panel = document.getElementById('panel-params')
      if (panel !== null) {
        panel.scrollTop = 50
      }
    })

    // Confirm the scroll was accepted (if content doesn't overflow, scrollTop
    // stays 0 and the test catches a fixture regression rather than a silent pass).
    const scrollTopBefore = await page.evaluate(() => {
      const panel = document.getElementById('panel-params')
      return panel?.scrollTop ?? -1
    })
    expect(scrollTopBefore).toBe(50)

    // Switch away and back.
    await page.getByRole('tab', { name: 'Headers' }).click()
    await page.getByRole('tab', { name: 'Params' }).click()

    // The panel uses hidden attribute (no remount) so scrollTop must be preserved.
    const scrollTopAfter = await page.evaluate(() => {
      const panel = document.getElementById('panel-params')
      return panel?.scrollTop ?? -1
    })
    expect(scrollTopAfter).toBe(50)

    // Focus and value must also still be intact (same DOM node, no remount).
    await expect(page.getByTestId('ct-rst-params-input')).toBeFocused()
    await expect(page.getByTestId('ct-rst-params-input')).toHaveValue('hello')
  })
})

// ---------------------------------------------------------------------------
// AC-8 — A→B→A per-request-tab state
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — AC-8 A→B→A per-request-tab sub-tab state', () => {
  /**
   * Each request tab independently stores its activeSubTab. Switching request
   * tabs A→B→A must restore A's stored sub-tab (Headers) rather than
   * defaulting to Params each time. The component reads activeSubTab from the
   * currently active request tab's store entry.
   */
  test("switching request tabs A→B→A preserves each tab's active sub-tab independently", async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsTwoRequestTabsFixture />)

    // Wait for the store to seed: Tab A is active with activeSubTab='headers'.
    await expect(page.getByRole('tab', { name: 'Headers' })).toHaveAttribute(
      'aria-selected',
      'true'
    )

    // Switch to Tab B (activeSubTab='body' in store).
    await page.getByTestId('ct-rst-select-tab-b').click()
    await expect(page.getByRole('tab', { name: 'Body' })).toHaveAttribute('aria-selected', 'true')

    // Switch back to Tab A — must restore Tab A's stored 'headers' sub-tab.
    await page.getByTestId('ct-rst-select-tab-a').click()
    await expect(page.getByRole('tab', { name: 'Headers' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
    // Verify Body is not selected (Tab A's stored state, not Tab B's).
    await expect(page.getByRole('tab', { name: 'Body' })).toHaveAttribute('aria-selected', 'false')
  })

  test("Tab B's sub-tab is not mutated by re-selecting Tab A", async ({ mount, page }) => {
    await mount(<RequestSubTabsTwoRequestTabsFixture />)

    // Wait for seed: Tab A active, headers selected.
    await expect(page.getByRole('tab', { name: 'Headers' })).toHaveAttribute(
      'aria-selected',
      'true'
    )

    // Switch A→B→A.
    await page.getByTestId('ct-rst-select-tab-b').click()
    await page.getByTestId('ct-rst-select-tab-a').click()

    // Re-select Tab B to confirm B's state was not corrupted.
    await page.getByTestId('ct-rst-select-tab-b').click()
    await expect(page.getByRole('tab', { name: 'Body' })).toHaveAttribute('aria-selected', 'true')
  })
})

// ---------------------------------------------------------------------------
// Finding 1 regression — scroll state must NOT leak across request tabs
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — scroll state does not leak across request tabs', () => {
  /**
   * Regression for Finding 1: scrollTops map is keyed by SubTabKey only and was
   * shared across request-tab switches. Scrolling tab A's Params to a non-zero
   * value then switching to tab B must NOT restore A's scrollTop onto B's Params.
   *
   * The fix: a useEffect on activeTabId clears both scrollTops and
   * lastFocusedInPanel whenever the active request tab changes.
   *
   * Uses RequestSubTabsScrollLeakFixture: two tabs, both on 'params', with a
   * scrollable Params slot containing a 600px spacer.
   */
  test('switching request tabs clears scroll state — tab B Params scrollTop is 0 after scrolling tab A', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsScrollLeakFixture />)

    // Wait for the store to seed: both tabs on 'params'; tab A is active.
    await expect(page.getByRole('tablist')).toBeVisible()

    // Scroll tab A's Params panel to a non-zero value. The 600px spacer in the
    // fixture ensures the panel has enough overflow for scrollTop to stick.
    await page.evaluate(() => {
      const panel = document.getElementById('panel-params')
      if (panel !== null) {
        panel.scrollTop = 50
      }
    })

    // Confirm the scroll was accepted (non-vacuous assertion).
    const scrollTopTabA = await page.evaluate(() => {
      return document.getElementById('panel-params')?.scrollTop ?? -1
    })
    expect(scrollTopTabA).toBe(50)

    // Also trigger handleSubTabChange path to seed scrollTops via the outgoing
    // panel capture: click to a different sub-tab then back.
    // This ensures scrollTops.current.set(activeSubTab, ...) fires for 'params'.
    await page.getByRole('tab', { name: 'Auth' }).click()
    await page.getByRole('tab', { name: 'Params' }).click()

    // Confirm scrollTop is still 50 after within-tab switch-back (AC-9 still holds).
    const scrollTopAfterSwitchBack = await page.evaluate(() => {
      return document.getElementById('panel-params')?.scrollTop ?? -1
    })
    expect(scrollTopAfterSwitchBack).toBe(50)

    // Switch to request tab B — the useEffect on activeTabId must clear scrollTops.
    await page.getByTestId('ct-rst-sl-select-tab-b').click()

    // Tab B is already on 'params'; its Params panel is immediately visible.
    await expect(page.getByRole('tablist')).toBeVisible()

    // B's Params scrollTop must be 0 — NOT leaked from tab A.
    const scrollTopTabB = await page.evaluate(() => {
      return document.getElementById('panel-params')?.scrollTop ?? -1
    })
    expect(scrollTopTabB).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// AC-27 — Per-theme computed-style fidelity (§6 values from design/styles.css)
// ---------------------------------------------------------------------------

/**
 * Fidelity assertions read RESOLVED COMPUTED STYLES (getComputedStyle), never
 * screenshot pixels — Risk R3: a sub-1% colour change must not survive within
 * Playwright's screenshot threshold.
 *
 * §6 values are hardcoded at write time from tokens.css (exact hex → rgb()
 * map documented in the file header above). --accent-soft is resolved
 * dynamically because it is a color-mix() expression that the browser
 * evaluates at layout time.
 *
 * Tests are parametrised by theme: light (no data-theme attribute, :root
 * tokens) and dark ([data-theme='dark'] tokens).
 */

/** --accent: #10b981 → rgb(16, 185, 129) — unchanged across both themes. */
const ACCENT_RGB = 'rgb(16, 185, 129)'

test.describe('RequestSubTabs — AC-27 §6 computed-style fidelity (light theme)', () => {
  // Light-theme tests use the default (no data-theme) from beforeEach.

  test('light — .tabs.pane-tabs: overflow:visible, height:36px, border-bottom 1px --border-faint, padding 0 16px', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.locator('.pane-tabs .tabs__badge').first()).toBeVisible()

    const tabsEl = page.locator('.tabs.pane-tabs')

    const overflow = await tabsEl.evaluate((el) => window.getComputedStyle(el).overflow)
    expect(overflow).toBe('visible')

    const height = await tabsEl.evaluate((el) => window.getComputedStyle(el).height)
    expect(height).toBe('36px')

    const borderWidth = await tabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomWidth)
    expect(borderWidth).toBe('1px')

    const borderColor = await tabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomColor)
    expect(borderColor).toBe('rgb(240, 239, 237)') // --border-faint light

    const borderStyle = await tabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomStyle)
    expect(borderStyle).toBe('solid')

    // §6 padding 0 16px.
    const paddingLeft = await tabsEl.evaluate((el) => window.getComputedStyle(el).paddingLeft)
    expect(paddingLeft).toBe('16px')

    const paddingRight = await tabsEl.evaluate((el) => window.getComputedStyle(el).paddingRight)
    expect(paddingRight).toBe('16px')
  })

  test('light — inactive tab: color --text-muted, font-size 12.5px, font-weight 500, height 36px', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    // Auth tab has no badge, is not the active tab — pure inactive state.
    const authTab = page.getByRole('tab', { name: 'Auth' })

    const color = await authTab.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe('rgb(108, 108, 117)') // --text-muted light

    const fontSize = await authTab.evaluate((el) => window.getComputedStyle(el).fontSize)
    expect(fontSize).toBe('12.5px')

    const fontWeight = await authTab.evaluate((el) => window.getComputedStyle(el).fontWeight)
    expect(fontWeight).toBe('500')

    // §6 .pane-tab height 36px (individual tab button, separate from the container).
    const tabHeight = await authTab.evaluate((el) => window.getComputedStyle(el).height)
    expect(tabHeight).toBe('36px')
  })

  test('light — active tab: color --text, box-shadow:none, background transparent', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const activeTab = page.locator('.pane-tabs .tabs__tab--active')

    const color = await activeTab.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe('rgb(24, 24, 27)') // --text light

    const boxShadow = await activeTab.evaluate((el) => window.getComputedStyle(el).boxShadow)
    expect(boxShadow).toBe('none')

    const bgColor = await activeTab.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    // Transparent serializes as rgba(0, 0, 0, 0) in Chrome.
    expect(bgColor).toBe('rgba(0, 0, 0, 0)')
  })

  test('light — active underline ::after: height 1.5px, bottom -1px, background --accent', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const activeTab = page.locator('.pane-tabs .tabs__tab--active')

    const afterHeight = await activeTab.evaluate(
      (el) => window.getComputedStyle(el, '::after').height
    )
    expect(afterHeight).toBe('1.5px')

    // R7 gate: the overflow:visible rationale depends on bottom:-1px bleed.
    const afterBottom = await activeTab.evaluate(
      (el) => window.getComputedStyle(el, '::after').bottom
    )
    expect(afterBottom).toBe('-1px')

    const afterBg = await activeTab.evaluate(
      (el) => window.getComputedStyle(el, '::after').backgroundColor
    )
    expect(afterBg).toBe(ACCENT_RGB) // --accent: same in both themes
  })

  test('light — inactive badge: bg --bg-active, color --text-muted, font-size 10px, radius 999px, weight 600', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    // The inactive Headers badge must be present before asserting.
    await expect(
      page.locator('.pane-tabs .tabs__tab:not(.tabs__tab--active) .tabs__badge').first()
    ).toBeVisible()

    const inactiveBadge = page
      .locator('.pane-tabs .tabs__tab:not(.tabs__tab--active) .tabs__badge')
      .first()

    const bg = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    expect(bg).toBe('rgb(232, 230, 227)') // --bg-active light

    const color = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe('rgb(108, 108, 117)') // --text-muted light

    const fontSize = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).fontSize)
    expect(fontSize).toBe('10px')

    const radius = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).borderRadius)
    expect(radius).toBe('999px')

    const weight = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).fontWeight)
    expect(weight).toBe('600')
  })

  test('light — inactive badge: padding 1px top/bottom, 6px left/right (pill geometry)', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.locator('.pane-tabs .tabs__badge').first()).toBeVisible()

    // Use any visible badge; padding values are the same for active and inactive.
    const badge = page.locator('.pane-tabs .tabs__badge').first()

    const pt = await badge.evaluate((el) => window.getComputedStyle(el).paddingTop)
    expect(pt).toBe('1px')
    const pb = await badge.evaluate((el) => window.getComputedStyle(el).paddingBottom)
    expect(pb).toBe('1px')
    const pl = await badge.evaluate((el) => window.getComputedStyle(el).paddingLeft)
    expect(pl).toBe('6px')
    const pr = await badge.evaluate((el) => window.getComputedStyle(el).paddingRight)
    expect(pr).toBe('6px')
  })

  test('light — active badge accent wash: color --accent, background --accent-soft', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.locator('.pane-tabs .tabs__tab--active .tabs__badge')).toBeVisible()

    const activeBadge = page.locator('.pane-tabs .tabs__tab--active .tabs__badge')

    const color = await activeBadge.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe(ACCENT_RGB) // --accent: same in both themes

    // --accent-soft is color-mix(in oklab, var(--accent) 14%, transparent) —
    // resolve it by creating a reference element with the same token applied.
    const expectedAccentSoft = await page.evaluate(() => {
      const el = document.createElement('div')
      el.style.cssText =
        'position:absolute;top:-9999px;left:-9999px;background-color:var(--accent-soft)'
      document.body.appendChild(el)
      const val = window.getComputedStyle(el).backgroundColor
      document.body.removeChild(el)
      return val
    })
    const bg = await activeBadge.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    expect(bg).toBe(expectedAccentSoft)
  })
})

test.describe('RequestSubTabs — AC-27 §6 computed-style fidelity (dark theme)', () => {
  test.beforeEach(async ({ page }) => {
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark')
    })
  })

  test('dark — .tabs.pane-tabs: overflow:visible, height:36px, border-bottom 1px --border-faint, padding 0 16px', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.locator('.pane-tabs .tabs__badge').first()).toBeVisible()

    const tabsEl = page.locator('.tabs.pane-tabs')

    const overflow = await tabsEl.evaluate((el) => window.getComputedStyle(el).overflow)
    expect(overflow).toBe('visible')

    const height = await tabsEl.evaluate((el) => window.getComputedStyle(el).height)
    expect(height).toBe('36px')

    const borderWidth = await tabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomWidth)
    expect(borderWidth).toBe('1px')

    const borderColor = await tabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomColor)
    expect(borderColor).toBe('rgb(28, 28, 31)') // --border-faint dark

    const borderStyle = await tabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomStyle)
    expect(borderStyle).toBe('solid')

    // §6 padding 0 16px.
    const paddingLeft = await tabsEl.evaluate((el) => window.getComputedStyle(el).paddingLeft)
    expect(paddingLeft).toBe('16px')

    const paddingRight = await tabsEl.evaluate((el) => window.getComputedStyle(el).paddingRight)
    expect(paddingRight).toBe('16px')
  })

  test('dark — inactive tab: color --text-muted, font-size 12.5px, font-weight 500', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const authTab = page.getByRole('tab', { name: 'Auth' })

    const color = await authTab.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe('rgb(161, 161, 170)') // --text-muted dark

    const fontSize = await authTab.evaluate((el) => window.getComputedStyle(el).fontSize)
    expect(fontSize).toBe('12.5px')

    const fontWeight = await authTab.evaluate((el) => window.getComputedStyle(el).fontWeight)
    expect(fontWeight).toBe('500')
  })

  test('dark — active tab: color --text, box-shadow:none, background transparent', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const activeTab = page.locator('.pane-tabs .tabs__tab--active')

    const color = await activeTab.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe('rgb(244, 244, 245)') // --text dark

    const boxShadow = await activeTab.evaluate((el) => window.getComputedStyle(el).boxShadow)
    expect(boxShadow).toBe('none')

    const bgColor = await activeTab.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    expect(bgColor).toBe('rgba(0, 0, 0, 0)')
  })

  test('dark — active underline ::after: height 1.5px, bottom -1px, background --accent (theme-invariant)', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const activeTab = page.locator('.pane-tabs .tabs__tab--active')

    const afterHeight = await activeTab.evaluate(
      (el) => window.getComputedStyle(el, '::after').height
    )
    expect(afterHeight).toBe('1.5px')

    // R7 gate: the overflow:visible rationale depends on bottom:-1px bleed.
    const afterBottom = await activeTab.evaluate(
      (el) => window.getComputedStyle(el, '::after').bottom
    )
    expect(afterBottom).toBe('-1px')

    const afterBg = await activeTab.evaluate(
      (el) => window.getComputedStyle(el, '::after').backgroundColor
    )
    // --accent: #10b981 — does not change between light and dark themes.
    expect(afterBg).toBe(ACCENT_RGB)
  })

  test('dark — inactive badge: bg --bg-active, color --text-muted, pill padding', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(
      page.locator('.pane-tabs .tabs__tab:not(.tabs__tab--active) .tabs__badge').first()
    ).toBeVisible()

    const inactiveBadge = page
      .locator('.pane-tabs .tabs__tab:not(.tabs__tab--active) .tabs__badge')
      .first()

    const bg = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    expect(bg).toBe('rgb(37, 37, 42)') // --bg-active dark

    const color = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe('rgb(161, 161, 170)') // --text-muted dark

    // font-size / radius / weight are theme-invariant; assert once for completeness.
    const fontSize = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).fontSize)
    expect(fontSize).toBe('10px')

    const radius = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).borderRadius)
    expect(radius).toBe('999px')

    const weight = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).fontWeight)
    expect(weight).toBe('600')

    // Padding: mirrors the light-theme badge test (§6 pill geometry — 1px top/bottom, 6px left/right).
    const pt = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).paddingTop)
    expect(pt).toBe('1px')
    const pb = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).paddingBottom)
    expect(pb).toBe('1px')
    const pl = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).paddingLeft)
    expect(pl).toBe('6px')
    const pr = await inactiveBadge.evaluate((el) => window.getComputedStyle(el).paddingRight)
    expect(pr).toBe('6px')
  })

  test('dark — active badge accent wash: color --accent, background --accent-soft', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsFidelityFixture />)
    await expect(page.locator('.pane-tabs .tabs__tab--active .tabs__badge')).toBeVisible()

    const activeBadge = page.locator('.pane-tabs .tabs__tab--active .tabs__badge')

    const color = await activeBadge.evaluate((el) => window.getComputedStyle(el).color)
    expect(color).toBe(ACCENT_RGB)

    // Resolve --accent-soft dynamically in the dark-theme browser context.
    const expectedAccentSoft = await page.evaluate(() => {
      const el = document.createElement('div')
      el.style.cssText =
        'position:absolute;top:-9999px;left:-9999px;background-color:var(--accent-soft)'
      document.body.appendChild(el)
      const val = window.getComputedStyle(el).backgroundColor
      document.body.removeChild(el)
      return val
    })
    const bg = await activeBadge.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    expect(bg).toBe(expectedAccentSoft)
  })
})

// ---------------------------------------------------------------------------
// AC-14 — a11y: aria-labelledby on each tabpanel resolves to its tab button id
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — AC-14 aria-labelledby resolves to tab button id', () => {
  test('each panel aria-labelledby links to the corresponding tab button id', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const subTabKeys = ['params', 'auth', 'headers', 'body', 'tests', 'code'] as const

    for (const key of subTabKeys) {
      const result = await page.evaluate((k: string) => {
        const panel = document.getElementById(`panel-${k}`)
        if (panel === null) return `panel-${k} not found`

        const labelledBy = panel.getAttribute('aria-labelledby')
        if (labelledBy === null) return `panel-${k} has no aria-labelledby`

        const tabEl = document.getElementById(labelledBy)
        if (tabEl === null) return `element with id=${labelledBy} not found`

        if (tabEl.id !== `tab-${k}`) return `expected id=tab-${k}, got id=${tabEl.id}`
        return 'ok'
      }, key)

      expect(result, `panel-${key}`).toBe('ok')
    }
  })

  test('each tab button carries id="tab-<key>" (linkPanels emitted)', async ({ mount, page }) => {
    await mount(<RequestSubTabsBasicFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    const subTabKeys = ['params', 'auth', 'headers', 'body', 'tests', 'code'] as const

    for (const key of subTabKeys) {
      const tabEl = page.locator(`#tab-${key}`)
      await expect(tabEl).toBeAttached()
      // The element must be a role=tab button.
      await expect(tabEl).toHaveRole('tab')
    }
  })
})

// ---------------------------------------------------------------------------
// Finding 3 — AC-9 with real KVTable organism in the Params slot
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — AC-9 focus+value survive switch with live KVTable (Finding 3)', () => {
  /**
   * Verifies that a real KVTable cell input (not a plain <input>) retains focus
   * and its typed value after a sub-tab switch and switch-back. This covers the
   * composed path: App injects KVTable → RequestSubTabs wires the slot →
   * useLayoutEffect restores focus on re-show.
   *
   * Uses RequestSubTabsWithKVTableFixture: one tab seeded with one params row so
   * KVTable renders a real row input (not just the virtual trailing row).
   */
  test('KVTable key input retains focus and typed value after switch-to-Headers and switch-back', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsWithKVTableFixture />)
    await expect(page.getByRole('tablist')).toBeVisible()

    // Wait for the real KVTable row to appear (store is seeded after useEffect fires).
    const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
    await expect(keyInput).toBeVisible()

    // Focus the KVTable key input — fires onFocus on the Params panel div,
    // recording it as the last focused element for the 'params' sub-tab.
    await keyInput.click()
    await expect(keyInput).toBeFocused()

    // Fill a new value — triggers KVTable's onChange → writeRows → updateActiveSpec.
    // The store now has params[0].key = 'new-key'.
    await keyInput.fill('new-key')
    await expect(keyInput).toHaveValue('new-key')

    // Switch to Headers sub-tab: Params panel gets hidden, blurring the input.
    await page.getByRole('tab', { name: 'Headers' }).click()
    await expect(page.locator('#panel-params')).toHaveAttribute('hidden')

    // Switch back to Params: useLayoutEffect fires and refocuses the KVTable input.
    await page.getByRole('tab', { name: 'Params' }).click()
    await expect(page.locator('#panel-params')).not.toHaveAttribute('hidden')

    // Same DOM node is focused (identity preserved — KVTable panels are never unmounted).
    await expect(keyInput).toBeFocused()

    // Value must survive: KVTable is store-controlled; the store still holds 'new-key'.
    await expect(keyInput).toHaveValue('new-key')
  })
})

// ---------------------------------------------------------------------------
// Finding 11 — body-slot + BodyEditor seam CT
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — body-slot + BodyEditor seam (Finding 11)', () => {
  /**
   * Verifies that when the Body sub-tab is active and the body slot receives a
   * real BodyEditor component, the BodyEditor toolbar renders inside #panel-body.
   *
   * Previously the body panel always fell to emptyState because no CT exercised
   * the RequestSubTabs body prop → BodyEditor composition path.
   *
   * Uses RequestSubTabsWithBodyFixture: one tab seeded with activeSubTab='body'
   * so the Body panel is immediately visible; the body slot receives a live
   * BodyEditor instance.
   */
  test('BodyEditor toolbar is present inside #panel-body when body slot is active', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsWithBodyFixture />)

    // Wait for the store seed to complete (useEffect fires after render).
    await page.waitForSelector('[data-testid="ct-rst-body-ready"]', { state: 'attached' })

    // The Body panel must not be hidden.
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')

    // BodyEditor's toolbar must be present within the Body panel, not merely
    // somewhere on the page — scoping the locator to #panel-body confirms the
    // assembled seam (RequestSubTabs body slot → BodyEditor) is wired correctly.
    const bodyToolbar = page.locator('#panel-body [data-testid="body-toolbar"]')
    await expect(bodyToolbar).toBeAttached()
  })

  /**
   * Finding 4 — non-body sub-tabs work correctly while the body slot holds a
   * live BodyEditor.
   *
   * Switching away from Body to Params/Headers must:
   *   - Hide #panel-body (hidden attribute present).
   *   - Show the target panel (hidden attribute absent).
   *   - Render the panel's fallback content (EmptyPanel "Panel not yet available")
   *     when no slot prop is provided for that panel.
   *
   * Switching back to Body must restore #panel-body and the BodyEditor toolbar
   * (mount-all — BodyEditor is never unmounted while its panel is hidden).
   *
   * Uses RequestSubTabsWithBodyFixture (body=BodyEditor, no params/headers props)
   * so non-body panels fall through to the shared EmptyPanel placeholder.
   */
  test('switching away from Body to Params/Headers shows those panels; BodyEditor survives switch-back (Finding 4)', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsWithBodyFixture />)
    await page.waitForSelector('[data-testid="ct-rst-body-ready"]', { state: 'attached' })

    // Body is initially active.
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')

    // Switch to Params.
    await page.getByRole('tab', { name: 'Params' }).click()
    // #panel-params is now visible; #panel-body is hidden.
    await expect(page.locator('#panel-params')).not.toHaveAttribute('hidden')
    await expect(page.locator('#panel-body')).toHaveAttribute('hidden')
    // No params slot prop in this fixture → EmptyPanel placeholder is shown.
    await expect(page.locator('#panel-params')).toContainText('Panel not yet available')

    // Switch to Headers.
    await page.getByRole('tab', { name: 'Headers' }).click()
    await expect(page.locator('#panel-headers')).not.toHaveAttribute('hidden')
    await expect(page.locator('#panel-body')).toHaveAttribute('hidden')
    // No headers slot prop in this fixture → EmptyPanel placeholder is shown.
    await expect(page.locator('#panel-headers')).toContainText('Panel not yet available')

    // Switch back to Body — BodyEditor must still be mounted (mount-all; no unmount).
    await page.getByRole('tab', { name: 'Body' }).click()
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')
    await expect(page.locator('#panel-body [data-testid="body-toolbar"]')).toBeAttached()
  })
})

// ---------------------------------------------------------------------------
// Finding 2 — textarea focus-restoration across body sub-tab switch
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — body textarea focus survives sub-tab switch (Finding 2)', () => {
  /**
   * When the Body sub-tab is active and body.active = 'raw', the
   * `<textarea aria-label="Request body">` is rendered and focusable.
   * Switching away to Params and switching back must restore focus to the
   * textarea via RequestSubTabs' lastFocusedInPanel / useLayoutEffect
   * restoration — the same path tested for Params inputs in AC-9.
   *
   * Uses RequestSubTabsWithBodyRawFixture: body.active='raw', activeSubTab='body'.
   */
  test('textarea in Body panel regains focus after switch-to-Params and switch-back', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsWithBodyRawFixture />)
    await page.waitForSelector('[data-testid="ct-rst-body-raw-ready"]', { state: 'attached' })

    // Body panel is immediately visible (activeSubTab='body').
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')

    const textarea = page.getByLabel('Request body', { exact: true })
    await expect(textarea).toBeVisible()

    // Focus the textarea — fires onFocus on the Body panel div, recording it
    // as the last focused element for the 'body' sub-tab in lastFocusedInPanel.
    await textarea.click()
    await expect(textarea).toBeFocused()

    // Switch to Params: body panel gets hidden attribute, blurring the textarea.
    await page.getByRole('tab', { name: 'Params' }).click()
    await expect(page.locator('#panel-body')).toHaveAttribute('hidden')

    // Switch back to Body: useLayoutEffect fires, finds the recorded textarea,
    // and calls savedEl.focus() synchronously before the browser paints.
    await page.getByRole('tab', { name: 'Body' }).click()
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')

    // The textarea must be focused again (same DOM node — no remount).
    await expect(textarea).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// Finding 3 — body textarea content preserved across sub-tab switch (scroll seam)
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — body textarea content survives sub-tab switch (Finding 3)', () => {
  /**
   * The assembled body-panel + sub-tab-switch path. mount-all keeps the body
   * panel always mounted (hidden attribute, not unmounted), so the textarea
   * value is preserved across the hidden/shown toggle.
   *
   * Uses RequestSubTabsWithBodyRawFixture: seeds body.raw.text='body-raw-content'.
   *
   * NOTE: textarea internal scrollTop is NOT preserved across the display:none
   * toggle by design — accepted/known behavior (the panel-level scroll capture
   * in handleSubTabChange does not reach the textarea's internal scrollTop).
   * Only content survival is asserted here; scrollTop preservation is out of scope.
   */
  test('textarea content is preserved after switch-to-Params and switch-back (mount-all keeps panel mounted)', async ({
    mount,
    page
  }) => {
    await mount(<RequestSubTabsWithBodyRawFixture />)
    await page.waitForSelector('[data-testid="ct-rst-body-raw-ready"]', { state: 'attached' })

    const textarea = page.getByLabel('Request body', { exact: true })
    await expect(textarea).toBeVisible()

    // Confirm the seeded raw text is present before switching.
    await expect(textarea).toHaveValue('body-raw-content')

    // Switch away to Params — body panel gets the hidden attribute.
    await page.getByRole('tab', { name: 'Params' }).click()
    await expect(page.locator('#panel-body')).toHaveAttribute('hidden')

    // Switch back to Body — mount-all: panel was never unmounted, only unhidden.
    await page.getByRole('tab', { name: 'Body' }).click()
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')

    // Content must be preserved — the store still holds the seeded text and the
    // textarea DOM node was never remounted.
    // (scrollTop is NOT asserted — see note above.)
    await expect(textarea).toHaveValue('body-raw-content')
  })
})

// ---------------------------------------------------------------------------
// Finding 4 — concurrent-subscription topology (all three slots live)
// ---------------------------------------------------------------------------

test.describe('RequestSubTabs — concurrent-subscription topology (all slots live, Finding 4)', () => {
  /**
   * Asserts store-slice independence when all three slots (params KVTable,
   * headers KVTable, body BodyEditor) are simultaneously mounted and
   * subscribed to the same tabsStore — mirroring the real App.tsx composition
   * root exactly.
   *
   * The critical invariant: a write to one slice must NOT bleed into another.
   *   - handleTextChange → updateActiveSpec({ body: { ...body, raw: ... } })
   *     must not alter spec.params or spec.headers.
   *   - KVTable writeRows → updateActiveSpec({ params: [...] }) must not
   *     alter body.raw.text.
   *
   * Fixture: RequestSubTabsWithAllSlotsFixture seeds one tab with:
   *   params=[{key:'p-key'}], headers=[{key:'h-key'}],
   *   body={active:'raw', raw.text:'initial-body-text'}, activeSubTab='body'.
   */

  test('typing in Body raw textarea does not mutate params rows', async ({ mount, page }) => {
    await mount(<RequestSubTabsWithAllSlotsFixture />)
    await page.waitForSelector('[data-testid="ct-rst-all-slots-ready"]', { state: 'attached' })

    // Body panel is initially active (activeSubTab='body').
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')

    // Fill the raw textarea — fires handleTextChange →
    // updateActiveSpec({ body: { ...body, raw: { ...body.raw, text: newText } } }).
    // Only body.raw.text changes; spec.params must be untouched.
    const textarea = page.getByLabel('Request body', { exact: true })
    await expect(textarea).toBeVisible()
    await textarea.fill('{"edited":"body"}')

    // Switch to Params and assert the seeded row is unchanged.
    await page.getByRole('tab', { name: 'Params' }).click()
    await expect(page.locator('#panel-params')).not.toHaveAttribute('hidden')

    // If the body write had mutated spec.params, the row would be gone or corrupt.
    const paramsKeyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
    await expect(paramsKeyInput).toHaveValue('p-key')

    // Headers share the same updateActiveSpec write path — assert the body write
    // left the seeded headers row untouched too (qa Gap 4: seeded h-key was unused).
    await page.getByRole('tab', { name: 'Headers' }).click()
    await expect(page.locator('#panel-headers')).not.toHaveAttribute('hidden')
    const headersKeyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
    await expect(headersKeyInput).toHaveValue('h-key')
  })

  test('editing a params row does not mutate body raw text', async ({ mount, page }) => {
    await mount(<RequestSubTabsWithAllSlotsFixture />)
    await page.waitForSelector('[data-testid="ct-rst-all-slots-ready"]', { state: 'attached' })

    // Switch to Params.
    await page.getByRole('tab', { name: 'Params' }).click()
    await expect(page.locator('#panel-params')).not.toHaveAttribute('hidden')

    // Edit the params key — fires KVTable writeRows →
    // updateActiveSpec({ params: [...] }). Only spec.params changes.
    const paramsKeyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
    await expect(paramsKeyInput).toBeVisible()
    await paramsKeyInput.fill('edited-p-key')
    await expect(paramsKeyInput).toHaveValue('edited-p-key')

    // Switch back to Body and verify body.raw.text is unchanged.
    await page.getByRole('tab', { name: 'Body' }).click()
    await expect(page.locator('#panel-body')).not.toHaveAttribute('hidden')
    const textarea = page.getByLabel('Request body', { exact: true })
    await expect(textarea).toHaveValue('initial-body-text')
  })
})
