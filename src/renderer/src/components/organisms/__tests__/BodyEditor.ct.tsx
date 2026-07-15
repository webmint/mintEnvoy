/**
 * BodyEditor.ct.tsx — Playwright component tests for BodyEditor.
 *
 * Two halves:
 *  - Fidelity: §8 computed-style assertions via test-utils/fidelityAssert.ts
 *    (fail-closed — UNVERIFIED, never PASS, when the live computed-style channel
 *    is unavailable; AC-19). Per-theme literal hex (AC-20 light / AC-21 dark),
 *    token-binding resolution (AC-22), grid (AC-24), gutter/pre alignment (AC-23).
 *  - Behavior: radiogroup + roving focus (AC-18), default/mode switch (AC-6/7),
 *    lang-pill cycle (AC-8), two-pass highlight (AC-9/10), empty/malformed
 *    degrade (AC-16/17), cross-mode retention (AC-14), scroll sync, BLANK_BODY.
 *
 * Highlight coloring is debounced (~100ms), so token spans (`.tk-*`) appear
 * shortly after mount — every fidelity/highlight assertion first waits for the
 * relevant span to attach (Playwright auto-polling) before reading its style.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  assertComputedStyle,
  assertResolvesToToken,
  skipIfChannelUnavailable
} from '@renderer/test-utils/fidelityAssert'
import {
  BodyEditorRawJsonLightFixture,
  BodyEditorRawJsonDarkFixture,
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
  BodyEditorScrollBleedFixture,
  JSON_ALL_TOKENS
} from './BodyEditor.stories'

// Structural token classes the JSON pass can emit.
const STRUCTURAL = '.tk-key, .tk-str, .tk-num, .tk-bool, .tk-punc, .tk-var'

// ===========================================================================
// Fidelity — per-theme literal hex (AC-20 light / AC-21 dark) + fail-closed (AC-19)
// ===========================================================================

test('AC-20 — light-theme tk-* colors resolve to the design literals', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  await expect(page.locator('.tk-key').first()).toBeAttached() // wait for debounced coloring

  await assertComputedStyle(page, '.tk-key', 'color', 'rgb(3, 105, 161)', 'light tk-key')
  await assertComputedStyle(page, '.tk-str', 'color', 'rgb(21, 128, 61)', 'light tk-str')
  await assertComputedStyle(page, '.tk-num', 'color', 'rgb(180, 83, 9)', 'light tk-num')
  await assertComputedStyle(page, '.tk-bool', 'color', 'rgb(190, 24, 93)', 'light tk-bool')
})

test('AC-21 — dark-theme tk-* colors resolve to the design literals', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonDarkFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await skipIfChannelUnavailable(page)
  await expect(page.locator('.tk-key').first()).toBeAttached()

  await assertComputedStyle(page, '.tk-key', 'color', 'rgb(125, 211, 252)', 'dark tk-key')
  await assertComputedStyle(page, '.tk-str', 'color', 'rgb(134, 239, 172)', 'dark tk-str')
  await assertComputedStyle(page, '.tk-num', 'color', 'rgb(252, 211, 77)', 'dark tk-num')
  await assertComputedStyle(page, '.tk-bool', 'color', 'rgb(240, 171, 252)', 'dark tk-bool')
})

test('AC-22 — tk-null/punc/var resolve to their bound tokens', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await skipIfChannelUnavailable(page)
  await expect(page.locator('.tk-var').first()).toBeAttached()

  await assertResolvesToToken(page, '.tk-null', 'color', '--text-faint', 'tk-null → --text-faint')
  await assertResolvesToToken(page, '.tk-punc', 'color', '--text-muted', 'tk-punc → --text-muted')
  await assertResolvesToToken(page, '.tk-var', 'color', '--accent', 'tk-var → --accent')
})

/**
 * AC-22 dark-theme counterpart.
 *
 * The three token bindings that use CSS custom properties rather than literal
 * per-theme hex values (tk-null → --text-faint, tk-punc → --text-muted,
 * tk-var → --accent) must resolve to the SAME tokens in both themes.
 * The resolved HEX will differ from the light-theme values (because the
 * dark-theme overrides --text-faint / --text-muted / --accent), but each
 * element's computed color must still equal the token's resolved value.
 */
