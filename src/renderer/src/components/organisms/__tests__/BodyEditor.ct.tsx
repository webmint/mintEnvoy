/**
 * BodyEditor.ct.tsx — Playwright component tests for BodyEditor (organism level).
 *
 * Molecule-level fidelity + code-editor mechanics (per-theme hex, token bindings,
 * grid geometry, row heights, caret-at-click, conditional-mount internals) live in
 * CodeEditor.ct.tsx. This file proves the ORGANISM behaviors the molecule CT cannot:
 * the radiogroup, the lang-pill, per-request-tab body isolation, the urlencoded
 * assembled path, and — new for the edit/preview toggle (tasks 001/002) — the
 * `body-edit-toggle` control, the F-002 preventDefault exit, the toggle-entry
 * focus, the standalone blur exit, and the AC-6 tab-switch-while-editing reset.
 *
 * Model note (post-018 rebuild): CodeEditor is an edit/preview CONDITIONAL-MOUNT
 * toggle. In raw mode BodyEditor starts in PREVIEW (editing=false) — only the
 * highlighted <pre> (`body-pre`) is mounted; the <textarea> mounts ONLY after an
 * edit entry (toggle click / pre click / Enter). Tokenisation is SYNCHRONOUS
 * (useMemo) — `.tk-*` spans are present on first preview render, so there is NO
 * debounce to wait out and NO page.clock machinery. The old always-mounted-overlay
 * scroll-sync (`handleTextareaScroll`) is gone — only one layer is ever in the DOM.
 *
 * NOTE: the local Playwright CT harness cannot mount these organism fixtures
 * (pre-existing break — MEMORY `ct-organism-fixtures-cannot-mount-locally`).
 * These tests are verified statically + downstream live-verify; `test:ct` is
 * left UNVERIFIED for this task.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  BodyEditorRawJsonLightFixture,
  BodyEditorRawJsonToggleFixture,
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
// Behavior — edit/preview toggle control (AC-3 / AC-11 / AC-16 / F-002)
// ===========================================================================

/**
 * AC-3 — the `body-edit-toggle` control renders in the toolbar right slot in raw
 * mode and is hidden in non-raw modes (mirrors the lang-pill gating).
 */
test('AC-3 — body-edit-toggle is present+visible in raw mode, hidden in non-raw', async ({
  mount,
  page
}) => {
  const raw = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(raw.getByTestId('ct-be-ready')).toBeAttached()
  await expect(page.getByTestId('body-edit-toggle')).toBeVisible()

  await raw.unmount()

  const none = await mount(<BodyEditorNoneFixture />)
  await expect(none.getByTestId('ct-be-ready')).toBeAttached()
  // Present in the DOM (mount-all raw panel) but hidden because active !== 'raw'.
  await expect(page.getByTestId('body-edit-toggle')).not.toBeVisible()
})

/**
 * AC-3 (a11y) — the toggle is a proper WAI-ARIA toggle button: `aria-pressed`
 * reflects the current edit/preview state (false in preview, true in edit), and
 * the button carries NO aria-label so its visible text ("Edit"/"Preview") is its
 * accessible name (WCAG 2.5.3 Label-in-Name). Guards the aria-pressed semantics
 * and the deliberate absence of a stale aria-label.
 */
test('AC-3 — toggle exposes aria-pressed state and text-based accessible name', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonToggleFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const toggle = page.getByTestId('body-edit-toggle')

  // Preview (default): not pressed; no aria-label (text is the accessible name).
  await expect(toggle).toHaveAttribute('aria-pressed', 'false')
  await expect(toggle).not.toHaveAttribute('aria-label')
  await expect(toggle).toHaveText('Edit')

  // Enter edit → pressed flips to true; visible text (the accessible name) updates.
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-pressed', 'true')
  await expect(toggle).toHaveText('Preview')
})

/**
 * AC-11 — only the visible layer is mounted per editing state. In preview
 * (default) the <pre> is mounted and the textarea is NOT; after a toggle entry
 * the textarea is mounted and the <pre> is NOT.
 */
