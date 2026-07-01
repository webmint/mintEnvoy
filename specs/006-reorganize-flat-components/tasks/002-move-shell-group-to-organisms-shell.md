# Task 002: Move shell-domain group and Shell test trio into organisms/shell

**Feature**: 006-reorganize-flat-components
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003
**Spec criteria**: AC-1, AC-3, AC-4, AC-5, AC-6, AC-7, AC-11, AC-12, AC-13, AC-14
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File                                                                                                                                        | Action        | Description                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/organisms/Shell.tsx → src/renderer/src/components/organisms/shell/Shell.tsx                                     | Move + Modify | Relocate; rewrite `@renderer` imports of Titlebar/PaneSplit/Statusbar to `organisms/shell/*` (Sidebar import unchanged)                                                 |
| src/renderer/src/components/organisms/Shell.css → src/renderer/src/components/organisms/shell/Shell.css                                     | Move          | Sibling stylesheet travels with the .tsx                                                                                                                                |
| src/renderer/src/components/organisms/Titlebar.tsx → src/renderer/src/components/organisms/shell/Titlebar.tsx                               | Move          | Relocate; no content change (imports only the Icon atom, which does not move)                                                                                           |
| src/renderer/src/components/organisms/Titlebar.css → src/renderer/src/components/organisms/shell/Titlebar.css                               | Move          | Sibling stylesheet travels                                                                                                                                              |
| src/renderer/src/components/organisms/Statusbar.tsx → src/renderer/src/components/organisms/shell/Statusbar.tsx                             | Move          | Relocate; no content change (no component imports)                                                                                                                      |
| src/renderer/src/components/organisms/Statusbar.css → src/renderer/src/components/organisms/shell/Statusbar.css                             | Move          | Sibling stylesheet travels                                                                                                                                              |
| src/renderer/src/components/organisms/PaneSplit.tsx → src/renderer/src/components/organisms/shell/PaneSplit.tsx                             | Move          | Relocate; its Divider import already points at `molecules/Divider` (rewritten in task 001) and is NOT re-touched here                                                   |
| src/renderer/src/components/organisms/PaneSplit.css → src/renderer/src/components/organisms/shell/PaneSplit.css                             | Move          | Sibling stylesheet travels                                                                                                                                              |
| src/renderer/src/App.tsx                                                                                                                    | Modify        | Rewrite the Shell import to `@renderer/components/organisms/shell/Shell`                                                                                                |
| src/renderer/src/components/organisms/**tests**/Shell.test.tsx → src/renderer/src/components/organisms/shell/**tests**/Shell.test.tsx       | Move + Modify | Relocate; rewrite `@renderer` imports of Shell/Titlebar/Statusbar/PaneSplit to `organisms/shell/*` (Divider import already at molecules/ from task 001, not re-touched) |
| src/renderer/src/components/organisms/**tests**/Shell.stories.tsx → src/renderer/src/components/organisms/shell/**tests**/Shell.stories.tsx | Move + Modify | Relocate; same `@renderer` rewrites as Shell.test.tsx                                                                                                                   |
| src/renderer/src/components/organisms/**tests**/Shell.ct.tsx → src/renderer/src/components/organisms/shell/**tests**/Shell.ct.tsx           | Move          | Relocate; its relative `import … from './Shell.stories'` is preserved by moving together — no `@renderer` rewrite needed                                                |
| src/renderer/src/components/molecules/**tests**/Tabs.stories.tsx                                                                            | Modify        | Rewrite the cross-file `@renderer/components/organisms/Shell.css` import to `@renderer/components/organisms/shell/Shell.css`                                            |

## Description

