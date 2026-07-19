/**
 * BodyEditor.ct.tsx — Playwright component tests for BodyEditor (organism level).
 *
 * Molecule-level fidelity tests (per-theme hex colors, token bindings, grid
 * geometry, row heights) were re-homed to CodeEditor.ct.tsx (AC-12/13/16/17/21).
 *
 * Behavior: radiogroup + roving focus (AC-18), default/mode switch (AC-6/7),
 * lang-pill cycle (AC-8), two-pass highlight (AC-9/10), empty/malformed
 * degrade (AC-16/17), cross-mode retention (AC-14), scroll sync, BLANK_BODY,
 * org-boundary wiring (resetKey passthrough), per-request-tab isolation.
 *
 * Highlight coloring is debounced (~100ms), so token spans (`.tk-*`) appear
 * shortly after mount — highlight assertions first wait for the relevant span
 * to attach (Playwright auto-polling) before asserting.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  BodyEditorRawJsonLightFixture,
  BodyEditorNoneFixture,
  BodyEditorRawXmlFixture,
  BodyEditorUrlencodedFixture,
  BodyEditorEmptyRawFixture,
  BodyEditorMalformedJsonFixture,
  BodyEditorBlankBodyFixture,
  BodyEditorScrollFixture,
  BodyEditorUrlencodedLiveFixture,
  BodyEditorTwoTabsFixture,
  BodyEditorNoneDirtyProbeFixture,
  BodyEditorUrlencodedNegativeInvariantFixture,
  BodyEditorScrollHFixture,
  BodyEditorTwoTabsRawSameBodyFixture,
  BodyEditorTwoTabsScrollResetFixture,
  BodyEditorTwoTabsMixedFixture,
  JSON_ALL_TOKENS
} from './BodyEditor.stories'

// Structural token classes the JSON pass can emit.
const STRUCTURAL = '.tk-key, .tk-str, .tk-num, .tk-bool, .tk-punc, .tk-var'

// ===========================================================================
// Behavior — gutter/CodeEditor integration (AC-23 line count)
// ===========================================================================

test('AC-23 — gutter line count equals the rendered line count', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  // The seeded JSON body has JSON_ALL_TOKENS.split('\n').length lines; the gutter
  // renders one <div> per line. Derived from the imported constant so a change to
  // JSON_ALL_TOKENS fails here with a meaningful count mismatch, not a silent 6.
  await expect(page.getByTestId('body-gutter').locator('> div')).toHaveCount(
    JSON_ALL_TOKENS.split('\n').length
  )
})

// ===========================================================================
// Behavior — radiogroup default + options (AC-7) + roving focus (AC-18)
// ===========================================================================

test('AC-7 — six body-type options, default none', async ({ mount, page }) => {
  const c = await mount(<BodyEditorNoneFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const radios = page.getByTestId('body-radio')
  await expect(radios).toHaveCount(6)
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'true') // none is first + default
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'false')

  // Selecting a different option flips aria-checked on both (ARIA radio contract).
  await radios.nth(1).click()
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true')
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'false')
})

test('AC-18 — arrow keys move + select; ArrowLeft wraps first→last', async ({ mount, page }) => {
  const c = await mount(<BodyEditorNoneFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const radios = page.getByTestId('body-radio')

  await radios.nth(0).focus()
  await radios.nth(0).press('ArrowRight')
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true') // advanced + selected

  // From the first option, ArrowLeft wraps to the last (index 5).
  await radios.nth(0).focus()
  await radios.nth(0).press('ArrowLeft')
  await expect(radios.nth(5)).toHaveAttribute('aria-checked', 'true')
})

test('AC-18 — Space and Enter select the focused option', async ({ mount, page }) => {
  const c = await mount(<BodyEditorNoneFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const radios = page.getByTestId('body-radio')

  await radios.nth(2).focus()
  await radios.nth(2).press(' ')
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')

  await radios.nth(3).focus()
  await radios.nth(3).press('Enter')
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true')
})

// WCAG 1.3.1 a11y-tree regression guard. The radiogroup wrapper must be a REAL
// layout box (display:flex) so Chrome keeps role="radiogroup" in the accessibility
// tree. A prior fix regressed this to `display:contents`, which drops the element
// from the AX tree and un-groups the radios. getByRole/aria-* assertions read the
// DOM attribute, not the computed AX tree, so they would NOT catch a revert — this
// test pins the computed `display` explicitly.
test('a11y — radiogroup wrapper is display:flex (not contents) so it stays in the a11y tree', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorNoneFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const rg = page.locator('[role="radiogroup"][aria-label="Request body type"]')
  await expect(rg).toBeAttached()
  const display = await rg.evaluate((el) => window.getComputedStyle(el).display)
  expect(display).toBe('flex')
  expect(display).not.toBe('contents')
  // the 6 radios must be direct children of the radiogroup (grouped for AT).
  await expect(rg.locator('[role="radio"]')).toHaveCount(6)
})

// ===========================================================================
// Behavior — mode switch mount-all (AC-6)
// ===========================================================================

test('AC-6 — the raw code-editor stays mounted even when none is active', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorNoneFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  // active is 'none': the raw panel's .code-editor is still mounted in the DOM
  // (mount-all) but NOT visible (its panel carries the `hidden` attribute).
  await expect(page.getByTestId('body-code-editor')).toBeAttached()
  await expect(page.getByTestId('body-code-editor')).not.toBeVisible()
})

// ===========================================================================
// Behavior — lang-pill cycle (AC-8)
// ===========================================================================

test('AC-8 — lang-pill defaults JSON and cycles json→xml→html→text→json', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const pill = page.getByTestId('body-lang-pill')

  await expect(pill).toHaveText('JSON')
  await pill.click()
  await expect(pill).toHaveText('XML')
  await pill.click()
  await expect(pill).toHaveText('HTML')
  await pill.click()
  await expect(pill).toHaveText('TEXT')
  await pill.click()
  await expect(pill).toHaveText('JSON') // wraps back
})

// The lang-pill carries `hidden` when the active body type is not 'raw'. A prior
// fix (`.lang-pill[hidden]{display:none}`) restores that suppression after
// `.lang-pill{display:flex}` had defeated the UA `[hidden]` rule. Without the fix
// the pill leaks (visible + AT-exposed) into every non-raw mode — a purely-visual
// regression the click-sequence tests above cannot catch.
test('lang-pill is hidden in non-raw modes (none) and visible in raw', async ({ mount, page }) => {
  const c = await mount(<BodyEditorNoneFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  // active='none' → pill carries `hidden`; the scoped rule must keep it display:none
  await expect(page.getByTestId('body-lang-pill')).not.toBeVisible()
})

test('lang-pill is visible in raw mode', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.getByTestId('body-lang-pill')).toBeVisible()
})

// ===========================================================================
// Behavior — two-pass highlight (AC-9 var-pass-wins JSON / AC-10 var-only non-JSON)
// ===========================================================================

test('AC-9 — JSON var-pass-wins: {{x}} is a tk-var beside tk-str content', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const varSpan = page.locator('.tk-var').first()
  await expect(varSpan).toBeAttached()
  await expect(varSpan).toHaveText('{{x}}')
  await expect(page.locator('.tk-str').first()).toBeAttached()
})

test('AC-10 — non-JSON (xml) highlights only {{var}}, no structural tokens', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawXmlFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.locator('.tk-var').first()).toBeAttached() // var pass runs
  await expect(
    page.getByTestId('body-pre').locator('.tk-key, .tk-str, .tk-num, .tk-bool')
  ).toHaveCount(0)
})

// ===========================================================================
// Behavior — F3 regression guard: pre plain-text render before debounce
// ===========================================================================

/**
 * F3 regression guard — typed characters are NEVER invisible during the 100 ms
 * compose() debounce window.
 *
 * The BodyEditor pre renders two exclusive paths:
 *   showColored=true  → colored token spans (compose() snapshot)
 *   showColored=false → <span>{body.raw.text}</span>  (plain-degrade)
 *
 * On first paint, `colored` state is null so `showColored` is always false.
 * The plain-degrade span must be in the DOM immediately, making every typed
 * character visible (via the transparent textarea caret) before the highlight
 * pass fires. If this path were removed or made conditional, characters would
 * appear invisible for 100 ms on every keystroke — the F3 regression.
 *
 * Every other highlight CT waits for `.tk-key` to attach (i.e. waits for the
 * debounce). This test intentionally does NOT wait for `.tk-key` — it asserts
 * the raw text is present BEFORE any token span appears.
 */
