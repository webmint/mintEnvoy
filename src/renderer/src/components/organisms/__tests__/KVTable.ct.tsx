/**
 * KVTable.ct.tsx — Playwright Component Tests for the KVTable organism.
 *
 * These tests run in a real Chromium browser via @playwright/experimental-ct-react,
 * covering concerns jsdom cannot exercise:
 *
 *   - Auto-promote: typing in the virtual row's key/value creates a real row.
 *   - Variable highlighting: {{var}} tokens render .var; absent tokens get .var.missing
 *     only when validVars.size > 0 (the ∅-default path never produces .missing).
 *   - Delete + focus: removing a row moves keyboard focus to an adjacent input.
 *   - Checkbox: clicking a real row's checkbox flips .disabled on the row.
 *   - Paste: multi-line paste into a key/value cell collapses newlines to spaces.
 *   - External mutation: replacing the store's rows array re-renders the grid.
 *   - Field independence: editing params does not mutate the headers field.
 *   - Computed-style fidelity: var(--token) resolves; grid tracks, heights, and
 *     font metrics match the CSS specification.
 *
 * Fixture components are imported from KVTable.stories.tsx — Playwright
 * experimental-ct-react requires that mounted components be defined in a
 * separate file from the test file.
 *
 * Styling context:
 *   - tokens.css is already loaded globally via playwright/index.tsx.
 *   - data-theme="dark" is set on documentElement in beforeEach so that
 *     dark-theme custom properties apply even to elements mounted outside a
 *     fixture's wrapper div.
 */

import { test, expect } from '@playwright/experimental-ct-react'

// Non-component imports must be in a SEPARATE statement from fixture components.
// Playwright CT's Babel transform only replaces an import's specifiers with
// importRef objects when EVERY specifier in that statement is used as a JSX element.
// Mixing constants and component imports in one statement prevents the transform
// and causes a runtime "cannot be mounted" error.

import {
  KVTableStoreResetFixture,
  KVTableEmptyParamsFixture,
  KVTableOneRowParamsFixture,
  KVTableThreeRowsFixture,
  KVTableVarNoValidVarsFixture,
  KVTableVarWithValidVarsFixture,
  KVTableDescVarFixture,
  KVTableExternalMutationFixture,
  KVTableDisabledRowFixture,
  KVTableTwoFieldsFixture,
  KVTablePaddedTokenFixture,
  KVTableValueCellFixture,
  KVTableControlledFixture,
  KVTableControlledVarFixture
} from './KVTable.stories'

// ---------------------------------------------------------------------------
// Setup — reset store state and apply full styling context before every test
// ---------------------------------------------------------------------------

/**
 * Before each test:
 * 1. Mount KVTableStoreResetFixture, wait for its readiness signal, then unmount.
 *    This writes a clean state to the singleton tabsStore so no test inherits
 *    stale params/headers from a previous test.
 * 2. Set data-theme='dark' on <html> so dark-theme CSS custom properties resolve
 *    for elements mounted outside a fixture's explicit wrapper div.
 */
test.beforeEach(async ({ mount, page }) => {
  const resetFixture = await mount(<KVTableStoreResetFixture />)
  await page.waitForSelector('[data-testid="ct-kv-store-reset-done"]', { state: 'attached' })
  await resetFixture.unmount()

  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'dark')
  })
})

// ---------------------------------------------------------------------------
// 1. Auto-promote / no-promote (AC-8, AC-26)
// ---------------------------------------------------------------------------

