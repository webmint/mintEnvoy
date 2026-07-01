# Plan: reorganize-flat-components

**Date**: 2026-06-26
**Spec**: specs/006-reorganize-flat-components/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A (the 3 alternatives were settled upstream in the research handoff `adopt_rule_corrected_panesplit_placement_organisms_shell`; per the seed-from-plan-seeds rule no fresh alternative discovery is run, and no new unsettled alternative arose)
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — see table

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: rows 1-5
- Key Design Decisions: rows a-e
- Risk Assessment seeds: rows 1-5
- Constitution Compliance flags: §2.2:56 (cleared), §2.2 rule edit, §2.2:70 tree, §5.1:198 list, §2.3 alias, §6.1 minimal

| Specialist | Sub-question | Input summary | Verdict | Cites |
| ---------- | ------------ | ------------- | ------- | ----- |
| (none)     | —            | —             | —       | —     |

The architect consulted no specialists: the approach is settled upstream, every risk is mechanical and statically detectable (tsc + build + grep ACs), and the one subtle coupling (Shell.ct.tsx → `./Shell.stories` relative import) was already resolved in planning recon. Decided from architect's own reasoning.

## Summary

This plan implements a zero-behavior-change relocation of the renderer's flat `components/organisms/` tree. It extends constitution §2.2's existing layering canon with a single labelled domain-placement rule, then applies it minimally: Divider (a domain-agnostic shared primitive) moves to `molecules/` — clearing the live §2.2:56 sibling-tier import violation — while Shell, Titlebar, Statusbar, and PaneSplit group under a new `organisms/shell/`, and Sidebar + TabBar stay flat as domain singletons. The change is pure file moves + `@renderer` import-path rewrites with no prop, export-surface, runtime, or logic change; correctness is proven mechanically by type-check (both configs), build, the full Vitest + Playwright CT suites, and an old-path grep gate.