test('F3 regression guard — pre shows live raw text as plain span before debounce fires', async ({
  mount,
  page
}) => {
  // Install fake clock BEFORE mount so the 100ms debounce setTimeout is held at t=0.
  // This eliminates the point-in-time count() race: under a frozen virtual clock the
  // debounce timer cannot fire between mount and the pre-debounce assertion.
  // Mirrors CodeEditor.ct.tsx's AC-23 deterministic pattern exactly.
  await page.clock.install()

  // Use the existing raw-JSON fixture: JSON_ALL_TOKENS is the seeded body text.
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')

  // At virtual t=0 the debounce timer is frozen. Assert the plain-degrade path:
  // raw text is present and NO .tk-key span exists.
  await expect(pre).toContainText(JSON_ALL_TOKENS.slice(0, 14)) // '{\n  "key": 1,' substring

  // Retrying form (toHaveCount) instead of point-in-time count() — under the fake
  // clock this is provably 0 (the debounce timer cannot have fired yet).
  await expect(page.locator('[data-testid="body-pre"] .tk-key')).toHaveCount(0)

  // Advance virtual time past the 100ms debounce to confirm the highlight fires.
  await page.clock.fastForward(150)

  // After the debounce fires, .tk-key must attach. Playwright auto-retries.
  await expect(page.locator('.tk-key').first()).toBeAttached()
})

