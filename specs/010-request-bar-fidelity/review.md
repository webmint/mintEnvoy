# Feature Review — specs/010-request-bar-fidelity — 2026-06-29

**Feature**: specs/010-request-bar-fidelity
**Scope**: assembled feature diff (all tasks together) — 20 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst, design-auditor
**Refuters invoked**: code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
1. [Info] src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx:1029 — Cross-task blind-spot — Task 002 adds method-button hover CSS, Task 003 adds Save hover CT but omits method-button hover CT [Certain]

## Confirmed Findings

### src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx

#### Mislogic
- [F-001] [Info] :1029 — Cross-task blind-spot — Task 002 adds method-button hover CSS, Task 003 adds Save hover CT but omits method-button hover CT  [Certain]
  Severity: Info
  File: src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx
  Line: 1029
  Pattern: Cross-task blind-spot — Task 002 adds method-button hover CSS, Task 003 adds Save hover CT but omits method-button hover CT
  Confidence: Certain
  Category: blind_spot
  Evidence:
  ```
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
  ```
  Why it's wrong: Task 002 adds `.request-bar .request-bar__method.method:hover { border-color: var(--border-strong); }` at RequestBar.css:108. This is the identical hover treatment as Save's `:hover` rule (border strengthens to `--border-strong`). The fix commit that remediated the prior round added the Save hover CT test (the Evidence block above) — proving the hover-test pattern is established in the suite. However no corresponding CT test exists for the method button's hover state: a future edit that removes or changes the `border-color` on `.request-bar__method.method:hover` would be undetected in the real browser. The gap requires reading both task diffs together: Task 002 establishes the method hover rule, and Task 003's CT suite (post-fix) applies the hover pattern to Save but not to the method button.
  Remediation: Add a CT test inside `RequestBar — fidelity` that uses `page.locator('.request-bar__method').hover()` with `prefers-reduced-motion: reduce` emulated, then asserts `borderTopColor` equals the probe-resolved `--border-strong` value — mirroring the Save hover test structure verbatim.


## Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 1
- Confirmed: 1 | Contested: 0 | Dismissed: 0 | Uncertain: 0
- Finders skipped (not installed): none

## Methodology
Findings are grounded — every finding carries a verbatim quote from the actual
cross-task code, and validation discards ungrounded ones. A refutation stage
then cross-examines each grounded finding before it reaches the report: a
finding earns the headline only by surviving an adversary who default-dismisses
anything not demonstrable as emergent at feature scope. Confirmed findings reach
the headline; dismissed findings and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; contested findings (a high-stakes `security`
/ `[CONSTITUTION-VIOLATION]` finding the refuter could not confirm, or a
`[CONSTITUTION-VIOLATION]` finding the refuter dismissed) are surfaced in the
headline, flagged `[CONTESTED]`, never buried. This report is findings only —
the verdict is `/verify`'s.
