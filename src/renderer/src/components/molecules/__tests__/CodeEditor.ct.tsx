/**
 * CodeEditor.ct.tsx — Playwright component tests for the rebuilt CodeEditor
 * molecule (task 001: edit/preview conditional-mount toggle).
 *
 * Fixtures live in CodeEditor.stories.tsx (Playwright experimental-ct-react
 * cannot mount components defined inline in a test file — the CT bundler
 * statically extracts mountable components from importable modules only).
 *
 * New model these tests target (vs the 018-era debounced two-layer editor):
 *  - Conditional mount: editing=true mounts ONLY the <textarea>; editing=false
 *    mounts ONLY the highlighted <pre>. Never both (AC-10/11).
 *  - Synchronous tokenisation: a {value,lang}-snapshot useMemo gated to !editing.
 *    There is NO debounce and NO setColored — `.tk-*` spans are present on the
 *    first preview render (AC-17), so no page.clock / fastForward is needed.
 *  - Edit entry focuses the textarea on every path (click / Enter-Space / toggle)
 *    via a focus-on-mount effect keyed on `editing` (AC-18).
 *  - The textarea has NO data-testid by design — it is located by its accessible
 *    name, getByLabel('Request body', { exact: true }); the pre carries a longer
 *    aria-label so `exact: true` disambiguates the two.
 *
 * NOTE: the local Playwright CT harness cannot mount these molecule fixtures
 * (pre-existing break — see MEMORY `ct-organism-fixtures-cannot-mount-locally`).
 * These tests are verified statically + downstream live-verify; `test:ct` is
 * left UNVERIFIED for this task.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import type { Page } from 'playwright-core'
import {
  assertComputedStyle,
  assertResolvesToToken,
  skipIfChannelUnavailable
} from '@renderer/test-utils/fidelityAssert'
import {
  CodeEditorPreviewFixture,
  CodeEditorEditFixture,
  CodeEditorDarkFixture,
  CodeEditorToggleFixture,
  CodeEditorEmptyToggleFixture,
  CodeEditorScrollFixture,
  CodeEditorFontOverrideFixture,
  CodeEditorMalformedFixture,
  CodeEditorMissingVarFixture
} from './CodeEditor.stories'

// The structural token classes emitted by compose() for highlighted JSON.
const TK_SELECTORS = '.tk-key, .tk-str, .tk-num, .tk-bool, .tk-null, .tk-punc, .tk-var'

/**
 * Caret-CT precondition (G-5): caretPositionFromPoint maps a click coordinate
 * against the RENDERED font metrics. If JetBrains Mono has not loaded, the click
 * is measured against a fallback font and the predicted selectionStart is wrong
 * / flaky (MEMORY `fontsource-vite-relative-url`). Assert the mono face is loaded
 * before any caret-offset assertion.
 */
async function assertMonoFontLoaded(page: Page): Promise<void> {
  const loaded = await page.evaluate(async () => {
    await document.fonts.load('400 12.5px "JetBrains Mono"')
    await document.fonts.ready
    return document.fonts.check('400 12.5px "JetBrains Mono"')
  })
  expect(loaded, 'JetBrains Mono must be loaded for caret-metric accuracy').toBe(true)
}

// ===========================================================================
// Conditional mount — only-visible-layer testids (AC-10 / AC-11)
// ===========================================================================

/**
 * AC-10 / AC-11 — exactly one layer is in the DOM per `editing` state.
 *
 * editing=false → the highlighted <pre> (`body-pre`) is attached and the
 * textarea (`getByLabel('Request body')`) is NOT. editing=true → the reverse.
 * The static single-layer fixtures assert each end; the toggle test below
 * asserts the swap is atomic across a real edit entry.
 */
test('AC-10/11 — preview mounts pre only; edit mounts textarea only', async ({ mount, page }) => {
  const preview = await mount(<CodeEditorPreviewFixture />)
  await expect(preview.getByTestId('ce-preview-ready')).toBeAttached()
  await expect(page.getByTestId('body-pre')).toBeAttached()
  await expect(page.getByLabel('Request body', { exact: true })).not.toBeAttached()

  await preview.unmount()

  const edit = await mount(<CodeEditorEditFixture />)
  await expect(edit.getByTestId('ce-edit-ready')).toBeAttached()
  await expect(page.getByLabel('Request body', { exact: true })).toBeAttached()
  await expect(page.getByTestId('body-pre')).not.toBeAttached()
})