// ===========================================================================
// Behavior — degrade paths (AC-16 empty / AC-17 malformed)
// ===========================================================================

test('AC-16 — empty raw text renders zero highlight tokens, no error', async ({ mount, page }) => {
  const c = await mount(<BodyEditorEmptyRawFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.getByTestId('body-pre').locator(STRUCTURAL)).toHaveCount(0)
})

test('AC-17 — malformed JSON degrades to plain text, no error UI', async ({ mount, page }) => {
  const c = await mount(<BodyEditorMalformedJsonFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.getByTestId('body-pre').locator(STRUCTURAL)).toHaveCount(0)
  await expect(page.getByTestId('body-pre')).toContainText('{ bad json')
  // No error UI: malformed JSON degrades silently — no alert/error banner rendered.
  await expect(page.getByRole('alert')).toHaveCount(0)
})

// ===========================================================================
// Behavior — cross-mode retention (AC-14)
// ===========================================================================

test('AC-14 — raw text survives a switch away and back', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const textarea = page.getByLabel('Request body', { exact: true })
  await expect(textarea).toHaveValue(/"msg": "a \{\{x\}\} b"/)

  const radios = page.getByTestId('body-radio')
  await radios.nth(2).click() // urlencoded (index 2)
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')
  await radios.nth(3).click() // back to raw (index 3)
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true')

  await expect(textarea).toHaveValue(/"msg": "a \{\{x\}\} b"/) // retained from the store
})

// ===========================================================================
// Behavior — per-request-tab body isolation (Finding 2)
// ===========================================================================

/**
 * Finding 2 — Two distinct request tabs carry independent body states.
 *
 * BodyEditor reads `spec.body` for the ACTIVE tab only. Switching the active
 * request tab must cause BodyEditor to reflect the incoming tab's own body
 * state (active mode + raw text / urlencoded rows) — not the outgoing tab's.
 *
 * Fixture seeds:
 *   Tab A — active='raw',        raw.text='tab-a-text'
 *   Tab B — active='urlencoded', urlencoded.rows=[{ key:'b-key' }]
 */
test('body-isolation — each request tab shows its own body type independently (Finding 2)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsFixture />)
  await expect(c.getByTestId('ct-be-two-tabs-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')
  const textarea = page.getByLabel('Request body', { exact: true })

  // Tab A is initially active: raw mode (radio index 3) is checked.
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true') // raw (index 3)
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'false') // none
  await expect(textarea).toHaveValue('tab-a-text')

  // Switch to Tab B: BodyEditor must now show Tab B's urlencoded mode.
  await page.getByTestId('ct-be-select-tab-b').click()
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true') // urlencoded
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'false') // raw not active (index 3)

  // Tab B's urlencoded row data must be visible in the live KVTable (row-data isolation).
  // The fixture seeded b-key for Tab B; if isolation breaks, Tab A's empty rows would show.
  const bKeyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(bKeyInput).toBeAttached()
  await expect(bKeyInput).toHaveValue('b-key')

  // Switch back to Tab A: BodyEditor must restore Tab A's raw mode and text.
  await page.getByTestId('ct-be-select-tab-a').click()
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true') // raw again (index 3)
  await expect(textarea).toHaveValue('tab-a-text') // raw text unchanged

  // Tab A has no urlencoded rows and is in raw mode — Tab B's b-key row must be gone.
  // Tab A's body.urlencoded.rows is [] so the KVTable renders zero non-empty rows.
  await expect(page.locator('.kv-row:not(.empty) .kv-cell.key input')).toHaveCount(0)
})

// ===========================================================================
// Behavior — AC-14 mirror: urlencoded rows survive a body-type switch (Finding 3)
// ===========================================================================

/**
 * Finding 3 — Mirror of the existing AC-14 (raw text retention) for the
 * urlencoded direction: seeded urlencoded rows must be present after switching
 * away to raw mode and switching back to urlencoded.
 *
 * BodyEditor's mount-all / hidden-toggle architecture keeps all panels always
 * mounted; the tagged-record SSOT (`body.urlencoded.rows` in the store) ensures
 * rows survive any mode switch without needing the panel to remain visible.
 */
test('AC-14 mirror — urlencoded rows survive a switch to raw and back (Finding 3)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorUrlencodedLiveFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')
  // The live KVTable rendered via renderUrlencodedLive exposes its key cell input.
  const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()

  // Start in urlencoded mode: the row seeded by the fixture is visible.
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true') // urlencoded
  await expect(keyInput).toBeAttached()
  await expect(keyInput).toHaveValue('init-key')

  // Switch to raw.
  await radios.nth(3).click() // raw is index 3
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true') // raw now active (index 3)
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'false')

  // Switch back to urlencoded.
  await radios.nth(2).click()
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true') // urlencoded again

  // Rows must survive the round-trip: the store's `body.urlencoded.rows` is unchanged.
  await expect(keyInput).toHaveValue('init-key')
})