test.describe('KVTable — auto-promote', () => {
  /**
   * Typing any character into the virtual trailing row's KEY input must promote
   * it: exactly one new real (.kv-row:not(.empty)) row is appended.
   */
  test('should create exactly one new real row when typing in the virtual KEY input (AC-8)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableEmptyParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(0)

    const virtualKeyInput = page.locator('.kv-row.empty .kv-cell.key .kv-input-wrap input')
    await virtualKeyInput.fill('a')

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)
  })

  /**
   * Typing any character into the virtual trailing row's VALUE input must also
   * promote it into a real row.
   */
  test('should create exactly one new real row when typing in the virtual VALUE input (AC-26)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableEmptyParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(0)

    const virtualValueInput = page.locator('.kv-row.empty .kv-cell.value .kv-input-wrap input')
    await virtualValueInput.fill('v')

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)
  })

  /**
   * The virtual trailing row's checkbox must have the `disabled` attribute.
   * Force-clicking it (bypassing the actionability check) must not add a row.
   */
  test('should have disabled checkbox on virtual row — clicking it adds no row (AC-26)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableEmptyParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const virtualCheckbox = page.locator('.kv-row.empty input[type="checkbox"]')
    await expect(virtualCheckbox).toBeDisabled()

    // Force-click bypasses the actionability gate; no row should be added.
    await virtualCheckbox.click({ force: true })
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(0)
  })

  /**
   * The virtual trailing row's description input must have the `readonly` attribute.
   * Keyboard-typing into it (after clicking to focus) must not add a row.
   */
  test('should have readOnly description on virtual row — typing adds no row (AC-26)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableEmptyParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const virtualDescInput = page.locator('.kv-row.empty input[readonly]')
    await expect(virtualDescInput).toHaveAttribute('readonly')

    // Click to focus then keyboard-type; readOnly inputs reject keyboard input natively.
    await virtualDescInput.click({ force: true })
    await page.keyboard.type('hello')
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(0)
  })
})

// ---------------------------------------------------------------------------
// 2. Variable highlighting — both validVars paths (AC-19 / AC-20, R11)
// ---------------------------------------------------------------------------

test.describe('KVTable — variable highlighting', () => {
  /**
   * AC-20 ∅-default path: mount WITHOUT the validVars prop (defaults to envVars()
   * which is an empty Set in v1).
   *   - {{x}} in the key cell renders a span.var.
   *   - ZERO span.var.missing elements exist anywhere in the grid.
   *
   * This is the load-bearing regression guard: a future change that starts
   * passing validVars with non-zero size would silently produce .missing on
   * every previously-neutral token — this test catches that.
   */
  test('should render span.var for {{x}} key AND zero span.var.missing when no validVars prop (AC-20)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableVarNoValidVarsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    // Wait for the real row to be present (the row with {{x}} key)
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // span.var must be present (token recognised)
    await expect(page.locator('.kv-highlight .var')).toHaveCount(1)

    // Explicitly assert ZERO .var.missing — the critical degradation guard
    await expect(page.locator('.kv-highlight .var.missing')).toHaveCount(0)
  })

  /**
   * AC-19 injected validVars path: mount WITH validVars={new Set(['x'])}.
   *   - {{x}} (known) → span.var present, no .missing.
   *   - {{y}} (absent from validVars) → span.var.missing present.
   */
  test('should mark known {{x}} as span.var and unknown {{y}} as span.var.missing when validVars injected (AC-19)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableVarWithValidVarsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    // Both real rows must be rendered
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(2)

    // {{x}} row: has .var, must NOT have .missing
    const xRow = page.locator('.kv-row:not(.empty)').first()
    await expect(xRow.locator('.kv-highlight .var')).toHaveCount(1)
    await expect(xRow.locator('.kv-highlight .var.missing')).toHaveCount(0)

    // {{y}} row: has .var.missing
    const yRow = page.locator('.kv-row:not(.empty)').nth(1)
    await expect(yRow.locator('.kv-highlight .var.missing')).toHaveCount(1)
  })

  /**
   * R10/AC-11: description cells are NOT tokenised.
   * A row with `{{x}}` in the description field must have ZERO .var spans in
   * its description cell, even when validVars is non-empty and active.
   */
  test('should NOT render span.var in the description cell — description is not tokenised (AC-11)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableDescVarFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // Description is a plain input with no .kv-input-wrap overlay — no .var spans
    // The description cell is the third .kv-cell (no key/value class on it)
    const descCell = page.locator('.kv-row:not(.empty) .kv-cell:not(.key):not(.value)')
    await expect(descCell.locator('.var')).toHaveCount(0)
  })
})

// ---------------------------------------------------------------------------
// 3. Delete + focus recovery (AC-13, AC-18)
// ---------------------------------------------------------------------------

