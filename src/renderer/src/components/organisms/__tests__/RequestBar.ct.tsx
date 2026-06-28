/**
 * RequestBar.ct.tsx — Playwright Component Tests for the RequestBar organism.
 *
 * These tests run in a real Chromium browser via @playwright/experimental-ct-react,
 * covering concerns jsdom cannot exercise:
 *
 *   - Real layout: computed flex bounding boxes confirm [method ▾][URL][Send] order.
 *   - Disabled state: native browser `disabled` attribute prevents pointer events.
 *   - Keyboard shortcuts: real Chromium keydown dispatch (⌘↵, ⌘S).
 *   - Radix Dropdown dismiss: DismissableLayer pointer-event timing (two-step gate).
 *   - Per-tab isolation: live zustand re-renders in a real browser runtime.
 *
 * Fixture components are imported from RequestBar.stories.tsx — Playwright
 * experimental-ct-react requires that mounted components be defined in a
 * separate file from the test file (see Dropdown.stories.tsx comment for rationale).
 *
 * Styling context (project memory ct-fidelity-fixture-scoping):
 *   - `tokens.css` is imported globally for all CT tests via playwright/index.tsx.
 *   - `data-mstyle='soft'` is set on `document.documentElement` in `beforeEach`
 *     so the `.method.GET { background; color }` rules from tokens.css resolve
 *     and the method pill renders with its production colour — not uncolored.
 *
 * Dismiss gate (project memory ct-radix-dismiss-arm-race):
 *   Before any outside `page.mouse.click`, the two-step gate:
 *     1. `menu.evaluate(el => Promise.all(el.getAnimations().map(a => a.finished)))`
 *        — waits for all entry animations to complete.
 *     2. `page.evaluate(() => new Promise(r => setTimeout(r, 0)))`
 *        — yields one macrotask so Radix DismissableLayer's setTimeout(0)-deferred
 *        pointerdown listener is armed before the click dispatches.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import { RequestBar } from '@renderer/components/organisms/RequestBar'
// Non-component values must be in a SEPARATE import statement from fixture
// components.  Playwright CT's Babel transform (tsxTransform.js) only removes
// an import and replaces its specifiers with importRef objects when EVERY
// specifier in that statement is used as a JSX element.  Mixing string
// constants (CT_TAB_A_URL, CT_TAB_B_URL) with components in one statement
// prevents the component specifiers from being replaced and causes the
// "cannot be mounted" runtime error.
import { CT_TAB_A_URL, CT_TAB_B_URL } from './RequestBar.stories'
import {
  RequestBarSendSpyFixture,
  RequestBarTwoTabFixture,
  RequestBarStoreResetFixture
} from './RequestBar.stories'

// ---------------------------------------------------------------------------
// Setup — reset store state and apply full styling context before every test
// ---------------------------------------------------------------------------

/**
 * Before each test:
 *
 * 1. Mount `RequestBarStoreResetFixture`, which calls `tabsStore.setState` via
 *    `useEffect` to seed a single clean GET tab (empty URL), then signals
 *    completion via `data-testid="ct-store-reset-done"`.  Waiting for that
 *    testid guarantees the store is in the known state before any test-level
 *    mount runs (preventing order-dependent failures when a prior test leaves a
 *    non-empty URL or changed method in the singleton store).
 *
 *    The subsequent test's own `mount()` call replaces the seeder component
 *    in the DOM; the store state it wrote persists into the test.
 *
 * 2. Set `data-mstyle='soft'` on `<html>` so the method-pill colour rules from
 *    tokens.css resolve correctly in real Chromium.  tokens.css is already
 *    imported once for all CT tests in playwright/index.tsx; this attribute
 *    scopes the selector `[data-mstyle='soft'] .method.GET { … }`.
 */
