# Feature Review — specs/003-app-shell-layout — 2026-06-24

**Feature**: specs/003-app-shell-layout
**Scope**: assembled feature diff (all tasks together) — 31 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst
**Refuters invoked**: code-reviewer, architect
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities

Force-ranked across the confirmed findings. Fix these first.

1. [Medium] src/renderer/src/components/organisms/Shell.tsx:363 — cross-task slot gap [Certain]
2. [Medium] src/renderer/src/components/organisms/Divider.tsx:165 — cross-task duplicate clamp implementation [Certain]
3. [Medium] src/renderer/src/components/organisms/Divider.tsx:284 — Redundant CSS-var write per drag commit — Divider pointerup write + Shell Effect 2 write = double style-recalc [Certain]
4. [Medium] src/renderer/src/components/organisms/**tests**/Shell.test.tsx:1235 — AC-17 window-resize re-clamp coverage documented as "renderer-side only"; the complementary OS minWidth floor (main process / task 010) is explicitly untestable in jsdom — this split is undocumented in the test file, creating a risk that /verify treats AC-17 as fully covered [blind_spot] [Likely]
5. [Low] src/renderer/src/components/organisms/Sidebar.tsx:114 — Divergent onCommit binding convention for the same Divider→store seam across two mounter tasks [Likely]
6. [Info] src/renderer/src/components/organisms/Titlebar.tsx:156 — divergent export-default presence across organisms [Certain]
7. [Info] src/renderer/src/components/organisms/Divider.tsx:198 — divergent JSX return type form across organisms [Certain]

## Confirmed Findings

### src/renderer/src/components/organisms/Divider.tsx

#### System Design

- [F-006] [Medium] :284 — Redundant CSS-var write per drag commit — Divider pointerup write + Shell Effect 2 write = double style-recalc [Certain]
  Severity: Medium
  File: src/renderer/src/components/organisms/Divider.tsx
  Line: 284
  Pattern: Redundant CSS-var write per drag commit — Divider pointerup write + Shell Effect 2 write = double style-recalc
  Confidence: Certain
  Category: system_design
  Evidence:
  ```
  document.documentElement.style.setProperty(cssVar, `${clamped}${unit}`)
  ```
  Why it's wrong: On pointerup the Divider writes the committed value to `--sidebar-width`/`--pane-ratio` on `document.documentElement` (this line), then `onCommit(clamped)` calls the store action, which fires Shell's reactive `sidebarWidth`/`paneRatio` selector and re-runs Shell's Effect 2 (`src/renderer/src/components/organisms/Shell.tsx:252`, `style.setProperty('--sidebar-width', \`${sidebarWidth}px\`)`), writing the IDENTICAL value a second time. Two style recalculations for one commit. The CSS-var ownership is split across two tasks (Divider owns during-drag, Shell Effect 2 owns at-rest) with no coordination guarding against the double write. Cross-task: invisible in either diff alone.
  Remediation: Scope Shell Effect 2's CSS-var write to mount/resize rehydration (drop sidebarWidth/paneRatio from its dep array, or guard against re-writing a value already current on document.documentElement); the Divider's commit write already leaves the at-rest value correct.

#### Duplication

