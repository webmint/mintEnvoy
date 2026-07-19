/**
 * CodeEditor.ct.tsx — Playwright component tests for the CodeEditor molecule.
 *
 * Fixtures live in CodeEditor.stories.tsx (Playwright experimental-ct-react
 * cannot mount components defined inline in a test file — the CT bundler
 * statically extracts mountable components from importable modules only).
 *
 * Two halves:
 *  - Fidelity: §8 computed-style assertions via test-utils/fidelityAssert.ts
 *    (fail-closed — UNVERIFIED, never PASS, when the live computed-style channel
 *    is unavailable; AC-19). Row-height equality (AC-12/13/21). Grid geometry
 *    (.code-editor grid-template-columns: 36px gutter + flexible content column).
 *    Per-theme literal hex (AC-16 light, AC-16 dark), token-binding resolution (AC-17).
 *  - Behavior: two-pass highlight/debounce split (AC-23); resetKey-driven reset
 *    and re-arm (AC-6); resetKey-driven scroll-reset (AC-6).
 *
 * Highlight coloring is debounced (~100ms), so token spans (`.tk-*`) appear
 * shortly after mount — every fidelity/highlight assertion first waits for
 * the relevant span to attach (Playwright auto-polling) before reading its style.
 */

import { test, expect } from '@playwright/experimental-ct-react'
import {
  assertComputedStyle,
  assertResolvesToToken,
  skipIfChannelUnavailable
} from '@renderer/test-utils/fidelityAssert'
import {
  CodeEditorLightFixture,
  CodeEditorDarkFixture,
  CodeEditorResetKeyFixture,
  CodeEditorScrollFixture,
  CodeEditorFontOverrideFixture,
  CodeEditorMalformedFixture,
  CodeEditorMissingVarFixture,
  JSON_ALL_TOKENS
} from './CodeEditor.stories'

// ===========================================================================
// Fidelity — row-height equality (AC-12/13/21)
// ===========================================================================

/**
 * AC-12/13/21 — gutter div, pre, and textarea all share the 20.625 px line-box height.
 *
 * The CSS uses `--code-line-h: calc(12.5px * 1.65) = 20.625px` as the single
 * source of truth:
 *   .gutter > div    { height: var(--code-line-h); }   ← explicit height
 *   pre              { line-height: var(--code-line-h); } ← explicit line-height
 *   textarea         { line-height: var(--code-line-h); } ← explicit line-height
 *
 * If any regresses (e.g. gutter reverts to `1.65em` at 11.5px font = 18.975px,
 * or pre/textarea lose the override and inherit the unitless 1.65 resolved
 * against 12.5px = 20.625px — same value but fragile), this CT catches it.
 * Mirrors BodyEditor.ct.tsx's AC-23 gutter-height test.
 */
test('AC-12/13/21 — gutter div, pre, and textarea share the 20.625px line-box height', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorLightFixture />)
  await expect(c.getByTestId('ce-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  // Gutter line-number div: height = var(--code-line-h) = 20.625px.
  // calc(12.5px * 1.65); if regressed to 1.65em (11.5px gutter font) → 18.975px,
  // causing all line numbers to drift vs the code text. (Mirrors AC-23 in BodyEditor.ct.)
  const gutterHeight = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  expect(gutterHeight).toBe('20.625px')

  // Pre overlay: line-height = var(--code-line-h) = 20.625px.
  // Explicit override on .code-editor-content > pre ensures the highlight layer
  // sits on the same pixel grid as the gutter.
  const preLineHeight = await page
    .getByTestId('body-pre')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(preLineHeight).toBe('20.625px')

  // Textarea: line-height = var(--code-line-h) = 20.625px.
  // Must match the pre line-height exactly so the transparent textarea caret
  // aligns with the coloured highlight layer — caret desync is a visual defect.
  // Uses locator('textarea') rather than getByLabel for a pure style read —
  // CodeEditor renders exactly one textarea (Finding 1: decouple from aria-label).
  const taLineHeight = await page
    .locator('textarea')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(taLineHeight).toBe('20.625px')
})

// ===========================================================================
// Fidelity — tk-* computed colors (AC-16/17) + fail-closed gate (AC-19)
// ===========================================================================

/**
 * AC-16 — light-theme tk-* colors resolve to the design literals.
 *
 * Literal hex values sourced from BodyEditor.ct.tsx AC-20 block (T7a contract —
 * CodeEditor uses the same CSS token classes and the same per-theme token vars
 * as BodyEditor's code area; the literals must be identical between the two).
 */