test.beforeEach(async ({ mount, page }) => {
  // Reset store in the browser context via mount-time seeding (established
  // pattern — mirrors how RequestBarTwoTabFixture seeds the store via useEffect).
  //
  // Unmounting after the store is seeded is required: playwrightMount() throws
  // "Attempting to mount a component into a container that already has a React
  // root" if called twice on the same div#root.  Calling .unmount() removes the
  // root from __pwRootRegistry so the test's own mount() can create a fresh one.
  // The tabsStore state written by the fixture's useEffect persists after unmount.
  const resetFixture = await mount(<RequestBarStoreResetFixture />)
  await page.waitForSelector('[data-testid="ct-store-reset-done"]', { state: 'attached' })
  await resetFixture.unmount()

  await page.evaluate(() => {
    document.documentElement.setAttribute('data-mstyle', 'soft')
  })
})

// ---------------------------------------------------------------------------
// 1. Layout — [method ▾][URL input][Send] present and in left-to-right order
// ---------------------------------------------------------------------------

test.describe('RequestBar — layout', () => {
  /**
   * Asserts that all three primary elements are visible and that their
   * horizontal bounding boxes confirm the visual order: method pill → URL
   * input → Send button (left to right, flex row).
   *
   * jsdom has no layout engine; this is the real-browser proof of AC-20.
   */
  test('renders method pill, URL input, and Send button in left-to-right visual order', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const methodBtn = page.getByRole('button', { name: 'GET' })
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })
    const sendBtn = page.getByRole('button', { name: 'Send' })

    // All three controls must be visible
    await expect(methodBtn).toBeVisible()
    await expect(urlInput).toBeVisible()
    await expect(sendBtn).toBeVisible()

    // Collect bounding boxes in parallel
    const [methodBox, urlBox, sendBox] = await Promise.all([
      methodBtn.boundingBox(),
      urlInput.boundingBox(),
      sendBtn.boundingBox()
    ])

    expect(methodBox).not.toBeNull()
    expect(urlBox).not.toBeNull()
    expect(sendBox).not.toBeNull()

    // Method pill's left edge must precede the URL input's left edge
    expect(methodBox!.x).toBeLessThan(urlBox!.x)

    // URL input's right edge must precede the Send button's left edge
    // (+1 px tolerance for sub-pixel rounding in flex gap)
    expect(urlBox!.x + urlBox!.width).toBeLessThanOrEqual(sendBox!.x + 1)
  })

  /**
   * AC-20 overflow contract: a URL long enough to overflow the input width
   * scrolls horizontally INSIDE the `<input>` element — it does NOT push the
   * method pill left or the Send button right (no layout reflow).
   *
   * Strategy: capture the method pill's left edge (x) and the Send button's
   * left edge (x) before the fill, then again after, and assert both are
   * unchanged (±1 px sub-pixel tolerance).  The scroll behaviour is internal
   * to the `<input>`; only a layout-breaking width change would move the
   * flanking elements.
   */
  test('a very long URL scrolls inside the input without reflowing the method pill or Send button (AC-20)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const methodBtn = page.getByRole('button', { name: 'GET' })
    const sendBtn = page.getByRole('button', { name: 'Send' })

    // Baseline positions before the long fill
    const [methodBefore, sendBefore] = await Promise.all([
      methodBtn.boundingBox(),
      sendBtn.boundingBox()
    ])

    expect(methodBefore).not.toBeNull()
    expect(sendBefore).not.toBeNull()

    // Fill with a URL long enough to overflow a typical input (300+ chars path)
    const longUrl = 'https://example.com/' + 'a'.repeat(300) + '/endpoint'
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })
    await urlInput.fill(longUrl)

    // Positions after the long fill
    const [methodAfter, sendAfter] = await Promise.all([
      methodBtn.boundingBox(),
      sendBtn.boundingBox()
    ])

    expect(methodAfter).not.toBeNull()
    expect(sendAfter).not.toBeNull()

    // Neither element must shift by more than 1 px (sub-pixel rounding tolerance)
    expect(Math.abs(methodAfter!.x - methodBefore!.x)).toBeLessThanOrEqual(1)
    expect(Math.abs(sendAfter!.x - sendBefore!.x)).toBeLessThanOrEqual(1)
  })
})

