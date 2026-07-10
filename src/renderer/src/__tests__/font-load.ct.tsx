import { test, expect } from '@playwright/experimental-ct-react'

/**
 * Font-load fidelity CT (feature 016).
 *
 * Asserts the LOADED typeface, NOT a pixel-diff against design/reference.html.
 * The self-hosted faces (Inter + JetBrains Mono) must actually load. `'Inter'`
 * leads --font-sans, so the app renders Inter on all platforms — matching the
 * design mockup, which also renders Inter. JetBrains Mono leads --font-mono.
 * We assert the loaded typeface (Inter leads sans, JetBrains Mono leads mono),
 * never a pixel-diff (which would just confirm platform-fallback glyphs).
 *
 * fonts.css is loaded globally via playwright/index.tsx, mirroring production
 * (main.tsx imports fonts.css before tokens.css). The testids match the feature's
 * design-manifest pairs (body -> app-root, .method -> request-bar-method).
 */
test.describe('design fonts load', () => {
  test('Inter and JetBrains Mono load and the tokens resolve to them', async ({ mount, page }) => {
    await mount(
      <div>
        <span data-testid="app-root" style={{ fontFamily: 'var(--font-sans)' }}>
          Inter sans sample
        </span>
        <span data-testid="request-bar-method" style={{ fontFamily: 'var(--font-mono)' }}>
          GET
        </span>
      </div>
    )

    // The faces are requested + fully loaded.
    const loaded = await page.evaluate(async () => {
      await Promise.all([
        document.fonts.load('400 16px "Inter"'),
        document.fonts.load('500 16px "Inter"'),
        document.fonts.load('600 16px "Inter"'),
        document.fonts.load('700 16px "Inter"'),
        document.fonts.load('400 16px "JetBrains Mono"'),
        document.fonts.load('600 16px "JetBrains Mono"'),
        document.fonts.load('700 16px "JetBrains Mono"')
      ])
      await document.fonts.ready
      return {
        interRegular: document.fonts.check('400 16px "Inter"'),
        interMedium: document.fonts.check('500 16px "Inter"'),
        interSemibold: document.fonts.check('600 16px "Inter"'),
        interBold: document.fonts.check('700 16px "Inter"'),
        monoRegular: document.fonts.check('400 16px "JetBrains Mono"'),
        monoSemibold: document.fonts.check('600 16px "JetBrains Mono"'),
        monoBold: document.fonts.check('700 16px "JetBrains Mono"')
      }
    })
    expect(loaded.interRegular).toBe(true)
    expect(loaded.interMedium).toBe(true)
    expect(loaded.interSemibold).toBe(true)
    expect(loaded.interBold).toBe(true)
    expect(loaded.monoRegular).toBe(true)
    expect(loaded.monoSemibold).toBe(true)
    expect(loaded.monoBold).toBe(true)

    // Tokens resolve to the design faces FIRST: sans -> Inter, mono -> JetBrains
    // Mono. 'Inter' leads --font-sans so the app renders Inter (matching the design
    // mockup, which renders Inter); JetBrains Mono leads --font-mono.
    const sansFamily = await page
      .getByTestId('app-root')
      .evaluate((el) => getComputedStyle(el).fontFamily)
    const monoFamily = await page
      .getByTestId('request-bar-method')
      .evaluate((el) => getComputedStyle(el).fontFamily)

    expect(sansFamily).toMatch(/^["']?Inter["']?/)
    expect(monoFamily).toMatch(/^["']?JetBrains Mono["']?/)
  })

  test('form-control reset rule makes buttons inherit Inter from an Inter ancestor', async ({
    mount,
    page
  }) => {
    await mount(
      <div>
        {/* The EXACT reset rule from base.css — supplied inline because base.css is
            NOT imported in the CT harness (a global import breaks screenshot baselines,
            see memory: ct-borderbox-harness-import-breaks-screenshots). */}
        <style>{`button, input, select, textarea { font-family: inherit }`}</style>
        {/* Wrapper sets Inter as the ancestor font via the --font-sans token. */}
        <div style={{ fontFamily: 'var(--font-sans)' }}>
          <button data-testid="reset-btn">test</button>
        </div>
        {/* Control: reset applies (font-family: inherit) but the ancestor is body,
            which has no font-family in CT (base.css absent) → UA default, not Inter. */}
        <button data-testid="noreset-btn">control</button>
      </div>
    )

    const resetFamily = await page
      .getByTestId('reset-btn')
      .evaluate((el) => getComputedStyle(el).fontFamily)
    const noResetFamily = await page
      .getByTestId('noreset-btn')
      .evaluate((el) => getComputedStyle(el).fontFamily)

    // reset-btn: reset rule causes inherit → wrapper's var(--font-sans) → Inter leads.
    expect(resetFamily).toMatch(/^["']?Inter/)
    // noreset-btn: reset rule causes inherit → body UA default → not Inter in CT.
    expect(noResetFamily).not.toMatch(/^["']?Inter/)
  })
})