// ===========================================================================
// Behavior — already-active radio early-return guard (Finding 7)
// ===========================================================================

/**
 * Verifies that clicking the already-active body-type radio does NOT dirty the
 * tab. The early-return guard in `handleRadioSelect` (`if (next === body.active)
 * return`) must block the `updateActiveSpec` call so `dirty` stays false.
 *
 * DirtyProbe (BodyEditor.stories.tsx) reflects the store's dirty flag as a
 * `data-dirty` attribute so the CT can assert state without window hacks.
 */
test('early-return — clicking the already-active radio does not dirty the tab', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorNoneDirtyProbeFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')
  const dirtyProbe = page.getByTestId('ct-be-dirty-probe')

  // Sanity: 'none' (index 0) is the active radio; tab is clean.
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'true')
  await expect(dirtyProbe).toHaveAttribute('data-dirty', 'false')

  // Click the already-active 'none' radio — must trigger the early-return guard.
  await radios.nth(0).click()

  // body.active is still 'none' (aria-checked unchanged).
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'true')
  // dirty flag must remain false — updateActiveSpec was NOT called.
  await expect(dirtyProbe).toHaveAttribute('data-dirty', 'false')
})

// ===========================================================================
// Behavior — textarea → pre scroll sync
// ===========================================================================

test('scroll — the pre overlay tracks the textarea scrollTop', async ({ mount, page }) => {
  const c = await mount(<BodyEditorScrollFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const textarea = page.getByLabel('Request body', { exact: true })

  // Force the textarea into a bounded, internally-scrollable box so scrollTop
  // sticks (its natural height grows to content, which would otherwise clamp
  // scrollTop to 0). This isolates the onScroll → pre-sync handler under test.
  const taTop = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // the browser may clamp to the max scrollable offset
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return ta.scrollTop // the ACTUAL (possibly clamped) offset the handler saw
  })

  expect(taTop).toBeGreaterThan(0) // the textarea genuinely scrolled
  const preTop = await page.getByTestId('body-pre').evaluate((el) => el.scrollTop)
  expect(preTop).toBe(taTop) // the pre overlay mirrors the textarea exactly
})

/**
 * Horizontal scroll sync — handleTextareaScroll syncs BOTH scrollTop AND
 * scrollLeft to the pre overlay ref, but the existing scrollTop CT only covers
 * the vertical axis. This test drives scrollLeft via a single very long line
 * (BodyEditorScrollHFixture) and asserts pre.scrollLeft === textarea.scrollLeft.
 *
 * handleTextareaScroll:
 *   preRef.current.scrollTop  = e.currentTarget.scrollTop
 *   preRef.current.scrollLeft = e.currentTarget.scrollLeft   ← this axis
 */
test('scroll — the pre overlay tracks the textarea scrollLeft', async ({ mount, page }) => {
  const c = await mount(<BodyEditorScrollHFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  const textarea = page.getByLabel('Request body', { exact: true })

  // The fixture seeds a single ~1000-char line in a 300px container.
  // The textarea's `white-space: pre` / `overflow: auto` lets scrollLeft go
  // to ~700px+. Setting 100px is well within the scrollable range.
  const taLeft = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.scrollLeft = 100 // the browser may clamp to the max scrollable offset
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return ta.scrollLeft // the ACTUAL (possibly clamped) offset the handler saw
  })

  expect(taLeft).toBeGreaterThan(0) // textarea genuinely scrolled horizontally
  const preLeft = await page.getByTestId('body-pre').evaluate((el) => el.scrollLeft)
  expect(preLeft).toBe(taLeft) // the pre overlay mirrors textarea scrollLeft exactly
})

// ===========================================================================
// Behavior — BLANK_BODY fallback (carried from task 006 review)
// ===========================================================================

test('blank-body — mounts cleanly with none active when the store body is absent', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorBlankBodyFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.getByTestId('body-toolbar')).toBeAttached()
  await expect(page.getByTestId('body-radio').nth(0)).toHaveAttribute('aria-checked', 'true')
})

// ===========================================================================
// Behavior — urlencoded render-prop slot
// ===========================================================================

test('urlencoded — the render-prop slot mounts in the urlencoded panel', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorUrlencodedFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.getByTestId('ct-be-urlencoded-stub')).toBeAttached()
})

// ===========================================================================
// Behavior — urlencoded assembled path (AC-11 + AC-12)
// ===========================================================================