Group the four shell-domain organisms — `Shell`, `Titlebar`, `Statusbar`, `PaneSplit` — together under a new `components/organisms/shell/` subfolder, moving each component's sibling `.css` with it, and relocate the Shell test trio (`Shell.test.tsx`, `Shell.stories.tsx`, `Shell.ct.tsx`) into a new `components/organisms/shell/__tests__/`. PaneSplit co-locates with its sole consumer Shell because its public contract carries request/response domain vocabulary (props `request?`/`response?`), so the agnostic molecules tier is wrong for it.

This is one logical relocation (the rename-across-many-files exception applies — keep it as a single task so the tree never sits in a half-moved, non-compiling state). Rewrite every `@renderer` import that references a moved file: `App.tsx` (Shell), `Shell.tsx` (its Titlebar/PaneSplit/Statusbar imports), the two moved Shell fixtures (Shell/Titlebar/Statusbar/PaneSplit imports), and `Tabs.stories.tsx` (the cross-file `Shell.css` import). The `Shell.ct.tsx` → `./Shell.stories` relative import stays relative and stays valid because the two files move together. `Sidebar`, `TabBar`, and `organisms/__tests__/TabBar.test.tsx` stay flat and are not moved. Create NO barrel/index files.

Pure relocation + import-path rewrites — no prop, export-surface, runtime, styling, or logic change. The Shell `settingsStore`→`documentElement` CSS-var contract must be preserved exactly.

## Change Details

- Move the four components and their sibling stylesheets into `src/renderer/src/components/organisms/shell/`:
  - `Shell.tsx`, `Shell.css`, `Titlebar.tsx`, `Titlebar.css`, `Statusbar.tsx`, `Statusbar.css`, `PaneSplit.tsx`, `PaneSplit.css`.
- Move the Shell test trio into `src/renderer/src/components/organisms/shell/__tests__/`:
  - `Shell.test.tsx`, `Shell.stories.tsx`, `Shell.ct.tsx`.
- In `src/renderer/src/components/organisms/shell/Shell.tsx` (moved):
  - Rewrite `import { Titlebar } from '@renderer/components/organisms/Titlebar'` → `'@renderer/components/organisms/shell/Titlebar'`.
  - Rewrite `import { PaneSplit } from '@renderer/components/organisms/PaneSplit'` → `'@renderer/components/organisms/shell/PaneSplit'`.
  - Rewrite `import { Statusbar } from '@renderer/components/organisms/Statusbar'` → `'@renderer/components/organisms/shell/Statusbar'`.
  - Leave the `Sidebar` import (`@renderer/components/organisms/Sidebar`) unchanged — Sidebar stays flat.
- In `src/renderer/src/App.tsx`:
  - Rewrite `import { Shell } from '@renderer/components/organisms/Shell'` → `'@renderer/components/organisms/shell/Shell'`. Leave the flat `TabBar` import unchanged.
- In the moved `__tests__/Shell.test.tsx` and `__tests__/Shell.stories.tsx`:
  - Rewrite the Shell/Titlebar/Statusbar/PaneSplit `@renderer` imports to `@renderer/components/organisms/shell/*`. Do NOT re-touch the Divider import — it already points at `@renderer/components/molecules/Divider` (task 001).
- In the moved `__tests__/Shell.ct.tsx`:
  - No import edits — the relative `./Shell.stories` import remains valid because `Shell.stories.tsx` moved into the same `__tests__/` folder.
- In `src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx`:
  - Rewrite `import '@renderer/components/organisms/Shell.css'` → `import '@renderer/components/organisms/shell/Shell.css'`.
- Create no `index.ts`/`index.tsx` barrel file in `molecules/`, `organisms/`, or `organisms/shell/`.

## Contracts

### Expects (checked before execution)

- (from task 001) `PaneSplit.tsx` imports `Divider` from `@renderer/components/molecules/Divider`; `__tests__/Shell.test.tsx` and `__tests__/Shell.stories.tsx` import `Divider` from `@renderer/components/molecules/Divider`.
- `Shell.tsx` (at `organisms/`) imports `Titlebar`, `PaneSplit`, `Statusbar` from `@renderer/components/organisms/*`.
- `App.tsx` imports `Shell` from `@renderer/components/organisms/Shell`.
- `__tests__/Shell.ct.tsx` imports from `./Shell.stories`.
- `Tabs.stories.tsx` imports `@renderer/components/organisms/Shell.css`.

