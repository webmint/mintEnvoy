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
import { CT_TAB_A_URL, CT_TAB_B_URL, CT_FILLED_URL } from './RequestBar.stories'
import { METHODS } from '@renderer/lib/httpMethods'
import {
  RequestBarSendSpyFixture,
  RequestBarTwoTabFixture,
  RequestBarStoreResetFixture,
  RequestBarFilledFixture,
  RequestBarMethodSwitchFixture
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
   * left edge (x) with a SHORT but NON-EMPTY URL, then again after filling a
   * 300+ char URL, and assert both are unchanged (±1 px sub-pixel tolerance).
   *
   * Why non-empty baseline? The ⌘↵ keycap (.request-bar__kbd) mounts only when
   * canSend is true (URL non-empty). Baselining with an empty URL would capture
   * the pre-keycap (narrow) Send width; the subsequent long fill would make the
   * keycap appear and widen Send ~30 px — conflating keycap appearance with
   * URL-length reflow and producing a false failure. Using a short non-empty URL
   * for the baseline ensures the keycap is already present before measuring, so
   * the only variable between the two samples is URL length — exactly what AC-20
   * protects against.
   */
  test('a very long URL scrolls inside the input without reflowing the method pill or Send button (AC-20)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const methodBtn = page.getByRole('button', { name: 'GET' })
    const sendBtn = page.getByRole('button', { name: 'Send' })
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })

    // ── Baseline: short but non-empty URL so the keycap is already present ──
    // Both samples must be non-empty to isolate URL length as the only variable.
    await urlInput.fill('https://x.co')

    const [methodBefore, sendBefore] = await Promise.all([
      methodBtn.boundingBox(),
      sendBtn.boundingBox()
    ])

    expect(methodBefore).not.toBeNull()
    expect(sendBefore).not.toBeNull()

    // ── Long fill: URL long enough to overflow a typical input (300+ chars) ──
    // The keycap is still present; only URL length changes between the samples.
    const longUrl = 'https://example.com/' + 'a'.repeat(300) + '/endpoint'
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

// ---------------------------------------------------------------------------
// 6. Fidelity — computed styles from Tasks 001 + 002 verified in real Chromium
// ---------------------------------------------------------------------------

/**
 * Tiered fidelity suite for the restyled RequestBar (Tasks 001 + 002).
 *
 * jsdom cannot resolve computed pseudo-class styles (:focus), token-derived
 * colors (color-mix()), or CSS cascade tie-breaks at runtime.  These tests run
 * in real Chromium via @playwright/experimental-ct-react to prove:
 *
 *   1. Reference geometry  — all primary controls render at ~32 px tall.
 *   2. Token binding       — `border-radius` equals the `--radius` token (7 px).
 *   3. Focus ring          — URL `:focus` resolves `--accent` border + ring shadow.
 *   4. Method-select style — `--bg-elev` background, border present, per-method
 *                            GET colour via the (0,3,0) tie-break + no-colour
 *                            fall-through that Task 002 relies on.
 *   5. Send inset shadow   — `font-weight: 600` + non-none `box-shadow` when enabled.
 *   6. Keycap gating       — `.request-bar__kbd` absent/present with canSend.
 *   7. Ghost actions       — Save + Share are visible with text labels + borders.
 *   8. Visual regression   — `toHaveScreenshot` baseline on `.request-bar`.
 *
 * Pitfalls handled (project memory):
 *   - ct-fidelity-fixture-scoping: `tokens.css` is already imported globally in
 *     playwright/index.tsx; `data-mstyle='soft'` is set on <html> by `beforeEach`;
 *     the method-select overrride selector `.request-bar .request-bar__method.method`
 *     at (0,3,0) is scoped inside `.request-bar` which the component provides.
 *   - ct-radix-dismiss-arm-race: no Radix overlay is opened in these fidelity
 *     tests, so the two-step dismiss gate is not needed here.
 */