test('AC-22 dark-theme — tk-null/punc/var resolve to their bound tokens in dark mode', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonDarkFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  await expect(page.locator('.tk-var').first()).toBeAttached() // wait for debounced coloring

  // assertResolvesToToken appends its probe to document.body, which is OUTSIDE the
  // fixture's data-theme="dark" wrapper. Set the theme on documentElement so the
  // probe resolves --text-faint/--text-muted in the SAME dark scope as the tokens
  // under test (otherwise the probe reads light-theme values and the tk-null/tk-punc
  // comparison is against the wrong scope). Reset afterward for test isolation.
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'))
  try {
    await assertResolvesToToken(
      page,
      '.tk-null',
      'color',
      '--text-faint',
      'dark tk-null → --text-faint'
    )
    await assertResolvesToToken(
      page,
      '.tk-punc',
      'color',
      '--text-muted',
      'dark tk-punc → --text-muted'
    )
    await assertResolvesToToken(page, '.tk-var', 'color', '--accent', 'dark tk-var → --accent')
  } finally {
    await page.evaluate(() => document.documentElement.removeAttribute('data-theme'))
  }
})

// ===========================================================================
// Fidelity — grid (AC-24) + gutter/pre alignment (AC-23)
// ===========================================================================

test('AC-24 — .code-editor grid is a 36px gutter track + flexible content', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate (matches sibling fidelity tests)
  const cols = await page
    .getByTestId('body-code-editor')
    .first()
    .evaluate((el) => window.getComputedStyle(el).gridTemplateColumns)
  expect(cols.startsWith('36px')).toBe(true)
})

test('AC-23 — gutter line count equals the rendered line count', async ({ mount, page }) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  // The seeded JSON body has 6 lines; the gutter renders one <div> per line.
  await expect(page.getByTestId('body-gutter').locator('> div')).toHaveCount(6)
})

/**
 * AC-23 — gutter div height regression guard.
 *
 * Each gutter <div> must be exactly 20.625 px tall — the code-editor line box
 * height (font-size 12.5 px × line-height 1.65). The CSS uses
 * `height: calc(12.5px * 1.65)` rather than `height: 1.65em` because `em`
 * resolves against the gutter's OWN font-size (11.5 px), which would yield
 * 18.975 px and drift ~1.65 px per line vs the code lines.
 *
 * This CT pins the resolved value so reverting to `1.65em` is caught immediately.
 */
test('AC-23 — gutter div height is 20.625px (code-line-height fix — prevents drift)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate (reads live computed style)
  const height = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  // calc(12.5px * 1.65) = 20.625px. If regressed to 1.65em (gutter font 11.5px)
  // this would be 18.975px, causing all line numbers to drift vs the code text.
  expect(height).toBe('20.625px')
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
  // Use the existing raw-JSON fixture: JSON_ALL_TOKENS is the seeded body text.
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')

  // Assert raw text is present RIGHT NOW — before waiting for any .tk-* span.
  // On first paint, showColored=false → pre renders <span>{body.raw.text}</span>.
  // If the plain-degrade path is broken the pre stays empty until the debounce
  // fires; toContainText would then resolve only AFTER highlighting (see below).
  await expect(pre).toContainText(JSON_ALL_TOKENS.slice(0, 14)) // '{\n  "key": 1,' substring

  // Sanity: no token spans should exist yet — confirms this assertion ran before
  // the 100 ms debounce fired. If tkKeyCount > 0 here, the plain-degrade path is
  // broken (toContainText resolved only because the tokenized content appeared).
  // page.locator().count() is non-retrying — a point-in-time snapshot.
  const tkKeyCount = await page.locator('[data-testid="body-pre"] .tk-key').count()
  expect(tkKeyCount).toBe(0)
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
  await radios.nth(2).click() // urlencoded
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')
  await radios.nth(1).click() // back to raw
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true')

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

  // Tab A is initially active: raw mode (radio index 1) is checked.
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true') // raw
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'false') // none
  await expect(textarea).toHaveValue('tab-a-text')

  // Switch to Tab B: BodyEditor must now show Tab B's urlencoded mode.
  await page.getByTestId('ct-be-select-tab-b').click()
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true') // urlencoded
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'false') // raw not active

  // Tab B's urlencoded row data must be visible in the live KVTable (row-data isolation).
  // The fixture seeded b-key for Tab B; if isolation breaks, Tab A's empty rows would show.
  const bKeyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(bKeyInput).toBeAttached()
  await expect(bKeyInput).toHaveValue('b-key')

  // Switch back to Tab A: BodyEditor must restore Tab A's raw mode and text.
  await page.getByTestId('ct-be-select-tab-a').click()
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true') // raw again
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
  await radios.nth(1).click()
  await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true') // raw now active
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
//   - setColored(null) on activeTabId — BodyEditor-internal, no impact on
//     UrlencodedKVTable's memo props (rows + callback remain stable). Accurate.