test('AC-11 + AC-12 — urlencoded real KVTable: key edit propagates through onRowsChange → store body.urlencoded.rows', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorUrlencodedLiveFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  // The fixture seeds active=urlencoded with one real row (key='init-key').
  // KVTable key cell uses a .kv-input-wrap overlay input (color: transparent)
  // on top of the .kv-highlight div; the overlay input carries the live value.
  const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(keyInput).toBeAttached()

  // Edit the key — fires onChange → KVTable calls onRowsChange(nextRows) →
  // BodyEditor's handleUrlencodedRowsChange → updateActiveSpec({ body: ... }).
  await keyInput.fill('edited-key')

  // KVTable is in controlled mode: it renders only what the store says.
  // If the store write did NOT occur, the value would revert to 'init-key' on
  // the next re-render. Asserting 'edited-key' proves the full round-trip:
  // edit → handleUrlencodedRowsChange → store write → re-render (AC-11 + AC-12).
  await expect(keyInput).toHaveValue('edited-key')
})

// ===========================================================================
// Behavior — AC-11 negative invariant: urlencoded write does NOT touch params/headers
// ===========================================================================

/**
 * AC-11 negative invariant — the plan requires that `handleUrlencodedRowsChange`
 * writes ONLY `body.urlencoded.rows` and leaves `spec.params` + `spec.headers`
 * untouched (plan KVTable.tsx:152-156).
 *
 * SpecProbe (BodyEditor.stories.tsx) reflects `spec.params.length` and
 * `spec.headers.length` as DOM data attributes so the CT can compare
 * before/after without needing direct module access from page.evaluate().
 *
 * makeBlankRequest() seeds: params=[] (len 0), headers=[Accept] (len 1).
 * Editing the KVTable row triggers the full chain:
 *   edit → onRowsChange → handleUrlencodedRowsChange → updateActiveSpec({ body: ... })
 * The spread `{ ...currentBody, urlencoded: { rows: next } }` must not alter
 * `params` or `headers`.
 */
test('AC-11 negative invariant — urlencoded row edit writes ONLY body.urlencoded.rows; spec.params and spec.headers are untouched', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorUrlencodedNegativeInvariantFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const probe = page.getByTestId('ct-be-spec-probe')

  // Assert the LIVE seeded values first — this proves SpecProbe is actually
  // subscribed to the seeded tab (params=[] len 0, headers=[Accept] len 1).
  // Without this, a broken probe (tabId miss → -1 sentinel both before/after)
  // would make the capture-then-compare below trivially pass on '-1' === '-1'.
  await expect(probe).toHaveAttribute('data-params-len', '0')
  await expect(probe).toHaveAttribute('data-headers-len', '1')
  // AC-11 body.raw preservation: fixture seeds raw.text='raw-preserved-text'
  // so this assertion is non-vacuous (not just checking an empty string).
  await expect(probe).toHaveAttribute('data-raw-text', 'raw-preserved-text')

  // Edit the KVTable row key — fires handleUrlencodedRowsChange → updateActiveSpec.
  const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(keyInput).toBeAttached()
  await keyInput.fill('edited-key')
  await expect(keyInput).toHaveValue('edited-key')

  // params.length and headers.length must be UNCHANGED after the body write.
  // Any change would mean updateActiveSpec clobbered a non-body spec field.
  await expect(probe).toHaveAttribute('data-params-len', '0')
  await expect(probe).toHaveAttribute('data-headers-len', '1')
  // body.raw.text must also be UNCHANGED — the `{...currentBody, urlencoded}`
  // spread in handleUrlencodedRowsChange preserved the raw slice.
  await expect(probe).toHaveAttribute('data-raw-text', 'raw-preserved-text')
})

// ===========================================================================
// Behavior — raw textarea onChange chain: typing propagates to store (coverage gap)
// ===========================================================================

/**
 * Locks the primary raw-mode workflow against regression: a user typing in the
 * raw code-area must propagate through the full onChange chain and update the
 * store's body.raw.text.
 *
 * Chain under test:
 *   textarea onChange → CodeEditor.handleTextChange → CodeEditor.props.onChange
 *   → BodyEditor: (text) => setRaw({ ...body.raw, text })
 *   → updateActiveSpec({ body: ... }) → tabsStore write.
 *
 * The textarea renders `value={body.raw.text}` from the store (controlled
 * component). If the chain fails to write the store, React re-renders with the
 * old store value and the textarea reverts — so toHaveValue('typed body text')
 * proves the full chain fired. Mirrors the AC-11 + AC-12 store-proof pattern
 * (controlled-value assertion) applied to the raw text path.
 */
test('onChange — typing in the raw code-area updates the store body.raw.text', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const textarea = page.getByLabel('Request body', { exact: true })

  // fill() dispatches input events; React's synthetic onChange observes them on
  // the controlled textarea and propagates the value through the chain above.
  await textarea.fill('typed body text')

  // Controlled-value round-trip: React re-renders with the new store value.
  // If the onChange → setRaw → updateActiveSpec chain is broken, the store is
  // not updated and React reverts the textarea to the original seed value —
  // toHaveValue('typed body text') would fail, catching the regression.
  await expect(textarea).toHaveValue('typed body text')
})