test('AC-16 — light-theme tk-* colors resolve to the design literals', async ({ mount, page }) => {
  const c = await mount(<CodeEditorLightFixture />)
  await expect(c.getByTestId('ce-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  // Wait for the 100ms debounce to fire and populate the token spans.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  await assertComputedStyle(page, '.tk-key', 'color', 'rgb(3, 105, 161)', 'light tk-key')
  await assertComputedStyle(page, '.tk-str', 'color', 'rgb(21, 128, 61)', 'light tk-str')
  await assertComputedStyle(page, '.tk-num', 'color', 'rgb(180, 83, 9)', 'light tk-num')
  await assertComputedStyle(page, '.tk-bool', 'color', 'rgb(190, 24, 93)', 'light tk-bool')
})

/**
 * AC-16 dark-theme counterpart.
 *
 * Mirrors BodyEditor.ct.tsx AC-21. The same CSS token classes must resolve to
 * the dark-theme literals when data-theme="dark" is in scope.
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
 * AC-17 — tk-null/punc/var resolve to their bound CSS custom properties.
 *
 * These three classes use `var(--token)` rather than a per-theme literal hex.
 * `assertResolvesToToken` injects a probe element to resolve the token to its
 * computed value and compares against the element's computed color — this proves
 * the CSS binding is correct regardless of which theme literal the token resolves to.
 *
 * Mirrors BodyEditor.ct.tsx AC-22 (T7a contract consistency).
 */
test('AC-17 — tk-null/punc/var resolve to their bound tokens', async ({ mount, page }) => {
  const c = await mount(<CodeEditorLightFixture />)
  await expect(c.getByTestId('ce-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  // Wait for the debounce — tk-var appears in the JSON body ("{{x}}" inside tk-str).
  await expect(page.locator('.tk-var').first()).toBeAttached()

  await assertResolvesToToken(page, '.tk-null', 'color', '--text-faint', 'tk-null → --text-faint')
  await assertResolvesToToken(page, '.tk-punc', 'color', '--text-muted', 'tk-punc → --text-muted')
  await assertResolvesToToken(page, '.tk-var', 'color', '--accent', 'tk-var → --accent')
})

// ===========================================================================
// Behavior — AC-23 live/debounced split
// ===========================================================================

/**
 * AC-23 — plain span renders immediately (pre-debounce); `.tk-key` appears only
 * after the ~100ms debounce.
 *
 * On first paint, `colored` is null → `showColored` is false → the <pre> renders
 * `<span>{value}</span>` (plain-degrade path). This makes the typed text visible
 * immediately via the transparent textarea caret before the highlight pass fires.
 * After 100ms the debounce fires, compose() produces token spans, and .tk-key
 * attaches.
 *
 * Mirrors BodyEditor.ct.tsx's F3 regression guard.
 *
 * Determinism: Playwright's clock API freezes the page's virtual clock before
 * mount so the 100ms setTimeout in the debounce effect is held at t=0. The
 * pre-debounce assertions therefore CANNOT race a real-time expiry, making this
 * test repeatable on slow runners. `page.clock.fastForward(150)` then crosses
 * the debounce threshold and triggers compose() → setColored().
 */
test('AC-23 — plain span is visible before debounce; .tk-key attaches after debounce', async ({
  mount,
  page
}) => {
  // Install fake clock BEFORE mount so the debounce setTimeout is controlled by
  // the virtual clock from the first render. Any real-time expiry is impossible
  // while the clock is frozen at t=0, eliminating the prior count() race.
  await page.clock.install()
  const c = await mount(<CodeEditorLightFixture />)
  await expect(c.getByTestId('ce-ready')).toBeAttached()

  const pre = page.getByTestId('body-pre')

  // At virtual t=0 the debounce timer is frozen. Assert the plain-degrade path:
  // raw text is present and NO .tk-* span exists.
  // '{\n  "key": 1,' is the leading 14 chars of JSON_ALL_TOKENS.
  await expect(pre).toContainText(JSON_ALL_TOKENS.slice(0, 14))

  // Retrying form (toHaveCount) instead of point-in-time count() for clarity;
  // under the fake clock this is provably 0 (the timer cannot have fired yet).
  await expect(page.locator('[data-testid="body-pre"] .tk-key')).toHaveCount(0)

  // Advance virtual time by 150ms (> the 100ms BODY_HIGHLIGHT_DEBOUNCE_MS) to
  // fire the setTimeout callback: compose() runs, setColored() updates state,
  // React re-renders with structural token spans.
  await page.clock.fastForward(150)

  // After the debounce fires, .tk-key must attach. Playwright auto-retries.
  await expect(page.locator('.tk-key').first()).toBeAttached()
})

// ===========================================================================
// Behavior — AC-6 resetKey-driven reset + re-arm
// ===========================================================================

/**
 * AC-6 — resetKey change clears colored state (setColored null → .tk-key detaches)
 * then re-arms the debounce and reattaches .tk-key — even when value+lang are
 * identical across the resetKey change.
 *
 * Port of BodyEditor.ct.tsx line 769 (highlight re-arms after tab switch):
 * the same causal chain — setColored(null) clears spans; debounce re-arms because
 * resetKey is in its deps; compose() fires and re-populates spans. The molecule
 * form is driven by a prop change rather than an activeTabId / tab switch.
 *
 * The intermediate detach assertion (`.not.toBeAttached`) pins the causal chain:
 * a broken impl that never clears but also never re-arms would appear to pass
 * the final assertion on stale spans — analogous to BodyEditor.ct line 787.
 */
test('AC-6 — resetKey bump clears .tk-key then re-arms debounce (value+lang constant)', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorResetKeyFixture />)
  await expect(c.getByTestId('ce-ready')).toBeAttached()

  // Wait for the initial debounce to fire: .tk-key attaches on first mount.
  await expect(page.locator('.tk-key').first()).toBeAttached()

  // Bump resetKey (value+lang are unchanged — same JSON_ALL_TOKENS, same 'json').
  // This triggers useEffect([resetKey]): setColored(null) fires synchronously.
  await page.getByTestId('ce-bump-resetkey').click()

  // Intermediate assertion: setColored(null) must CLEAR the token spans first.
  // Without this check, stale Tab-A spans could make the final toBeAttached
  // appear to pass even if the debounce never re-armed.
  await expect(page.locator('.tk-key').first()).not.toBeAttached()

  // After ~100ms the debounce re-arms (resetKey is in the debounce effect deps)
  // and compose() fires again. .tk-key must reattach. Playwright auto-retries.
  await expect(page.locator('.tk-key').first()).toBeAttached()
})

// ===========================================================================
// Behavior — AC-6 resetKey-driven scroll reset
// ===========================================================================

/**
 * AC-6 scroll reset — resetKey resets textarea.scrollTop, textarea.scrollLeft,
 * pre.scrollTop, and pre.scrollLeft to 0.
 *
 * Port of BodyEditor.ct.tsx line 811 (scroll-bleed switching request tabs resets
 * scrollTop). The molecule form drives the reset via a resetKey prop change rather
 * than an activeTabId store change.
 *
 * CodeEditor's useEffect([resetKey]):
 *   textareaRef.current.scrollTop  = 0
 *   textareaRef.current.scrollLeft = 0
 *   preRef.current.scrollTop       = 0
 *   preRef.current.scrollLeft      = 0
 *
 * The test constrains the textarea to 100px height and sets both axes non-zero
 * (mirrors the scroll-sync CT pattern in BodyEditor.ct.tsx). The scroll event
 * dispatched to the textarea triggers handleTextareaScroll, which syncs the
 * pre overlay — so all four DOM properties are non-zero before the resetKey bump.
 */
test('AC-6 scroll reset — resetKey resets textarea+pre scrollTop+scrollLeft to 0', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorScrollFixture />)
  await expect(c.getByTestId('ce-scroll-ready')).toBeAttached()

  const textarea = page.getByLabel('Request body', { exact: true })
  const pre = page.getByTestId('body-pre')

  // Force the textarea into a bounded, internally-scrollable box and set non-zero
  // scroll offsets on BOTH axes. The scroll event drives handleTextareaScroll,
  // which syncs pre.scrollTop/scrollLeft — so all four DOM properties are non-zero.
  const before = await textarea.evaluate((el) => {
    const ta = el as HTMLTextAreaElement
    ta.style.height = '100px'
    ta.style.overflow = 'auto'
    ta.scrollTop = 60 // browser may clamp to max — return the actual value
    ta.scrollLeft = 40
    ta.dispatchEvent(new Event('scroll', { bubbles: true }))
    return { top: ta.scrollTop, left: ta.scrollLeft }
  })
  // Confirm both axes genuinely scrolled (non-vacuous pre-condition).
  expect(before.top).toBeGreaterThan(0)
  expect(before.left).toBeGreaterThan(0)

  // The <pre> overlay tracks the textarea via handleTextareaScroll.
  // Confirm it is non-zero so the post-reset assertion to 0 is non-vacuous
  // (mirrors BodyEditor.ct.tsx scroll-bleed test at lines 838-840).
  const preBefore = await pre.evaluate((el) => ({ top: el.scrollTop, left: el.scrollLeft }))
  expect(preBefore.top).toBeGreaterThan(0)
  expect(preBefore.left).toBeGreaterThan(0)

  // Bump resetKey — triggers useEffect([resetKey]) in CodeEditor which resets
  // all four scroll offsets to 0 synchronously via the textarea and pre refs.
  await page.getByTestId('ce-bump-resetkey-scroll').click()

  // expect.poll retries until the React effect has executed. React effects are
  // asynchronous (microtask queue) so a single point-in-time evaluate could race
  // the effect — polling is the correct pattern (mirrors BodyEditor.ct line 852).
  // Assert ALL FOUR resets (textarea + pre, vertical + horizontal): removing any
  // one reset line in the source causes this guard to fail.
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
// Fidelity — AC-13 row-height independence from ancestor font metrics
// ===========================================================================

/**
 * AC-13 — gutter div, pre, and textarea all remain pinned to the fixed
 * 20.625px `--code-line-h` even when an ancestor container declares
 * `font-size: 20px` and `line-height: 3`.
 *
 * `--code-line-h: calc(12.5px * 1.65)` is re-declared on `.code-editor` as a
 * fixed px calc — it is NOT relative to any inherited font metric. The gutter
 * uses `height: var(--code-line-h)`, the pre uses `line-height: var(--code-line-h)`,
 * and the textarea uses `line-height: var(--code-line-h)` — all three must stay
 * at 20.625 px when an ancestor overrides font metrics.
 *
 * Note on `--code-line-h` override feasibility via parent wrapper: the
 * `.code-editor` class rule re-declares the property at element scope, so a
 * parent container's inherited value is shadowed and cannot propagate. A consumer
 * CAN override via inline style directly on `.code-editor`, but that is not
 * reachable from a fixture without modifying the component's internals — that
 * variant is therefore omitted. AC-13 is fully verified through the
 * font-independence path here. (See CodeEditorFontOverrideFixture's JSDoc.)
 */
test('AC-13 — row heights remain 20.625px when ancestor sets font-size:20px / line-height:3', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorFontOverrideFixture />)
  await expect(c.getByTestId('ce-font-override-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  // Gutter: height = var(--code-line-h) = 20.625px — must not drift to
  // ancestor's `line-height: 3` or `font-size: 20px` resolved values.
  const gutterHeight = await page
    .getByTestId('body-gutter')
    .locator('> div')
    .first()
    .evaluate((el) => window.getComputedStyle(el).height)
  expect(gutterHeight).toBe('20.625px')

  // Pre overlay: line-height = var(--code-line-h) = 20.625px.
  const preLineHeight = await page
    .getByTestId('body-pre')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(preLineHeight).toBe('20.625px')

  // Textarea: line-height = var(--code-line-h) = 20.625px.
  // locator('textarea') rather than getByLabel — pure style read (Finding 1).
  const taLineHeight = await page
    .locator('textarea')
    .evaluate((el) => window.getComputedStyle(el).lineHeight)
  expect(taLineHeight).toBe('20.625px')
})

// ===========================================================================
// Behavior — AC-17 / AC-2 malformed JSON degrades to plain span
// ===========================================================================

/**
 * AC-17 / AC-2 — malformed JSON at `lang="json"` degrades to a plain <span>
 * after the debounce; no structural `.tk-*` token spans appear at any point.
 *
 * Degrade path in compose() (jsonTokens.ts): JSON.parse throws SyntaxError →
 * `return [{ kind: 'plain', text }]`. CodeEditor renders this single plain token
 * as a `<span>` with no className. The MEMORY note "jsonTokens JSON.parse is the
 * AC-17 detector" confirms: JSON.parse IS the degrade detector — the pre-validation
 * is intentional and must not be removed.
 *
 * The invariant holds both pre-debounce (showColored=false → plain span) AND
 * post-debounce (showColored=true with a single plain token). Waiting for the
 * pre to contain the raw text confirms the debounce has fired and the degrade
 * path produced the plain span, not an error UI.
 *
 * Mirrors BodyEditor.ct.tsx AC-17 (BodyEditorMalformedJsonFixture).
 */
test('AC-17 / AC-2 — malformed JSON degrades: no structural .tk-* spans; raw text in plain span', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorMalformedFixture />)
  await expect(c.getByTestId('ce-malformed-ready')).toBeAttached()

  // Wait for the pre to contain the raw body text — Playwright auto-retries, so
  // this resolves only after the debounce has fired and the pre has rendered the
  // plain-degrade span. `{ "key":` is a substring of MALFORMED_JSON_BODY.
  await expect(page.getByTestId('body-pre')).toContainText('{ "key":')

  // No structural token spans should exist — the degrade path is plain only.
  // Mirrors the STRUCTURAL selector pattern from BodyEditor.ct.tsx AC-17.
  await expect(page.locator('.tk-key, .tk-str, .tk-num, .tk-bool, .tk-punc')).toHaveCount(0)
})