// ===========================================================================
// Behavior — highlight re-arms after tab switch even when raw text+lang are
// identical (Finding 1 — highlight-lock regression guard)
// ===========================================================================

/**
 * Regression guard — without `activeTabId` in the debounce effect deps, switching
 * to a tab with the SAME raw text+lang leaves `colored` null permanently.
 *
 * The `useEffect([activeTabId])` calls `setColored(null)` on every tab switch.
 * The debounce effect `useEffect([body.raw.text, body.raw.lang, activeTabId])`
 * must include `activeTabId` so it re-arms and reschedules `compose()` even
 * when the text+lang values are identical on the incoming tab. Without that dep,
 * the debounce never fires on the new tab and no `.tk-key` span ever appears.
 *
 * Fixture: two tabs, both `active='raw'`, same JSON body `{"key": 1}`, same lang.
 */
test('highlight re-arms after tab switch — .tk-key appears on Tab B even when raw text+lang are identical to Tab A', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsRawSameBodyFixture />)
  await expect(c.getByTestId('ct-be-same-raw-ready')).toBeAttached()

  // Wait for the debounce to fire on Tab A so .tk-key is present.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Switch to Tab B (same raw text + lang as Tab A).
  // The activeTabId effect fires: setColored(null) — .tk-key spans disappear.
  // The debounce effect re-arms because activeTabId is in its deps.
  await page.getByTestId('ct-be-sr-select-tab-b').click()

  // Pin the causal chain: setColored(null) must first CLEAR the spans. Without
  // this intermediate detach, a broken impl that never clears but also never
  // re-arms would pass the final assertion on stale Tab A spans (qa Gap 3).
  await expect(page.locator('.tk-key').first()).not.toBeAttached()

  // After ~100 ms the debounce fires, compose() produces token spans, and
  // .tk-key must reattach. Playwright auto-retries within the 5 s timeout.
  await expect(page.locator('.tk-key').first()).toBeAttached()
})

// ===========================================================================
// Behavior — textarea scrollTop resets to 0 on request-tab switch
// (Finding 2 — scroll-bleed regression guard)
// ===========================================================================

/**
 * Regression guard — the `useEffect([activeTabId])` in BodyEditor resets
 * `textareaRef.current.scrollTop` and `preRef.current.scrollTop` to 0 on
 * every request-tab switch so the new tab's body always starts at the top.
 *
 * Without this reset, the DOM textarea (which persists across tab switches —
 * BodyEditor is mounted once) would display the incoming tab's body at the
 * outgoing tab's scroll offset.
 *
 * Fixture: two tabs, both raw with long multi-line bodies (100 × 80-char
 * lines) in a 150px bounded container so the textarea is scrollable.
 */
test('scroll-bleed — switching request tabs resets textarea scrollTop to 0 (activeTabId effect)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorScrollBleedFixture />)
  await expect(c.getByTestId('ct-be-scroll-bleed-ready')).toBeAttached()

  const textarea = page.getByLabel('Request body', { exact: true })
  const pre = c.getByTestId('body-pre')

  // Force the textarea into a bounded, internally-scrollable box and set a
  // non-zero scroll offset on BOTH axes (mirrors the existing scroll-sync CT
  // pattern). The scroll event drives handleTextareaScroll, which syncs the
  // <pre> overlay's scrollTop/scrollLeft to match — so all four DOM properties
  // the activeTabId effect resets are non-zero going into the switch.
  const before = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // browser may clamp to max — return the actual value
    ta.scrollLeft = 40
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return { top: ta.scrollTop, left: ta.scrollLeft }
  })
  expect(before.top).toBeGreaterThan(0) // confirm vertical scroll genuinely took
  expect(before.left).toBeGreaterThan(0) // confirm horizontal scroll genuinely took
  // The <pre> overlay tracks the textarea via handleTextareaScroll — confirm it
  // is non-zero so the post-switch assertion that it reset to 0 is non-vacuous.
  const preBefore = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
  expect(preBefore.top).toBeGreaterThan(0)
  expect(preBefore.left).toBeGreaterThan(0)

  // Switch to Tab B — the activeTabId useEffect fires and resets all four
  // scroll offsets (textarea + pre, both axes) to 0.
  await page.getByTestId('ct-be-sb-select-tab-b').click()

  // expect.poll retries until the React effect has executed. React effects are
  // asynchronous (microtask queue) so a single point-in-time evaluate could race
  // the effect; polling is the correct pattern here. Assert ALL FOUR resets —
  // textarea + pre, vertical + horizontal — so removing any one reset line in
  // the source fails this guard (qa Gap 1 + Gap 2).
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