test('AC-11 — only the visible layer is mounted (preview=pre, edit=textarea)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')
  const textarea = page.getByLabel('Request body', { exact: true })

  // Preview default: pre mounted, textarea not.
  await expect(pre).toBeAttached()
  await expect(textarea).not.toBeAttached()

  // Enter edit via the toggle: textarea mounts, pre unmounts.
  await page.getByTestId('body-edit-toggle').click()
  await expect(textarea).toBeAttached()
  await expect(pre).not.toBeAttached()
})

/**
 * AC-16 / AC-18 — clicking the toggle from preview enters edit mode AND focuses
 * the freshly-mounted textarea (the focus-on-mount effect keyed on `editing`).
 * Located by accessible name (G-7), never by an internal textareaRef.
 */
test('AC-16/18 — toggle entry from preview focuses the mounted textarea', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonToggleFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  await page.getByTestId('body-edit-toggle').click()
  await expect(page.getByLabel('Request body', { exact: true })).toBeFocused()
})

/**
 * F-002 — clicking the toggle WHILE EDITING lands in preview (a single clean
 * flip), proving the toggle's `onMouseDown` preventDefault suppresses the
 * blur-then-click double-fire.
 *
 * Without preventDefault: mousedown blurs the textarea → onBlur fires
 * onEditingChange(false) → preview; THEN the toggle's onClick reads editing=false
 * and flips it back to true → the editor bounces back to edit mode. With
 * preventDefault the textarea never blurs on mousedown, so the single onClick
 * flips edit→preview and stays there.
 */
test('F-002 — clicking the toggle while editing lands in preview (preventDefault suppresses blur bounce)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonToggleFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const toggle = page.getByTestId('body-edit-toggle')
  const pre = page.getByTestId('body-pre')
  const textarea = page.getByLabel('Request body', { exact: true })

  // Enter edit.
  await toggle.click()
  await expect(textarea).toBeAttached()

  // Click the toggle again WHILE editing → must land in PREVIEW (not bounce back).
  await toggle.click()

  // This assertion is a GENUINE discriminator, not a vacuous pass: the toggle's
  // onClick is `setEditing((v) => !v)` (a flip), NOT an idempotent
  // `setEditing(false)`. So the BROKEN path (no preventDefault) lands in EDIT, not
  // preview — mousedown blurs → onBlur sets editing=false → onClick flips it back
  // to TRUE → textarea. Only the CORRECT path (preventDefault suppresses the blur,
  // the lone onClick flips true→false) leaves the textarea unmounted. Asserting the
  // textarea is NOT attached therefore fails iff preventDefault is missing.
  await expect(pre).toBeAttached()
  await expect(textarea).not.toBeAttached()
})

/**
 * AC-16 blur exit (standalone, isolated from the toggle) — entering edit then
 * removing focus by clicking an UNRELATED element (not the toggle) returns to
 * preview. This isolates CodeEditor's blur handler: the F-002 test above also
 * fires the toggle's onClick(onEditingChange(false)), so a bug where the blur
 * handler called onEditingChange(TRUE) would slip through without this test.
 */
test('AC-16 — blurring the textarea (click outside, not the toggle) returns to preview', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonToggleFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  await page.getByTestId('body-edit-toggle').click()
  await expect(page.getByLabel('Request body', { exact: true })).toBeAttached()

  // Click a neutral focusable element OUTSIDE the editor (does not change mode).
  await page.getByTestId('ct-be-blur-target').click()

  // The textarea blur → onEditingChange(false) → preview <pre> re-mounts.
  await expect(page.getByTestId('body-pre')).toBeAttached()
  await expect(page.getByLabel('Request body', { exact: true })).not.toBeAttached()
})

/**
 * Toggle swaps to a FRESH layer at scrollTop 0 — each toggle unmounts the current
 * layer and mounts the other, so the new layer always starts at the top. Height-
 * bounded fixture (per CT-harness constraint 5) so the preview <pre> genuinely
 * overflows and can be scrolled non-zero before the toggle.
 */