test.describe('RequestBar — fidelity', () => {
  /**
   * Asserts that all five primary bar controls render at approximately 32 px
   * tall (the reference-geometry contract from AC-fidelity).
   *
   * Uses `getBoundingClientRect().height` (border-box height) so that both the
   * explicitly-sized controls (URL input, Send, Save, Share at `height: 32px`)
   * and the auto-height method button (padding + content ≈ 28 px) all fall
   * within the ±6 px tolerance band around 32 px.
   */
  test('all primary controls render at approximately 32px (reference geometry)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Explicitly-sized controls carry `height: 32px` in CSS.  The CT harness has no
    // box-sizing reset (playwright/index.tsx only imports tokens.css), so the default
    // box-sizing is `content-box`.  getBoundingClientRect().height is the border-box:
    //   - `border: none` elements (Send): content 32px + 0px border = 32px
    //   - `border: 1px solid` elements (URL input, Save, Share): 32px + 2px = 34px
    // Valid range is 32–34px; the old 24px design must NOT pass (lower bound > 24).
    const explicitlySized = [
      { selector: '.request-bar__url', label: 'URL input' },
      { selector: '.request-bar__send', label: 'Send' },
      { selector: '.request-bar__save', label: 'Save' },
      { selector: '.request-bar__share', label: 'Share' }
    ]

    for (const { selector, label } of explicitlySized) {
      const height = await page
        .locator(selector)
        .evaluate((el) => el.getBoundingClientRect().height)
      // 32px (no border) or 34px (1px border × 2); 24px must NOT pass
      expect(height, `${label} height`).toBeGreaterThanOrEqual(32)
      expect(height, `${label} height`).toBeLessThanOrEqual(34)
    }

    // Auto-height method button: `padding: 7px 10px 7px 12px` + `border: 1px solid`
    // + `font-size: 11.5px` line-box → expected ~28–34px.
    // Lower bound 28px > 24px: the old 24px design baseline must NOT pass.
    const methodHeight = await page
      .locator('.request-bar__method')
      .evaluate((el) => el.getBoundingClientRect().height)
    expect(methodHeight, 'method-select height').toBeGreaterThanOrEqual(28)
    expect(methodHeight, 'method-select height').toBeLessThanOrEqual(34)
  })

  /**
   * Asserts that `.request-bar` carries exactly the right layout geometry:
   *   - `padding`: 12px (top/bottom) × 16px (left/right)  — AC-8
   *   - `gap` (column-gap): 8px                            — AC-8
   *
   * Read via getComputedStyle so CSS-variable values are fully resolved.
   */
  test('.request-bar padding is 12px 16px and column-gap is 8px (AC-8 layout geometry)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const [paddingTop, paddingRight, paddingBottom, paddingLeft, columnGap] = await page
      .locator('.request-bar')
      .evaluate((el) => {
        const s = window.getComputedStyle(el)
        return [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft, s.columnGap]
      })

    expect(paddingTop, 'padding-top').toBe('12px')
    expect(paddingRight, 'padding-right').toBe('16px')
    expect(paddingBottom, 'padding-bottom').toBe('12px')
    expect(paddingLeft, 'padding-left').toBe('16px')
    expect(columnGap, 'column-gap (gap)').toBe('8px')
  })

  /**
   * Asserts that the inner actions group `.request-bar__actions` has a
   * column-gap of exactly 8px (the F-002 fidelity fix: was 4px, corrected to 8px).
   *
   * The outer bar padding test above asserts `.request-bar` column-gap (between
   * method/URL/actions), but does NOT cover the gap between Send/Save/Share
   * siblings inside the actions group.  This test is the lock for the inner gap.
   */
  test('.request-bar__actions column-gap is 8px (inner actions gap — F-002)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const columnGap = await page
      .locator('.request-bar__actions')
      .evaluate((el) => window.getComputedStyle(el).columnGap)

    expect(columnGap, '.request-bar__actions column-gap').toBe('8px')
  })

  /**
   * Asserts that `border-radius` on each primary control exactly resolves to
   * the `--radius` design token (7 px in light theme).
   *
   * This is the primary binding test for Task 002: every control uses
   * `border-radius: var(--radius)` — a deviation from that token (or a missing
   * token import) would cause the assertion to fail.
   *
   * The expected value is read dynamically from `document.documentElement` so
   * the test stays correct if the token value ever changes.
   */
  test('border-radius on all primary controls exactly equals --radius (7px)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Read the resolved token value at runtime — avoids hardcoding "7px"
    const expectedRadius = await page.evaluate(() =>
      window.getComputedStyle(document.documentElement).getPropertyValue('--radius').trim()
    )

    const selectors = [
      { selector: '.request-bar__url', label: 'URL input' },
      { selector: '.request-bar__method', label: 'method-select' },
      { selector: '.request-bar__send', label: 'Send' },
      { selector: '.request-bar__save', label: 'Save' },
      { selector: '.request-bar__share', label: 'Share' }
    ]

    for (const { selector, label } of selectors) {
      const borderRadius = await page
        .locator(selector)
        .evaluate((el) => window.getComputedStyle(el).borderTopLeftRadius)
      expect(borderRadius, `${label} border-top-left-radius`).toBe(expectedRadius)
    }
  })

  /**
   * Asserts the URL input focus ring: `:focus` must resolve
   *   - `border-color` = `--accent` (#10b981 = rgb(16, 185, 129))
   *   - `box-shadow`   = non-empty ring (0 0 0 3px var(--accent-soft))
   *
   * jsdom cannot apply `:focus` pseudo-class computed styles; Chromium is required.
   */
  test('URL input focus: border-color resolves to --accent and box-shadow ring is non-empty', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Disable CSS transitions before focusing so getComputedStyle reads the
    // FINAL focused value rather than the mid-transition value.
    //
    // Root cause: RequestBar.css has `transition: border-color 80ms ease` on
    // `.request-bar__url`. When el.focus() is called and getComputedStyle() is
    // read synchronously in the same evaluate callback, the transition has only
    // just started (t ≈ 0). The computed border-color at t=0 is the UNFOCUSED
    // starting value (--border, rgb(232,230,227)), not the target --accent value.
    //
    // Fix: emulate `prefers-reduced-motion: reduce`. RequestBar.css already
    // has a `@media (prefers-reduced-motion: reduce)` block that sets
    // `.request-bar__url { transition: none }`. With transitions disabled, the
    // focused style resolves instantly — no CDP timing race.
    await page.emulateMedia({ reducedMotion: 'reduce' })

    const [borderColor, boxShadow] = await page.evaluate(() => {
      const el = document.querySelector('.request-bar__url') as HTMLInputElement
      el.focus()
      const s = window.getComputedStyle(el)
      return [s.borderColor, s.boxShadow]
    })

    // --accent = #10b981 = rgb(16, 185, 129)
    expect(borderColor).toBe('rgb(16, 185, 129)')

    // Exact ring assertion: resolve --accent-soft's serialized rgba via a probe
    // element (color-mix with transparent cannot be computed analytically), then
    // reconstruct the Chromium-serialized box-shadow string.
    // Chromium format: "<color> <x>px <y>px <blur>px <spread>px"
    const accentSoftRgb = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.backgroundColor = 'var(--accent-soft)'
      document.body.appendChild(probe)
      const rgb = window.getComputedStyle(probe).backgroundColor
      probe.remove()
      return rgb
    })
    expect(boxShadow).toBe(`${accentSoftRgb} 0px 0px 0px 3px`)
  })

  /**
   * Asserts the method-select button's computed style:
   *   - `backgroundColor` = `--bg-elev` (rgb(255, 255, 255)) — elevated ghost surface
   *   - border is present (borderTopStyle = 'solid') — ghost-bordered treatment
   *   - `color` = `--m-get` (rgb(14, 165, 233)) for GET under data-mstyle='soft'
   *
   * The color assertion is the critical proof for Task 002: the
   * `.request-bar .request-bar__method.method` rule at specificity (0,3,0)
   * sets `background` and `border` but deliberately omits `color`, allowing the
   * per-method chip colour from `[data-mstyle='soft'] .method.GET { color: var(--m-get) }`
   * to fall through unchallenged.  A color of `rgb(0, 0, 0)` (browser default)
   * here means the fall-through is broken.
   */
  test('method-select: background is --bg-elev, border is solid, GET color resolves to --m-get via soft cascade', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const methodBtn = page.locator('.request-bar__method')

    const [backgroundColor, borderTopStyle, color, fontWeight, fontSize] = await methodBtn.evaluate(
      (el) => {
        const s = window.getComputedStyle(el)
        return [s.backgroundColor, s.borderTopStyle, s.color, s.fontWeight, s.fontSize]
      }
    )

    // --bg-elev = #ffffff = rgb(255, 255, 255)
    expect(backgroundColor).toBe('rgb(255, 255, 255)')
    // Ghost-bordered: border must be solid
    expect(borderTopStyle).toBe('solid')
    // GET soft color: --m-get = #0ea5e9 = rgb(14, 165, 233)
    // Proves no-colour fall-through: if RequestBar.css had set `color` this would be wrong
    expect(color).toBe('rgb(14, 165, 233)')
    // AC-6 bold coloured method text (RequestBar.css lines 96-98)
    expect(fontWeight).toBe('700')
    expect(fontSize).toBe('11.5px')
  })

  /**
   * Structural proof that the cascade fall-through applies to EVERY method, not
   * only GET.  A single GET assertion would pass even if RequestBar.css happened
   * to hard-code GET's colour.  Adding POST proves the `.request-bar__method.method`
   * override deliberately omits `color` and the `[data-mstyle='soft'] .method.{M}`
   * rule supplies the per-method colour for any method value.
   *
   * Reuses `RequestBarTwoTabFixture` (Tab B is POST `CT_TAB_B_URL`); switches the
   * active tab to Tab B so the method button re-renders with class `POST`.
   */
  test('method-select: POST color resolves to --m-post, proving fall-through for all methods (AC-6)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBarTwoTabFixture />)

    // Wait for the fixture's useEffect to seed the store (Tab A = GET is active)
    await expect(page.getByRole('textbox', { name: 'Request URL' })).toHaveValue(CT_TAB_A_URL)

    // Switch to Tab B (POST method)
    await page.getByTestId('ct-rb-select-tab-b').click()
    await expect(page.getByRole('button', { name: 'POST' })).toBeVisible()

    const color = await page.locator('.request-bar__method').evaluate((el) => {
      return window.getComputedStyle(el).color
    })

    // --m-post = #22c55e = rgb(34, 197, 94)
    // If RequestBar.css had set `color` on .request-bar__method.method, the
    // per-method token would not fall through and this assertion would fail.
    expect(color).toBe('rgb(34, 197, 94)')
  })

  /**
   * Asserts the Send button's enabled-state typography and inset shadow.
   *
   * The ENABLED state must be tested (URL filled) because the disabled CSS rule
   * `.request-bar__send:disabled { box-shadow: none }` would suppress the shadow
   * when the URL is empty (the beforeEach-seeded state).
   */
  test('Send button when enabled: font-weight is 600 and box-shadow is non-empty', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Fill a URL so Send is enabled — validates the enabled-state CSS
    const urlInput = page.getByRole('textbox', { name: 'Request URL' })
    await urlInput.fill('https://ct-fidelity.example.com')

    const sendBtn = page.locator('.request-bar__send')
    await expect(sendBtn).toBeEnabled()

    const [fontWeight, boxShadow] = await sendBtn.evaluate((el) => {
      const s = window.getComputedStyle(el)
      return [s.fontWeight, s.boxShadow]
    })

    // font-weight: 600 (Task 002 Send weight assertion)
    expect(fontWeight).toBe('600')

    // Exact two-layer Send shadow assertion.
    // Expected CSS: `0 1px 0 rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.15)`
    // Use a probe element to get Chromium's exact serialized form without guessing
    // whether spread-radius (0) is elided or included (cross-version safe).
    const expectedSendShadow = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.boxShadow = '0 1px 0 rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.15)'
      document.body.appendChild(probe)
      const shadow = window.getComputedStyle(probe).boxShadow
      probe.remove()
      return shadow
    })
    expect(boxShadow).toBe(expectedSendShadow)
  })

  /**
   * Asserts the canSend-gated keycap (Task 001 markup):
   *   - `.request-bar__kbd` is NOT in the DOM when URL is empty (canSend false)
   *   - `.request-bar__kbd` IS in the DOM after typing a URL (canSend true)
   *
   * The keycap is `aria-hidden` — it is purely decorative and must not appear
   * when it would be meaningless (disabled Send state).
   */
  test('request-bar__kbd is absent with empty URL and present after typing a URL', async ({
    mount,
    page
  }) => {
    // beforeEach seeds empty URL → canSend false → kbd must NOT be in the DOM
    await mount(<RequestBar />)
    await expect(page.locator('.request-bar__kbd')).not.toBeAttached()

    // Fill URL → updateActiveSpec → canSend true → kbd mounts
    await page.getByRole('textbox', { name: 'Request URL' }).fill('https://ct-kbd.example.com')
    await expect(page.locator('.request-bar__kbd')).toBeAttached()
  })

  /**
   * Asserts the computed styles of the `.request-bar__kbd` keycap when it is
   * present (canSend true). The keycap has six declared CSS properties:
   * font-size 11px, color --text-faint, background --bg-elev, border 1px solid
   * --border, border-radius 3px, padding 1px 5px.
   *
   * The `borderTopLeftRadius === '3px'` assertion proves the keycap uses the
   * LITERAL 3px — NOT the component-level `--radius` token (7px). A regression
   * on any of these properties would be invisible to the DOM-presence test above
   * but caught here.
   */
  test('keycap (.request-bar__kbd) computed styles: 11px font-size, solid border, 3px radius, bg-elev background', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Fill URL so canSend becomes true and the keycap mounts
    await page
      .getByRole('textbox', { name: 'Request URL' })
      .fill('https://ct-kbd-style.example.com')

    // Wait for the keycap to be present before reading its styles
    await expect(page.locator('.request-bar__kbd')).toBeAttached()

    const [fontSize, borderTopStyle, borderTopLeftRadius, paddingTop, paddingLeft, letterSpacing] =
      await page.locator('.request-bar__kbd').evaluate((el) => {
        const s = window.getComputedStyle(el)
        return [
          s.fontSize,
          s.borderTopStyle,
          s.borderTopLeftRadius,
          s.paddingTop,
          s.paddingLeft,
          s.letterSpacing
        ]
      })

    // font-size: 11px — declared literally (NOT var(--fs-base) or --fs-sm)
    expect(fontSize).toBe('11px')
    // border: 1px solid var(--border) → borderTopStyle must be solid
    expect(borderTopStyle).toBe('solid')
    // border-radius: 3px — the literal keycap radius, NOT the --radius token (7px)
    expect(borderTopLeftRadius).toBe('3px')
    // padding: 1px 5px — declared in RequestBar.css lines 278
    expect(paddingTop).toBe('1px')
    expect(paddingLeft).toBe('5px')

    // letter-spacing: 0.02em (F-004 fidelity fix — reference .kbd declares 0.02em).
    // At font-size 11px this resolves to ~0.22px.  Use a probe element (same technique
    // as the bg-elev and focus-ring assertions) to get Chromium's exact serialized px
    // form without hardcoding a potentially rounding-fragile literal.
    const expectedLetterSpacing = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.fontSize = '11px'
      probe.style.letterSpacing = '0.02em'
      document.body.appendChild(probe)
      const ls = window.getComputedStyle(probe).letterSpacing
      probe.remove()
      return ls
    })
    // Primary assertion: computed value matches the 0.02em probe resolution
    expect(letterSpacing, 'keycap letter-spacing must equal resolved 0.02em').toBe(
      expectedLetterSpacing
    )
    // Secondary: ensure the value is not 'normal' (which means no letter-spacing at all)
    expect(letterSpacing, 'keycap letter-spacing must not be normal').not.toBe('normal')

    // backgroundColor must resolve to var(--bg-elev). Use a probe element to get
    // Chromium's serialized rgb() form without hardcoding the hex value —
    // the same technique used for the focus-ring and Send-shadow assertions above.
    const bgElvRgb = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.backgroundColor = 'var(--bg-elev)'
      document.body.appendChild(probe)
      const rgb = window.getComputedStyle(probe).backgroundColor
      probe.remove()
      return rgb
    })

    const backgroundColor = await page
      .locator('.request-bar__kbd')
      .evaluate((el) => window.getComputedStyle(el).backgroundColor)

    expect(backgroundColor).toBe(bgElvRgb)

    // color must resolve to var(--text-faint). Probe-element technique —
    // same pattern used for bg-elev above and focus-ring assertions.
    const textFaintRgb = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.color = 'var(--text-faint)'
      document.body.appendChild(probe)
      const rgb = window.getComputedStyle(probe).color
      probe.remove()
      return rgb
    })

    const keycapColor = await page
      .locator('.request-bar__kbd')
      .evaluate((el) => window.getComputedStyle(el).color)

    expect(keycapColor).toBe(textFaintRgb)
  })

  /**
   * Asserts that Save and Share are visible bordered ghost actions with
   * visible text labels (Task 001: no aria-label — the visible text is the
   * accessible name).
   */
  test('Save and Share are visible bordered actions with text labels', async ({ mount, page }) => {
    await mount(<RequestBar />)

    const saveBtn = page.getByRole('button', { name: 'Save' })
    const shareBtn = page.getByRole('button', { name: 'Share' })

    // Both must be visible in the actions row
    await expect(saveBtn).toBeVisible()
    await expect(shareBtn).toBeVisible()

    // Both carry a solid border (ghost-bordered treatment from Task 002)
    const saveBorderStyle = await saveBtn.evaluate(
      (el) => window.getComputedStyle(el).borderTopStyle
    )
    const shareBorderStyle = await shareBtn.evaluate(
      (el) => window.getComputedStyle(el).borderTopStyle
    )
    expect(saveBorderStyle).toBe('solid')
    expect(shareBorderStyle).toBe('solid')

    // Both carry font-weight: 500 (F-002 fidelity fix — reference .btn base sets 500;
    // the shared base rule in RequestBar.css propagates it to Save and Share).
    // Send has its own `font-weight: 600` declared later, which overrides the base.
    const [saveFontWeight, shareFontWeight] = await page.evaluate(() => {
      const saveEl = document.querySelector('.request-bar__save') as HTMLElement
      const shareEl = document.querySelector('.request-bar__share') as HTMLElement
      return [
        window.getComputedStyle(saveEl).fontWeight,
        window.getComputedStyle(shareEl).fontWeight
      ]
    })
    expect(saveFontWeight, 'Save fontWeight').toBe('500')
    expect(shareFontWeight, 'Share fontWeight').toBe('500')

    // Visible text labels — the accessible name must come from rendered text
    await expect(saveBtn).toContainText('Save')
    await expect(shareBtn).toContainText('Share')

    // AC-19 / AC-11: Share is the 009 no-op stub and must remain disabled
    // (the `disabled` attribute is present in the JSX; browser enforces pointer events)
    await expect(shareBtn).toBeDisabled()
  })

  /**
   * AC-13 — URL input font-family resolves to the --font-mono token.
   *
   * Uses the probe-element technique: inject a div with `font-family: var(--font-mono)`,
   * read its resolved fontFamily, then assert the URL input matches it exactly.
   * This proves the URL field is monospace (JetBrains Mono / SF Mono / ui-monospace),
   * not the sans-serif stack used by action buttons.
   */
  test('URL input font-family resolves to --font-mono (monospace, not sans)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Probe --font-mono without hardcoding the resolved stack
    const fontMonoValue = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.fontFamily = 'var(--font-mono)'
      document.body.appendChild(probe)
      const fontFamily = window.getComputedStyle(probe).fontFamily
      probe.remove()
      return fontFamily
    })

    const urlFontFamily = await page
      .locator('.request-bar__url')
      .evaluate((el) => window.getComputedStyle(el).fontFamily)

    // Proves the URL field is monospace — not the --font-sans action-button stack
    expect(urlFontFamily).toBe(fontMonoValue)
  })

  /**
   * AC-13 — URL input horizontal padding is exactly 12px on both sides.
   *
   * RequestBar.css declares `padding: 0 12px` on `.request-bar__url`.
   * A padding change (e.g. back to the old 8px) would be invisible to the
   * layout and screenshot tests but caught here.
   */
  test('URL input horizontal padding is 12px left and 12px right (AC-13)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    const [paddingLeft, paddingRight] = await page.locator('.request-bar__url').evaluate((el) => {
      const s = window.getComputedStyle(el)
      return [s.paddingLeft, s.paddingRight]
    })

    expect(paddingLeft, 'URL input paddingLeft').toBe('12px')
    expect(paddingRight, 'URL input paddingRight').toBe('12px')
  })

  /**
   * AC-13 — Action buttons (Send and Save) have 14px horizontal padding each side.
   *
   * The shared `.request-bar__send, .request-bar__save, .request-bar__share` rule
   * declares `padding: 0 14px`. Asserting both Send and Save proves the base rule
   * is active on the group selector, not just one button's individual rule.
   */
  test('action buttons (Send, Save) have 14px horizontal padding on each side (AC-13)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Send button — accent-fill primary action
    const [sendPaddingLeft, sendPaddingRight] = await page
      .locator('.request-bar__send')
      .evaluate((el) => {
        const s = window.getComputedStyle(el)
        return [s.paddingLeft, s.paddingRight]
      })

    expect(sendPaddingLeft, 'Send paddingLeft').toBe('14px')
    expect(sendPaddingRight, 'Send paddingRight').toBe('14px')

    // Save button — ghost-bordered action; shares the base group rule
    const [savePaddingLeft, savePaddingRight] = await page
      .locator('.request-bar__save')
      .evaluate((el) => {
        const s = window.getComputedStyle(el)
        return [s.paddingLeft, s.paddingRight]
      })

    expect(savePaddingLeft, 'Save paddingLeft').toBe('14px')
    expect(savePaddingRight, 'Save paddingRight').toBe('14px')
  })

  /**
   * AC-13 — Bar border-bottom color resolves to the --border-faint token.
   *
   * RequestBar.css sets `border-bottom: 1px solid var(--border-faint)` on
   * `.request-bar`. This assertion proves the faint separator token is used,
   * NOT the stronger --border token. Uses the probe-element technique so the
   * expected rgb() form is derived at runtime without hardcoding the hex value.
   */
  test('.request-bar border-bottom color resolves to --border-faint token (AC-13)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Probe --border-faint to get Chromium's serialized rgb() form
    const borderFaintRgb = await page.evaluate(() => {
      const probe = document.createElement('div')
      probe.style.borderBottomColor = 'var(--border-faint)'
      document.body.appendChild(probe)
      const color = window.getComputedStyle(probe).borderBottomColor
      probe.remove()
      return color
    })

    const barBorderBottomColor = await page
      .locator('.request-bar')
      .evaluate((el) => window.getComputedStyle(el).borderBottomColor)

    // Proves the bar uses --border-faint, not --border (the stronger separator)
    expect(barBorderBottomColor).toBe(borderFaintRgb)
  })

  /**
   * Asserts that hovering the Save button applies the `.request-bar__save:hover`
   * rule that was changed by the /fix: `border-color: var(--border-strong)` instead
   * of the old `background: var(--bg-hover)`.
   *
   * Two assertions:
   *   1. `borderTopColor` exactly equals the resolved `--border-strong` token.
   *   2. `backgroundColor` stays at `--bg-elev` (the /fix removed --bg-hover fill).
   *
   * Uses probe-element technique for both expected values so the test stays correct
   * if token hex values ever change — same pattern as the focus-ring and keycap tests.
   *
   * `prefers-reduced-motion: reduce` is emulated before hover so any CSS transition
   * on `border-color` resolves instantly rather than being caught mid-interpolation.
   */
  test('Save button on hover: border-color resolves to --border-strong and background stays --bg-elev (no fill)', async ({
    mount,
    page
  }) => {
    await mount(<RequestBar />)

    // Disable transitions so the hovered computed value is the final resolved value,
    // not a mid-transition interpolation (same technique as the URL focus-ring test).
    await page.emulateMedia({ reducedMotion: 'reduce' })

    // Resolve expected values at runtime via probe elements — avoids hardcoding hex.
    const [borderStrongRgb, bgElvRgb] = await page.evaluate(() => {
      const probeB = document.createElement('div')
      probeB.style.borderTopColor = 'var(--border-strong)'
      document.body.appendChild(probeB)
      const border = window.getComputedStyle(probeB).borderTopColor
      probeB.remove()

      const probeBg = document.createElement('div')
      probeBg.style.backgroundColor = 'var(--bg-elev)'
      document.body.appendChild(probeBg)
      const bg = window.getComputedStyle(probeBg).backgroundColor
      probeBg.remove()

      return [border, bg]
    })

    // Move the pointer over the Save button so :hover applies.
    await page.locator('.request-bar__save').hover()

    const [borderTopColor, backgroundColor] = await page
      .locator('.request-bar__save')
      .evaluate((el) => {
        const s = window.getComputedStyle(el)
        return [s.borderTopColor, s.backgroundColor]
      })

    // The /fix changed :hover from `background: var(--bg-hover)` to
    // `border-color: var(--border-strong)` — this is the primary regression guard.
    expect(borderTopColor, 'Save :hover borderTopColor should equal --border-strong').toBe(
      borderStrongRgb
    )

    // Secondary: the hover rule must NOT set a background fill.
    // backgroundColor must remain the rest-state --bg-elev (not --bg-hover).
    expect(backgroundColor, 'Save :hover backgroundColor should remain --bg-elev (no fill)').toBe(
      bgElvRgb
    )
  })

  /**
   * Supplementary visual regression gate: screenshot of `.request-bar` in the
   * filled state (Send enabled, ⌘↵ keycap visible) against a stable
   * chromium-darwin baseline.
   *
   * PRIMARY fidelity proof is the computed-style assertions above.
   * The screenshot gates against visual regression across future CSS changes.
   *
   * FIRST-EVER BASELINE: Playwright generates `request-bar-fidelity.png` on the
   * first run with `--update-snapshots`.  After generation, manually inspect the
   * baseline under `__snapshots__/` to confirm the visual is correct (green Send
   * button, ⌘↵ keycap, ghost-bordered Save/Share, GET method in --m-get blue)
   * before treating this as a blocking gate.
   */
  test('request-bar visual regression screenshot (filled state)', async ({ mount, page }) => {
    await mount(<RequestBarFilledFixture />)

    // Wait for the store to be seeded and the URL to appear in the input.
    // The useEffect in RequestBarFilledFixture fires after the first render;
    // this auto-wait gate ensures the Send button is enabled before the screenshot.
    await expect(page.getByRole('textbox', { name: 'Request URL' })).toHaveValue(CT_FILLED_URL)

    await expect(page.locator('.request-bar')).toHaveScreenshot('request-bar-fidelity.png', {
      maxDiffPixelRatio: 0.01,
      threshold: 0.1,
      animations: 'disabled'
    })
  })
})

