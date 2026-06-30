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
  TabsAllDisabledFixture,
  TabsClosableFixture,
  TabsClosableRemoveFixture,
  TabsNonCloseReRenderFixture,
  TabsClosableRemoveTwoPhase,
  TabbarFidelityFixture,
  TabbarInShellTabsFixture,
  TabbarLongTitleFidelityFixture
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

// ---------------------------------------------------------------------------
// AC-22 — Delete/Backspace closes the focused tab when closable=true
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-22 Delete/Backspace close key', () => {
  test("pressing Delete on a focused tab fires onClose with that tab's id", async ({
    mount,
    page
  }) => {
    await mount(<TabsClosableFixture initialActiveId="params" />)

    // Tab into the strip — lands on the active tab (Params).
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Press Delete — should fire onClose with "params".
    await page.keyboard.press('Delete')

    // The fixture records the last onClose id in ct-closable-last-close.
    await expect(page.getByTestId('ct-closable-last-close')).toHaveText('params')
    // onChange must NOT have fired (ct-closable-last-change stays empty).
    await expect(page.getByTestId('ct-closable-last-change')).toHaveText('')
  })

  test("pressing Backspace on a focused tab fires onClose with that tab's id", async ({
    mount,
    page
  }) => {
    await mount(<TabsClosableFixture initialActiveId="headers" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeFocused()

    await page.keyboard.press('Backspace')

    await expect(page.getByTestId('ct-closable-last-close')).toHaveText('headers')
    await expect(page.getByTestId('ct-closable-last-change')).toHaveText('')
  })

  test('Delete fires onClose but does NOT fire onChange', async ({ mount, page }) => {
    // Focused tab is "auth" — pressing Delete should call onClose("auth") only.
    await mount(<TabsClosableFixture initialActiveId="auth" />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()

    await page.keyboard.press('Delete')

    await expect(page.getByTestId('ct-closable-last-close')).toHaveText('auth')
    // ct-closable-last-change is still empty — onChange was never called.
    await expect(page.getByTestId('ct-closable-last-change')).toHaveText('')
  })
})

// ---------------------------------------------------------------------------
// AC-23 — roving-focus restoration after a tab is removed
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-23 roving-focus restoration after close re-render', () => {
  test('after active tab is removed focus lands on the neighbor tab, not body', async ({
    mount,
    page
  }) => {
    // TabsClosableRemoveFixture: on onClose, the fixture removes the closed tab
    // from the list and sets activeId to the neighbor — exactly what the store
    // does. The useLayoutEffect inside Tabs must then restore focus to the new
    // active tab button.
    await mount(<TabsClosableRemoveFixture />)

    // Tab into the strip — lands on "Params" (the initial active tab).
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Press Delete — triggers onClose("params") → fixture removes "params"
    // and sets activeId to "headers".
    await page.keyboard.press('Delete')

    // Focus must have moved to the new active tab ("headers"), not to <body>.
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeFocused()
  })

  test('after close re-render exactly one tabIndex=0 remains (no dangling tabindex)', async ({
    mount,
    page
  }) => {
    await mount(<TabsClosableRemoveFixture />)

    // Focus the strip and close the active tab.
    await page.keyboard.press('Tab')
    await page.keyboard.press('Delete')

    // After the re-render: "params" is gone, "headers" is the new active tab.
    // Exactly one tab button should have tabIndex=0.
    const zeroStops = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[role="tab"]')).filter(
        (b) => (b as HTMLElement).tabIndex === 0
      ).length
    })
    expect(zeroStops).toBe(1)
  })
})