test('toggle — entering edit mounts a fresh textarea at scrollTop 0 (layer swap resets scroll)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorScrollFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')
  // Scroll the preview pre non-zero (non-vacuous precondition).
  const preTop = await pre.evaluate((el) => {
    el.scrollTop = 60
    return el.scrollTop
  })
  expect(preTop).toBeGreaterThan(0)

  // Toggle into edit — the textarea is a fresh mount, so it starts at scrollTop 0.
  await page.getByTestId('body-edit-toggle').click()
  const taTop = await page
    .getByLabel('Request body', { exact: true })
    .evaluate((el) => (el as HTMLTextAreaElement).scrollTop)
  expect(taTop).toBe(0)
})

// ===========================================================================
// Behavior — AC-6 return-to-preview on tab switch while editing
// ===========================================================================

/**
 * AC-6 (render-phase reset) — a request-tab switch WHILE EDITING lands in preview
 * for the new tab: the immediate post-switch DOM has the <pre> mounted and the
 * textarea NOT. BodyEditor's set-state-in-render reset (`if (activeTabId !==
 * prevTab) setEditing(false)`) commits editing=false ATOMICALLY with the tab
 * switch — the forbidden passive-useEffect form would first commit editing=true /
 * textarea for the new tab, then reset on a later effect, showing a stale edit frame.
 */
test('AC-6 — switching request tabs while editing returns to preview for the new tab', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsRawSameBodyFixture />)
  await expect(c.getByTestId('ct-be-same-raw-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')
  const textarea = page.getByLabel('Request body', { exact: true })

  // Enter edit on Tab A.
  await page.getByTestId('body-edit-toggle').click()
  await expect(textarea).toBeAttached()

  // Switch to Tab B (activeTabId changes) → render-phase reset → preview.
  await page.getByTestId('ct-be-sr-select-tab-b').click()

  // Immediate post-switch state: preview pre mounted, textarea gone.
  await expect(pre).toBeAttached()
  await expect(textarea).not.toBeAttached()
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
// Behavior — preview highlight (AC-9 var-pass-wins JSON / AC-10 var-only non-JSON)
// ===========================================================================

test('AC-9 — JSON var-pass-wins: {{x}} is a tk-var beside tk-str content', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()
  // Preview is tokenised synchronously (useMemo) — spans are present on first render.
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
  // Synchronous degrade (JSON.parse throws → single plain span) — no debounce wait.
  await expect(page.getByTestId('body-pre').locator(STRUCTURAL)).toHaveCount(0)
  await expect(page.getByTestId('body-pre')).toContainText('{ bad json')
  // No error UI: malformed JSON degrades silently — no alert/error banner rendered.
  await expect(page.getByRole('alert')).toHaveCount(0)
})

// ===========================================================================
// Behavior — cross-mode retention (AC-14)
// ===========================================================================

test('AC-14 — raw text survives a switch away and back (read via the edit textarea)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')
  // Preview shows the seeded text tokenised.
  await expect(page.getByTestId('body-pre')).toContainText('msg')

  await radios.nth(2).click() // urlencoded (index 2)
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')
  await radios.nth(3).click() // back to raw (index 3)
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true')

  // Enter edit and read the textarea value — retained from the store round-trip.
  await page.getByTestId('body-edit-toggle').click()
  await expect(page.getByLabel('Request body', { exact: true })).toHaveValue(
    /"msg": "a \{\{x\}\} b"/
  )
})

// ===========================================================================
// Behavior — per-request-tab body isolation (Finding 2)
// ===========================================================================

/**
 * Finding 2 — Two distinct request tabs carry independent body states. BodyEditor
 * reads `spec.body` for the ACTIVE tab only; switching the active request tab must
 * reflect the incoming tab's own body (mode + raw text / urlencoded rows).
 *
 * Fixture seeds:
 *   Tab A — active='raw',        raw.text='tab-a-text'
 *   Tab B — active='urlencoded', urlencoded.rows=[{ key:'b-key' }]
 *
 * Raw text is asserted via the preview <pre> content (editing defaults to preview),
 * not the textarea (which is unmounted until an edit entry).
 */