### Produces (checked after execution)

- `components/organisms/shell/Shell.tsx`, `Titlebar.tsx`, `Statusbar.tsx`, `PaneSplit.tsx` exist (each exporting its component) with sibling `.css` files; none of these `.tsx`/`.css` files remain directly under `components/organisms/`.
- `components/organisms/shell/__tests__/Shell.test.tsx`, `Shell.stories.tsx`, `Shell.ct.tsx` exist; `Shell.ct.tsx` still imports from `./Shell.stories`.
- `App.tsx` imports `Shell` from `@renderer/components/organisms/shell/Shell`.
- `Shell.tsx` imports `Titlebar`/`PaneSplit`/`Statusbar` from `@renderer/components/organisms/shell/*`.
- `Tabs.stories.tsx` imports `@renderer/components/organisms/shell/Shell.css`.
- `Sidebar.tsx`, `TabBar.tsx` (and `TabBar.css`) and `organisms/__tests__/TabBar.test.tsx` remain directly under `components/organisms/`.
- No `index.ts` or `index.tsx` file exists in `components/molecules/`, `components/organisms/`, or `components/organisms/shell/`.
- No occurrence of `@renderer/components/organisms/(Shell|Titlebar|Statusbar|PaneSplit)` anywhere under `src/renderer`.

## Done When

- [x] `Shell`, `Titlebar`, `Statusbar`, `PaneSplit` (`.tsx` + `.css`) live under `components/organisms/shell/` and no longer directly under `components/organisms/`
- [x] The Shell test trio lives under `components/organisms/shell/__tests__/`; `Shell.ct.tsx`'s `./Shell.stories` import resolves
- [x] `Sidebar` and `TabBar` remain flat under `components/organisms/`
- [x] No barrel/index file exists in `molecules/`, `organisms/`, or `organisms/shell/`
- [x] `grep -rE '@renderer/components/organisms/(Divider|Shell|Titlebar|Statusbar|PaneSplit)' src/renderer` returns nothing
- [x] The production build (`npm run build`) succeeds
- [x] The full Vitest unit + Playwright CT suites pass with no assertion changes
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (both node and web configs)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T21:58:03Z
**Files changed**: src/renderer/src/App.tsx, src/renderer/src/components/molecules/**tests**/Tabs.stories.tsx, src/renderer/src/components/organisms/shell/Shell.tsx, src/renderer/src/components/organisms/shell/Shell.css, src/renderer/src/components/organisms/shell/Titlebar.tsx, src/renderer/src/components/organisms/shell/Titlebar.css, src/renderer/src/components/organisms/shell/Statusbar.tsx, src/renderer/src/components/organisms/shell/Statusbar.css, src/renderer/src/components/organisms/shell/PaneSplit.tsx, src/renderer/src/components/organisms/shell/PaneSplit.css, src/renderer/src/components/organisms/shell/**tests**/Shell.test.tsx, src/renderer/src/components/organisms/shell/**tests**/Shell.stories.tsx, src/renderer/src/components/organisms/shell/**tests**/Shell.ct.tsx
**Contract**: Expects 5/5 | Produces 8/8
**Notes**: git-mv relocation of shell group (Shell/Titlebar/Statusbar/PaneSplit +css) + test trio into organisms/shell/; 6 importer rewrites (App, Shell internal x3, 2 fixtures, Tabs.stories css). typecheck/lint/build green; Vitest 336/336, CT 127/127. Stale playwright/.cache caused transient EISDIR (cleared, non-code); one pre-existing CT timing flake (ShellCollapsedFixture) passed on re-run.