// ===========================================================================
// Finding 5 — UrlencodedKVTable memo render-skip (SKIPPED — not testable from outside)
// ===========================================================================
//
// `UrlencodedKVTable` is a memo-wrapped KVTable defined inside `App.tsx` as a
// module-level `const` that is NOT exported. This makes it impossible to import
// or mount directly from this CT file without introducing a production test-hook
// (export or forwardRef with a render-count probe), which would violate the
// constitution's minimal-change rule and the KISS principle.
//
// The memo optimization's correctness rests on two source-level guarantees that
// can be verified by reading the code — no CT instrumentation is required:
//
//   1. `handleUrlencodedRowsChange` in BodyEditor.tsx is stabilized via
//      `useCallback([updateActiveSpec])`. `updateActiveSpec` is a zustand action
//      whose identity never changes across renders, so `handleUrlencodedRowsChange`
//      gets the same reference on every BodyEditor re-render.
//
//   2. `body.urlencoded.rows` is reference-stable between raw-mode keystrokes
//      because each `updateActiveSpec({ body: { ...body, raw: ... } })` call
//      carries through the SAME `body.urlencoded` reference — only `body.raw` is
//      replaced. Shallow spreading does not create a new `urlencoded` object when
//      the urlencoded state is unchanged.
//
// Consequence: when the user types in raw mode, BodyEditor calls
// `renderUrlencoded(body.urlencoded.rows, stableCallback)`. `UrlencodedKVTable`'s
// memo sees stable `rows` + stable `onRowsChange` → skips re-render. This
// optimization is structural (derivable from the code) rather than behavioral,
// so it is documented here rather than force-tested via a production hook.
//
// Decision: SKIP the instrumented CT for this path. If `UrlencodedKVTable` is
// ever exported or the implementation changes, add a render-counter CT here.
//
// Source-pass (spec/017) additions confirmed NOT to affect this skip:
//   - Gutter/token span useMemo inside BodyEditor — BodyEditor-internal only.
//   - setColored(null) on activeTabId (now in CodeEditor, driven by resetKey prop) — no impact on
//     UrlencodedKVTable's memo props (rows + callback remain stable). Accurate.

// ===========================================================================
// Behavior — org-boundary wiring: BodyEditor passes resetKey={activeTabId}
// ===========================================================================

/**
 * Org-boundary wiring assertion — BodyEditor passes `resetKey={activeTabId}` to
 * CodeEditor. When the active request tab changes, CodeEditor receives a new
 * resetKey, which triggers setColored(null) then re-arms the debounce.
 *
 * Fixture: two tabs, both `active='raw'`, same JSON body — identical text+lang
 * ensures the debounce would NOT re-arm without the resetKey dep in CodeEditor's
 * useEffect. Failure mode: .tk-key spans never reappear after the tab switch
 * (colored stays null) because the debounce effect sees no input change.
 *
 * This test asserts the BodyEditor→CodeEditor wiring at the organism boundary,
 * not the molecule reset mechanics (those are CodeEditor.ct's AC-6 tests).
 */
test('wiring — BodyEditor passes resetKey={activeTabId}: switching tabs re-arms the CodeEditor highlight', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsRawSameBodyFixture />)
  await expect(c.getByTestId('ct-be-same-raw-ready')).toBeAttached()

  // Wait for Tab A's initial debounce to fire — .tk-key attaches.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Switch to Tab B (same raw text + lang as Tab A).
  // BodyEditor's activeTabId changes → resetKey={activeTabId} changes →
  // CodeEditor's useEffect([resetKey]) fires: setColored(null) clears spans,
  // then the debounce re-arms because resetKey is in its deps.
  await page.getByTestId('ct-be-sr-select-tab-b').click()

  // Causal chain pin: setColored(null) must first CLEAR the spans. Without this
  // intermediate detach check, stale Tab A spans would make the final assertion
  // vacuously pass even if the debounce never re-armed.
  await expect(page.locator('.tk-key').first()).not.toBeAttached()

  // After ~100ms the debounce re-fires and compose() populates .tk-key spans.
  // Playwright auto-retries within the default timeout.
  await expect(page.locator('.tk-key').first()).toBeAttached()
})

// ===========================================================================
// Behavior — org-boundary scroll-reset: activeTabId → resetKey → scroll-to-0
// ===========================================================================

/**
 * Org-boundary scroll-reset — switching the active request tab resets the
 * CodeEditor's textarea + pre scrollTop/scrollLeft to 0.
 *
 * BodyEditor passes `resetKey={activeTabId}` to CodeEditor. When activeTabId
 * changes (tab switch), CodeEditor's useEffect([resetKey]) fires and resets all
 * four scroll offsets (textarea.scrollTop, textarea.scrollLeft, pre.scrollTop,
 * pre.scrollLeft) to 0. This test proves the wiring at the organism boundary.
 *
 * Mirrors CodeEditor.ct.tsx's AC-6 scroll-reset test (molecule form), but drives
 * the reset via a tab switch (activeTabId → resetKey prop change) rather than a
 * direct prop change — proving the BodyEditor→CodeEditor wiring carries the signal.
 */
