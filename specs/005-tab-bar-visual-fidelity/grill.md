# Plan Grill -- specs/005-tab-bar-visual-fidelity -- 2026-06-26

**Feature**: specs/005-tab-bar-visual-fidelity
**Scope**: plan.md + referenced specs -- 2 files
**Finders invoked**: devils-advocate
**Refuters invoked**: code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React / TypeScript

## Disposition

**Verdict**: REVISE-PLAN

**Rationale**:

REVISE-PLAN (cycle 2; both plan-local, no KILL/upstream). The prior grill's 3 findings are CLOSED — Decision (g)'s tokens.css import path + per-test data-mstyle mechanism are sound, and the .tabbar-scoping rationale was regrounded on the AC-2 test. Two NEW smaller findings survived: (F1, Medium) Decision (g) names two of three CT styling-context prerequisites (load tokens.css, set data-mstyle='soft') but omits the third — the mounted fidelity fixture must carry className='tabbar' + closable + active; every new fidelity-scoped rule is behind a .tabbar compound selector (.tabbar .tabs\_\_tab-wrapper--active, .tabs.tabbar) and the active ::before/::after only render on the wrapper in the closable branch, yet every existing Tabs.stories.tsx fixture mounts a bare <Tabs> with no className — so a fixture built to the plan's letter measures an unscoped element (the same proof-integrity gap as the closed F-001). (F2, Info) Risk-5's mitigation says 'regenerate/verify any affected baseline', but no existing .ct.tsx uses toHaveScreenshot — there is no baseline to regenerate; a real token-shift would instead force edits to out-of-scope Dropdown/Modal/Toast/Shell .ct.tsx. Both are small, plan-local corrections (state the fidelity-fixture wiring in Decision (g) + Tabs.ct/stories File Impact; correct the Risk-5 remedy) — and equally resolvable as explicit /breakdown task constraints. This is the 2nd grill cycle; per the bounded-loop guidance the user decides whether to revise once more or proceed and bind these as breakdown constraints.

> The defects are real but correctable at the plan level. Revise `plan.md` to address the confirmed findings, then re-run `/plan` (or hand-patch `plan.md`), and optionally re-run `/grill` before proceeding to `/breakdown`.

## Confirmed -- Top Priorities

Force-ranked across the confirmed findings. Fix these first.

1. [Medium] specs/005-tab-bar-visual-fidelity/plan.md:60 -- Decision (g) enumerates two of three CT styling-context prerequisites — omits the `.tabbar` class the fidelity assertions are scoped to [Likely]
2. [Info] specs/005-tab-bar-visual-fidelity/plan.md:121 -- Risk-row-5 mitigation names "regenerate baseline" but no existing CT suite has a screenshot baseline; a real shift would force edits to out-of-scope test files [Speculative]

## Confirmed Findings

### specs/005-tab-bar-visual-fidelity/plan.md

#### Mislogic

- [F-001] [Medium] :60 -- Decision (g) enumerates two of three CT styling-context prerequisites — omits the `.tabbar` class the fidelity assertions are scoped to [Likely]
  Severity: Medium
  File: specs/005-tab-bar-visual-fidelity/plan.md
  Line: 60
  Pattern: Decision (g) enumerates two of three CT styling-context prerequisites — omits the `.tabbar` class the fidelity assertions are scoped to
  Confidence: Likely
  Category: blind_spot
  Evidence:

  ```
  | Test harness (CT styling context — Decision (g)) | Import `tokens.css` globally into the CT mount root so every CT page resolves real token values + `.method` rules; the fidelity suite sets `data-mstyle='soft'` per-test on the document root (the prerequisite for AC-18/AC-19/AC-21 computed-style resolution) | playwright/index.tsx |
  ```

  Why it's wrong: Decision (g) was added to close grill F-001/F-002 by guaranteeing the CT mount reproduces the app's styling context. But the revision enumerates only TWO of the THREE context prerequisites: (i) load tokens.css, (ii) set `data-mstyle='soft'`. It omits the third — the mounted fidelity fixture must carry `className="tabbar"`. Every fidelity assertion is `.tabbar`-scoped: the active accent is `.tabbar .tabs__tab-wrapper--active` (Layer Map row 1/2 + Decision (a): selector `.tabbar .tabs__tab-wrapper--active`), the geometry is `.tabbar`-scoped (`.tabs.tabbar{overflow:visible}`, `.tabbar`-scoped gap/padding/border, AC-14/AC-15), and the active `::before/::after` only exist on the wrapper, which itself only renders in the `closable` branch. The mounted Tabs molecule receives `.tabbar` only when a caller passes it (TabBar.tsx:133 `className="tabbar"`); the CT fidelity test mounts a fixture from Tabs.stories.tsx, and EVERY existing fixture there mounts a bare `<Tabs>` with no className (grep for `tabbar` in Tabs.stories.tsx returns zero matches) and most are non-closable (no wrapper at all). The plan's File Impact for Tabs.stories.tsx ("dirty fixture … active ::before; method chip") and Tabs.ct.tsx ("set `data-mstyle='soft'` … assert token-RESOLVED values") never states the fidelity fixture must be `className="tabbar"` + `closable` + active. So a fixture built to the plan's letter mounts unscoped Tabs and every `.tabbar`-scoped assertion measures the wrong element — the exact "measuring an unstyled span" failure mode the revision claims Decision (g) eliminates. This is the same proof-integrity family as the High-severity F-001 the revision was built to close; the harness completeness claim is overstated by one prerequisite.
  Remediation: Extend Decision (g) (and the File Impact rows for Tabs.stories.tsx + Tabs.ct.tsx) to enumerate the third styling-context prerequisite: the fidelity fixture must mount Tabs with `className="tabbar"`, `closable`, an active tab, and a `method` set — OR mount the TabBar organism directly (which already supplies `.tabbar` + `closable` + the store). State this in the same place the tokens.css / data-mstyle wiring is scheduled, so `/breakdown` cannot decompose a fidelity task that asserts `.tabbar`-scoped rules against an unscoped fixture.