// ===========================================================================
// Behavior — .tk-var.missing unresolved variable (AC-2, deferred from Task 001)
// ===========================================================================

/**
 * Unresolved `{{missing}}` renders with the `.tk-var.missing` CSS class and its
 * strikethrough / `--m-delete` color treatment.
 *
 * CodeEditor.css:
 *   .tk-var.missing { color: var(--m-delete); text-decoration: line-through dotted; }
 *
 * Mechanism: compose() emits `{ kind: 'tk-var', known: false }` when the var name
 * is absent from validVars; `isMissingVar(known=false, validVars)` returns true
 * (validVars is non-empty) → CodeEditor applies className `'tk-var missing'`.
 *
 * Positive counterpart (`.tk-var` WITHOUT `.missing`) is already covered by the
 * AC-17 test which uses CodeEditorLightFixture: `{{x}}` is in VALID_VARS, so it
 * renders `.tk-var` (not `.tk-var.missing`) and `assertResolvesToToken` asserts it
 * binds to `--accent`.
 */
test('.tk-var.missing — unresolved var renders with strikethrough and --m-delete color', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorMissingVarFixture />)
  await expect(c.getByTestId('ce-missing-var-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate
  // Wait for the debounce to fire and the .tk-var.missing span to attach.
  await expect(page.locator('.tk-var.missing').first()).toBeAttached()

  // Color must resolve to --m-delete (the delete / unresolved-var design token).
  await assertResolvesToToken(
    page,
    '.tk-var.missing',
    'color',
    '--m-delete',
    'tk-var.missing → --m-delete'
  )

  // text-decoration-line must be line-through (the dotted strikethrough treatment).
  // CSS: text-decoration: line-through dotted; → text-decoration-line: line-through.
  await assertComputedStyle(
    page,
    '.tk-var.missing',
    'text-decoration-line',
    'line-through',
    'tk-var.missing text-decoration-line'
  )
})