- [F-003] [Medium] :165 — cross-task duplicate clamp implementation [Certain]
  Severity: Medium
  File: src/renderer/src/components/organisms/Divider.tsx
  Line: 165
  Pattern: cross-task duplicate clamp implementation
  Confidence: Certain
  Category: duplication
  Evidence:
  ```
  function clamp(v: number, lo: number, hi: number): number {
    return Math.min(Math.max(v, lo), hi)
  }
  ```
  Why it's wrong: Task 001 (`settingsStore.ts`, lines 90–107) already exports `clampSidebarWidth` and `clampPaneRatio`, each wrapping `Math.min/Math.max` with an explicit NaN/Infinity guard (`if (!Number.isFinite(px)) return DEFAULT_SIDEBAR_WIDTH`). Task 002 (`Divider.tsx`) introduces its own private `clamp(v, lo, hi)` using the same `Math.min(Math.max(...))` idiom but without the NaN guard. Two parallel clamp implementations now exist in the assembled feature. The omission of the NaN guard in the Divider `clamp` is not a runtime defect in the current flow (pointer pixel arithmetic on a store-committed start value never produces NaN), but it diverges from the NaN-safety contract established in Task 001 and would silently propagate `NaN` to `onCommit` if either input were ever not-a-number (e.g. via a future `value` prop source). Only visible as a duplication concern when Tasks 001 and 002 are assembled.
  Remediation: Divider is deliberately store-free (by design). The cleanest fix is to export a generic `clamp(v, lo, hi)` utility from `src/renderer/src/lib/clamp.ts` (or inline it into `settingsStore.ts` and re-export it), then import it in both `settingsStore.ts` and `Divider.tsx`, eliminating the duplication without coupling Divider to the settings domain.

---

- [F-005] [Info] :198 — divergent JSX return type form across organisms [Certain]
  Severity: Info
  File: src/renderer/src/components/organisms/Divider.tsx
  Line: 198
  Pattern: divergent JSX return type form across organisms
  Confidence: Certain
  Category: duplication
  Evidence:
  ```
  }: DividerProps): React.JSX.Element {
  ```
  Why it's wrong: `Divider.tsx` (Task 002, line 198) and `PaneSplit.tsx` (Task 004, line 83) annotate the component return as `React.JSX.Element` — relying on a global `React` namespace without an explicit React import in either file (`Divider.tsx` imports only `useEffect, useRef` from 'react'; `PaneSplit.tsx` imports only `useRef, type ReactNode`). `Sidebar.tsx` (Task 003, line 83) uses `React.JSX.Element | null` the same way. Meanwhile `Titlebar.tsx` (Task 005) and `Statusbar.tsx` (Task 006) explicitly `import { type JSX } from 'react'` and annotate as `JSX.Element`, and `Shell.tsx` (Task 007/009, line 175) uses `JSX.Element` without importing it (relying on the global). Three different approaches to the same type annotation exist in the assembled organism set. No runtime impact, but type-checker behaviour can differ across tsconfig targets and `isolatedModules`, and the inconsistency signals each task was decided independently. Only visible once the full set of organism files is assembled.
  Remediation: Standardise on one form project-wide. The constitution §3.1 requires strict mode but does not prescribe `React.JSX.Element` vs `JSX.Element`. The `import { type JSX } from 'react'` pattern (`JSX.Element`) is explicit and works regardless of whether `React` is in scope, making it the safer choice. Update `Divider.tsx`, `PaneSplit.tsx`, and `Sidebar.tsx` (remove the `React.` prefix and add the named import); update `Shell.tsx` to add the explicit import rather than relying on the global.

---

### src/renderer/src/components/organisms/Shell.tsx

#### System Design

- [F-002] [Medium] :363 — cross-task slot gap [Certain]
  Severity: Medium
  File: src/renderer/src/components/organisms/Shell.tsx
  Line: 363
  Pattern: cross-task slot gap
  Confidence: Certain
  Category: system_design
  Evidence:
  ```
  {/* ---- Statusbar row ---- */}
        <Statusbar />
  ```
  Why it's wrong: Task 006 (`Statusbar.tsx`) defines a `children?: ReactNode` slot explicitly documented as the surface "downstream features populate with status items." Task 007/009 (`Shell.tsx` / `ShellProps`) never exposes a `statusbar` slot — `ShellProps` (lines 110–140) has `sidebar`, `tabs`, `panes`, and `modals` but no `statusbar`. `<Statusbar />` is rendered unconditionally with no `children`, making the slot permanently unreachable through Shell's composition API. Any feature that wants to place content in the statusbar cannot do so via the Shell contract — it must reach around Shell to the store or use a separate provider, neither of which is documented or intended. Only visible once Task 006 and Task 007/009 are assembled.
  Remediation: Add a `statusbar?: ReactNode` prop to `ShellProps` and thread it as `<Statusbar>{statusbar}</Statusbar>`. This is a one-line prop addition and preserves backward compatibility (the default is `undefined`, which renders the bar empty as today).