// ---------------------------------------------------------------------------
// AC-23 — onBlur internal-transfer guard: ✕ click within the list does NOT
// clear the keyboard-restore guard, so a subsequent Delete still restores focus.
//
// The guard (lastFocusWasInListRef) is a SINGLE boolean. It is set true on any
// focus-capture event inside the tablist and cleared false only when focus
// leaves the tablist entirely (relatedTarget not contained in the list).
// An internal blur (e.g. tab-button → sibling ✕) leaves the guard true because
// the ✕ is also inside the tablist element — the onBlur handler's
// relatedTarget-contains check detects this and does NOT clear it.
//
// The tests below prove this in two ways:
//   1. Single-phase: focus a tab, click its OWN ✕ (which both closes the tab
//      and is an internal transfer) → useLayoutEffect fires → focus restored.
//   2. Two-phase: focus a tab → click the ✕ of a DIFFERENT tab (internal
//      transfer, guard stays, that tab closes, useLayoutEffect refocuses the
//      original tab) → press Delete on the refocused tab → focus restored again.
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-23 onBlur internal-transfer guard', () => {
  test('clicking the ✕ button (internal blur) then pressing Delete still restores focus', async ({
    mount,
    page
  }) => {
    // This test verifies that the onBlur handler's relatedTarget-contains check
    // correctly identifies an internal focus transfer (tab → ✕) and does NOT
    // clear lastFocusWasInListRef. If the guard were cleared incorrectly, the
    // subsequent Delete-close's useLayoutEffect would not fire and focus would
    // fall to <body> instead of the neighbor tab.
    await mount(<TabsClosableRemoveFixture />)

    // 1. Tab into the strip — focus lands on "Params".
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // 2. Click the ✕ for "Params". The click moves focus from the role=tab button
    //    to the sibling ✕ button (both inside the tablist) — this is an internal
    //    blur transfer and must NOT clear the guard.
    //    The ✕ click also fires onClose, which the fixture handles by removing
    //    "params" and setting activeId to "headers".
    const closeBtn = page.getByRole('button', { name: 'Close Params' })
    await closeBtn.click()

    // 3. After the close re-render the fixture removes "params" and updates
    //    activeId to "headers". The useLayoutEffect must restore focus to
    //    "headers" (guard was still set because the blur was internal).
    await expect(page.getByRole('tab', { name: 'Headers' })).toBeFocused()
  })

  test('after ✕ click close and focus restoration, exactly one tabIndex=0 remains', async ({
    mount,
    page
  }) => {
    await mount(<TabsClosableRemoveFixture />)

    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    const closeBtn = page.getByRole('button', { name: 'Close Params' })
    await closeBtn.click()

    // After removal and focus restoration: exactly one tabIndex=0.
    const zeroStops = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('[role="tab"]')).filter(
        (b) => (b as HTMLElement).tabIndex === 0
      ).length
    })
    expect(zeroStops).toBe(1)
  })

  test('two-phase: ✕ of DIFFERENT tab keeps guard set → second Delete also restores focus', async ({
    mount,
    page
  }) => {
    // Two-phase sequence proving the guard's single-boolean nature survives an
    // internal blur from one tab to a DIFFERENT tab's ✕:
    //   Phase 1 — focus Params tab button, then click ✕ of Headers (a different
    //             tab). The blur from Params button → Headers ✕ is internal
    //             (relatedTarget is inside the tablist). The guard must stay set.
    //             Headers is removed; fixture keeps Params as activeId. The
    //             useLayoutEffect refocuses Params (guard still true, Params not
    //             already focused).
    //   Phase 2 — press Delete on now-focused Params → closes Params → fixture
    //             sets activeId to Auth (neighbor). useLayoutEffect must restore
    //             focus to Auth (guard still true from phase-1 focus event).
    await mount(<TabsClosableRemoveTwoPhase />)

    // Phase 1: Tab into strip, focus Params.
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Click ✕ of Headers — internal blur (Params tab → Headers ✕), guard stays.
    // Headers is removed; Params remains active.
    await page.getByRole('button', { name: 'Close Headers' }).click()

    // useLayoutEffect fires: guard=true, activeEl=Params button, Params is not
    // focused (focus was on Headers ✕ which is now gone) → Params gets focus.
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Phase 2: press Delete on focused Params → closes Params → Auth becomes active.
    await page.keyboard.press('Delete')

    // useLayoutEffect fires again: guard=true (never cleared between phases),
    // activeEl=Auth button → focus lands on Auth.
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeFocused()
  })
})