// ---------------------------------------------------------------------------
// 7. Chip-mode fidelity — per-method colored background restored in chip mode
// ---------------------------------------------------------------------------

/**
 * Chip-mode regression guards for the RequestBar method selector.
 *
 * Root cause of the regression:
 *   The (0,3,0) ancestor-scoped rule in RequestBar.css sets
 *   `background: var(--bg-elev)` unconditionally, winning the source-order
 *   tie-break over the tokens.css chip-mode rule
 *   `[data-mstyle='chip'] .method.GET` (also 0,3,0).  Result: white background
 *   with white chip text — unreadable.
 *
 * Fix (RequestBar.css):
 *   Seven (0,5,0) counter-rules — one per method, locked to METHODS in
 *   httpMethods.ts — each matching
 *   `[data-mstyle='chip'] .request-bar .request-bar__method.method.{METHOD}`
 *   restore the per-method background and clear the border.  The white text
 *   (`color: #fff`) falls through from the (0,2,0) chip-mode base rule in
 *   tokens.css and is not re-declared in the counter-rules.
 *
 * Tests in this block:
 *   1. All 7 METHODS: backgroundColor === resolved var(--m-{method}) via
 *      RequestBarMethodSwitchFixture + per-method testid button, covering the
 *      full METHODS array so a future METHODS addition immediately fails here
 *      if the matching CSS counter-rule is missing.
 *   2. GET text color === rgb(255, 255, 255) — contrast guard (white-on-white proof).
 *
 * Setup:
 *   The global beforeEach (outer scope) resets the store and sets data-mstyle='soft'.
 *   This block's own beforeEach then overrides data-mstyle to 'chip'.  Playwright CT
 *   gives a fresh page per test so no cross-block leakage occurs, but the explicit
 *   inner beforeEach makes the chip context unambiguous for every test in this block.
 */