test('body-isolation — each request tab shows its own body type independently (Finding 2)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsFixture />)
  await expect(c.getByTestId('ct-be-two-tabs-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')

  // Tab A is initially active: raw mode (radio index 3) is checked; preview shows text.
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true') // raw (index 3)
  await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'false') // none
  await expect(page.getByTestId('body-pre')).toContainText('tab-a-text')

  // Switch to Tab B: BodyEditor must now show Tab B's urlencoded mode.
  await page.getByTestId('ct-be-select-tab-b').click()
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true') // urlencoded
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'false') // raw not active (index 3)

  // Tab B's urlencoded row data must be visible in the live KVTable (row-data isolation).
  const bKeyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(bKeyInput).toBeAttached()
  await expect(bKeyInput).toHaveValue('b-key')

  // Switch back to Tab A: BodyEditor must restore Tab A's raw mode and text.
  await page.getByTestId('ct-be-select-tab-a').click()
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true') // raw again (index 3)
  await expect(page.getByTestId('body-pre')).toContainText('tab-a-text') // raw text unchanged

  // Tab A has no urlencoded rows and is in raw mode — Tab B's b-key row must be gone.
  await expect(page.locator('.kv-row:not(.empty) .kv-cell.key input')).toHaveCount(0)
})

// ===========================================================================
// Behavior — AC-14 mirror: urlencoded rows survive a body-type switch (Finding 3)
// ===========================================================================

test('AC-14 mirror — urlencoded rows survive a switch to raw and back (Finding 3)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorUrlencodedLiveFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')
  const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()

  // Start in urlencoded mode: the row seeded by the fixture is visible.
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true') // urlencoded
  await expect(keyInput).toBeAttached()
  await expect(keyInput).toHaveValue('init-key')

  // Switch to raw.
  await radios.nth(3).click() // raw is index 3
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true')
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'false')

  // Switch back to urlencoded.
  await radios.nth(2).click()
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')

  // Rows must survive the round-trip: the store's `body.urlencoded.rows` is unchanged.
  await expect(keyInput).toHaveValue('init-key')
})

// ===========================================================================
// Behavior — already-active radio early-return guard (Finding 7)
// ===========================================================================

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

  const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(keyInput).toBeAttached()

  // Edit the key — fires onChange → KVTable calls onRowsChange(nextRows) →
  // BodyEditor's handleUrlencodedRowsChange → updateActiveSpec({ body: ... }).
  await keyInput.fill('edited-key')

  // KVTable is controlled: it renders only what the store says. Asserting
  // 'edited-key' proves the full round-trip (edit → store write → re-render).
  await expect(keyInput).toHaveValue('edited-key')
})

// ===========================================================================
// Behavior — AC-11 negative invariant: urlencoded write does NOT touch params/headers
// ===========================================================================

/**
 * AC-11 negative invariant — `handleUrlencodedRowsChange` writes ONLY
 * `body.urlencoded.rows` and leaves `spec.params` + `spec.headers` + `body.raw`
 * untouched. SpecProbe reflects those lengths + raw.text as DOM data attributes.
 */
test('AC-11 negative invariant — urlencoded row edit writes ONLY body.urlencoded.rows; spec.params and spec.headers are untouched', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorUrlencodedNegativeInvariantFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const probe = page.getByTestId('ct-be-spec-probe')

  // Assert the LIVE seeded values first — proves SpecProbe is subscribed to the
  // seeded tab (else a -1 sentinel both before/after would pass trivially).
  await expect(probe).toHaveAttribute('data-params-len', '0')
  await expect(probe).toHaveAttribute('data-headers-len', '1')
  await expect(probe).toHaveAttribute('data-raw-text', 'raw-preserved-text')

  // Edit the KVTable row key — fires handleUrlencodedRowsChange → updateActiveSpec.
  const keyInput = page.locator('.kv-row:not(.empty) .kv-cell.key input').first()
  await expect(keyInput).toBeAttached()
  await keyInput.fill('edited-key')
  await expect(keyInput).toHaveValue('edited-key')

  // params/headers/raw must be UNCHANGED after the body write.
  await expect(probe).toHaveAttribute('data-params-len', '0')
  await expect(probe).toHaveAttribute('data-headers-len', '1')
  await expect(probe).toHaveAttribute('data-raw-text', 'raw-preserved-text')
})

