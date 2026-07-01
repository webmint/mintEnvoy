# Spec: reorganize-flat-components

**Date**: 2026-06-26
**Status**: Complete
**Design source**: none
**Author**: Claude + User

## 1. Overview

Reorganize the renderer's flat components/organisms/ folder so it stays navigable as later epics (C response, E persistence/collections/history, F navigation) add organisms toward a ~25-file count. Adopt a domain-placement convention in constitution §2.2, then apply it minimally: move the one genuinely shared primitive (Divider) to molecules/, group the shell-domain organisms under organisms/shell/, and keep Sidebar + TabBar as flat domain singletons. The change is pure file relocation + import-path updates with zero behavior change — all tests stay green.

## 2. Current State

All seven renderer organisms sit flat under src/renderer/src/components/organisms/ (Divider, PaneSplit, Shell, Sidebar, Statusbar, TabBar, Titlebar), each with a sibling .css and co-located **tests**/ fixtures. Two placement defects exist: (1) Divider (src/renderer/src/components/organisms/Divider.tsx) is a domain-agnostic primitive — imports only ./Divider.css, react, and @renderer/lib/cx, with pure-primitive props and two consumers (PaneSplit.tsx:40, Sidebar.tsx:39) — yet lives in the organism tier; those two consumers are organism→organism sibling-tier imports that constitution §2.2:56 forbids (the live violation). (2) The folder has no domain grouping and no placement rule, so it trends toward an unnavigable junk drawer as epics land. PaneSplit (src/renderer/src/components/organisms/PaneSplit.tsx:40) is NOT a shared primitive: its public contract carries request/response vocabulary (props request?/response?, docstring 'request/response vertical split', sole consumer Shell.tsx:80), so it is shell/request-domain-bound. Shell.tsx is the sole production importer of Titlebar (Shell.tsx:78), PaneSplit (Shell.tsx:80), and Statusbar (Shell.tsx:81); App.tsx:3 imports Shell. All cross-module imports use the absolute @renderer alias (constitution §2.3:78). The current layout is enumerated in three classification sites: constitution §2.2:70 (membership tree), constitution §5.1:198 (UI primitives list), and docs/architecture.md (UI-Primitives Layer table + mermaid Dependency Overview).

## 3. Desired Behavior

Record a domain-placement convention as a single labelled rule inside constitution §2.2 (extending, not replacing, the §2.2:56 layering canon): shared + domain-agnostic → molecules/; single-domain-bound → organisms/<domain>/; create organisms/<domain>/ only when a domain reaches ≥2 components (no empty future domain folders); NO barrel/index files. Apply the rule minimally now: (a) move Divider.tsx + Divider.css from organisms/ to molecules/ (clears the §2.2:56 sibling-import violation); (b) move Shell, Titlebar, Statusbar, PaneSplit (.tsx + .css) into organisms/shell/ (PaneSplit joins its sole consumer Shell; molecules/ would breach the agnostic-tier invariant); (c) keep Sidebar and TabBar flat as domain singletons. Update every absolute @renderer import path that references a moved file — production callers and co-located test/story fixtures alike — and move each moved component's sibling .css and **tests**/ fixtures with it. Update all three classification sites in lockstep: constitution §2.2 membership tree (the EXAMPLE module-structure tree) + §5.1:198, and docs/architecture.md (UI-Primitives Layer table + mermaid). Zero behavior change: no prop, export-surface, runtime, or logic change; type-check, lint, build, and the full unit + Playwright CT suites all pass.

## 4. Affected Areas