test.describe('KVTable — delete and focus', () => {
  /**
   * Deleting the sole real row must:
   *   - Remove the real row (only virtual remains).
   *   - Leave focus inside the .kv grid on an INPUT element, NOT on document.body.
   */
  test('should remove the only real row on delete and keep focus on an input inside .kv (AC-13, AC-18)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // Hover to reveal the .kv-actions delete button (reveal-on-hover), then click it
    const realRow = page.locator('.kv-row:not(.empty)').first()
    await realRow.hover()

    // Assert delete control is a real <button> element (AC-14)
    expect(await realRow.locator('[aria-label^="Delete row"]').evaluate((el) => el.tagName)).toBe(
      'BUTTON'
    )

    await realRow.locator('[aria-label^="Delete row"]').click()

    // Real row is gone
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(0)

    // Focus must be on an INPUT inside .kv (focus recovery via useLayoutEffect)
    const activeTag = await page.evaluate(() => document.activeElement?.tagName ?? '')
    expect(activeTag).toBe('INPUT')

    const isInsideKV = await page.evaluate(
      () => document.querySelector('.kv')?.contains(document.activeElement) ?? false
    )
    expect(isInsideKV).toBe(true)
  })

  /**
   * WCAG 2.1.1 — the delete button is display:none by default and revealed on
   * hover; a fix added `.kv-row:focus-within .kv-actions{display:flex}` so it is
   * ALSO revealed when keyboard focus lands on a row input, making it reachable
   * without a pointer. This CT exercises the FOCUS path (not hover): focusing a
   * cell input must make the row's delete button visible.
   */
  test('delete button is revealed on keyboard focus-within (no hover) — WCAG 2.1.1', async ({
    mount,
    page
  }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const realRow = page.locator('.kv-row:not(.empty)').first()
    const del = realRow.locator('[aria-label^="Delete row"]')

    // Baseline: not hovered, not focused → delete button hidden.
    await expect(del).toBeHidden()

    // Focus a cell input via keyboard-equivalent .focus() — no hover.
    await realRow.locator('input').first().focus()

    // focus-within must now reveal the delete button.
    await expect(del).toBeVisible()
  })

  /**
   * Deleting the MIDDLE row of three must move focus to an adjacent row's cell
   * (not to document.body and not to a row that no longer exists).
   */
  test('should focus an adjacent row input after deleting the middle of three rows (AC-18)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableThreeRowsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(3)

    const middleRow = page.locator('.kv-row:not(.empty)').nth(1)
    await middleRow.hover() // reveal the .kv-actions delete button (reveal-on-hover)
    await middleRow.locator('[aria-label^="Delete row"]').click()

    // Two real rows remain
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(2)

    // Focus is on an input, not on body
    const activeTag = await page.evaluate(() => document.activeElement?.tagName ?? '')
    expect(activeTag).toBe('INPUT')

    const isInsideKV = await page.evaluate(
      () => document.querySelector('.kv')?.contains(document.activeElement) ?? false
    )
    expect(isInsideKV).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// 4. Checkbox toggle (AC-14, AC-16, AC-17)
// ---------------------------------------------------------------------------

test.describe('KVTable — checkbox', () => {
  /**
   * Clicking an enabled real row's checkbox must:
   *   - Add the .disabled CSS class to that row (opacity 0.55 guard).
   *   - The store's row.enabled flips — observable via the .disabled class.
   */
  test('should add .disabled class to a real row when its checkbox is clicked (AC-14, AC-16, AC-17)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const realRow = page.locator('.kv-row:not(.empty)').first()

    // Initially enabled — no .disabled class
    await expect(realRow).not.toHaveClass(/disabled/)

    const checkbox = realRow.locator('input[type="checkbox"]')
    await checkbox.click()

    // After toggle: row gets .disabled
    await expect(realRow).toHaveClass(/disabled/)
  })
})

// ---------------------------------------------------------------------------
// 5. Multi-line paste collapsing (AC-23, AC-24 — R9)
// ---------------------------------------------------------------------------

test.describe('KVTable — paste', () => {
  /**
   * Pasting text with newlines into the virtual KEY input must:
   *   - Create exactly ONE new real row (no row-per-line explosion).
   *   - The new row's key must not contain a literal newline character.
   *
   * Implementation: dispatch a ClipboardEvent with clipboardData so the
   * component's handlePaste intercepts and collapses the newlines to spaces.
   */
  test('should collapse multi-line paste in the virtual KEY input into a single row with no newlines (AC-23, AC-24)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableEmptyParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(0)

    // Dispatch a real ClipboardEvent with multi-line text in the browser context
    await page.evaluate(() => {
      const input = document.querySelector(
        '.kv-row.empty .kv-cell.key .kv-input-wrap input'
      ) as HTMLInputElement | null
      if (!input) throw new Error('Virtual key input not found')
      input.focus()
      const dt = new DataTransfer()
      dt.setData('text', 'a\nb\nc')
      const event = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true })
      input.dispatchEvent(event)
    })

    // Exactly one new real row — no row-per-line explosion
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // The new row's key must not contain a newline
    const keyValue = await page
      .locator('.kv-row:not(.empty) .kv-cell.key .kv-input-wrap input')
      .inputValue()
    expect(keyValue).toBe('a b c')
  })
})