// ---------------------------------------------------------------------------
// AC-23 (non-close guard) — re-render with CHANGED tabs[] but SAME activeId
// while focus IS INSIDE the list must NOT steal focus from the focused button.
//
// This exercises the SECOND guard inside useLayoutEffect:
//   if (document.activeElement === activeEl) return   ← this branch
//
// The focus-outside path (lastFocusWasInListRef = false) short-circuits at
// the FIRST check and never reaches this branch. To exercise the second branch
// we need focus to be inside the tablist (lastFocusWasInListRef = true) during
// a non-close re-render where the same tab button is still focused.
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-23 non-close re-render with focus inside the list', () => {
  test('changing tabs[] but keeping the SAME activeId does NOT steal focus from the focused tab button', async ({
    mount,
    page
  }) => {
    // TabsNonCloseReRenderFixture: closable strip starting with [params, headers],
    // activeId="params". The fixture exposes window.__tabsNonCloseAddTab() which
    // appends Auth — same activeId, tabs[] changes — without stealing browser focus.
    //
    // This exercises the SECOND guard inside useLayoutEffect:
    //   if (document.activeElement === activeEl) return   ← this branch
    //
    // Clicking an external button would steal focus out of the tablist and clear
    // lastFocusWasInListRef, which would short-circuit at the FIRST check — the
    // wrong branch. page.evaluate() triggers the React state update without any
    // browser focus side-effect, keeping focus on the Params tab button throughout.
    await mount(<TabsNonCloseReRenderFixture />)

    // Step 1: Tab into the strip — focus lands on Params (the active tab).
    // This fires the onFocus-capture handler inside Tabs, setting
    // lastFocusWasInListRef.current = true.
    await page.keyboard.press('Tab')
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Step 2: Trigger a non-close re-render via the window global — does NOT move
    // browser focus. Appends Auth tab, keeps activeId="params".
    // useLayoutEffect deps change (tabs[] is a new array reference), the effect runs:
    //   - lastFocusWasInListRef.current === true  (passes first guard)
    //   - activeEl = buttonRefs.get("params")     (the Params button)
    //   - document.activeElement === activeEl      (Params is already focused)
    //   → RETURNS EARLY: does NOT call activeEl.focus() — no focus theft.
    await page.evaluate(() => {
      ;(window as Window & { __tabsNonCloseAddTab?: () => void }).__tabsNonCloseAddTab?.()
    })

    // Step 3: Focus must REMAIN on the Params tab button — not stolen.
    await expect(page.getByRole('tab', { name: 'Params' })).toBeFocused()

    // Step 4: Sanity-check the new tab appeared (confirming the re-render happened).
    await expect(page.getByRole('tab', { name: 'Auth' })).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// Feature-005 — .tabbar fidelity: computed-style assertions (Task 009)
//
// PRIMARY gate: these exact-value computed-style assertions are the authoritative
// proof that the .tabbar-scoped CSS rules in Tabs.css match the design reference
// (design/styles.css .tab / .tabbar rules). A failing assertion here indicates a
// real fidelity gap — do NOT loosen the expected values to force a pass.
//
// Token → rgb() map used throughout (light theme, no data-theme attribute):
//   --bg-sunken  #f4f3f1 → rgb(244, 243, 241)
//   --accent     #10b981 → rgb(16, 185, 129)
//   --bg         #fbfaf9 → rgb(251, 250, 249)
//   --border     #e8e6e3 → rgb(232, 230, 227)
//   --m-head     #ec4899 → rgb(236, 72, 153)
//
// Grill binding F1: every assertion uses a .tabbar-compound-scoped fixture.
// The active ::before/::after render only in the closable=true + wrapper branch.
// A bare <Tabs> would measure unscoped, inert rules (incorrect baseline).
//
// Grill binding (per-test data-mstyle='soft'): Shell never mounts in CT, so the
// [data-mstyle] attribute is written by beforeEach. The HEAD chip color rule
// lives under [data-mstyle='soft'] .method.HEAD — without this attribute the
// chip would be unstyled and the AC-19 assertion would spuriously fail.
// ---------------------------------------------------------------------------

test.describe('Tabs — Feature-005 .tabbar fidelity: computed-style (primary gate)', () => {
  test.beforeEach(async ({ page }) => {
    // Set data-mstyle='soft' before mount so the [data-mstyle='soft'] .method.HEAD
    // color rule is active when the component renders (AC-19).
    // Shell (the runtime writer) never mounts in CT — this is the CT stand-in.
    // Do NOT set this globally in playwright/index.tsx (grill binding requirement).
    await page.evaluate(() => {
      document.documentElement.dataset.mstyle = 'soft'
    })
  })

  // ---- AC-14/AC-18: tabbar strip container geometry + surface ----

  test('AC-14 — .tabbar strip: background-color resolves to --bg-sunken (rgb(244,243,241))', async ({
    mount
  }) => {
    // The design reference (.tabbar { background: var(--bg-sunken) }) requires
    // the outer .tabs.tabbar container to carry the sunken surface color.
    // Tabs.css must apply this via .tabs.tabbar or a descendant rule that reaches
    // the outer div. A transparent computed value here is a fidelity gap.
    const component = await mount(<TabbarFidelityFixture />)
    const bg = await component.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    expect(bg).toBe('rgb(244, 243, 241)')
  })

  test('AC-14 — .tabbar strip: height resolves to 36px', async ({ mount }) => {
    // The design reference specifies height: 36px for the tabbar strip.
    // Tabs.css must set this explicitly; relying on content size (tab buttons
    // are 32px) would yield 32px and fail this assertion.
    const component = await mount(<TabbarFidelityFixture />)
    const height = await component.evaluate((el) => window.getComputedStyle(el).height)
    expect(height).toBe('36px')
  })

  test('AC-14 — .tabbar strip: padding-right resolves to 8px', async ({ mount }) => {
    // The design reference specifies padding-right: 8px for the tabbar strip
    // (right gutter before the new-tab button). Tabs.css must apply this.
    const component = await mount(<TabbarFidelityFixture />)
    const pr = await component.evaluate((el) => window.getComputedStyle(el).paddingRight)
    expect(pr).toBe('8px')
  })

  test('AC-14 — .tabbar strip: border-bottom-width 1px + border color --border', async ({
    mount
  }) => {
    // The base .tabs rule sets border-bottom: 1px solid var(--border).
    // This test verifies both width and color resolve correctly from the token.
    const component = await mount(<TabbarFidelityFixture />)
    const bWidth = await component.evaluate((el) => window.getComputedStyle(el).borderBottomWidth)
    expect(bWidth).toBe('1px')

    const bColor = await component.evaluate((el) => window.getComputedStyle(el).borderBottomColor)
    // --border: #e8e6e3 → rgb(232, 230, 227)
    expect(bColor).toBe('rgb(232, 230, 227)')
  })

  test('AC-22 (feat-005) — .tabs.tabbar: overflow resolves to visible (::after mask not clipped)', async ({
    mount,
    page
  }) => {
    // .tabs.tabbar { overflow: visible } overrides .tabs { overflow: hidden }.
    // This is required so the active-tab ::after mask (bottom: -1px) is not
    // clipped at the container edge, creating the seamless "lifted" open-tab look.
    // The flip side (bare .tabs stays overflow:hidden) is proven by the
    // bare-consumer non-regression describe below.
    await mount(<TabbarFidelityFixture />)
    const tabsEl = page.locator('.tabs.tabbar')

    const overflow = await tabsEl.evaluate((el) => window.getComputedStyle(el).overflow)
    expect(overflow).toBe('visible')
  })

  // ---- AC-15: tab cell geometry ----

  test('AC-15 — .tabbar .tabs__tab-wrapper: column-gap 8px, padding 0px 10px 0px 12px; button padding 0px', async ({
    mount,
    page
  }) => {
    // Fix A: padding and gap moved from the role=tab button to the wrapper so
    // the full cell (button + close sibling) is padded uniformly.
    // .tabbar .tabs__tab-wrapper { display: flex; gap: 8px; padding: 0 10px 0 12px }
    // .tabbar .tabs__tab { padding: 0; flex: 1 1 auto }
    await mount(<TabbarFidelityFixture />)
    const wrapper = page.locator('.tabbar .tabs__tab-wrapper').first()

    const gap = await wrapper.evaluate((el) => window.getComputedStyle(el).columnGap)
    expect(gap).toBe('8px')

    const padding = await wrapper.evaluate((el) => window.getComputedStyle(el).padding)
    // Shorthand computed value in Chrome: top right bottom left
    expect(padding).toBe('0px 10px 0px 12px')

    // After Fix A the role=tab button is content-only: padding must be 0.
    const tabButton = page.locator('.tabbar .tabs__tab').first()
    const buttonPadding = await tabButton.evaluate((el) => window.getComputedStyle(el).padding)
    expect(buttonPadding).toBe('0px')
  })

  test('AC-D — .tabbar__new button: border-radius 0px (flush, no border-radius)', async ({
    mount,
    page
  }) => {
    // Fix D: .tabbar__new has no border-radius so it renders as a flush full-height
    // strip cell, matching the reference .tab-new (no border-radius in design/styles.css).
    // TabbarFidelityFixture now passes the actions row (tabbar__new + spacer + chevron)
    // so this element is present and can be asserted.
    await mount(<TabbarFidelityFixture />)
    const newBtn = page.locator('.tabbar__new')
    await expect(newBtn).toBeVisible()

    const borderRadius = await newBtn.evaluate((el) => window.getComputedStyle(el).borderRadius)
    expect(borderRadius).toBe('0px')
  })

  test('AC-15 — .tabbar .tabs__tab-wrapper: border-right-width 1px + border-right-color --border', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab-wrapper { border-right: 1px solid var(--border) }
    // provides the per-tab vertical separator in the .tabbar variant.
    // Gap 6: also assert border-right-color resolves to --border (symmetry with
    // AC-14's border-bottom-color assertion above).
    await mount(<TabbarFidelityFixture />)
    const wrapper = page.locator('.tabbar .tabs__tab-wrapper').first()

    const brWidth = await wrapper.evaluate((el) => window.getComputedStyle(el).borderRightWidth)
    expect(brWidth).toBe('1px')

    const brColor = await wrapper.evaluate((el) => window.getComputedStyle(el).borderRightColor)
    // --border: #e8e6e3 → rgb(232, 230, 227)
    expect(brColor).toBe('rgb(232, 230, 227)')
  })

  test('AC-6/AC-9 — .tabbar .tabs__tab-wrapper: max-width computed value is exactly 220px', async ({
    mount,
    page
  }) => {
    // The cap was relocated from .tabbar .tabs__tab-label (TabBar.css) to
    // .tabbar .tabs__tab-wrapper (Tabs.css) in Task 001. This assertion proves
    // the property resolves in a real browser — jsdom cannot compute layout.
    // Exact string equality ('220px') rather than numeric comparison so a unit
    // drift (e.g. 'none', 'auto', 'em') is caught rather than silently passing.
    await mount(<TabbarFidelityFixture />)
    const wrapper = page.locator('.tabbar .tabs__tab-wrapper').first()

    const maxWidth = await wrapper.evaluate((el) => window.getComputedStyle(el).maxWidth)
    expect(maxWidth).toBe('220px')
  })

  test('AC-15 — .tabbar .tabs__tab: font-size resolves to 12.5px (--fs-base token)', async ({
    mount,
    page
  }) => {
    // .tabs__tab { font-size: var(--fs-base, 12.5px) } in Tabs.css.
    // With tokens.css loaded via playwright/index.tsx, --fs-base must resolve to
    // 12.5px. A fallback-only resolution (token not loaded) would still yield
    // 12.5px from the CSS fallback literal; if tokens.css overrides --fs-base to
    // a different value this assertion catches the drift.
    await mount(<TabbarFidelityFixture />)
    const tabEl = page.locator('.tabbar .tabs__tab').first()

    const fontSize = await tabEl.evaluate((el) => window.getComputedStyle(el).fontSize)
    // --fs-base: 12.5px
    expect(fontSize).toBe('12.5px')
  })

  // ---- AC-16: label flex-grow ----

  test('AC-16 — .tabs__tab-label: flex-grow 1 (label fills available space)', async ({
    mount,
    page
  }) => {
    // .tabs__tab-label { flex: 1 } → flex-grow: 1 so the label takes remaining
    // width after the method chip and close button, enabling ellipsis truncation.
    await mount(<TabbarFidelityFixture />)
    const label = page.locator('.tabbar .tabs__tab-label').first()

    const flexGrow = await label.evaluate((el) => window.getComputedStyle(el).flexGrow)
    expect(flexGrow).toBe('1')
  })

  test('AC-16 — .tabs__tab-label: text-overflow ellipsis and overflow hidden (truncation guard)', async ({
    mount,
    page
  }) => {
    // .tabs__tab-label { overflow: hidden; text-overflow: ellipsis } in Tabs.css.
    // Together with flex-grow: 1 and white-space: nowrap this ensures long labels
    // are truncated (…) at the tab boundary rather than overflowing their button.
    await mount(<TabbarFidelityFixture />)
    const label = page.locator('.tabbar .tabs__tab-label').first()

    const textOverflow = await label.evaluate((el) => window.getComputedStyle(el).textOverflow)
    expect(textOverflow).toBe('ellipsis')

    const overflow = await label.evaluate((el) => window.getComputedStyle(el).overflow)
    expect(overflow).toBe('hidden')
  })

  // ---- AC-11: active wrapper pseudo-element stripes ----

  test('AC-11 — active wrapper ::before: height 1.5px, background-color --accent', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab-wrapper--active::before draws the top accent stripe.
    // height: 1.5px and background: var(--accent, #10b981).
    // The pseudo-element only renders in the closable=true + wrapper branch —
    // hence the .tabbar-scoped fixture with closable prop (grill binding F1).
    await mount(<TabbarFidelityFixture />)
    const activeWrapper = page.locator('.tabbar .tabs__tab-wrapper--active')

    const beforeHeight = await activeWrapper.evaluate(
      (el) => window.getComputedStyle(el, '::before').height
    )
    expect(beforeHeight).toBe('1.5px')

    const beforeBg = await activeWrapper.evaluate(
      (el) => window.getComputedStyle(el, '::before').backgroundColor
    )
    // --accent: #10b981 → rgb(16, 185, 129)
    expect(beforeBg).toBe('rgb(16, 185, 129)')
  })

  test('AC-11 — active wrapper .tabs__tab-wrapper--active: own background-color resolves to --bg (rgb(251,250,249))', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab-wrapper--active { background: var(--bg, #ffffff) }
    // lifts the active tab surface to the app background color, making it appear
    // to "float" above the sunken strip. With tokens.css loaded, --bg resolves to
    // #fbfaf9 (rgb(251, 250, 249)), NOT the CSS fallback #ffffff.
    // This is the wrapper's own background, distinct from the ::after mask.
    await mount(<TabbarFidelityFixture />)
    const activeWrapper = page.locator('.tabbar .tabs__tab-wrapper--active')

    const bgColor = await activeWrapper.evaluate(
      (el) => window.getComputedStyle(el).backgroundColor
    )
    // --bg: #fbfaf9 → rgb(251, 250, 249) (from tokens.css, not the CSS fallback #ffffff)
    expect(bgColor).toBe('rgb(251, 250, 249)')
  })

  test('AC-11 — active wrapper ::after: height 1px, background-color --bg', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab-wrapper--active::after is the bottom mask that hides
    // the outer strip's border-bottom under the active tab (bottom: -1px).
    // height: 1px and background: var(--bg, #ffffff).
    // With tokens.css loaded, --bg resolves to #fbfaf9 (rgb(251, 250, 249)),
    // NOT the CSS fallback #ffffff. The CT page imports tokens.css via
    // playwright/index.tsx (task 006), so the token should resolve correctly.
    await mount(<TabbarFidelityFixture />)
    const activeWrapper = page.locator('.tabbar .tabs__tab-wrapper--active')

    const afterHeight = await activeWrapper.evaluate(
      (el) => window.getComputedStyle(el, '::after').height
    )
    expect(afterHeight).toBe('1px')

    const afterBg = await activeWrapper.evaluate(
      (el) => window.getComputedStyle(el, '::after').backgroundColor
    )
    // --bg: #fbfaf9 → rgb(251, 250, 249) (from tokens.css, not the CSS fallback #ffffff)
    expect(afterBg).toBe('rgb(251, 250, 249)')
  })

  // ---- AC-19: HEAD method chip color under soft mstyle ----

  test('AC-19 — HEAD method chip: color resolves to --m-head (rgb(236,72,153)) under data-mstyle=soft', async ({
    mount,
    page
  }) => {
    // [data-mstyle='soft'] .method.HEAD { color: var(--m-head) } in tokens.css.
    // The beforeEach sets data-mstyle='soft' on document.documentElement so this
    // rule activates. --m-head: #ec4899 → rgb(236, 72, 153).
    await mount(<TabbarFidelityFixture />)
    const methodChip = page.locator('.tabbar .method.HEAD')

    const color = await methodChip.evaluate((el) => window.getComputedStyle(el).color)
    // --m-head: #ec4899 → rgb(236, 72, 153)
    expect(color).toBe('rgb(236, 72, 153)')
  })

  // ---- Gap 1: whole-cell hover (Fix B) ----

  test('Fix B — whole-cell hover: wrapper background-color resolves to --bg-hover, tab text to --text', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab-wrapper:not(.tabs__tab-wrapper--active):hover sets the
    // background on the whole cell; .tabbar .tabs__tab-wrapper:hover .tabs__tab
    // elevates the inner button's text color. Both rules must fire on a non-active
    // wrapper hover.
    //
    // Transition note: .tabs__tab has `transition: color 80ms ease`. Without
    // disabling the transition, getComputedStyle reads the pre-transition color
    // at t=0 immediately after hover(). Emulate prefers-reduced-motion: reduce
    // so the @media rule in Tabs.css fires (.tabs__tab { transition: none }),
    // making the computed value reflect the final hover state instantly. The
    // wrapper's background-color has no transition (it changes immediately).
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await mount(<TabbarFidelityFixture />)
    // dirty-tab (index 1) is non-active — hover it to trigger Fix B rules.
    const wrapper = page.locator('.tabbar .tabs__tab-wrapper').nth(1)
    await wrapper.hover()

    // Read both values in a single synchronous page.evaluate() call to ensure
    // both are read under the same :hover pseudo-class state.
    const values = await page.evaluate(() => {
      const wrappers = document.querySelectorAll('.tabbar .tabs__tab-wrapper')
      const w = wrappers[1] as HTMLElement
      const tab = w.querySelector('.tabs__tab') as HTMLElement
      return {
        bg: window.getComputedStyle(w).backgroundColor,
        color: window.getComputedStyle(tab).color
      }
    })
    // --bg-hover: #f0efed → rgb(240, 239, 237)
    expect(values.bg).toBe('rgb(240, 239, 237)')
    // --text: #18181b → rgb(24, 24, 27)
    expect(values.color).toBe('rgb(24, 24, 27)')
  })

  // ---- Gap 2: tabbar active neutralization ----

  test('Tabbar active-neutralization: active tab computes box-shadow none and transparent background', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab--active { box-shadow: none; background: transparent }
    // overrides the global .tabs__tab--active underline + --accent-soft wash so
    // the wrapper ::before/::after own the active visual treatment inside .tabbar.
    await mount(<TabbarFidelityFixture />)
    const activeTab = page.locator('.tabbar .tabs__tab--active')

    const boxShadow = await activeTab.evaluate((el) => window.getComputedStyle(el).boxShadow)
    expect(boxShadow).toBe('none')

    const bgColor = await activeTab.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    // Transparent serializes as rgba(0, 0, 0, 0) in Chrome.
    expect(bgColor).toBe('rgba(0, 0, 0, 0)')
  })

  // ---- Gap 3: Fix C — tablist is content-width ----

  test('Fix C — .tabbar .tabs__list: flex-grow resolves to 0 (content-width, actions hug last tab)', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__list { flex: 0 0 auto } overrides .tabs__list { flex: 1 }
    // so the tablist is content-width and the actions row (+ / spacer / chevron)
    // sits directly after the last tab separator instead of floating at far right.
    await mount(<TabbarFidelityFixture />)
    const list = page.locator('.tabbar .tabs__list')

    const flexGrow = await list.evaluate((el) => window.getComputedStyle(el).flexGrow)
    expect(flexGrow).toBe('0')
  })

  // ---- Gap 4: overflow flush (border-radius: 0px) ----

  test('AC-D — .tabbar__overflow button: border-radius 0px (flush, symmetry with tabbar__new)', async ({
    mount,
    page
  }) => {
    // TabBar.css .tabbar__overflow has no border-radius (Fix D comment: flush
    // full-height strip cell matching .tab-new). Computed value must be 0px,
    // symmetrical with the existing .tabbar__new AC-D assertion above.
    await mount(<TabbarFidelityFixture />)
    const overflowBtn = page.locator('.tabbar__overflow')
    await expect(overflowBtn).toBeVisible()

    const borderRadius = await overflowBtn.evaluate(
      (el) => window.getComputedStyle(el).borderRadius
    )
    expect(borderRadius).toBe('0px')
  })

  // ---- Gap 5: method chip aria-hidden ----

  test('Fix E — method chip (.method) has aria-hidden="true" (decorative visual affordance)', async ({
    mount,
    page
  }) => {
    // The method chip is rendered with aria-hidden="true" to prevent
    // double-announcement on URL-only tabs where deriveLabel already prepends
    // the method string (see TabDescriptor.method JSDoc for the AT tradeoff).
    // TabbarFidelityFixture renders a HEAD chip on the active tab — assert it.
    await mount(<TabbarFidelityFixture />)
    const methodChip = page.locator('.tabbar .method').first()

    const ariaHidden = await methodChip.getAttribute('aria-hidden')
    expect(ariaHidden).toBe('true')
  })

  // ---- AC-21: screenshot baseline (supplementary) ----

  test('AC-21 — screenshot baseline: tabbar fidelity fixture (supplementary)', async ({
    mount
  }) => {
    // Supplementary visual gate. The EXACT computed-style assertions above are
    // the primary fidelity proof. The screenshot captures the assembled visual
    // including token colors, spacing, and the active stripe under soft mstyle.
    //
    // FIRST-EVER baseline: Playwright generates tabbar-fidelity.png on the first
    // run. After this test run, MANUALLY inspect the generated baseline PNG under
    // __snapshots__/ to confirm: the active tab shows a top green stripe, the
    // HEAD chip renders in pink (#ec4899) on a soft tinted background, and the
    // strip is rendered on the --bg-sunken surface. Do NOT rely on the screenshot
    // gate until the baseline has been visually confirmed (Risk-6 in grill report).
    const component = await mount(<TabbarFidelityFixture />)
    await expect(component).toHaveScreenshot('tabbar-fidelity.png', {
      threshold: 0.2,
      maxDiffPixelRatio: 0.01,
      animations: 'disabled'
    })
  })
})