test.describe('RequestBar — chip mode fidelity', () => {
  /**
   * Override data-mstyle to 'chip' for every test in this block.
   *
   * The outer beforeEach (line ~71) already ran: store was reset and
   * data-mstyle was set to 'soft'.  This inner hook runs second (Playwright
   * executes beforeEach hooks from outermost to innermost scope) and overwrites
   * the attribute to 'chip' so the chip-mode CSS counter-rules take effect.
   */
  test.beforeEach(async ({ page }) => {
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-mstyle', 'chip')
    })
  })


  /**
   * All-methods regression guard: every HTTP method in METHODS must render its
   * per-method colored background in chip mode, NOT the elevated white surface
   * (--bg-elev).
   *
   * Uses RequestBarMethodSwitchFixture which exposes one testid button per
   * method (ct-rb-set-method-{METHOD}), each wired to updateActiveSpec({ method })
   * from the React context — avoiding the Radix dropdown click-outside arm-race
   * (memory: ct-radix-dismiss-arm-race).
   *
   * Looping over METHODS (the httpMethods.ts SSOT) means a future METHODS addition
   * automatically creates a new assertion here; if the matching CSS counter-rule in
   * RequestBar.css is missing, this test fails immediately on that method.
   *
   * Probe-element technique: creates a div with `backgroundColor: var(--m-{method})`,
   * reads the computed rgb(), then removes the div — avoids hardcoding hex values.
   */
  test('all methods in chip mode: backgroundColor resolves to per-method token', async ({
    mount,
    page
  }) => {
    await mount(<RequestBarMethodSwitchFixture />)

    for (const method of METHODS) {
      // Switch the active tab to this method via the fixture button
      await page.getByTestId(`ct-rb-set-method-${method}`).click()
      // Wait for the RequestBar method button to update its label before reading its background.
      // Use .request-bar__method directly (not getByRole) to avoid a strict-mode conflict:
      // both the RequestBar method trigger and the fixture switch button share the same label text.
      await expect(page.locator('.request-bar__method')).toContainText(method)

      const tokenName = `--m-${method.toLowerCase()}`

      // Probe the CSS custom property to get Chromium's serialized rgb() form
      const expectedRgb = await page.evaluate((token: string) => {
        const probe = document.createElement('div')
        probe.style.backgroundColor = `var(${token})`
        document.body.appendChild(probe)
        const rgb = window.getComputedStyle(probe).backgroundColor
        probe.remove()
        return rgb
      }, tokenName)

      const [actualBg, color, borderTopStyle] = await page
        .locator('.request-bar__method')
        .evaluate((el) => {
          const s = window.getComputedStyle(el)
          return [s.backgroundColor, s.color, s.borderTopStyle]
        })

      // The chip counter-rule must win: per-method colored background, NOT --bg-elev
      expect(actualBg, `chip mode: ${method} background should be ${tokenName}`).toBe(expectedRgb)

      // text color must be white — [data-mstyle='chip'] .method sets color:#fff at (0,2,0);
      // chip counter-rules deliberately omit `color` so this falls through unchallenged.
      // Guards against a future per-method rule accidentally overriding the color.
      expect(color, `chip mode: ${method} text color must be white (rgb(255,255,255))`).toBe(
        'rgb(255, 255, 255)'
      )

      // border must be none — chip counter-rules each declare `border: none` to clear
      // the (0,3,0) ghost-border set by the RequestBar.css ancestor-scoped override.
      // Guards against a future counter-rule accidentally omitting `border: none`.
      expect(borderTopStyle, `chip mode: ${method} borderTopStyle must be none`).toBe('none')
    }
  })

})