// ---------------------------------------------------------------------------
// 5b. Tab traversal (AC-25)
// ---------------------------------------------------------------------------

test.describe('KVTable — tab traversal', () => {
  /**
   * Tab moves focus through the interactive cells of a real row in order:
   * checkbox → key → value → description → next row's checkbox.
   * The delete <button> carries no tabindex, so Tab does not land on it — even
   * though `.kv-row:focus-within .kv-actions` now reveals it (display:flex) while
   * a row input is focused, it is revealed-but-not-tabbable, so the Tab order is
   * unchanged.
   */
  test('should move focus checkbox → key → value → description → next row on Tab (AC-25)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    // Focus the real row's checkbox
    await page.locator('.kv-row:not(.empty) input[type="checkbox"]').first().focus()

    // Tab → KEY input of the same row
    await page.keyboard.press('Tab')
    const afterTab1 = await page.evaluate(() => ({
      tag: document.activeElement?.tagName ?? '',
      cellClass: document.activeElement?.closest('.kv-cell')?.className ?? '',
      type: (document.activeElement as HTMLInputElement)?.type ?? ''
    }))
    expect(afterTab1.cellClass).toContain('key')

    // Tab → VALUE input
    await page.keyboard.press('Tab')
    const afterTab2 = await page.evaluate(() => ({
      tag: document.activeElement?.tagName ?? '',
      cellClass: document.activeElement?.closest('.kv-cell')?.className ?? '',
      type: (document.activeElement as HTMLInputElement)?.type ?? ''
    }))
    expect(afterTab2.cellClass).toContain('value')

    // Tab → DESCRIPTION input (not key, not value cell)
    await page.keyboard.press('Tab')
    const afterTab3 = await page.evaluate(() => ({
      tag: document.activeElement?.tagName ?? '',
      cellClass: document.activeElement?.closest('.kv-cell')?.className ?? '',
      type: (document.activeElement as HTMLInputElement)?.type ?? ''
    }))
    expect(afterTab3.tag).toBe('INPUT')
    expect(afterTab3.cellClass).not.toContain('key')
    expect(afterTab3.cellClass).not.toContain('value')

    // Tab → next row's checkbox (the virtual row's checkbox).
    // The delete <button> has no tabindex, so Tab skips it even though
    // focus-within reveals it (display:flex) while a row input is focused.
    await page.keyboard.press('Tab')
    const afterTab4 = await page.evaluate(() => ({
      tag: document.activeElement?.tagName ?? '',
      type: (document.activeElement as HTMLInputElement)?.type ?? '',
      isInsideKV: document.querySelector('.kv')?.contains(document.activeElement) ?? false
    }))
    // Focus must land on a checkbox or remain inside .kv
    expect(afterTab4.type === 'checkbox' || afterTab4.isInsideKV).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// 6. External state mutation (AC-21)
// ---------------------------------------------------------------------------

test.describe('KVTable — external mutation', () => {
  /**
   * Replacing the active tab's params array via tabsStore (simulating a cURL
   * import) must cause the grid to re-render with the new rows, discarding all
   * previous rows.
   */
  test('should re-render showing new rows after tabsStore params are replaced externally (AC-21)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableExternalMutationFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    // Initial row: api_key
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)
    await expect(
      page.locator('.kv-row:not(.empty) .kv-cell.key .kv-input-wrap input').first()
    ).toHaveValue('api_key')

    // Replace via the control button (calls tabsStore.getState().updateActiveSpec)
    await page.getByTestId('ct-kv-replace').click()

    // Grid must now show the replaced row
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)
    await expect(
      page.locator('.kv-row:not(.empty) .kv-cell.key .kv-input-wrap input').first()
    ).toHaveValue('imported_key')
  })
})