// ---------------------------------------------------------------------------
// [011] Feature-011 — tab width cap: no cell growth + ellipsis truncation
//
// Proves the .tabbar .tabs__tab-wrapper { max-width: 220px } rule from Tabs.css
// holds in a real browser with real layout (jsdom cannot resolve computed geometry).
// TabbarLongTitleFidelityFixture provides TWO long-titled tabs that overflow if
// uncapped (exercising the "multiple long-titled tabs open" condition from spec AC-8),
// plus one short tab for contrast.
//
// NOTE: The existing AC-7/AC-8/AC-6/AC-9 numbered tests earlier in this file
// cover FEATURE-002 concerns (a11y roles, actions slot, arrow-nav, disabled tab).
// The [011]-prefixed tests below are for FEATURE-011 (tab width cap) and share
// those AC numbers only because the same spec AC entries cover both features in
// different contexts. The [011] prefix disambiguates them.
// ---------------------------------------------------------------------------

test.describe('[011] Tabs — tab width cap: long titles held to 220px border-box cap', () => {
  test.beforeEach(async ({ page }) => {
    // Match the Feature-005 fidelity suite's beforeEach: [data-mstyle="soft"] so
    // the cascade is consistent. The cap is mstyle-independent, but setting this
    // keeps the fixture rendering identical to TabbarFidelityFixture's environment.
    await page.evaluate(() => {
      document.documentElement.dataset.mstyle = 'soft'
    })
  })

  test('[011] AC-7 — long-title tab cell: width cap ≤ 221px and label text-overflow ellipsis under cap (border-box 220px cap via fixture scoped <style>)', async ({
    mount,
    page
  }) => {
    // TabbarLongTitleFidelityFixture mounts two tabs with ~65-char labels that
    // overflow the 220px cell if uncapped. getBoundingClientRect().width reflects
    // the actual rendered layout (unlike getComputedStyle(el).maxWidth which only
    // confirms the CSS constraint is present — proven separately in the AC-6/AC-9 test).
    //
    // The border-box context for this assertion comes from TabbarLongTitleFidelityFixture's
    // own scoped <style> (`.ct-borderbox-scope`), which reproduces production base.css's
    // `* { box-sizing: border-box }` reset locally — a global base.css harness import was
    // deliberately avoided because it shifts unrelated screenshot baselines (playwright/
    // index.tsx imports only tokens.css). Under border-box, max-width:220px caps the WHOLE
    // border box (content + padding + border), so the total rendered wrapper width must be
    // ≤220px. The +1 tolerance accounts for fractional pixel rounding in the browser layout
    // engine.
    //
    // Without the cap the label (~65 chars at 12.5px) would render at ~450px+.
    await mount(<TabbarLongTitleFidelityFixture />)
    const wrapper = page.locator('.tabbar .tabs__tab-wrapper').first()

    const width = await wrapper.evaluate((el) => el.getBoundingClientRect().width)
    expect(width).toBeLessThanOrEqual(221) // 220px border-box cap + 1px sub-pixel tolerance

    // Assert that the label computes text-overflow: ellipsis in the long-title-under-cap
    // scenario — proves the base .tabs__tab-label rule in Tabs.css resolves text-overflow:
    // ellipsis on the label when the cell is genuinely capped and the label overflows (the
    // computed property, not the rendered glyph). Combined with the ≤221px width assertion
    // above (cap proven active) and the fixture's ~65-char overflowing labels, this exercises
    // the truncation contract under the cap. This is distinct from AC-16, which uses
    // normal-length titles well under the 220px cap; that test cannot prove the property
    // resolves under cap pressure via the base rule.
    const label = page.locator('.tabbar .tabs__tab-label').first()
    const textOverflow = await label.evaluate((el) => window.getComputedStyle(el).textOverflow)
    expect(textOverflow).toBe('ellipsis')
  })

  test('[011] AC-8 — tablist total width stays within cap-derived bound; fails if any long tab grows beyond 220px', async ({
    mount,
    page
  }) => {
    // This test is genuinely diagnostic: it measures the tablist (.tabs__list)
    // total rendered width and asserts it stays within a cap-derived bound.
    //
    // The bound derivation (border-box: border absorbed inside cap, not additive):
    //   N_TABS × CAP_PX + TOLERANCE
    //   = 3 × 220 + 2 = 662px
    //
    // If the cap fails (max-width removed), the 2 long tabs grow to ~450px each
    // (~980px+ for those 2 alone), causing the tablist to far exceed 662px.
    // This assertion is independent of [011] AC-7: removing AC-7 does not neuter it.
    //
    // Why tablist width (not the new-tab button gap):
    //   .tabbar .tabs__list { flex: 0 0 auto } (Fix C) makes the tablist content-width
    //   so the new-tab button always hugs it regardless of cap. A "gap ≤ 1px" assertion
    //   is trivially true even when tabs have grown to 450px — it provides no diagnostic
    //   signal for cap failure. Measuring the tablist width directly is what catches it.
    await mount(<TabbarLongTitleFidelityFixture />)

    const tablistWidth = await page.evaluate(() => {
      // Null guard: if the selector misses, return Infinity so the assertion fails
      // with a clear numeric failure rather than a cryptic null dereference.
      const tablist = document.querySelector('.tabbar .tabs__list') as HTMLElement | null
      if (tablist == null) return Infinity
      return tablist.getBoundingClientRect().width
    })

    // Under border-box (fixture's scoped .ct-borderbox-scope <style>), each capped
    // wrapper's border-right:1px is ABSORBED inside the 220px cap — it is NOT additive.
    // Each wrapper is ≤220px total (border included), so 3 tabs → ≤660px.
    // +2px sub-pixel tolerance → 662px bound.
    // Uncapped: 2 × ~450px + ~80px ≈ ~980px — far exceeds this bound.
    const N_TABS = 3
    const CAP_PX = 220
    const TOLERANCE_PX = 2
    const bound = N_TABS * CAP_PX + TOLERANCE_PX // 662px
    expect(tablistWidth).toBeLessThanOrEqual(bound)
  })
})