/**
 * AC-10/11 (swap) — clicking the preview swaps pre → textarea in one transition;
 * the pre detaches and the textarea attaches (never both mounted at once).
 */
test('AC-10/11 — clicking preview swaps the mounted layer (pre → textarea)', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorToggleFixture />)
  await expect(c.getByTestId('ce-toggle-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')
  const textarea = page.getByLabel('Request body', { exact: true })

  await expect(pre).toBeAttached()
  await expect(textarea).not.toBeAttached()

  await pre.click()

  await expect(textarea).toBeAttached()
  await expect(pre).not.toBeAttached()
})

// ===========================================================================
// Synchronous recolor — first-mount colored + recolor-in-preview (AC-17 / AC-14)
// ===========================================================================

/**
 * AC-17 — first-mount preview is colored SYNCHRONOUSLY.
 *
 * Replaces the deleted 018-era two-pass debounce test (G-1). There is no
 * setColored state and no ~100ms timer any more — compose() runs inside a
 * useMemo during the first preview render, so `.tk-key` is present immediately.
 * No page.clock / fastForward is used: `toBeAttached` resolves on first poll.
 */
test('AC-17 — preview is tokenised synchronously on first mount (no debounce)', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorPreviewFixture />)
  await expect(c.getByTestId('ce-preview-ready')).toBeAttached()

  // Colored immediately — no clock advance needed.
  await expect(page.locator('.tk-key').first()).toBeAttached()
})

/**
 * AC-14 — recolor is bound to the visible-layer transition, NOT to keystrokes.
 *
 * Behavioural framing (G-4): a CT cannot read the useMemo invocation count, so
 * we assert the observable evidence instead — while editing=true the <pre> is
 * unmounted so NO `.tk-*` span exists; switching back to preview re-mounts the
 * pre and the tokens reappear. A lang-cycle while in preview recolors without a
 * keystroke (the tokens remain present after the lang changes). We never claim
 * "composed exactly once" — that once-per-transition guarantee is a code-review
 * property the CT cannot prove.
 */
test('AC-14 — tokens absent while editing, present in preview; lang-cycle recolors', async ({
  mount,
  page
}) => {
  // Start in edit mode: the pre is unmounted, so no token spans exist.
  const c = await mount(<CodeEditorToggleFixture startEditing={true} />)
  await expect(c.getByTestId('ce-toggle-ready')).toBeAttached()
  await expect(page.locator(TK_SELECTORS)).toHaveCount(0)

  // Leave edit mode (blur the textarea) → preview re-mounts → tokens reappear.
  await page.getByLabel('Request body', { exact: true }).blur()
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Lang-cycle in preview (json → xml) recolors without any keystroke. Prove the
  // recolor is REAL, not a no-op: capture the pre's token-class signature (the
  // ordered join of every span className), cycle the lang, and assert the
  // signature CHANGES to a still-tokenised value.
  //
  // `preTokenSignature` is a FUNCTION that RE-QUERIES the DOM on every call.
  // `expect.poll(preTokenSignature)` therefore re-evaluates it each poll tick
  // until the matcher passes — it never compares a stale snapshot. Passing the
  // resolved string instead would make the poll a constant and prove nothing.
  const preTokenSignature = (): Promise<string> =>
    page
      .getByTestId('body-pre')
      .evaluate((el) => Array.from(el.querySelectorAll('span'), (s) => s.className).join('|'))

  const jsonSignature = await preTokenSignature()
  expect(jsonSignature).toContain('tk-key') // json genuinely highlights object keys

  await page.getByTestId('ce-cycle-lang').click()

  // json→xml recolor must CHANGE the token composition. A tokeniser that ignored
  // the lang change would leave the signature identical, so this poll would time
  // out and fail (it re-queries the live DOM each tick, not the captured string).
  await expect.poll(preTokenSignature).not.toBe(jsonSignature)

  // Guard against a blanked/crashed pre: `.not.toBe(jsonSignature)` alone would
  // also pass if the pre rendered empty, so assert the post-cycle layer is still
  // tokenised (≥1 token span) AND its signature is non-empty.
  await expect(page.locator(TK_SELECTORS).first()).toBeAttached()
  const xmlSignature = await preTokenSignature()
  expect(xmlSignature.length).toBeGreaterThan(0)
})

// ===========================================================================
// Caret-at-click — enter edit with caret at clicked offset (AC-12 / AC-13)
// ===========================================================================

