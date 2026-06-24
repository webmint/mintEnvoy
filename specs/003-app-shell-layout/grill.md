# Plan Grill -- specs/003-app-shell-layout -- 2026-06-23

**Feature**: specs/003-app-shell-layout
**Scope**: plan.md + referenced specs -- 2 files
**Finders invoked**: devils-advocate
**Refuters invoked**: code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React

## Disposition

**Verdict**: REVISE-PLAN

**Rationale**:

Re-grill of the revised plan. All 5 prior REVISE-PLAN findings verified genuinely resolved by the adversary (ToastProvider preserved, window minWidth 720 added, reset()/clearAll() corrected, Cmd-B unmount + focus-return, concrete defaults) — none re-raised. Three new findings, only ONE confirmed and it is Medium: (F2) the dependency-direction Risk row names 'lint/CBM check the edge' as its mitigation, but eslint.config.mjs (@electron-toolkit/eslint-config-ts + react/react-hooks/react-refresh/prettier) defines no no-restricted-imports / import/no-restricted-paths / boundaries rule, so npm run lint (AC-13) cannot detect a lib→component import — the named automated gate is illusory; the real guard is leaf-level discipline + review + a CBM query. Fixable by a one-line plan edit (reword the mitigation, or add an eslint import-boundary rule). F1 (Cmd-B handler scope) dismissed — design-level label, Tests row already names a Cmd-B test that catches mis-scoping. F3 (cross-organism focus-return from Divider unmount to the Titlebar toggle) uncertain/Low — Shell is the common ancestor and can coordinate the focus move, but the mechanism is unnamed; a /breakdown-closeable spec gap, not a design breakage. No High/Critical, no contested, no upstream root cause — the design is sound; this is a single light plan-text correction.

> The defects are real but correctable at the plan level. Revise `plan.md` to address the confirmed findings, then re-run `/plan` (or hand-patch `plan.md`), and optionally re-run `/grill` before proceeding to `/breakdown`.

## Confirmed -- Top Priorities

Force-ranked across the confirmed findings. Fix these first.

1. [Medium] specs/003-app-shell-layout/plan.md:92 -- Risk mitigation claims a lint edge-check the toolchain does not provide [Certain]

## Confirmed Findings

### specs/003-app-shell-layout/plan.md

#### Best Practices

- [F-001] [Medium] :92 -- Risk mitigation claims a lint edge-check the toolchain does not provide [Certain]
  Severity: Medium
  File: specs/003-app-shell-layout/plan.md
  Line: 92
  Pattern: Risk mitigation claims a lint edge-check the toolchain does not provide
  Confidence: Certain
  Category: best_practice
  Evidence:
  ```
  | Dependency-direction: a new organism imports `lib` in the wrong direction, or `lib/settingsStore` imports a component | Low | Med | Keep `settingsStore` leaf-level (imports only `zustand`); organisms import lib, never the reverse; lint/CBM check the edge |
  ```
  Why it's wrong: The mitigation rests on "lint/CBM check the edge", but the project's ESLint config (eslint.config.mjs — `@electron-toolkit/eslint-config-ts` + react/react-hooks/react-refresh/prettier only) defines NO `no-restricted-imports`, `import/no-restricted-paths`, or boundaries rule. As configured, ESLint cannot detect a `lib/settingsStore.ts` that imports a `components/organisms/*` module, nor a wrong-direction organism import — `npm run lint` (AC-13) will pass on the exact violation this row claims lint guards. CBM is a query graph an agent must choose to consult, not an automated gate. So the named mitigation for a Med-impact dependency-inversion risk is illusory; the real protection is reviewer discipline plus the leaf-level discipline stated earlier in the same cell.
  Remediation: Either drop the "lint ... check the edge" clause (the truthful mitigation is "keep settingsStore importing only zustand; reviewer/CBM verify direction"), or add a concrete enforcement task — an `import/no-restricted-paths` (eslint-plugin-import) zone forbidding `src/renderer/src/lib/**` from importing `src/renderer/src/components/**`. Do not let a Risk row assert an automated check that the configured toolchain does not perform.

## Summary

- Critical: 0 | High: 0 | Medium: 1 | Info: 0
- Confirmed: 1 | Contested: 0 | Dismissed: 1 | Uncertain: 1
- Disposition: REVISE-PLAN
- Finders skipped (not installed): none

## Dismissed / Worth a Glance

These findings were reviewed but not confirmed. Dismissed findings had no demonstrable plan-level defect; uncertain findings could not be resolved from the plan alone. A reviewer may want to glance at them before accepting the verdict.

### Dismissed

- [D-001] [Medium] specs/003-app-shell-layout/plan.md:71 -- Global Cmd-B shortcut reduced to an unscoped "key handler"

### Uncertain (low-stakes)

- [U-001] [Low] specs/003-app-shell-layout/plan.md:84 -- Cross-organism focus-return mechanism undesigned

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
