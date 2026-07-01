# Task 001: Move Divider to molecules and rewrite its importers

**Feature**: 006-reorganize-flat-components
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002
**Spec criteria**: AC-2, AC-5, AC-6, AC-7, AC-11, AC-12, AC-13, AC-14
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                                                                                  | Action | Description                                                                                                      |
| ----------------------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/organisms/Divider.tsx → src/renderer/src/components/molecules/Divider.tsx | Move   | Relocate the component file; no content change                                                                   |
| src/renderer/src/components/organisms/Divider.css → src/renderer/src/components/molecules/Divider.css | Move   | Sibling stylesheet travels with the .tsx; `Divider.tsx`'s `import './Divider.css'` is relative and needs no edit |
| src/renderer/src/components/organisms/Sidebar.tsx                                                     | Modify | Rewrite the Divider import to the new molecules path (stays in organisms/)                                       |
| src/renderer/src/components/organisms/PaneSplit.tsx                                                   | Modify | Rewrite the Divider import to the new molecules path (PaneSplit itself stays in organisms/ until task 002)       |
| src/renderer/src/components/organisms/**tests**/Shell.test.tsx                                        | Modify | Rewrite ONLY the Divider import to the new molecules path, in place (file stays put until task 002 moves it)     |
| src/renderer/src/components/organisms/**tests**/Shell.stories.tsx                                     | Modify | Rewrite ONLY the Divider import to the new molecules path, in place (file stays put until task 002 moves it)     |

## Description

Move the `Divider` component (the one genuinely domain-agnostic shared primitive) from the organism tier down to the molecule tier, and rewrite **every** importer of it to the new path. This clears the live constitution §2.2:56 sibling-tier import violation (`PaneSplit → Divider` and `Sidebar → Divider` were organism→organism sibling imports; after the move they are legal organism→molecule downward imports).

There are **four** importers of `@renderer/components/organisms/Divider` in the renderer — PaneSplit, Sidebar, Shell.test.tsx, and Shell.stories.tsx. All four must be rewritten in this task so the tree type-checks and the test suite resolves `Divider` at this task's boundary. The two `__tests__/` fixtures are edited **in place** here — they do not move in this task (task 002 relocates them); because the import is the absolute `@renderer` alias, the rewritten path survives the later move untouched.

Pure relocation + import-path rewrite — no prop, export-surface, runtime, styling, or logic change. `Divider` must still export the same `Divider` symbol and behave identically (the ratio-valued drag mapping and CSS-var write contract are unchanged).

## Change Details

- Move `src/renderer/src/components/organisms/Divider.tsx` → `src/renderer/src/components/molecules/Divider.tsx` (content unchanged; its `import './Divider.css'` relative import is preserved because the .css moves alongside it).
- Move `src/renderer/src/components/organisms/Divider.css` → `src/renderer/src/components/molecules/Divider.css`.
- In `src/renderer/src/components/organisms/Sidebar.tsx`:
  - Rewrite `import { Divider } from '@renderer/components/organisms/Divider'` → `import { Divider } from '@renderer/components/molecules/Divider'`.
- In `src/renderer/src/components/organisms/PaneSplit.tsx`:
  - Rewrite `import { Divider } from '@renderer/components/organisms/Divider'` → `import { Divider } from '@renderer/components/molecules/Divider'`.
- In `src/renderer/src/components/organisms/__tests__/Shell.test.tsx`:
  - Rewrite the `Divider` import line `import { Divider } from '@renderer/components/organisms/Divider'` → `import { Divider } from '@renderer/components/molecules/Divider'`. Leave every other import (Shell/Titlebar/Statusbar/PaneSplit) untouched — those are rewritten in task 002.
- In `src/renderer/src/components/organisms/__tests__/Shell.stories.tsx`:
  - Rewrite the `Divider` import line `import { Divider } from '@renderer/components/organisms/Divider'` → `import { Divider } from '@renderer/components/molecules/Divider'`. Leave every other import untouched.

## Contracts

### Expects (checked before execution)

- `src/renderer/src/components/organisms/Divider.tsx` exists and exports `Divider`; `src/renderer/src/components/organisms/Divider.css` exists.
- `Sidebar.tsx` imports `Divider` from `@renderer/components/organisms/Divider`.
- `PaneSplit.tsx` imports `Divider` from `@renderer/components/organisms/Divider`.
- `__tests__/Shell.test.tsx` and `__tests__/Shell.stories.tsx` each import `Divider` from `@renderer/components/organisms/Divider`.

### Produces (checked after execution)

- `src/renderer/src/components/molecules/Divider.tsx` exists and exports `Divider`; `src/renderer/src/components/molecules/Divider.css` exists.
- No file `src/renderer/src/components/organisms/Divider.tsx` and no file `src/renderer/src/components/organisms/Divider.css`.
- `Sidebar.tsx`, `PaneSplit.tsx`, `__tests__/Shell.test.tsx`, and `__tests__/Shell.stories.tsx` each import `Divider` from `@renderer/components/molecules/Divider`.
- No occurrence of `@renderer/components/organisms/Divider` anywhere under `src/renderer`.

## Done When

- [x] `Divider.tsx` and `Divider.css` live under `components/molecules/` and no longer exist under `components/organisms/`
- [x] All four Divider importers (Sidebar, PaneSplit, Shell.test.tsx, Shell.stories.tsx) reference `@renderer/components/molecules/Divider`
- [x] `grep -rE '@renderer/components/organisms/Divider' src/renderer` returns nothing
- [x] The full Vitest unit + Playwright CT suites pass with no assertion changes
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T21:29:48Z
**Files changed**: src/renderer/src/components/molecules/Divider.tsx, src/renderer/src/components/molecules/Divider.css, src/renderer/src/components/organisms/Divider.tsx, src/renderer/src/components/organisms/Divider.css, src/renderer/src/components/organisms/PaneSplit.tsx, src/renderer/src/components/organisms/Sidebar.tsx, src/renderer/src/components/organisms/**tests**/Shell.stories.tsx, src/renderer/src/components/organisms/**tests**/Shell.test.tsx
**Contract**: Expects 4/4 | Produces 4/4
**Notes**: Pure git-mv relocation of Divider organisms→molecules + 4 importer path rewrites. typecheck/lint/build green; Vitest 336/336, Playwright CT 127/127 (run manually — no test command configured in verify gate).
