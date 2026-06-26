# Task 006: CT fidelity-harness token context

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 009
**Spec criteria**: AC-18, AC-19, AC-21
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| playwright/index.tsx | Modify | Import tokens.css globally into the CT mount root |

## Description

Decision (g) — the grill-mandated CT fidelity-harness setup. The Playwright CT mount root currently imports no stylesheet, so a CT-mounted component resolves no design tokens. Add the global token context so the task-009 fidelity assertions can read real `var(--token)` / `.method` values rather than measuring an unstyled element.

1. **Global token import** — add `import '../src/renderer/styles/tokens.css'` to `playwright/index.tsx` (the CT mount root injected into every CT page). This is the CT analog of `main.tsx`'s global token sheet. Do NOT set `data-mstyle` here — that is per-test in task 009 (a global `data-mstyle` would perturb every other CT suite's styling context).

2. **F2 binding — verify no existing-suite shift (Risk-5 isolated step).** This is the one-time blast-radius check the plan requires BEFORE any fidelity assertion exists (do NOT defer it into task 009): run the full CT suite after adding the import and confirm no existing CT suite (Dropdown/Modal/Toast/Icon/nested-overlays/Shell) regressed. NOTE for the implementer: no existing `.ct.tsx` uses `toHaveScreenshot`, so there is NO screenshot baseline to "regenerate" — existing CT assertions are hardcoded dimensional/behavioral checks (e.g. `Shell.ct.tsx` `toBe(520)`). If the global token import shifts one of those, the fix is EDITING that out-of-scope `.ct.tsx` (Dropdown/Modal/Toast/Shell — none in this feature's File Impact) — surface it as a flagged out-of-scope consequence at the review checkpoint, do NOT silently edit beyond scope or treat it as a baseline regen. If no shift occurs (the expected case — the surveyed assertions are token-robust), record that the suite is green and proceed.

## Change Details

- In `playwright/index.tsx`:
  - Add `import '../src/renderer/styles/tokens.css'` (a side-effect CSS import) alongside the existing comment block.
- Run the full CT suite (`npm run test:ct` or the project's CT command) once and record the green/shift result per the F2 binding above.

## Contracts

### Expects (checked before execution)
- `playwright/index.tsx` is a comment-only file with no stylesheet import.
- `playwright.config.ts` `ctViteConfig` provides the `@renderer` alias; `tokens.css` exists at `src/renderer/styles/tokens.css` (relative `../src/renderer/styles/tokens.css` from `playwright/index.tsx`).
- Task 001 produced the `--m-head` / `.method.HEAD` rules the fidelity suite will assert against.

### Produces (checked after execution)
- `playwright/index.tsx` imports `tokens.css` so every CT page resolves real token values + `.method` rules.
- No `data-mstyle` is set globally in `playwright/index.tsx`.
- The full CT suite is green after the import (or any existing-suite shift is flagged as an out-of-scope consequence at the checkpoint).

## Done When

- [x] `playwright/index.tsx` contains `import '../src/renderer/styles/tokens.css'` (AC-18/AC-19/AC-21 prerequisite)
- [x] No `data-mstyle` is set globally in `playwright/index.tsx`
- [x] Full CT suite runs green after the import, OR any existing-suite assertion shift is flagged (not silently fixed) at the review checkpoint (F2 / Risk-5)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T09:32:00Z
**Files changed**: playwright/index.tsx
**Contract**: Expects 3/3 | Produces 3/3
**Notes**: F2 verified: tokens.css import caused zero CT-suite shift (Dropdown.ct.tsx:185 fails identically with/without import — pre-existing, filed as a bug). CT suite 100/101.