// ===========================================================================
// Behavior — raw textarea onChange chain: typing propagates to store
// ===========================================================================

/**
 * Locks the raw-mode edit workflow: entering edit mode and typing must propagate
 * through the full onChange chain into the store's body.raw.text. Under the toggle
 * model the textarea mounts only after an edit entry, so the test toggles in first.
 *
 * Chain: textarea onChange → CodeEditor.handleTextChange → props.onChange →
 * BodyEditor setRaw → updateActiveSpec → tabsStore write. The textarea renders
 * `value={body.raw.text}` (controlled) so a broken chain reverts the value — thus
 * toHaveValue('typed body text') proves the full round-trip.
 */
test('onChange — typing in the raw code-area (edit mode) updates the store body.raw.text', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorRawJsonLightFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  // Enter edit mode so the textarea is mounted.
  await page.getByTestId('body-edit-toggle').click()
  const textarea = page.getByLabel('Request body', { exact: true })
  await expect(textarea).toBeAttached()

  await textarea.fill('typed body text')

  // Controlled-value round-trip: a broken chain would revert to the seed value.
  await expect(textarea).toHaveValue('typed body text')
})

// ===========================================================================
// Behavior — org-boundary wiring: resetKey={activeTabId} resets scroll on tab switch
// ===========================================================================

/**
 * Org-boundary scroll-reset — BodyEditor passes `resetKey={activeTabId}` to
 * CodeEditor; switching the active request tab changes resetKey, and CodeEditor's
 * useEffect([resetKey]) resets the mounted layer's scroll to 0.
 *
 * Under the conditional-mount model only ONE layer is mounted at a time. In
 * preview the <pre> is the scrollable layer; the old dual-layer (textarea+pre)
 * scroll-sync driver is gone. This drives the preview <pre> scroll, switches tab,
 * and asserts the reset — the organism-boundary counterpart to CodeEditor.ct's
 * molecule AC-6 scroll-reset.
 */
test('org-scroll-reset — switching request tabs resets the preview pre scroll to 0', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsScrollResetFixture />)
  await expect(c.getByTestId('ct-be-sc-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')

  // Scroll the preview pre non-zero on both axes (non-vacuous precondition).
  const before = await pre.evaluate((el) => {
    el.scrollTop = 60
    el.scrollLeft = 40
    return { top: el.scrollTop, left: el.scrollLeft }
  })
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // Switch to Tab B — activeTabId → new resetKey → useEffect([resetKey]) resets scroll.
  await page.getByTestId('ct-be-sc-select-tab-b').click()

  // Poll: React effects run on the microtask queue after the click.
  await expect
    .poll(async () => pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft })))
    .toEqual({ top: 0, left: 0 })
})

// ===========================================================================
// Behavior — mixed-mode tab switch: raw → urlencoded → raw (hidden CodeEditor)
// ===========================================================================

/**
 * Mixed-mode switch: Tab A=raw (JSON, overflowing), Tab B=urlencoded. Visiting
 * Tab B hides the raw panel (CodeEditor stays mounted, `hidden={true}`); returning
 * to Tab A un-hides it. Asserts the two organism-boundary guarantees under the
 * synchronous/conditional-mount model:
 *   1. Highlight: `.tk-key` present on Tab A (synchronous), absent while Tab B
 *      (urlencoded, raw body '') is active, present again on return to Tab A.
 *   2. Scroll: the preview pre scroll resets to 0 on the return tab switch.
 */
test('mixed-tab-switch — highlight and scroll behave across a visit to the urlencoded tab (hidden CodeEditor)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorTwoTabsMixedFixture />)
  await expect(c.getByTestId('ct-be-mx-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')

  // Tab A raw JSON: tokens present synchronously.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Scroll the preview pre non-zero (non-vacuous precondition).
  const before = await pre.evaluate((el) => {
    el.scrollTop = 60
    el.scrollLeft = 40
    return { top: el.scrollTop, left: el.scrollLeft }
  })
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // Switch to Tab B (urlencoded, raw body ''): raw panel hidden; the mounted
  // preview reflects Tab B's empty raw body → no tk-key spans.
  await page.getByTestId('ct-be-mx-select-tab-b').click()
  await expect(page.locator('.tk-key').first()).not.toBeAttached()

  // Return to Tab A — tokens reappear (synchronous) and the pre scroll resets to 0.
  await page.getByTestId('ct-be-mx-select-tab-a').click()
  await expect(page.locator('.tk-key').first()).toBeAttached()
  await expect
    .poll(async () =>
      page.getByTestId('body-pre').evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
    )
    .toEqual({ top: 0, left: 0 })
})