test('org-scroll-reset — switching request tabs resets textarea+pre scrollTop+scrollLeft to 0', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsScrollResetFixture />)
  await expect(c.getByTestId('ct-be-sc-ready')).toBeAttached()

  const textarea = page.getByLabel('Request body', { exact: true })
  const pre = page.getByTestId('body-pre')

  // Force the textarea into a bounded, internally-scrollable state and set non-zero
  // scroll offsets on BOTH axes, then dispatch scroll so the pre overlay syncs
  // (mirrors CodeEditor.ct.tsx AC-6 scroll-reset test pattern exactly).
  const before = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // browser may clamp to max — return the actual value
    ta.scrollLeft = 40
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return { top: ta.scrollTop, left: ta.scrollLeft }
  })
  // Non-vacuous pre-condition: both axes genuinely scrolled.
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // The <pre> overlay syncs via handleTextareaScroll — confirm it is non-zero.
  const preBefore = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
  expect(preBefore.top).toBeGreaterThan(0)
  expect(preBefore.left).toBeGreaterThan(0)

  // Switch to Tab B — activeTabId changes → BodyEditor passes a new resetKey to
  // CodeEditor → CodeEditor's useEffect([resetKey]) resets all four offsets to 0.
  await page.getByTestId('ct-be-sc-select-tab-b').click()

  // expect.poll retries until the React effect has executed (async microtask queue).
  // Assert ALL FOUR resets (textarea + pre, vertical + horizontal).
  await expect
    .poll(async () => {
      const ta = await textarea.evaluate((el) => {
        const t = el as HTMLTextAreaElement
        return { top: t.scrollTop, left: t.scrollLeft }
      })
      const pr = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
      return { taTop: ta.top, taLeft: ta.left, preTop: pr.top, preLeft: pr.left }
    })
    .toEqual({ taTop: 0, taLeft: 0, preTop: 0, preLeft: 0 })
})

// ===========================================================================
// Behavior — mixed-mode tab switch: raw → urlencoded → raw (F2)
// ===========================================================================

/**
 * Mixed-mode switch: Tab A=raw (JSON, overflowing), Tab B=urlencoded.
 *
 * When the user visits Tab B (urlencoded), the CodeEditor's parent panel receives
 * `hidden={true}` — CodeEditor stays mounted but is hidden. On return to Tab A:
 *  1. Highlight re-arms: .tk-key spans must re-attach after the debounce fires
 *     through the now-visible CodeEditor panel (resetKey effect in CodeEditor).
 *  2. Scroll resets: textarea + pre scrollTop/scrollLeft return to 0 (the
 *     resetKey useEffect in CodeEditor resets all four offsets).
 *
 * Mirrors the org-scroll-reset test structure but with Tab B in a DIFFERENT mode
 * (urlencoded, not raw), specifically exercising the hidden=true CodeEditor path.
 */
test('mixed-tab-switch — highlight re-arms and scroll resets after visiting urlencoded tab (hidden CodeEditor)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsMixedFixture />)
  await expect(c.getByTestId('ct-be-mx-ready')).toBeAttached()

  const textarea = page.getByLabel('Request body', { exact: true })
  const pre = page.getByTestId('body-pre')

  // Wait for Tab A's initial debounce to fire — .tk-key spans attach.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Force the textarea into a bounded, internally-scrollable state with non-zero
  // scroll offsets on BOTH axes (mirrors org-scroll-reset test pattern exactly).
  const before = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // browser may clamp to max — return the actual value
    ta.scrollLeft = 40
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return { top: ta.scrollTop, left: ta.scrollLeft }
  })
  // Non-vacuous pre-condition: both axes genuinely scrolled.
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // The <pre> overlay syncs via handleTextareaScroll — confirm it is non-zero.
  const preBefore = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
  expect(preBefore.top).toBeGreaterThan(0)
  expect(preBefore.left).toBeGreaterThan(0)

  // Switch to Tab B (urlencoded) — CodeEditor's parent div gains hidden={true}.
  // resetKey changes to Tab B's id → setColored(null) fires in CodeEditor.
  await page.getByTestId('ct-be-mx-select-tab-b').click()

  // Causal chain pin: .tk-key must detach. Tab B body.raw.text is '' so even when
  // the debounce re-fires after the resetKey change, no tk-key spans appear.
  await expect(page.locator('.tk-key').first()).not.toBeAttached()

  // Switch back to Tab A — CodeEditor's panel loses hidden; resetKey changes again.
  // useEffect([resetKey]) in CodeEditor fires: setColored(null) then debounce re-arms
  // with Tab A's JSON body → .tk-key spans reappear after ~100 ms.
  await page.getByTestId('ct-be-mx-select-tab-a').click()

  // Assert highlight re-arms through the hidden→visible transition. Playwright auto-retries.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Assert ALL FOUR scroll offsets reset to 0 (mirrors org-scroll-reset assertion).
  await expect
    .poll(async () => {
      const ta = await textarea.evaluate((el) => {
        const t = el as HTMLTextAreaElement
        return { top: t.scrollTop, left: t.scrollLeft }
      })
      const pr = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
      return { taTop: ta.top, taLeft: ta.left, preTop: pr.top, preLeft: pr.left }
    })
    .toEqual({ taTop: 0, taLeft: 0, preTop: 0, preLeft: 0 })
})