---

### src/renderer/src/components/organisms/Sidebar.tsx

#### Duplication

- [F-001] [Low] :114 — Divergent onCommit binding convention for the same Divider→store seam across two mounter tasks [Likely]
  Severity: Low
  File: src/renderer/src/components/organisms/Sidebar.tsx
  Line: 114
  Pattern: Divergent onCommit binding convention for the same Divider→store seam across two mounter tasks
  Confidence: Likely
  Category: duplication
  Evidence:
  ```
  onCommit={(px) => settingsStore.getState().setSidebarWidth(px)}
  ```
  Why it's wrong: Sidebar and PaneSplit both mount the identical Divider abstraction to commit a clamped layout value to settingsStore — the same architectural seam — but each binds onCommit with a different convention. Sidebar (this line) wraps the action in a fresh arrow that calls getState() at commit time, whereas PaneSplit at src/renderer/src/components/organisms/PaneSplit.tsx:112 passes the action by reference resolved at render time: onCommit={settingsStore.getState().setPaneRatio}. The PaneSplit form captures the action reference during render (it works only because zustand action identities are stable), while the Sidebar form re-reads the store at call time; the two styles diverge on the same concern, so a reader cannot infer one canonical "how a mounter wires a Divider to the store." This divergence only surfaces when the two sibling mounter files are read together — each file in isolation looks internally consistent. It is a DRY/convention drift, not a correctness bug.
  Remediation: Pick one binding convention for the Divider→store seam and apply it in both mounters. Prefer the call-time form (onCommit={(v) => settingsStore.getState().setPaneRatio(v)}) since it matches the imperative getState() pattern Shell already uses for actions, and avoids capturing an action reference at render time.

### src/renderer/src/components/organisms/Titlebar.tsx

#### Duplication

- [F-004] [Info] :156 — divergent export-default presence across organisms [Certain]
  Severity: Info
  File: src/renderer/src/components/organisms/Titlebar.tsx
  Line: 156
  Pattern: divergent export-default presence across organisms
  Confidence: Certain
  Category: duplication
  Evidence:
  ```
  export default Titlebar
  ```
  Why it's wrong: `Titlebar.tsx` (Task 005, line 156), `Statusbar.tsx` (Task 006, line 70), and `Shell.tsx` (Task 007/009, line 375) each add a redundant `export default` statement. The earlier three organisms — `Divider.tsx` (Task 002), `Sidebar.tsx` (Task 003), and `PaneSplit.tsx` (Task 004) — export named exports only and have no `export default`. All callers throughout the feature (Shell.tsx imports Titlebar/Sidebar/PaneSplit/Statusbar via named imports; App.tsx imports Shell via named import; the test file imports all organisms via named imports) use named imports exclusively. The default exports are dead. This divergence is invisible in any single task's diff but becomes apparent in the assembled set of organisms.
  Remediation: Remove the `export default` statements from `Titlebar.tsx`, `Statusbar.tsx`, and `Shell.tsx` to be consistent with the pattern established by the first three organism tasks. Named exports are sufficient and unambiguous.

---

### src/renderer/src/components/organisms/**tests**/Shell.test.tsx

#### Mislogic