**Why no new research**: No Phase 0 signals — pure file relocation, no external dependency, no new tech, and the one architectural choice (PaneSplit's tier) was settled by the upstream research handoff (recommended approach `adopt_rule_corrected_panesplit_placement_organisms_shell`). Two findings quoted from that handoff anchor the design: (1) "Divider alone is the genuinely shared primitive and its move to molecules/ additionally clears the live §2.2:56 sibling-import violation (PaneSplit->Divider, Sidebar->Divider)"; (2) PaneSplit "carries request/response vocabulary (props, docstring) with a single Shell consumer, so molecules/ would breach the feature-agnostic invariant ... -> organisms/shell/ is its correct home."

## Technical Context

**Architecture**: Renderer atomic-design tiers (constitution §2.2). The move touches `components/molecules/` (gains Divider), a new `components/organisms/shell/` subfolder (gains the shell-domain group), and leaves `components/organisms/` flat for the Sidebar/TabBar singletons. `atoms/`, `lib/`, and `styles/` are untouched.
**Error Handling**: N/A — no runtime logic changes; no new fallible operations introduced.
**State Management**: Unchanged — the Shell `settingsStore`→`documentElement` CSS-var contract and the Divider ratio-valued drag mapping are preserved byte-for-byte (move-only).

## Constitution Compliance

- §2.2:56 (downward-only tiers, no sibling/upward imports): **compliant — the move CLEARS the live violation.** PaneSplit→Divider and Sidebar→Divider become legal organism→molecule downward imports; zero residual sibling imports remain.
- §2.2 (domain-placement rule): **requires intentional edit (AC-8).** A single labelled rule is ADDED to §2.2 that EXTENDS the layering canon — a conscious amendment, not a rewrite.
- §2.2:70 (EXAMPLE membership tree): **requires lockstep update (AC-9)** to the new layout.
- §5.1:198 (UI-primitives list): **requires lockstep update (AC-9)** — Divider reclassified as molecule, shell organisms grouped.
- §2.3 (@renderer alias): **compliant** — all cross-module import rewrites stay on the `@renderer` alias; the only relative import (Shell.ct.tsx → `./Shell.stories`) is a pre-existing intra-fixture story-glue import preserved relative.
- §6.1 (minimal changes): **compliant** — only moved-path references are touched; no unrelated code modified.

## Implementation Approach

### Layer Map

| Layer                                         | What the move touches                                                                                                                                        | Files (existing or new)                                                               |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `components/molecules/`                       | Receives Divider — the one genuinely domain-agnostic shared primitive; its two consumers become legal organism→molecule downward imports                     | `Divider.tsx`, `Divider.css` (from `organisms/`)                                      |
| `components/organisms/shell/` (NEW)           | Shell-domain group; PaneSplit co-locates with its sole consumer Shell (props carry request/response vocabulary → cannot live in the agnostic molecules tier) | `Shell.{tsx,css}`, `Titlebar.{tsx,css}`, `Statusbar.{tsx,css}`, `PaneSplit.{tsx,css}` |
| `components/organisms/shell/__tests__/` (NEW) | Shell test trio moves intact (relative `./Shell.stories` coupling)                                                                                           | `Shell.test.tsx`, `Shell.stories.tsx`, `Shell.ct.tsx`                                 |
| `components/organisms/` (flat, unchanged)     | Domain singletons stay; Sidebar rewrites only its Divider import                                                                                             | `Sidebar.{tsx,css}`, `TabBar.{tsx,css}`, `__tests__/TabBar.test.tsx` (stays)          |
| `components/atoms/`, `lib/`, `styles/`        | Untouched — no move, no import rewrite                                                                                                                       | —                                                                                     |

### Key Design Decisions

| Decision                                          | Chosen Approach                                                                                                                                                                                                                                                                            | Why                                                                                                                                                                                                                                                                                                                                                         | Alternatives Rejected                                                                                                        |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| (a) Divider placement                             | `organisms/` → `molecules/`                                                                                                                                                                                                                                                                | Divider is domain-agnostic (imports only `./Divider.css`, react, `@renderer/lib/cx`; pure-primitive props; 2 consumers). Move makes PaneSplit→Divider and Sidebar→Divider legal organism→molecule downward imports, clearing the live §2.2:56 sibling-tier violation. Enforces the existing canon. (AC-2)                                                   | Keep in organisms/: leaves the §2.2:56 violation live and mis-tiers a shared primitive                                       |
| (b) PaneSplit placement                           | `organisms/` → `organisms/shell/`                                                                                                                                                                                                                                                          | Public contract carries domain vocabulary (props `request?`/`response?`, docstring "request/response vertical split", sole consumer Shell.tsx:80). molecules/ would breach the agnostic-tier invariant, and a zero-change move cannot strip the binding. Joins its consumer in the shell group. (AC-3)                                                      | PaneSplit→molecules/: §6-deferred (needs non-zero prop rename request/response→primary/secondary)                            |
| (c) Shell test trio + its `__tests__/`            | All three (`Shell.test.tsx`, `Shell.stories.tsx`, `Shell.ct.tsx`) → new `organisms/shell/__tests__/`; TabBar.test.tsx stays in `organisms/__tests__/`                                                                                                                                      | `Shell.ct.tsx` imports `./Shell.stories` by RELATIVE path — splitting the trio breaks that coupling. Co-locating tests at the new folder level follows the tests-next-to-code convention. (AC-7, constraint "move co-located **tests** together")                                                                                                           | Leave trio in `organisms/__tests__/`: dangles the relative import or forces a §2.3-discouraged deep relative path            |
| (d) Barrel / index files                          | None — at any of molecules/, organisms/, organisms/shell/                                                                                                                                                                                                                                  | Re-export tax, worse tree-shaking, cycle risk; `@renderer` already gives clean paths. Codebase has zero barrel files today — continuing is consistency. (AC-1)                                                                                                                                                                                              | Add `index.ts` re-exports: explicitly OOS (§6) and contradicts the chosen convention                                         |
| (e) docs/architecture.md beyond-§4 citation sites | Update ALL five moved-path sites in lockstep: UI-Primitives table (l.30), prose tier description (l.68), module-structure tree (l.83), the two code-comment markers `organisms/Shell.tsx:250` (l.136) and `organisms/Divider.tsx:250` (l.160), and the mermaid Dependency Overview (l.310) | AC-10 names only table + diagram, but a moved-path marker left stale is a dangling reference the feature itself creates; §3 mandates lockstep and §6.1 demands conscious-update-no-silent-drift. Updating exactly the moved-path references (line numbers unchanged — only the dir prefix moves) is the minimal set that leaves docs internally consistent. | Update only table+mermaid (literal AC-10): leaves 3 stale path sites, breaking the lockstep guarantee with no AC to catch it |

### File Impact

| File                                                                                                                | Action        | What Changes                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `src/renderer/src/components/organisms/Divider.tsx` → `molecules/Divider.tsx`                                       | Move          | Relocate; no content change                                                                                                            |
| `src/renderer/src/components/organisms/Divider.css` → `molecules/Divider.css`                                       | Move          | Sibling .css travels with .tsx                                                                                                         |
| `src/renderer/src/components/organisms/Shell.tsx` → `organisms/shell/Shell.tsx`                                     | Move + Modify | Relocate; rewrite `@renderer` imports of Titlebar/PaneSplit/Statusbar to `organisms/shell/*` (Sidebar import unchanged)                |
| `src/renderer/src/components/organisms/Shell.css` → `organisms/shell/Shell.css`                                     | Move          | Sibling .css travels                                                                                                                   |
| `src/renderer/src/components/organisms/Titlebar.{tsx,css}` → `organisms/shell/Titlebar.{tsx,css}`                   | Move          | Relocate; no content change                                                                                                            |
| `src/renderer/src/components/organisms/Statusbar.{tsx,css}` → `organisms/shell/Statusbar.{tsx,css}`                 | Move          | Relocate; no content change                                                                                                            |
| `src/renderer/src/components/organisms/PaneSplit.tsx` → `organisms/shell/PaneSplit.tsx`                             | Move + Modify | Relocate; rewrite `@renderer` import of Divider → `molecules/Divider`                                                                  |
| `src/renderer/src/components/organisms/PaneSplit.css` → `organisms/shell/PaneSplit.css`                             | Move          | Sibling .css travels                                                                                                                   |
| `src/renderer/src/components/organisms/Sidebar.tsx`                                                                 | Modify        | Rewrite line 39 Divider import → `@renderer/components/molecules/Divider` (no move)                                                    |
| `src/renderer/src/components/organisms/TabBar.{tsx,css}`                                                            | None          | Flat singleton, no moved-file import                                                                                                   |
| `src/renderer/src/App.tsx`                                                                                          | Modify        | Rewrite line 3 Shell import → `@renderer/components/organisms/shell/Shell`                                                             |
| `src/renderer/src/components/organisms/__tests__/Shell.test.tsx` → `organisms/shell/__tests__/Shell.test.tsx`       | Move + Modify | Relocate; rewrite `@renderer` imports of Shell/Titlebar/Statusbar/PaneSplit → `organisms/shell/*` and Divider → `molecules/Divider`    |
| `src/renderer/src/components/organisms/__tests__/Shell.stories.tsx` → `organisms/shell/__tests__/Shell.stories.tsx` | Move + Modify | Relocate; same `@renderer` rewrites as Shell.test.tsx                                                                                  |
| `src/renderer/src/components/organisms/__tests__/Shell.ct.tsx` → `organisms/shell/__tests__/Shell.ct.tsx`           | Move          | Relocate (DISCOVERY 1 — not in spec §4); relative `./Shell.stories` import preserved by moving together; no `@renderer` rewrite needed |
| `src/renderer/src/components/organisms/__tests__/TabBar.test.tsx`                                                   | None          | Stays in `organisms/__tests__/`; imports only flat TabBar                                                                              |
| `src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx`                                                  | Modify        | Rewrite line 45 cross-file `@renderer/components/organisms/Shell.css` import → `organisms/shell/Shell.css`                             |
| `constitution.md`                                                                                                   | Modify        | Add labelled domain-placement rule in §2.2; update §2.2:70 membership tree + §5.1:198 UI-primitives list to new layout                 |
| `docs/architecture.md`                                                                                              | Modify        | Update all 5 moved-path citation sites (table l.30, prose l.68, module tree l.83, markers l.136/l.160, mermaid l.310)                  |

### Documentation Impact

| Doc File             | Action | What Changes                                                                                                                                                                                                                                          |
| -------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| docs/architecture.md | Update | UI-Primitives Layer table row, prose tier description, module-structure tree, two code-comment path markers (Shell.tsx / Divider.tsx), and mermaid Dependency Overview — reclassify Divider as molecule, group shell organisms under organisms/shell/ |

Constitution updates (§2.2 rule + tree, §5.1 list) are tracked in File Impact above (they are spec-mandated classification sites, AC-8/AC-9). No package `docs/<package>/` overview/architecture changes — the move is internal to the renderer's component layout and the package-tier docs do not enumerate per-component paths.

## Risk Assessment

| Risk                                                                                                                                                                     | Likelihood | Impact  | Mitigation                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A moved-file `@renderer` import path is missed, breaking the renderer import graph                                                                                       | Low        | High    | `typecheck:node` + `typecheck:web` (zero unresolved) and `npm run build` statically catch every dangling import; AC-11 grep asserts no old `organisms/(Divider\|Shell\|Titlebar\|Statusbar\|PaneSplit)` path survives in `src/renderer`   |
| A sibling `.css` or cross-file CSS coupling is dropped, silently degrading visuals — esp. `Tabs.stories.tsx:45` importing `Shell.css` cross-folder (the 005 brittleness) | Med        | Med     | Move each `.css` atomically with its `.tsx`; rewrite the `Tabs.stories.tsx` Shell.css import to `organisms/shell/Shell.css`; Playwright CT fidelity suite catches regression (full styling context preserved — no className/scope change) |
| Shell test trio split breaks the `./Shell.stories` relative coupling                                                                                                     | Low        | Med     | Move all three files together to `organisms/shell/__tests__/` as one unit; keep the relative import relative (legal intra-fixture story-glue, not a cross-module §2.3 case)                                                               |
| Classification-site drift — docs code-comment markers (l.136/l.160) are NOT covered by any AC (AC-11 greps only `src/renderer`, AC-10 names only table+diagram)          | Med        | Low–Med | Explicit task step updates all 5 moved-path sites; add a manual `grep -nE 'organisms/(Divider\|Shell\|Titlebar\|Statusbar\|PaneSplit)' docs/architecture.md constitution.md` no-old-path check in the verify step                         |
| `@renderer`-alias regression — a rewritten import introduced as a deep relative path                                                                                     | Low        | Med     | All cross-module rewrites stay on the `@renderer` alias (§2.3); only the pre-existing `Shell.ct.tsx → ./Shell.stories` intra-fixture relative import is preserved relative                                                                |

## Dependencies

None — no packages to install, no services to configure, no environment variables. The move reuses the existing electron-vite `@renderer` alias, Vitest, and Playwright CT toolchains unchanged.

## Supporting Documents

- [Research handoff](../../research/2026-06-26-reorganize-the-flat-components/handoff.json) — settled the recommended approach (no new research.md generated; no Phase 0 signals)