// ---------------------------------------------------------------------------
// AC-17 — single strip bottom border (standalone mount context)
//
// Full AC-17 requires: .shell__tabs border-bottom-width = 0px (Shell wrapper
// removes its own bottom border when the tabbar provides it) AND .tabbar
// border-bottom-width = 1px. In the CT standalone mount (no Shell wrapper),
// only the .tabbar side can be asserted here.
//
// The full Shell-context single-border guarantee (both sides) is covered by
// the /verify design-auditor runtime probe against the running Electron app.
// ---------------------------------------------------------------------------

test.describe('Tabs — AC-17 single strip bottom border (standalone mount)', () => {
  test('AC-17 — .tabbar computes border-bottom-width: 1px from base .tabs rule', async ({
    mount
  }) => {
    // The base .tabs { border-bottom: 1px solid var(--border) } rule applies to
    // .tabs.tabbar. .tabs.tabbar does NOT override border-bottom in Tabs.css,
    // so the inherited 1px border from .tabs is the strip's bottom separator.
    // Assertion: .tabbar (outer container) border-bottom-width = 1px.
    const component = await mount(<TabbarFidelityFixture />)
    const bWidth = await component.evaluate((el) => window.getComputedStyle(el).borderBottomWidth)
    expect(bWidth).toBe('1px')
  })

  test('AC-17 — .shell__tabs wrapper: border-bottom-width 0px (Shell de-dup guard)', async ({
    mount,
    page
  }) => {
    // The Shell-context half of AC-17: .shell__tabs must NOT add its own bottom
    // border. Shell.css .shell__tabs has no border-bottom rule, so the strip
    // border lives exclusively on .tabbar (proven by the standalone-mount test
    // above). This test mounts the tabbar INSIDE a .shell__tabs wrapper with
    // Shell.css loaded, ensuring a future re-introduction of a .shell__tabs
    // border-bottom fails loudly here.
    // Shell.css is imported in Tabs.stories.tsx alongside TabBar.css (documented
    // test-harness CSS composition).
    await mount(<TabbarInShellTabsFixture />)
    const shellTabsEl = page.locator('.shell__tabs')

    const bWidth = await shellTabsEl.evaluate((el) => window.getComputedStyle(el).borderBottomWidth)
    expect(bWidth).toBe('0px')
  })
})