- [F-002] [Info] :121 -- Risk-row-5 mitigation names "regenerate baseline" but no existing CT suite has a screenshot baseline; a real shift would force edits to out-of-scope test files [Speculative]
  Severity: Info
  File: specs/005-tab-bar-visual-fidelity/plan.md
  Line: 121
  Pattern: Risk-row-5 mitigation names "regenerate baseline" but no existing CT suite has a screenshot baseline; a real shift would force edits to out-of-scope test files
  Confidence: Speculative
  Category: blind_spot
  Evidence:
  ```
  | Importing `tokens.css` globally into `playwright/index.tsx` shifts the styling context of existing CT suites (Dropdown/Modal/Toast) — currently rendering in CT against `var()` defensive fallbacks, not real tokens — perturbing layout-sensitive assertions or any screenshot baseline | Med | Low | Existing CT assertions read component-local `animation-name` + boundingBox with ±1px tolerance (token-robust); after the import, run the full CT suite and regenerate/verify any affected baseline as a one-time isolated step BEFORE adding the Tabs fidelity assertions — do not co-mingle baseline regen with source edits |
  ```
  Why it's wrong: The mitigation's remedy ("regenerate/verify any affected baseline") presumes the existing CT suites have screenshot baselines that can be regenerated. They do not — no existing `.ct.tsx` file calls `toHaveScreenshot` (zero matches across Dropdown/Modal/Toast/Icon/nested-overlays/Shell/Tabs CT). Their dimensional assertions are hardcoded values in test code (e.g. `expect(Number(committedText)).toBe(520)` in Shell.ct.tsx, boundingBox edge comparisons in Dropdown.ct.tsx). If the global tokens.css import actually shifts one of those, the fix is not "regenerate a baseline" — it is EDITING assertions in Dropdown/Modal/Toast/Shell `.ct.tsx`, none of which appear in the plan's File Impact (12 files, all Tabs/TabBar/tokens/Shell.css/test). So the named remedy does not match the actual failure mode, and a real shift would either break the build or push out-of-scope test edits into `/implement`. The impact is Low (the surveyed assertions are animation-name / focus / relative-boundingBox, all plausibly token-robust, so a shift may never occur), which is why this is Speculative rather than a confirmed break — but the mitigation as written is a remedy for a baseline that does not exist.
  Remediation: Reword Risk-row-5's mitigation to the remedy that actually applies: run the full existing CT suite once after the global tokens.css import and, IF any hardcoded computed-style/boundingBox assertion shifts, treat the required edit to that suite's `.ct.tsx` as an explicit (currently out-of-scope) work item — not a "baseline regen." Drop the "regenerate baseline" phrasing since no existing CT suite carries a screenshot baseline.

## Summary

- Critical: 0 | High: 0 | Medium: 1 | Info: 1
- Confirmed: 2 | Contested: 0 | Dismissed: 0 | Uncertain: 0
- Disposition: REVISE-PLAN
- Finders skipped (not installed): none

## Methodology

Findings are grounded -- every finding carries a verbatim quote from the
actual plan/spec/research artefacts. A refutation stage cross-examines each
grounded finding before it reaches the report: a finding earns the headline
only by surviving an adversary who default-dismisses anything not
demonstrable as a real plan-level defect. Confirmed findings reach the
headline; dismissed and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; high-stakes [CONTESTED] findings
(security / [CONSTITUTION-VIOLATION] the refuter could not confirm) are
surfaced in the headline, flagged [CONTESTED], never buried.