/**
 * AC-12 — clicking a preview character enters edit mode with the caret at the
 * clicked offset. AC-13 — clicking past end-of-line / below the text clamps the
 * caret to the nearest character (≤ value.length).
 *
 * Precondition (G-5): JetBrains Mono must be loaded, else caretPositionFromPoint
 * maps against a fallback font and the offset is calibrated wrong.
 */
test('AC-12/13 — click preview places caret at clicked offset; past-end clamps', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorToggleFixture />)
  await expect(c.getByTestId('ce-toggle-ready')).toBeAttached()
  await assertMonoFontLoaded(page)

  const pre = page.getByTestId('body-pre')
  const box = await pre.boundingBox()
  expect(box).not.toBeNull()

  // Click a point a few characters into the first line (not the very start).
  await page.mouse.click(box!.x + 40, box!.y + 6)

  const textarea = page.getByLabel('Request body', { exact: true })
  await expect(textarea).toBeFocused()

  // AC-12: caret landed at a non-zero, in-range offset near the click.
  const midOffset = await textarea.evaluate((el) => (el as HTMLTextAreaElement).selectionStart)
  const len = await textarea.evaluate((el) => (el as HTMLTextAreaElement).value.length)
  expect(midOffset).toBeGreaterThan(0)
  expect(midOffset).toBeLessThanOrEqual(len)

  // Return to preview and click far past the end of the text (bottom-right of
  // the box). AC-13: the offset clamps to value.length, never beyond.
  await textarea.blur()
  await expect(pre).toBeAttached()
  const box2 = await pre.boundingBox()
  await page.mouse.click(box2!.x + box2!.width - 4, box2!.y + box2!.height - 4)

  const clampedOffset = await page
    .getByLabel('Request body', { exact: true })
    .evaluate((el) => (el as HTMLTextAreaElement).selectionStart)
  expect(clampedOffset).toBeLessThanOrEqual(len)
})

/**
 * Whole-area click-to-edit (empty body) — with an empty body the preview `<pre>`
 * collapses to ~one line at the top of a taller editor, leaving dead space below.
 * Clicking that dead space (the `.code-editor` container, well below the `<pre>`)
 * must enter edit mode: the preview onClick is hoisted from the `<pre>` to the
 * container, so a short/empty body is fully clickable rather than a dead zone.
 * Guards the empty-body regression (clicking an empty editor did nothing).
 */
test('empty body — clicking the code area below the near-empty pre enters edit', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorEmptyToggleFixture />)
  await expect(c.getByTestId('ce-empty-ready')).toBeAttached()

  const container = page.getByTestId('body-code-editor')
  const textarea = page.getByLabel('Request body', { exact: true })

  // Preview default: pre mounted, textarea not.
  await expect(page.getByTestId('body-pre')).toBeAttached()
  await expect(textarea).not.toBeAttached()

  // Click the dead zone near the bottom of the container, well below the ~1-line pre.
  const box = await container.boundingBox()
  expect(box).not.toBeNull()
  await page.mouse.click(box!.x + box!.width / 2, box!.y + box!.height - 8)

  // The whole-area click-to-edit entered edit → the textarea mounts and focuses.
  await expect(textarea).toBeAttached()
  await expect(textarea).toBeFocused()
})

// ===========================================================================
// Keyboard entry focus — Enter on the focused preview focuses the textarea (AC-18)
// ===========================================================================

/**
 * AC-18 — with the preview <pre> focused, pressing Enter enters edit mode and
 * the textarea receives focus.
 *
 * Assertion-formula constraint (G-7/G-8): locate the textarea by its accessible
 * name and assert `toBeFocused()` — NEVER `document.activeElement ===
 * textareaRef.current` (an internal React ref inaccessible from the CT context).
 */