// ---------------------------------------------------------------------------
// 7. Field independence — params and headers are isolated (AC-10)
// ---------------------------------------------------------------------------

test.describe('KVTable — field independence', () => {
  /**
   * Mounting a params KVTable and a headers KVTable from the same store (bound
   * to different fields) must show the correct rows for each field, and editing
   * the params field must not mutate the headers field.
   */
  test('should isolate params rows from headers rows — editing one does not change the other (AC-10)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableTwoFieldsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const paramsTable = page.getByTestId('params-table')
    const headersTable = page.getByTestId('headers-table')

    // Verify initial state: each table shows its own seeded row
    await expect(
      paramsTable.locator('.kv-row:not(.empty) .kv-cell.key .kv-input-wrap input').first()
    ).toHaveValue('api_key')
    await expect(
      headersTable.locator('.kv-row:not(.empty) .kv-cell.key .kv-input-wrap input').first()
    ).toHaveValue('Content-Type')

    // Type into the virtual params key — promotes a NEW params row
    const paramsVirtualKey = paramsTable.locator('.kv-row.empty .kv-cell.key .kv-input-wrap input')
    await paramsVirtualKey.fill('new_param')

    // params table now has 2 real rows; headers table still has exactly 1
    await expect(paramsTable.locator('.kv-row:not(.empty)')).toHaveCount(2)
    await expect(headersTable.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // The headers row is unchanged
    await expect(
      headersTable.locator('.kv-row:not(.empty) .kv-cell.key .kv-input-wrap input').first()
    ).toHaveValue('Content-Type')
  })
})

// ---------------------------------------------------------------------------
// 8. Computed-style fidelity (var→token, grid metrics, font, colour)
// ---------------------------------------------------------------------------

