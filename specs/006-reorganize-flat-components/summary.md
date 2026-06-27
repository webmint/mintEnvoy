# Summary: reorganize-flat-components

**Feature**: 006-reorganize-flat-components
**Verdict**: APPROVED (see [verification.md](verification.md)) · **Spec status**: Complete

## What was built

The renderer's flat `components/organisms/` folder is reorganized into a navigable, domain-grouped layout so it stays scannable as later epics add organisms. A single labelled domain-placement convention is recorded in the constitution (`shared/domain-agnostic → molecules/`; `single-domain-bound → organisms/<domain>/`; a domain subfolder only at ≥2 components; no barrel files), then applied minimally. The change is a pure relocation with zero behavior change — no prop, export-surface, runtime, or visual change; every test stays green.

## Changes

- **Divider → molecules**: the one genuinely domain-agnostic primitive moved from `organisms/` to `molecules/`, which also cleared a live constitution §2.2 sibling-tier import violation (`PaneSplit → Divider`, `Sidebar → Divider` became legal downward imports).
- **Shell domain grouped**: `Shell`, `Titlebar`, `Statusbar`, `PaneSplit` (and the Shell test trio) moved into a new `organisms/shell/` subfolder; `Sidebar` and `TabBar` kept flat as domain singletons.
- **Classification sites updated in lockstep**: the constitution §2.2 domain-placement rule + membership tree, the §5.1 UI-primitives list, and `docs/architecture.md` (table, prose, module tree, code-comment markers, mermaid diagram) all updated to the new layout.
- **Follow-up cleanups** (gated `/fix` cycles): Divider's isolation tests co-located into `molecules/__tests__/`, and the duplicated `simulateDrag` test helper extracted to a shared `test-utils/simulateDrag.ts`.

## Files changed

39 files, +3623 / −1918 (the large line counts are dominated by relocated test files and planning artifacts; the runtime delta is import-path-only).

- `src/renderer/src/components/` — Divider moved to `molecules/`; Shell/Titlebar/Statusbar/PaneSplit moved to `organisms/shell/`; Sidebar/App/PaneSplit + the Shell test trio + `Tabs.stories.tsx` import-path rewrites; new co-located `molecules/__tests__/Divider.{test,ct,stories}.tsx`.
- `src/renderer/src/test-utils/simulateDrag.ts` — new shared test helper.
- `constitution.md`, `docs/architecture.md` — classification-site updates.
- `specs/006-reorganize-flat-components/` — planning + pipeline artifacts (spec, plan, tasks, review, verification).

## Key decisions

- **Divider → `molecules/`**: domain-agnostic shared primitive; the move enforces the existing tier canon and clears the sibling-import violation.
- **PaneSplit → `organisms/shell/`** (not `molecules/`): its public contract carries request/response domain vocabulary, so the agnostic molecules tier would breach the feature-agnostic invariant; promoting it to molecules was deferred (needs a non-zero prop rename).
- **Shell test trio moved together**: `Shell.ct.tsx` imports `./Shell.stories` relatively, so all three move as a unit to keep the coupling valid.
- **No barrel/index files**: kept consistent with the existing codebase; clean `@renderer` paths already suffice.
- **All five `docs/architecture.md` citation sites updated in lockstep** (beyond the two AC-10 named), so no moved-path reference is left stale.

## Deviations from plan

- Two follow-up gated `/fix` cycles landed beyond the original 3 tasks: test co-location (a §3.4 finding from `/review`) and `simulateDrag` dedup — both behavior-preserving test-hygiene repairs, verified clean.
- The scope-aware verify gate has no test command configured for the renderer package, so the Vitest (336/336) and Playwright CT (127/127) suites were run manually to confirm AC-7.
- A pre-existing, unrelated `Dropdown.ct.tsx` CT flake (2 `not.toBeVisible()` click-outside failures) was observed and confirmed failing on the clean baseline — out of scope for this feature; recommend filing separately.

## Acceptance criteria

All 14 verified PASS by `/verify` (mode `tests`; 9 shell-verified, 5 code-read):

- [x] AC-1 — no barrel/index files in molecules/organisms/organisms-shell
- [x] AC-2 — Divider (+css) under molecules/
- [x] AC-3 — Shell/Titlebar/Statusbar/PaneSplit (+css) under organisms/shell/
- [x] AC-4 — Sidebar/TabBar retained flat under organisms/
- [x] AC-5 — moved components preserve export surface/props/runtime
- [x] AC-6 — drag CSS-var contract unchanged
- [x] AC-7 — full Vitest + Playwright CT suites pass, no assertion changes
- [x] AC-8 — constitution records the labelled domain-placement rule
- [x] AC-9 — constitution membership tree + UI-primitives list in lockstep
- [x] AC-10 — architecture doc table + dependency diagram reflect new layout
- [x] AC-11 — no import references a moved component's former organisms path
- [x] AC-12 — production build succeeds
- [x] AC-13 — type-check passes (node + web)
- [x] AC-14 — linter passes on changed files