// ===========================================================================
// Behavior — AC-4 scroll-PRESERVATION: same-tab mode switch keeps scroll intact
// ===========================================================================

/**
 * AC-4 scroll+caret preservation (full) — a same-tab mode switch (raw →
 * urlencoded → raw) does NOT reset the CodeEditor's textarea+pre scroll offsets
 * OR the textarea's caret (selectionStart/selectionEnd).
 *
 * When the active body mode changes on the SAME request tab, activeTabId is
 * UNCHANGED, so resetKey={activeTabId} passed from BodyEditor to CodeEditor is
 * UNCHANGED. CodeEditor's useEffect([resetKey]) does NOT fire, so the scroll
 * reset does NOT happen. The `<div hidden={body.active !== 'raw'}>` wrapper
 * keeps CodeEditor mounted throughout, so the browser preserves both
 * textarea.scrollTop/scrollLeft and pre.scrollTop/scrollLeft natively. The
 * same native-preservation mechanism also keeps selectionStart/selectionEnd
 * intact across the hidden/display:none toggle.
 *
 * This is the OPPOSITE assertion from org-scroll-reset and mixed-tab-switch:
 * those tests assert scroll IS reset (tab switch → resetKey changes); this
 * test asserts scroll+caret are NOT reset (same-tab mode switch → resetKey
 * unchanged).
 *
 * Spec Risk table entry: "Mount-all hidden-panel scroll preservation."
 */
test('AC-4 — code-area scroll and caret state are preserved across a same-tab mode switch (raw → urlencoded → raw)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorScrollFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const textarea = page.getByLabel('Request body', { exact: true })
  const pre = page.getByTestId('body-pre')
  const radios = page.getByTestId('body-radio')

  // Force the textarea into a bounded, internally-scrollable state with non-zero
  // scroll offsets on BOTH axes, then dispatch scroll so the pre overlay syncs
  // (mirrors org-scroll-reset test setup pattern exactly).
  const before = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // browser may clamp to max — return the actual value
    ta.scrollLeft = 40
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return { top: ta.scrollTop, left: ta.scrollLeft }
  })
  // Non-vacuous pre-condition: both axes genuinely scrolled.
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // The <pre> overlay syncs via handleTextareaScroll — confirm it is non-zero.
  const preBefore = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
  expect(preBefore.top).toBeGreaterThan(0)
  expect(preBefore.left).toBeGreaterThan(0)

  // Set + capture caret (AC-4 caret dimension). Non-collapsed selection so both
  // endpoints are meaningful. Values are within the seeded body length.
  const caretBefore = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.selectionStart = 25
    ta.selectionEnd = 40
    return { start: ta.selectionStart, end: ta.selectionEnd }
  })
  // Non-vacuous pre-condition: caret was actually placed where we asked.
  expect(caretBefore.start).toBe(25)
  expect(caretBefore.end).toBe(40)

  // Switch to urlencoded on the SAME tab (index 2). activeTabId is UNCHANGED,
  // so resetKey is UNCHANGED. The raw panel becomes hidden but CodeEditor
  // stays mounted (mount-all architecture); scroll and caret are NOT reset.
  await radios.nth(2).click() // urlencoded (index 2)
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')

  // Switch back to raw (index 3). Still the same tab — resetKey still unchanged.
  await radios.nth(3).click() // raw (index 3)
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true')

  // Assert scroll AND caret are PRESERVED. The resetKey effect did NOT fire
  // (activeTabId unchanged), so no reset occurred. Chromium preserves both
  // scroll offsets and selectionStart/selectionEnd across the hidden toggle
  // natively. expect.poll retries until the React render settles.
  await expect
    .poll(async () => {
      const ta = await textarea.evaluate((el) => {
        const t = el as HTMLTextAreaElement
        return {
          top: t.scrollTop,
          left: t.scrollLeft,
          selStart: t.selectionStart,
          selEnd: t.selectionEnd
        }
      })
      const pr = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
      return {
        taTop: ta.top,
        taLeft: ta.left,
        preTop: pr.top,
        preLeft: pr.left,
        taSelStart: ta.selStart,
        taSelEnd: ta.selEnd
      }
    })
    .toEqual({
      taTop: before.top,
      taLeft: before.left,
      preTop: preBefore.top,
      preLeft: preBefore.left,
      taSelStart: caretBefore.start,
      taSelEnd: caretBefore.end
    })
})