test.describe('KVTable — computed-style fidelity', () => {
  /**
   * Grid track widths: the grid-template-columns declaration is
   * "22px 1fr 1fr 1fr 24px". In a browser layout, the first track resolves
   * to exactly 22px and the last to exactly 24px. Assert both from the
   * computed style to prove the CSS rule loads and the fixed tracks are intact.
   */
  test('should resolve the first grid track to 22px and last to 24px on .kv-header', async ({
    mount,
    page
  }) => {
    await mount(<KVTableEmptyParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const columns = await page.evaluate(() => {
      const header = document.querySelector('.kv-header') as HTMLElement | null
      if (!header) throw new Error('.kv-header not found')
      return getComputedStyle(header).gridTemplateColumns
    })

    // Split into individual track values; 1fr resolves to pixels in used values
    const tracks = columns.split(' ')
    expect(tracks[0]).toBe('22px')
    expect(tracks[tracks.length - 1]).toBe('24px')
    // Exactly five tracks
    expect(tracks).toHaveLength(5)
  })

  /**
   * .kv-header height must be 30px; .kv-row min-height must be 32px.
   */
  test('should have .kv-header height 30px and .kv-row min-height 32px', async ({
    mount,
    page
  }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const { headerHeight, rowMinHeight } = await page.evaluate(() => {
      const header = document.querySelector('.kv-header') as HTMLElement | null
      const row = document.querySelector('.kv-row:not(.empty)') as HTMLElement | null
      if (!header || !row) throw new Error('Elements not found')
      return {
        headerHeight: getComputedStyle(header).height,
        rowMinHeight: getComputedStyle(row).minHeight
      }
    })

    expect(headerHeight).toBe('30px')
    expect(rowMinHeight).toBe('32px')
  })

  /**
   * Checkbox width and height must be 12px (the accent-colored tiny checkbox).
   */
  test('should render the row checkbox at 12px × 12px', async ({ mount, page }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const { cbWidth, cbHeight } = await page.evaluate(() => {
      const cb = document.querySelector(
        '.kv-row:not(.empty) .kv-check input[type="checkbox"]'
      ) as HTMLInputElement | null
      if (!cb) throw new Error('Checkbox not found')
      const style = getComputedStyle(cb)
      return { cbWidth: style.width, cbHeight: style.height }
    })

    expect(cbWidth).toBe('12px')
    expect(cbHeight).toBe('12px')
  })

  /**
   * .kv-cell font-size must be 12px and font-family must include the mono stack.
   */
  test('should apply 12px mono font to .kv-cell', async ({ mount, page }) => {
    await mount(<KVTableOneRowParamsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const { fontSize, fontFamily } = await page.evaluate(() => {
      const cell = document.querySelector('.kv-row:not(.empty) .kv-cell') as HTMLElement | null
      if (!cell) throw new Error('.kv-cell not found')
      const style = getComputedStyle(cell)
      return { fontSize: style.fontSize, fontFamily: style.fontFamily }
    })

    expect(fontSize).toBe('12px')
    // font-family must include at least one member of the mono stack
    expect(fontFamily.toLowerCase()).toMatch(
      /jetbrains mono|sf mono|ui-monospace|menlo|consolas|monospace/i
    )
  })

  /**
   * .var computed color must equal the resolved value of --accent.
   * Proves the CSS variable chain: .kv-cell .var { color: var(--accent) }.
   * Uses a temporary element to resolve --accent to its computed colour so the
   * comparison is format-stable (both sides are rgb(...)).
   */
  test('should resolve .var color to the --accent token value (AC-19)', async ({ mount, page }) => {
    await mount(<KVTableVarNoValidVarsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-highlight .var')).toHaveCount(1)

    const { varColor, accentColor } = await page.evaluate(() => {
      const varEl = document.querySelector('.kv-highlight .var') as HTMLElement | null
      if (!varEl) throw new Error('.var element not found')
      const varColor = getComputedStyle(varEl).color

      // Resolve --accent through a temporary element to get the computed colour
      const tmp = document.createElement('span')
      tmp.style.color = 'var(--accent)'
      document.body.appendChild(tmp)
      const accentColor = getComputedStyle(tmp).color
      document.body.removeChild(tmp)

      return { varColor, accentColor }
    })

    expect(varColor).toBe(accentColor)
  })

  /**
   * .var.missing computed color must equal --m-delete AND text-decoration-line
   * must include 'line-through'. Proves the missing-token CSS chain.
   */
  test('should resolve .var.missing color to --m-delete and apply line-through (AC-19)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableVarWithValidVarsFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-highlight .var.missing')).toHaveCount(1)

    const { missingColor, mDeleteColor, textDecoLine } = await page.evaluate(() => {
      const missingEl = document.querySelector('.kv-highlight .var.missing') as HTMLElement | null
      if (!missingEl) throw new Error('.var.missing element not found')
      const missingColor = getComputedStyle(missingEl).color
      const textDecoLine = getComputedStyle(missingEl).textDecorationLine

      // Resolve --m-delete to its computed colour
      const tmp = document.createElement('span')
      tmp.style.color = 'var(--m-delete)'
      document.body.appendChild(tmp)
      const mDeleteColor = getComputedStyle(tmp).color
      document.body.removeChild(tmp)

      return { missingColor, mDeleteColor, textDecoLine }
    })

    expect(missingColor).toBe(mDeleteColor)
    expect(textDecoLine).toContain('line-through')
  })

  /**
   * .kv-row.disabled must have opacity 0.55 (controlled via the store's
   * row.enabled flag; the fixture seeds an already-disabled row).
   */
  test('should render .kv-row.disabled with opacity 0.55 (AC-16)', async ({ mount, page }) => {
    await mount(<KVTableDisabledRowFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const opacity = await page.evaluate(() => {
      const row = document.querySelector('.kv-row.disabled') as HTMLElement | null
      if (!row) throw new Error('.kv-row.disabled not found')
      return getComputedStyle(row).opacity
    })

    expect(opacity).toBe('0.55')
  })
})

// ---------------------------------------------------------------------------
// 9. Display-length desync fix — padded token raw preservation
// ---------------------------------------------------------------------------

test.describe('KVTable — padded token overlay fidelity', () => {
  /**
   * Regression lock for the display-length desync fix.
   *
   * Prior to the fix, `renderSegments` reconstructed the overlay text as
   * `{{${seg.name}}}` (trimmed name), so `{{ x }}` (7 chars in the input)
   * rendered as `{{x}}` (5 chars) in the overlay → colored highlight and caret
   * drifted apart.
   *
   * After the fix, `seg.raw` holds the verbatim matched text, so the overlay
   * renders exactly the same character sequence as the backing input.
   */
  test('should render the var span with verbatim padded text "{{ x }}" not trimmed "{{x}}" (desync fix)', async ({
    mount,
    page
  }) => {
    await mount(<KVTablePaddedTokenFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // The overlay var span must contain the verbatim padded source text
    const varSpan = page.locator('.kv-row:not(.empty) .kv-cell.key .kv-highlight .var')
    await expect(varSpan).toHaveCount(1)
    await expect(varSpan).toHaveText('{{ x }}')

    // The token is known (validVars has 'x') → .var present, .var.missing absent
    await expect(page.locator('.kv-cell.key .kv-highlight .var.missing')).toHaveCount(0)
  })
})

// ---------------------------------------------------------------------------
// 10. Value-cell highlight coverage
// ---------------------------------------------------------------------------

test.describe('KVTable — value cell highlight', () => {
  /**
   * Asserts that the value cell's kv-highlight overlay tokenises the value text
   * (the `renderSegments(row.value)` path). This path was previously untested —
   * all existing CTs only seeded tokens in the key cell.
   */
  test('should render a .var span inside the value cell .kv-highlight when value contains {{v}}', async ({
    mount,
    page
  }) => {
    await mount(<KVTableValueCellFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(1)

    // The value cell's overlay must have a .var span for the {{v}} token
    const valueVarSpan = page.locator('.kv-row:not(.empty) .kv-cell.value .kv-highlight .var')
    await expect(valueVarSpan).toHaveCount(1)
    await expect(valueVarSpan).toHaveText('{{v}}')
  })
})

// ---------------------------------------------------------------------------
// Controlled-mode regression (task 005 prop union / AC-11)
//
// Field-mode regression is the ENTIRE existing suite above — it runs unchanged
// against the discriminated-prop KVTable, so its continued green is the proof
// that the union extension did not regress the `field` arm. These cases add the
// new controlled `{rows, onRowsChange}` arm.
// ---------------------------------------------------------------------------

test.describe('KVTable — controlled mode', () => {
  /**
   * A controlled-mode edit round-trips through `onRowsChange`: the callback
   * updates the caller's local state, which flows back into `props.rows` and
   * re-renders the cell — proving the rows are caller-owned (AC-11).
   */
  test('controlled edit round-trips through onRowsChange into props.rows', async ({ mount, page }) => {
    await mount(<KVTableControlledFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const valueInput = page.locator('.kv-row:not(.empty) .kv-cell.value .kv-input-wrap input').first()
    await expect(valueInput).toHaveValue('secret') // seeded ROW_ENABLED value
    await valueInput.fill('changed')
    await expect(valueInput).toHaveValue('changed') // driven by props.rows after onRowsChange
  })

  /**
   * AC-11 negative arm (carried from the task 005 review): a controlled-mode
   * edit must NEVER write the tabsStore. `beforeEach` seeds the active tab's
   * params to `[]`; the live read-out of the stored params length must stay `0`
   * across a controlled edit that grows the LOCAL rows to two.
   */
  test('controlled edit never writes the store — updateActiveSpec untouched (AC-11)', async ({
    mount,
    page
  }) => {
    await mount(<KVTableControlledFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    const storedParams = page.getByTestId('ct-kv-store-params-count')
    await expect(storedParams).toHaveText('0') // seeded empty

    // Promote the virtual row via a controlled edit → local rows grow to 2.
    const virtualKeyInput = page.locator('.kv-row.empty .kv-cell.key .kv-input-wrap input')
    await virtualKeyInput.fill('newkey')
    await expect(page.locator('.kv-row:not(.empty)')).toHaveCount(2)

    // The store's params were NEVER written by the controlled edit.
    await expect(storedParams).toHaveText('0')
  })

  /**
   * The retained `validVars` `.missing` highlight gate still fires in controlled
   * mode: `{{x}}` (in validVars) → `.var` only; `{{y}}` (absent) → `.var.missing`.
   */
  test('controlled mode retains the validVars .missing highlight gate', async ({ mount, page }) => {
    await mount(<KVTableControlledVarFixture />)
    await page.waitForSelector('[data-testid="ct-kv-ready"]', { state: 'attached' })

    // Two key cells → two .var spans ({{x}} and {{y}}); exactly one is .missing ({{y}}).
    await expect(page.locator('.kv-highlight .var')).toHaveCount(2)
    await expect(page.locator('.kv-highlight .var.missing')).toHaveCount(1)
  })
})