- [F-007] [Medium] :1235 — AC-17 window-resize re-clamp coverage documented as "renderer-side only"; the complementary OS minWidth floor (main process / task 010) is explicitly untestable in jsdom — this split is undocumented in the test file, creating a risk that /verify treats AC-17 as fully covered [blind_spot] [Likely]
  Severity: Medium
  File: src/renderer/src/components/organisms/**tests**/Shell.test.tsx
  Line: 1235
  Pattern: AC-17 window-resize re-clamp coverage documented as "renderer-side only"; the complementary OS minWidth floor (main process / task 010) is explicitly untestable in jsdom — this split is undocumented in the test file, creating a risk that /verify treats AC-17 as fully covered [blind_spot]
  Confidence: Likely
  Category: blind_spot
  Evidence:

  ```
  describe('Shell — window-resize re-clamp (AC-17)', () => {
    it('clamps out-of-bounds sidebarWidth back to SIDEBAR_MAX on resize', () => {
      render(<Shell />)

      // Seed an out-of-bounds value directly into the store
      act(() => {
        settingsStore.setState({ sidebarWidth: 9999 })
      })

      // Trigger resize
      act(() => {
        window.dispatchEvent(new Event('resize'))
      })

      expect(settingsStore.getState().sidebarWidth).toBe(SIDEBAR_MAX)
    })
  ```

  Why it's wrong: Shell.test.tsx:1235–1293 covers the renderer-side resize clamp (store mutation via window resize event) correctly. But AC-17 has two halves: (1) renderer re-clamp (covered) and (2) the OS-window minWidth floor in `src/main/index.ts` (task 010) that prevents the Electron window from being resized below a minimum pixel width. The main-process minWidth path is untestable in jsdom and is not mentioned in the test file. The Shell.tsx JSDoc at line 43 explicitly notes "The complementary OS-window minWidth floor lives in task 010" — but no test comment in Shell.test.tsx:1235 acknowledges the coverage split. If /verify reads AC-17 and its one passing test block, it may conclude AC-17 is PASS without noting that the main-process half is untested and requires a separate integration/e2e layer. The spec (AC-17) does not subdivide itself, so the gap is invisible at the AC level.
  Remediation: Add a `// NOTE: main-process minWidth (task 010) is not testable in jsdom; this block covers the renderer-side clamp only. The complementary OS-level constraint requires an Electron integration test.` comment at the top of the `Shell — window-resize re-clamp (AC-17)` describe block so /verify can accurately judge AC-17 as PARTIAL rather than PASS.

---

## Summary

- Critical: 0 | High: 0 | Medium: 4 | Info: 2
- Confirmed: 7 | Contested: 0 | Dismissed: 5 | Uncertain: 0
- Finders skipped (not installed): none

## Dismissed / Worth a Glance

These findings were reviewed but not confirmed. Dismissed findings had no demonstrable emergent defect at feature scope; uncertain findings could not be resolved from the code alone. A reviewer may want to glance at them before closing the review.

### Dismissed

- [D-001] [Medium] src/renderer/src/components/organisms/Shell.tsx:271 — AC-17 contract drift — renderer re-clamp is a structural no-op; the real overflow guard lives in the main process, contradicting Shell's documented responsibility
- [D-002] [Medium] src/renderer/src/components/organisms/PaneSplit.tsx:113 — getBoundingClientRect layout-read per pointermove interleaves with the rAF CSS-var write — forced synchronous reflow on the pane-drag hot path
- [D-003] [Critical] src/renderer/src/components/organisms/**tests**/Shell.ct.tsx:1 — CT harness broken → all CT-only assertions are unexecuted [blind_spot]
- [D-004] [High] src/renderer/src/components/organisms/**tests**/Shell.test.tsx:1163 — Titlebar toggleRef→Shell focus-return tested in Shell isolation but Titlebar's own ct.tsx fixture does not wire toggleRef — cross-task contract exercised one-sided [blind_spot]
- [D-005] [High] src/renderer/src/components/organisms/**tests**/Shell.test.tsx:1147 — Sidebar→Divider→setSidebarWidth integration: store-commit path exercised by CT (SidebarFixture) but CT is unexecuted; jsdom seam test only covers Divider in isolation (not the Sidebar-wired Divider calling setSidebarWidth) [blind_spot]

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