// ---------------------------------------------------------------------------
// 2. Send button — disabled with empty URL; enabled after typing a URL
// ---------------------------------------------------------------------------

test.describe('RequestBar — Send disabled / enabled', () => {
  /**
   * Verifies the real browser `disabled` attribute behaviour:
   *   - On mount the store's URL is '' → `canSend` is false → button disabled.
   *   - After `fill()` types a non-empty URL → `updateActiveSpec` → re-render
   *     → `canSend` true → button enabled.
   *
   * The `disabled` state is a DOM attribute enforced by the browser's pointer-
   * event model — something jsdom only partially emulates (AC-12, AC-13).
   */
  test('Send is disabled with an empty URL and becomes enabled after typing', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const sendBtn = page.getByRole('button', { name: 'Send' })
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })

    // Store starts with url: '' → canSend false → button must be disabled
    await expect(sendBtn).toBeDisabled()

    // Type a URL into the controlled input → onChange → updateActiveSpec
    await urlInput.fill('https://ct-enabled.example.com')

    // canSend is now true → button must be enabled
    await expect(sendBtn).toBeEnabled()
  })
})

// ---------------------------------------------------------------------------
// 3. Keyboard shortcuts — ⌘↵ triggers send path; ⌘S triggers save path
// ---------------------------------------------------------------------------

test.describe('RequestBar — keyboard shortcuts', () => {
  /**
   * Verifies the ⌘↵ global keydown listener in a real Chromium key-dispatch
   * context.  The fixture exposes `onSend` results in the DOM via
   * `data-testid="ct-rb-last-sent"` so no Node.js spy is needed.
   *
   * Steps:
   *   1. Type a URL (canSend guard must pass).
   *   2. Press Meta+Enter → document keydown handler reads live store state
   *      → calls onSend → fixture updates DOM indicator.
   *   3. Assert the DOM indicator shows the expected "METHOD::url" string.
   */
  test('⌘↵ (Meta+Enter) triggers the send path when the URL is non-empty', async ({
    mount,
    page
  }) => {
    await mount(<RequestBarSendSpyFixture />)

    // Type a URL — store's active tab url updates via updateActiveSpec
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })
    await urlInput.fill('https://ct-send.example.com')

    // ⌘↵ dispatches a document-level keydown with metaKey+Enter
    await page.keyboard.press('Meta+Enter')

    // Fixture renders last send intent as "METHOD::url"
    // Initial tab starts with GET method; URL was just filled in
    await expect(page.getByTestId('ct-rb-last-sent')).toHaveText('GET::https://ct-send.example.com')
  })

  /**
   * Verifies that ⌘S fires the save path: `markClean` is called and the dirty
   * modifier class is removed from the Save button.
   *
   * Typing into the URL input calls `updateActiveSpec` which sets `dirty: true`,
   * making the Save button show the `request-bar__save--dirty` CSS modifier class.
   * After ⌘S the class must be gone — that is the real assertion here.
   *
   * Note: the `e.preventDefault()` contract (suppressing the native save dialog)
   * cannot be verified in headless Chromium, which never shows native dialogs
   * regardless.  That contract is rigorously asserted in the jsdom unit test
   * (RequestBar.test.tsx — describe ⌘S prevents the default browser action).
   */
  test('⌘S (Meta+s) fires the save path and clears the dirty flag', async ({ mount, page }) => {
    await mount(<RequestBar />)

    const saveBtn = page.getByRole('button', { name: 'Save' })
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })

    // Typing calls updateActiveSpec → dirty: true → modifier class applied
    await urlInput.fill('https://ct-save.example.com')
    await expect(saveBtn).toHaveClass(/request-bar__save--dirty/)

    // ⌘S: document keydown → e.preventDefault() + markClean(activeTabId)
    await page.keyboard.press('Meta+s')

    // dirty: false → modifier class removed (markClean fired; save path confirmed)
    await expect(saveBtn).not.toHaveClass(/request-bar__save--dirty/)
  })
})