// ---------------------------------------------------------------------------
// 8. Untested mstyle variant characterization — outline, dot, bar
// ---------------------------------------------------------------------------

/**
 * Minimal non-degeneracy guards for mstyle variants not covered by the fidelity
 * or chip-mode suites (outline, dot, bar, text).
 *
 * The (0,3,0) ancestor-scoped override in RequestBar.css unconditionally sets
 * `background: var(--bg-elev)` and `border: 1px solid var(--border)` on the
 * method button for ALL mstyle variants.  Chip mode has (0,5,0) counter-rules
 * that restore per-method colors; outline/dot/bar/text have NO counter-rules.
 *
 * These tests assert that, for each variant, the method button:
 *   1. Is visible (not collapsed or hidden).
 *   2. Has a non-transparent background — the override sets var(--bg-elev) which
 *      is opaque, so the button has a visible surface.
 *   3. Has readable text color — the per-method color from the variant's rule
 *      (`[data-mstyle=X] .method.GET { color: var(--m-get) }`) falls through
 *      because the override does NOT declare `color`.  NOT white: the only
 *      degenerate case is white-on-white (which chip mode had before the fix).
 *
 * This is a characterization test, NOT a full fidelity suite.  It does not
 * assert exact token values — only that the button is visible and readable.
 *
 * Setup: the outer beforeEach resets the store (GET method, empty URL) and sets
 * data-mstyle='soft'.  Each test overrides the attribute inline via page.evaluate
 * before mounting, so the component renders under the target variant's CSS rules
 * from the first frame.
 */