| Area                                               | Files                                                                                                                                                                                                                                                                                                                                                                                                                        | Impact                                                                                                                                                                                                                                                                        |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Divider (organisms → molecules)                    | src/renderer/src/components/organisms/Divider.tsx, src/renderer/src/components/organisms/Divider.css                                                                                                                                                                                                                                                                                                                         | Move both files to src/renderer/src/components/molecules/; sibling .css travels with the .tsx. Resolves the §2.2:56 sibling-tier import violation.                                                                                                                            |
| Shell-domain group (organisms → organisms/shell)   | src/renderer/src/components/organisms/Shell.tsx, src/renderer/src/components/organisms/Shell.css, src/renderer/src/components/organisms/Titlebar.tsx, src/renderer/src/components/organisms/Titlebar.css, src/renderer/src/components/organisms/Statusbar.tsx, src/renderer/src/components/organisms/Statusbar.css, src/renderer/src/components/organisms/PaneSplit.tsx, src/renderer/src/components/organisms/PaneSplit.css | Move all four components + sibling .css into new src/renderer/src/components/organisms/shell/; PaneSplit co-locates with its sole consumer Shell.                                                                                                                             |
| Flat domain singletons (unchanged location)        | src/renderer/src/components/organisms/Sidebar.tsx, src/renderer/src/components/organisms/Sidebar.css, src/renderer/src/components/organisms/TabBar.tsx, src/renderer/src/components/organisms/TabBar.css                                                                                                                                                                                                                     | Stay flat under organisms/; only their @renderer import of the moved Divider (Sidebar) is rewritten. No file move.                                                                                                                                                            |
| Production import-path updates                     | src/renderer/src/App.tsx, src/renderer/src/components/organisms/Sidebar.tsx, src/renderer/src/components/organisms/Shell.tsx, src/renderer/src/components/organisms/PaneSplit.tsx                                                                                                                                                                                                                                            | Rewrite @renderer paths to moved files: App.tsx:3 (Shell); Sidebar.tsx:39 (Divider); Shell.tsx:78/80/81 (Titlebar/PaneSplit/Statusbar); PaneSplit.tsx:40 (Divider). Shell's import of flat Sidebar is unchanged.                                                              |
| Test + story fixture import-path updates           | src/renderer/src/components/organisms/**tests**/Shell.test.tsx, src/renderer/src/components/organisms/**tests**/Shell.stories.tsx, src/renderer/src/components/molecules/**tests**/Tabs.stories.tsx                                                                                                                                                                                                                          | Rewrite @renderer paths to moved files: Shell.test.tsx:23/25/26/27/28 + Shell.stories.tsx:14/15/17/18/19 (Shell/Titlebar/Statusbar/PaneSplit/Divider); Tabs.stories.tsx:45 (cross-file Shell.css import). Move co-located test/story fixtures with their component as needed. |
| Constitution placement rule + classification sites | constitution.md                                                                                                                                                                                                                                                                                                                                                                                                              | Add the labelled domain-placement rule inside §2.2; update the §2.2 EXAMPLE membership tree (l.70 region) and the §5.1 UI-primitives list (l.198) to the new layout. Conscious update — no silent config drift.                                                               |
| Architecture doc classification sites              | docs/architecture.md                                                                                                                                                                                                                                                                                                                                                                                                         | Update the renderer UI-Primitives Layer table + mermaid Dependency Overview so the third classification site matches the new layout (per the in-feature docs decision).                                                                                                       |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The reorganized renderer component tree shall contain no barrel or index re-export file in components/molecules/, components/organisms/, or components/organisms/shell/.
  > Verification: test -z "$(find src/renderer/src/components/molecules src/renderer/src/components/organisms -maxdepth 2 -name 'index.ts' -o -name 'index.tsx' 2>/dev/null)"
- [x] **AC-2**: The renderer source tree shall place the Divider component and its sibling stylesheet under components/molecules/ rather than components/organisms/.
  > Verification: test -f src/renderer/src/components/molecules/Divider.tsx && test -f src/renderer/src/components/molecules/Divider.css && ! test -e src/renderer/src/components/organisms/Divider.tsx && ! test -e src/renderer/src/components/organisms/Divider.css
- [x] **AC-3**: The renderer source tree shall place Shell, Titlebar, Statusbar, and PaneSplit (component and stylesheet files) under components/organisms/shell/ rather than directly under components/organisms/.
  > Verification: for n in Shell Titlebar Statusbar PaneSplit; do test -f src/renderer/src/components/organisms/shell/$n.tsx && test -f src/renderer/src/components/organisms/shell/$n.css && ! test -e src/renderer/src/components/organisms/$n.tsx || exit 1; done
- [x] **AC-4**: The renderer source tree shall retain Sidebar and TabBar directly under components/organisms/ as flat domain singletons.
  > Verification: test -f src/renderer/src/components/organisms/Sidebar.tsx && test -f src/renderer/src/components/organisms/TabBar.tsx && test -f src/renderer/src/components/organisms/Sidebar.css && test -f src/renderer/src/components/organisms/TabBar.css

### 5.2 Behavior preservation

- [x] **AC-5**: The moved components shall preserve their public export surface, prop types, and runtime behavior unchanged by the relocation.
- [x] **AC-6**: WHILE the user drags a pane or sidebar divider, the system shall write the same CSS custom properties to the document root element as before the move.
- [x] **AC-7**: The full Vitest unit suite and Playwright component-test suite shall pass without any modification to test assertions.
  > Verification: npm run test --silent

### 5.3 Behavior change

N/A — Zero-behavior-change refactor: no runtime behavior changes; only file locations, import paths, and documentation change.