// ---------------------------------------------------------------------------
// AC-22 (feature-005 non-regression) — bare .tabs consumer unaffected
//
// All .tabbar-scoped rules in Tabs.css use compound selectors (.tabbar .tabs__*,
// .tabs.tabbar) so they ONLY fire when .tabbar is on the outer container.
// This describe proves the task-003 scoped rules did NOT leak to bare .tabs.
//
// Mounts TabsClosableFixture which renders <Tabs closable> with NO className,
// so the outer div has class "tabs" only (no "tabbar"). The PRE-005 active
// treatment (box-shadow inset + --accent-soft wash) must remain unchanged.
// ---------------------------------------------------------------------------

test.describe('Tabs — [feat-005] AC-22 bare-consumer non-regression (.tabbar scope does not leak)', () => {
  test('bare .tabs active tab retains PRE-005 box-shadow underline containing --accent', async ({
    mount,
    page
  }) => {
    // In a bare .tabs (no .tabbar), the active tab's box-shadow is set by:
    //   .tabs__tab--active { box-shadow: inset 0 -2px 0 var(--accent, #10b981) }
    // The .tabbar .tabs__tab--active override (box-shadow: none) must NOT fire
    // because there is no .tabbar ancestor.
    await mount(<TabsClosableFixture initialActiveId="params" />)
    const activeTab = page.locator('.tabs__tab--active')

    const boxShadow = await activeTab.evaluate((el) => window.getComputedStyle(el).boxShadow)
    // Must be non-empty (not 'none') and must contain the accent rgb value.
    // --accent: #10b981 → rgb(16, 185, 129)
    expect(boxShadow).not.toBe('none')
    expect(boxShadow).toContain('rgb(16, 185, 129)')
  })

  test('bare .tabs active tab retains --accent-soft background wash (non-transparent)', async ({
    mount,
    page
  }) => {
    // .tabs__tab--active { background-color: var(--accent-soft, color-mix(...)) }
    // --accent-soft is a semi-transparent green tint. The .tabbar override sets
    // background: transparent; but that only fires under .tabbar. In a bare .tabs
    // the wash must remain (non-transparent background-color).
    await mount(<TabsClosableFixture initialActiveId="params" />)
    const activeTab = page.locator('.tabs__tab--active')

    const bgColor = await activeTab.evaluate((el) => window.getComputedStyle(el).backgroundColor)
    // Must NOT be transparent (rgba(0,0,0,0) is the serialized form of transparent).
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)')
    expect(bgColor).not.toBe('transparent')
  })

  test('bare .tabs computes overflow: hidden (NOT visible)', async ({ mount, page }) => {
    // .tabs { overflow: hidden } in Tabs.css.
    // .tabs.tabbar { overflow: visible } overrides ONLY for the .tabbar variant.
    // A bare .tabs (no .tabbar) must keep overflow: hidden so tab overflow is
    // clipped (pre-005 baseline behavior unchanged).
    await mount(<TabsClosableFixture />)
    const tabsEl = page.locator('.tabs')

    const overflow = await tabsEl.evaluate((el) => window.getComputedStyle(el).overflow)
    expect(overflow).toBe('hidden')
  })

  test('[011] bare .tabs__tab-wrapper: max-width computes to none (cap rule scoped to .tabbar only)', async ({
    mount,
    page
  }) => {
    // .tabbar .tabs__tab-wrapper { max-width: 220px } uses a compound selector
    // that requires .tabbar on the outer container. A bare <Tabs> (no .tabbar
    // className) must NOT be capped — max-width must compute to 'none'.
    //
    // Guards against future selector simplification: if .tabbar were dropped
    // and the rule changed to just .tabs__tab-wrapper, this test would fail
    // and surface the unintended cap on bare consumers.
    await mount(<TabsClosableFixture initialActiveId="params" />)
    const wrapper = page.locator('.tabs__tab-wrapper').first()

    const maxWidth = await wrapper.evaluate((el) => window.getComputedStyle(el).maxWidth)
    expect(maxWidth).toBe('none')
  })
})