test.describe('RequestBar — untested mstyle variants (characterization)', () => {
  for (const variant of ['outline', 'dot', 'bar', 'text'] as const) {
    test(`method button is visible and readable in ${variant} mode`, async ({ mount, page }) => {
      // Override data-mstyle before mounting so the component renders under the
      // target variant's CSS rules from the first frame.
      await page.evaluate((v: string) => {
        document.documentElement.setAttribute('data-mstyle', v)
      }, variant)

      await mount(<RequestBar />)

      const methodBtn = page.locator('.request-bar__method')

      // 1. Element must be visible (not collapsed or display:none)
      await expect(methodBtn).toBeVisible()

      const [color, backgroundColor] = await methodBtn.evaluate((el) => {
        const s = window.getComputedStyle(el)
        return [s.color, s.backgroundColor]
      })

      // 2. Text must not be white — per-method color (e.g. --m-get) falls through
      //    from `[data-mstyle=X] .method.GET` because the override omits `color`.
      //    A white text color would indicate a regression (white-on-white failure).
      expect(color, `${variant}: text color must not be white`).not.toBe('rgb(255, 255, 255)')

      // 3. Background must not be transparent — the (0,3,0) override sets var(--bg-elev)
      //    (opaque white) for these variants, ensuring a visible surface.
      //    'rgba(0, 0, 0, 0)' is Chromium's serialized form of `transparent`.
      expect(backgroundColor, `${variant}: background must not be transparent`).not.toBe(
        'rgba(0, 0, 0, 0)'
      )
    })
  }
})
