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
  TabsClosableRemoveTwoPhase
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
  test('pressing Delete on a focused tab fires onClose with that tab\'s id', async ({
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

  test('pressing Backspace on a focused tab fires onClose with that tab\'s id', async ({
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