test('AC-18 — Enter on the focused preview focuses the textarea', async ({ mount, page }) => {
  const c = await mount(<CodeEditorToggleFixture />)
  await expect(c.getByTestId('ce-toggle-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')
  await pre.focus()
  await expect(pre).toBeFocused()

  await pre.press('Enter')

  await expect(page.getByLabel('Request body', { exact: true })).toBeFocused()
})

// ===========================================================================
// Line-box split — edit-state read + preview-state read both = --code-line-h (AC-9)
// ===========================================================================

/**
 * AC-9 (preview read) — the gutter row and the <pre> line share the 20.625px
 * `--code-line-h` line-box. Under conditional mount the textarea is NOT present
 * in preview, so its row height is verified separately by the edit-state read.
 *
 * --code-line-h: calc(12.5px * 1.65) = 20.625px is the single source of truth:
 *   .gutter > div { height: var(--code-line-h); }
 *   pre           { line-height: var(--code-line-h); }
 */
test('AC-9 (preview) — gutter row and pre share the 20.625px line-box', async ({ mount, page }) => {
  const c = await mount(<CodeEditorPreviewFixture />)
  await expect(c.getByTestId('ce-preview-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  const gutterHeight = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  expect(gutterHeight).toBe('20.625px')

  const preLineHeight = await page
    .getByTestId('body-pre')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(preLineHeight).toBe('20.625px')
})

/**
 * AC-9 (edit read) — the textarea row shares the same 20.625px `--code-line-h`
 * line-box, so the caret sits on the identical pixel grid as the preview it
 * replaced. Read from the edit-state fixture (editing=true) where the textarea
 * is the mounted layer.
 */
test('AC-9 (edit) — textarea shares the 20.625px line-box', async ({ mount, page }) => {
  const c = await mount(<CodeEditorEditFixture />)
  await expect(c.getByTestId('ce-edit-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  const taLineHeight = await page
    .getByLabel('Request body', { exact: true })
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(taLineHeight).toBe('20.625px')
})

// ===========================================================================
// AC-15 — textarea horizontal-scroll / no-soft-wrap contract
// ===========================================================================

/**
 * AC-15 — the edit textarea disables spellcheck, disables user-resize, and uses
 * `white-space: pre` (horizontal scroll, no soft-wrap). Guards against a
 * regression to `pre-wrap` (which would soft-wrap long lines) or a native resize
 * handle appearing.
 */
test('AC-15 — textarea: spellcheck off, resize none, white-space pre', async ({ mount, page }) => {
  const c = await mount(<CodeEditorEditFixture />)
  await expect(c.getByTestId('ce-edit-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  const attrs = await page.getByLabel('Request body', { exact: true }).evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    const cs = window.getComputedStyle(ta)
    return { spellcheck: ta.spellcheck, resize: cs.resize, whiteSpace: cs.whiteSpace }
  })
  expect(attrs.spellcheck).toBe(false)
  expect(attrs.resize).toBe('none')
  expect(attrs.whiteSpace).toBe('pre')
})

/**
 * Textarea grows to its full content height — the edit textarea sets
 * `rows={lineCount}` so it is exactly as tall as its content, like the preview
 * <pre>. Guards the regression where the textarea kept its intrinsic 2-row height
 * and clipped any line past the second (e.g. a closing brace on line 3 was hidden
 * in edit mode). JSON_ALL_TOKENS is 6 lines, so rows must be 6 and the content is
 * not vertically clipped within the textarea.
 */
test('edit — textarea rows match the line count so no line is clipped', async ({ mount, page }) => {
  const c = await mount(<CodeEditorEditFixture />)
  await expect(c.getByTestId('ce-edit-ready')).toBeAttached()

  const metrics = await page.getByLabel('Request body', { exact: true }).evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    return {
      rows: ta.rows,
      lineCount: ta.value.split('\n').length,
      clipped: ta.scrollHeight > ta.clientHeight + 1
    }
  })
  // JSON_ALL_TOKENS has 6 lines; rows tracks that so the box fits every line.
  expect(metrics.rows).toBe(metrics.lineCount)
  expect(metrics.rows).toBe(6)
  expect(metrics.clipped).toBe(false)
})

// ===========================================================================
// AC-19 — gutter tracks the visible layer within one scroll container
// ===========================================================================

/**
 * AC-19 — the gutter is present and its rows align to the visible layer's line
 * box in BOTH states. One gutter row per source line; each row height equals the
 * visible layer's line-height (20.625px), so the numbers stay row-aligned with
 * the code within the single `.code-editor` grid.
 */
test('AC-19 — gutter row count and height track the visible layer (preview)', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorPreviewFixture />)
  await expect(c.getByTestId('ce-preview-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  // JSON_ALL_TOKENS has 6 lines → 6 gutter rows.
  await expect(page.getByTestId('body-gutter').locator('> div')).toHaveCount(6)

  const rowHeight = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  const preLineHeight = await page
    .getByTestId('body-pre')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(rowHeight).toBe(preLineHeight)
})

/**
 * AC-19 (edit mode) — the gutter is rendered OUTSIDE the editing conditional, so
 * it tracks the visible layer in edit mode too: one row per source line, each row
 * height equal to the textarea's line box (20.625px). Guards against the gutter
 * being accidentally coupled to the <pre> and vanishing / mis-sizing when the
 * textarea is the mounted layer.
 */
test('AC-19 — gutter row count and height track the textarea (edit mode)', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorEditFixture />)
  await expect(c.getByTestId('ce-edit-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  // JSON_ALL_TOKENS has 6 lines → 6 gutter rows, same as preview.
  await expect(page.getByTestId('body-gutter').locator('> div')).toHaveCount(6)

  const rowHeight = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  const taLineHeight = await page
    .getByLabel('Request body', { exact: true })
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(rowHeight).toBe(taLineHeight)
})

// ===========================================================================
// Fidelity — tk-* computed colors (AC-16) + fail-closed gate (AC-19)
// ===========================================================================

/**
 * AC-16 — light-theme tk-* colors resolve to the design literals. Tokens are
 * present synchronously (no debounce), so the wait is a plain `toBeAttached`.
 */
test('AC-16 — light-theme tk-* colors resolve to the design literals', async ({ mount, page }) => {
  const c = await mount(<CodeEditorPreviewFixture />)
  await expect(c.getByTestId('ce-preview-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  await expect(page.locator('.tk-key').first()).toBeAttached()

  await assertComputedStyle(page, '.tk-key', 'color', 'rgb(3, 105, 161)', 'light tk-key')
  await assertComputedStyle(page, '.tk-str', 'color', 'rgb(21, 128, 61)', 'light tk-str')
  await assertComputedStyle(page, '.tk-num', 'color', 'rgb(180, 83, 9)', 'light tk-num')
  await assertComputedStyle(page, '.tk-bool', 'color', 'rgb(190, 24, 93)', 'light tk-bool')
})

/**
 * AC-16 dark-theme counterpart — the same CSS token classes resolve to the
 * dark-theme literals when data-theme="dark" is in scope.
 */
test('AC-16 dark — dark-theme tk-* colors resolve to the design literals', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorDarkFixture />)
  await expect(c.getByTestId('ce-dark-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  await expect(page.locator('.tk-key').first()).toBeAttached()

  await assertComputedStyle(page, '.tk-key', 'color', 'rgb(125, 211, 252)', 'dark tk-key')
  await assertComputedStyle(page, '.tk-str', 'color', 'rgb(134, 239, 172)', 'dark tk-str')
  await assertComputedStyle(page, '.tk-num', 'color', 'rgb(252, 211, 77)', 'dark tk-num')
  await assertComputedStyle(page, '.tk-bool', 'color', 'rgb(240, 171, 252)', 'dark tk-bool')
})

/**
 * AC-17 — tk-null/punc/var resolve to their bound CSS custom properties (rather
 * than a per-theme literal hex), proving the CSS binding is correct regardless
 * of which theme literal each token resolves to.
 */
test('AC-17 — tk-null/punc/var resolve to their bound tokens', async ({ mount, page }) => {
  const c = await mount(<CodeEditorPreviewFixture />)
  await expect(c.getByTestId('ce-preview-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  await expect(page.locator('.tk-var').first()).toBeAttached()

  await assertResolvesToToken(page, '.tk-null', 'color', '--text-faint', 'tk-null → --text-faint')
  await assertResolvesToToken(page, '.tk-punc', 'color', '--text-muted', 'tk-punc → --text-muted')
  await assertResolvesToToken(page, '.tk-var', 'color', '--accent', 'tk-var → --accent')
})

// ===========================================================================
// AC-13 — row height is independent of ancestor font metrics
// ===========================================================================

/**
 * AC-13 — the gutter row and the <pre> stay pinned to the fixed 20.625px
 * `--code-line-h` even when an ancestor declares `font-size: 20px` and
 * `line-height: 3`. `--code-line-h` is re-declared on `.code-editor` as a fixed
 * px calc, so an inherited font metric cannot propagate into the line box.
 */
test('AC-13 — row heights remain 20.625px under ancestor font-size:20px / line-height:3', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorFontOverrideFixture />)
  await expect(c.getByTestId('ce-font-override-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  const gutterHeight = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  expect(gutterHeight).toBe('20.625px')

  const preLineHeight = await page
    .getByTestId('body-pre')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(preLineHeight).toBe('20.625px')
})

// ===========================================================================
// AC-4 — malformed JSON degrades to a single plain span (synchronous)
// ===========================================================================

/**
 * AC-4 — malformed JSON at `lang="json"` degrades to a plain <span> IMMEDIATELY
 * on mount; no structural `.tk-*` token span ever appears.
 *
 * Degrade path in compose() (jsonTokens.ts): JSON.parse throws SyntaxError →
 * `return [{ kind: 'plain', text }]`. Under the synchronous useMemo model the
 * plain span is present on first render — there is NO debounce to wait out (this
 * is the key behavioural difference from the deleted 018-era CT). MEMORY
 * `jsontokens-jsonparse-is-ac17-detector`: JSON.parse IS the degrade detector.
 */
test('AC-4 — malformed JSON degrades to a plain span synchronously; no .tk-* spans', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorMalformedFixture />)
  await expect(c.getByTestId('ce-malformed-ready')).toBeAttached()

  // Raw text is in the pre from first render (no debounce). `{ "key":` is a
  // substring of MALFORMED_JSON_BODY.
  await expect(page.getByTestId('body-pre')).toContainText('{ "key":')

  // The degrade path is plain-only — no structural token spans at any point.
  await expect(page.locator(TK_SELECTORS)).toHaveCount(0)
})

// ===========================================================================
// .tk-var.missing — unresolved variable treatment
// ===========================================================================

/**
 * Unresolved `{{missing}}` renders with the `.tk-var.missing` class and its
 * strikethrough / `--m-delete` color treatment. compose() emits
 * `{ kind: 'tk-var', known: false }`; isMissingVar(known=false, non-empty vars)
 * → true → CodeEditor applies `'tk-var missing'`.
 */
test('.tk-var.missing — unresolved var renders with strikethrough and --m-delete color', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorMissingVarFixture />)
  await expect(c.getByTestId('ce-missing-var-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  await expect(page.locator('.tk-var.missing').first()).toBeAttached()

  await assertResolvesToToken(
    page,
    '.tk-var.missing',
    'color',
    '--m-delete',
    'tk-var.missing → --m-delete'
  )
  await assertComputedStyle(
    page,
    '.tk-var.missing',
    'text-decoration-line',
    'line-through',
    'tk-var.missing text-decoration-line'
  )
})

// ===========================================================================
// Grid geometry — .code-editor grid-template-columns
// ===========================================================================

/**
 * Grid geometry — `.code-editor` has a 36px gutter track and a flexible content
 * column. Browsers resolve `1fr` to px in getComputedStyle, so we assert the
 * first track is exactly 36px and there are exactly two tracks.
 */
test('grid — .code-editor grid-template-columns: 36px gutter track + flexible content column', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorPreviewFixture />)
  await expect(c.getByTestId('ce-preview-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  const gridCols = await page
    .getByTestId('body-code-editor')
    .evaluate((el) => window.getComputedStyle(el).gridTemplateColumns)

  expect(gridCols.startsWith('36px ')).toBe(true)
  expect(gridCols.trim().split(/\s+/)).toHaveLength(2)
})

// ===========================================================================
// Scroll reset — resetKey resets the visible layer's scroll (AC-6, single-layer)
// ===========================================================================

/**
 * AC-6 scroll reset (single-layer rewrite) — the old 018-era test drove
 * `handleTextareaScroll` on BOTH pre + textarea from one mount; that handler is
 * deleted and only one layer mounts now. Rewritten for the conditional-mount
 * model: in preview the <pre> is the single scrollable layer. After scrolling it
 * on both axes, a resetKey bump fires `useEffect([resetKey])` in CodeEditor,
 * which resets the mounted layer's scrollTop/scrollLeft to 0.
 */
test('AC-6 — resetKey resets the preview pre scrollTop+scrollLeft to 0', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorScrollFixture />)
  await expect(c.getByTestId('ce-scroll-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')

  // Scroll the pre on both axes; confirm non-zero (non-vacuous pre-condition).
  const before = await pre.evaluate((el) => {
    el.scrollTop = 60
    el.scrollLeft = 40
    return { top: el.scrollTop, left: el.scrollLeft }
  })
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // Bump resetKey → useEffect([resetKey]) resets the mounted pre's scroll to 0.
  await page.getByTestId('ce-bump-resetkey-scroll').click()

  // Poll: React effects run on the microtask queue, so a point-in-time read
  // could race the effect.
  await expect
    .poll(async () => pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft })))
    .toEqual({ top: 0, left: 0 })
})