// ===========================================================================
// Behavior — AC-4 scroll+caret PRESERVATION across a same-tab mode switch
// ===========================================================================

/**
 * AC-4 scroll+caret preservation — a same-tab mode switch (raw → urlencoded →
 * raw) does NOT reset the edit textarea's scroll or caret. activeTabId is
 * UNCHANGED, so `resetKey={activeTabId}` is unchanged and CodeEditor's
 * useEffect([resetKey]) does NOT fire. The render-phase editing reset also does
 * NOT fire (it keys on activeTabId, not body.active), so `editing` stays true and
 * the textarea remains mounted (hidden via the mount-all panel) — Chromium
 * preserves scrollTop/scrollLeft and selectionStart/selectionEnd across the
 * display:none toggle natively.
 *
 * Opposite of org-scroll-reset (tab switch → resetKey changes → reset): here the
 * SAME tab's mode changes, so nothing resets.
 */
test('AC-4 — edit-mode scroll and caret are preserved across a same-tab mode switch (raw → urlencoded → raw)', async ({
  mount,
  page
}) => {
  const c = await mount(<BodyEditorScrollFixture />)
  await expect(c.getByTestId('ct-be-ready')).toBeAttached()

  const radios = page.getByTestId('body-radio')

  // Enter edit mode so the textarea is the mounted layer.
  await page.getByTestId('body-edit-toggle').click()
  const textarea = page.getByLabel('Request body', { exact: true })
  await expect(textarea).toBeAttached()

  // Set non-zero scroll on both axes + a non-collapsed caret (all within body length).
  const before = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // browser may clamp to max — return the actual value
    ta.scrollLeft = 40
    ta.selectionStart = 25
    ta.selectionEnd = 40
    return {
      top: ta.scrollTop,
      left: ta.scrollLeft,
      selStart: ta.selectionStart,
      selEnd: ta.selectionEnd
    }
  })
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)
  expect(before.selStart).toBe(25)
  expect(before.selEnd).toBe(40)

  // Switch to urlencoded then back to raw on the SAME tab. Three invariants make
  // the preservation non-vacuous:
  //   1. activeTabId is UNCHANGED → resetKey unchanged → CodeEditor's
  //      useEffect([resetKey]) does not fire (no scroll reset).
  //   2. The render-phase editing reset keys on activeTabId, not body.active, so
  //      editing stays true → the textarea stays mounted (hidden), not remounted.
  //   3. handleRadioSelect writes `{ ...body, active: next }` — it changes ONLY
  //      body.active and preserves body.raw.text, so the controlled textarea's
  //      `value` is byte-identical across the round-trip (no value change → no
  //      React remount that would drop scroll/caret).
  // Chromium then preserves scrollTop/scrollLeft + selectionStart/End across the
  // display:none toggle natively.
  await radios.nth(2).click() // urlencoded (index 2)
  await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')
  await radios.nth(3).click() // raw (index 3)
  await expect(radios.nth(3)).toHaveAttribute('aria-checked', 'true')

  // Assert scroll + caret PRESERVED (no reset fired). Poll until the render settles.
  await expect
    .poll(async () =>
      page.getByLabel('Request body', { exact: true }).evaluate((el) => {
        const ta = el as HTMLTextAreaElement
        return {
          top: ta.scrollTop,
          left: ta.scrollLeft,
          selStart: ta.selectionStart,
          selEnd: ta.selectionEnd
        }
      })
    )
    .toEqual({
      top: before.top,
      left: before.left,
      selStart: before.selStart,
      selEnd: before.selEnd
    })
})