// ---------------------------------------------------------------------------
// 4. Method Dropdown — opens on trigger click; outside click dismisses it
// ---------------------------------------------------------------------------

test.describe('RequestBar — method Dropdown open / dismiss', () => {
  /**
   * Verifies Radix Dropdown open + click-outside dismiss in a real browser.
   *
   * The two-step readiness gate (project memory ct-radix-dismiss-arm-race)
   * is applied before the outside click to prevent the race where an
   * immediate outside click dispatches before Radix DismissableLayer's
   * setTimeout(0)-deferred pointerdown listener is armed:
   *   1. Await all menu entry animations to completion.
   *   2. Yield one macrotask via setTimeout(0) to arm the listener.
   */
  test('method Dropdown opens on trigger click and closes on outside click (two-step gate)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Open the method Dropdown via pointer click on the method trigger pill
    // The trigger's accessible name is the current method text (initially 'GET')
    const methodTrigger = page.getByRole('button', { name: 'GET' })
    await methodTrigger.click()

    const menu = page.getByRole('menu')
    await expect(menu).toBeVisible()

    // ── Two-step readiness gate (ct-radix-dismiss-arm-race) ────────────────
    // Step 1: Wait for all menu entry animations to finish so the content is
    //         fully composited and the animation-completion floor is met.
    await menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))
    // Step 2: Yield one macrotask so Radix DismissableLayer's setTimeout(0)-
    //         deferred pointerdown listener arms before the outside click fires.
    await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))
    // ───────────────────────────────────────────────────────────────────────

    // Click well outside both the trigger (upper-left) and the menu panel.
    // Default CT viewport is 1280×720; bottom-right corner is safely outside.
    const vp = page.viewportSize() ?? { width: 1280, height: 720 }
    await page.mouse.click(vp.width - 10, vp.height - 10)

    await expect(menu).not.toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// 5. Per-tab isolation — switching active tab swaps method + URL; no bleed
// ---------------------------------------------------------------------------

test.describe('RequestBar — per-tab isolation', () => {
  /**
   * Verifies that RequestBar re-renders with the new tab's method + URL when
   * the active tab changes, and that Tab A's values do not bleed into Tab B.
   *
   * The `RequestBarTwoTabFixture` seeds the store (via useEffect) with two
   * known tabs and provides a `ct-rb-select-tab-b` button that calls
   * `tabsStore.getState().selectActive(CT_TAB_B_ID)` in the browser.
   *
   * The `await expect(urlInput).toHaveValue(CT_TAB_A_URL)` line acts as a
   * readiness gate that waits for the fixture's useEffect to fire and the
   * store to be seeded before asserting the per-tab state.
   */
  test('switching the active tab swaps the rendered method and URL with no bleed', async ({
    mount,
    page
  }) => {
    await mount(<RequestBarTwoTabFixture />)

    const urlInput = page.getByRole('textbox', { name: 'Request URL' })

    // ── Wait for fixture's useEffect to seed the store (async after mount) ──
    // Tab A is the initial active tab: GET method, CT_TAB_A_URL
    await expect(urlInput).toHaveValue(CT_TAB_A_URL)
    await expect(page.getByRole('button', { name: 'GET' })).toBeVisible()

    // ── Switch to Tab B ─────────────────────────────────────────────────────
    // The fixture's button calls tabsStore.getState().selectActive(CT_TAB_B_ID)
    await page.getByTestId('ct-rb-select-tab-b').click()

    // ── Assert Tab B values — no bleed from Tab A ───────────────────────────
    await expect(urlInput).toHaveValue(CT_TAB_B_URL)
    await expect(page.getByRole('button', { name: 'POST' })).toBeVisible()

    // Tab A's GET method pill must no longer be visible (no bleed)
    await expect(page.getByRole('button', { name: 'GET' })).not.toBeVisible()
  })
})