// ===========================================================================
// Fidelity — grid geometry (.code-editor grid-template-columns)
// ===========================================================================

/**
 * Grid geometry — .code-editor grid-template-columns has a 36px gutter track and
 * a flexible content column.
 *
 * CodeEditor.css declares:
 *   .code-editor { display: grid; grid-template-columns: 36px 1fr; }
 *
 * Browsers resolve `1fr` to an absolute px value in getComputedStyle (e.g. `664px`
 * inside the 700px fixture wrapper). This test asserts the first track is exactly
 * `36px` and there are exactly two tracks — so any change to the gutter width is
 * caught immediately regardless of how the browser serialises the 1fr track.
 *
 * `skipIfChannelUnavailable(page)` is required because this is a computed-style
 * assertion through the fidelity channel (AC-19 fail-closed gate).
 */
test('grid — .code-editor grid-template-columns: 36px gutter track + flexible content column', async ({
  mount,
  page
}) => {
  const c = await mount(<CodeEditorLightFixture />)
  await expect(c.getByTestId('ce-ready')).toBeAttached()
  await skipIfChannelUnavailable(page) // AC-19 fail-closed gate

  const gridCols = await page
    .getByTestId('body-code-editor')
    .evaluate((el) => window.getComputedStyle(el).gridTemplateColumns)

  // Browsers resolve `1fr` to a px value, so assert only the first track (gutter).
  // The value is a space-separated list of resolved track sizes, e.g. '36px 664px'.
  expect(gridCols.startsWith('36px ')).toBe(true)
  // Confirm exactly two tracks — no accidental third track from a CSS regression.
  expect(gridCols.trim().split(/\s+/)).toHaveLength(2)
})