### 5.4 CI / pipeline

N/A — No CI or pipeline configuration is added or changed by this reorganization.

### 5.5 Hooks / gates

N/A — No git hooks or quality gates are added or changed; existing type-check/lint/build gates are reused unchanged.

### 5.6 Documentation

- [x] **AC-8**: The constitution renderer-tier section shall record the domain-placement rule as a single labelled rule that extends the existing tier-layering canon.
- [x] **AC-9**: The constitution membership tree and the UI-primitives entity list shall both reflect the new component layout in lockstep.
- [x] **AC-10**: The architecture documentation UI-primitives table and dependency diagram shall reflect the new component layout.

### 5.7 Hygiene

- [x] **AC-11**: The renderer shall contain no import that references a moved component at its former organisms path.
  > Verification: ! grep -rqE '@renderer/components/organisms/(Divider|Shell|Titlebar|Statusbar|PaneSplit)' src/renderer
- [x] **AC-12**: The production build shall succeed.
  > Verification: npm run build
- [x] **AC-13**: The renderer type-check shall pass for both the node and web TypeScript configurations.
  > Verification: npm run typecheck:node && npm run typecheck:web
- [x] **AC-14**: The linter shall pass on all changed files.
  > Verification: npm run lint

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Promoting PaneSplit to molecules/ — that would require a non-zero-change prop rename (request/response → primary/secondary) to strip its domain vocabulary; deferred to a separate future change. — F-2026-06-26-reorganize-the-flat-components-6
- NOT included: Choosing PaneSplit's long-term home (organisms/shell/ now vs a future organisms/workspace/ or organisms/response/) — revisited when epic C ships.
- NOT included: Creating domain subfolders for future epics (response, persistence, navigation) ahead of need — a domain folder is created only when it reaches >=2 components (no empty future folders).
- NOT included: Moving Sidebar or TabBar into domain subfolders — both stay flat domain singletons.
- NOT included: Any back-compat re-export shim or barrel/index file at the old organisms/ paths.
- NOT included: Any runtime, logic, styling, or accessibility behavior change to the moved components.

## 7. Technical Constraints

- Must follow: §2.2 Renderer Tier Organization (constitution.md:56)
- Must follow: §2.2 membership tree (constitution.md:70)
- Must follow: §5.1 UI primitives (constitution.md:198)
- Must follow: §6.1 Minimal Changes (constitution.md:213)
- Must follow: Search before building
- Must follow: Move each relocated component's sibling .css and co-located **tests**/ fixtures together with its .tsx, and update all @renderer import paths in both production callers and test/story fixtures.
- Must follow: Make no logic, prop, export-surface, or visual change; keep the work to one logical refactor commit per Conventional Commits.
- Must not break: Preserve the Shell store-to-documentElement CSS-var contract and the Divider ratio-valued drag mapping exactly (PaneSplit composes Divider for the pane ratio).
- Must follow constitution §2.2: renderer component tiers flow downward only: organisms -> molecules -> atoms; no sibling-tier or upward imports
- Must follow constitution §6.1: every change impacts as little code as possible; never fix unrelated code you happen to see
- Must follow constitution §2.3: renderer imports cross-module code via the @renderer alias rather than deep relative paths

## 8. Open Questions

- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes

## 9. Risks

| Risk                                                                                                                                                                                                                                                                                        | Likelihood | Impact | Mitigation                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Import-graph breakage if any path missed (caught by tsc zero-unresolved + build); CSS co-location/load-order must travel with each .tsx (Shell.css/TabBar.css coupling proven brittle in 005); test/story import paths must move too. All mechanically detectable — no silent runtime risk. | Med        | Med    | tbd via /plan                                                                                                                                                                        |
| A moved-file import path is missed, breaking the renderer import graph.                                                                                                                                                                                                                     | Low        | High   | Type-check (both configs, zero unresolved) plus the production build statically catch every dangling import before completion; the §5.7 grep AC asserts no old-path import survives. |
| A moved component's sibling .css or a cross-file CSS coupling (e.g. Tabs.stories.tsx importing Shell.css) is dropped, silently degrading visuals.                                                                                                                                           | Med        | Med    | Move each .css atomically with its .tsx, rewrite the cross-file css import, and rely on the Playwright CT fidelity suite to catch visual regression.                                 |
| The three classification sites (constitution membership tree, constitution UI-primitives list, architecture doc) drift out of lockstep.                                                                                                                                                     | Low        | Med    | Update all three sites in the same change; §5.6 ACs assert each reflects the new layout.                                                                                             |
