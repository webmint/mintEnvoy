# Project Memory

## Architecture Decisions

<!-- Populated during constitute — records WHY decisions were made, not just what -->

## Known Pitfalls

<!-- Populated during work as mistakes are discovered -->

## What Worked

<!-- Patterns and approaches that solved problems well -->

## What Failed

<!-- Approaches that were tried and didn't work — avoid repeating these -->

## Task Outcomes

- **[Task 001 / 001-ui-primitives]**: set up renderer test stack and radix dependency — completed. _(Task 001)_
- **[Task 002 / 001-ui-primitives]**: define the project-owned icon set and lookup — completed. _(Task 002)_
- **[Task 003 / 001-ui-primitives]**: build the inline SVG Icon component — completed. _(Task 003)_
- **[Task 004 / 001-ui-primitives]**: build the zustand toastStore and imperative toast() API — completed. _(Task 004)_
- **[Task 005 / 001-ui-primitives]**: build the Toast component over Radix Toast — completed. _(Task 005)_
- **[Task 006 / 001-ui-primitives]**: build the Modal component over Radix Dialog — completed. _(Task 006)_
- **[Task 007 / 001-ui-primitives]**: Dropdown over Radix — completed. _(Task 007)_
- **[Task 008 / 001-ui-primitives]**: mount overlay substrate at App root — completed. _(Task 008)_
- **[Task 009 / 001-ui-primitives]**: build the dev-only primitives demo route — completed. _(Task 009)_

- **[Task 002 / 002-tabs-primitive]**: write-tabs-tests — completed. _(Task 002)_
- **[Task 003 / 002-tabs-primitive]**: register-tabs-in-primitivesdemo — completed. _(Task 003)_
- **[Task 001 / 003-app-shell-layout]**: create-settings-store — completed. _(Task 001)_
- **[Task 002 / 003-app-shell-layout]**: create-divider — completed. _(Task 002)_
- **[Task 003 / 003-app-shell-layout]**: create-sidebar — completed. _(Task 003)_
- **[Task 004 / 003-app-shell-layout]**: create-panesplit — completed. _(Task 004)_
- **[Task 005 / 003-app-shell-layout]**: create-titlebar — completed. _(Task 005)_
- **[Task 006 / 003-app-shell-layout]**: create-statusbar — completed. _(Task 006)_
- **[Task 007 / 003-app-shell-layout]**: shell-composition-and-store-dom-effects — completed. _(Task 007)_
- **[Task 008 / 003-app-shell-layout]**: shell-behaviors-resize-cmdb-focus — completed. _(Task 008)_
- **[Task 009 / 003-app-shell-layout]**: wire-shell-into-app — completed. _(Task 009)_
- **[Task 010 / 003-app-shell-layout]**: set-window-minwidth — completed. _(Task 010)_
- **[Task 011 / 003-app-shell-layout]**: shell-tests — completed. _(Task 011)_

- **[Task 001 / 004-working-tabs-state-machine]**: Create RequestSpec domain model — completed. _(Task 001)_
- **[Task 002 / 004-working-tabs-state-machine]**: Create tabsStore zustand slice — completed. _(Task 002)_
- **[Task 003 / 004-working-tabs-state-machine]**: Write tabsStore unit suite + serialization contract — completed. _(Task 003)_
- **[Task 004 / 004-working-tabs-state-machine]**: Extend Tabs primitive with opt-in closable/onClose — completed. _(Task 004)_
- **[Task 005 / 004-working-tabs-state-machine]**: Extend Tabs tests for closable extension — completed. _(Task 005)_
- **[Task 006 / 004-working-tabs-state-machine]**: Record Tabs contract extension in feature-002 lineage — completed. _(Task 006)_
- **[Task 007 / 004-working-tabs-state-machine]**: Create TabBar organism — completed. _(Task 007)_
- **[Task 008 / 004-working-tabs-state-machine]**: Write TabBar tests — completed. _(Task 008)_
- **[Task 009 / 004-working-tabs-state-machine]**: Wire TabBar into Shell tabs slot via App.tsx — completed. _(Task 009)_
- **[Task 010 / 004-working-tabs-state-machine]**: Register closable Tabs variant in PrimitivesDemo — completed. _(Task 010)_
- **[Task 001 / 007-remove-ping-handler]**: Remove dead ping IPC handler from main process — completed. _(Task 001)_
## 2026-06-22 — /verify scope pollution (feature 001-ui-primitives)

**Lesson**: /verify computed NEEDS WORK entirely from artifacts, not real defects. Causes: (1) `review.md` was stale — its 7 confirmed findings were already remediated by `/fix` before `/verify` ran (re-run `/review` after `/fix` to refresh); (2) the assembled-diff scope is `main..HEAD`, which here includes framework reformats (a repo-wide `prettier --write .`), `specs/`, `.devforge/`, and `docs/` housekeeping commits → 147 scope-creep + most leftover flags are NON-feature files; (3) the leftover-artifact detector flags ordinary `//` explanatory comments as `commented_code_block` (56 false positives in feature test files). Real feature signal was clean: 24/24 AC PASS, mechanical PASS, src/renderer hygiene clean.
**How to apply**: After `/fix`, re-run `/review` before `/verify` so folded findings aren't stale. Avoid committing repo-wide reformats / unrelated housekeeping onto a feature branch — it pollutes the verify hygiene scope vs the breakdown baseline. Treat `commented_code_block` leftover flags on normal comments as noise.

## 2026-06-23 — /verify NEEDS WORK from artifacts again (feature 002-tabs-primitive)

**Lesson**: Same false-positive pattern as 001 recurred. Verdict NEEDS WORK but BOTH blockers were artifacts, not defects: (1) AC-14 PARTIAL — the spec's own verification command `! grep -rEn 'style=[{][{]' Tabs.tsx` matches the JSDoc comment text at Tabs.tsx:72/264 that DOCUMENTS the "no style={{}}" rule, so the check fails on its own documentation despite zero real inline styles (behavioral AC met). (2) Hygiene: 6 "scope-creep" = the feature's own specs/_.md task records + design/reference.html + the review-driven PrimitivesDemo.test.tsx (all legit, just not in breakdown-handoff touched_files); 32 "leftover artifacts" = ordinary `//` explanatory comments in tests, spec `### Expects/Produces` headers, and design/reference.html commented markup + `// print()` text. Real feature signal clean: 14/15 AC genuine PASS, mechanical PASS, 1 Medium review finding (advisory, non-blocking).
**How to apply**: AC verification commands using `! grep PATTERN file` self-match when the file's JSDoc/comments quote the forbidden PATTERN — author the check to strip comment lines first (e.g. exclude `^\s_\*`/`^\s*//`), or verify behaviorally. Treat `commented_code_block`/`debug_print` hygiene flags on normal comments + markdown headers as noise. specs/*.md task files and the design reference ride main..HEAD and always trip scope-creep vs the src-only breakdown baseline.

## 2026-06-24 — Stale Playwright CT cache masked as a source error (feature 003-app-shell-layout)

**Lesson**: A `/review` finder (qa) reported Critical "CT harness broken — `RollupError: Could not resolve "./components/Versions" from playwright/index.tsx`, 92 tests dead" and a bug was filed on it. But `playwright/index.tsx` is a 5-line comment-only file with NO such import — the unresolved import lived ONLY in a stale Vite CT build cache (`playwright/.cache/`, gitignored) left over from when an entry once referenced `./components/Versions` (removed in feature 001, cache never invalidated). `rm -rf playwright/.cache` → `npm run test:ct` rebuilds clean, 92 CT tests pass. The refutation refuter correctly dismissed the finding (read index.tsx, saw it clean) but reached "harness not broken" via reading source, NOT running the build — so the dismissal was right by luck; the build genuinely failed until the cache was cleared. Also this feature: a px-delta was added to a 0-1 ratio in the pane Divider drag (the user-caught "jumps/disappears" bug) — fixed with a getDragExtent px→ratio conversion + keyboardStep prop.

**How to apply**: When a build/test error names a file as the import source but that file is clean, suspect a STALE build cache (`*/.cache/`, `node_modules/.vite`, `dist`) before editing source or filing a bug — clear it and re-run first. A refuter reading source alone can't see a cache-driven build failure; ground "harness broken" claims by actually running the build, not just reading the entrypoint. For resizable splitters: a Divider whose `value` is a unitless ratio MUST convert pointer pixel deltas via the container extent (px/extent), never add raw px to the ratio.

## 2026-06-25 — Verify caught what per-task gates can't: orphaned dev surface + missing end-to-end test (feature 004-working-tabs-state-machine)

**Lesson**: All 29 ACs passed (code-read) and assembled type-check/lint/build/test passed, yet `/verify` returned NEEDS WORK — driven entirely by folded `/review` cross-task findings the per-task `/implement` panel structurally could not see: (1) Task 010 built a `closable` PrimitivesDemo QA gallery whose own doc-comment + a test comment claim it is mounted from App.tsx behind `import.meta.env.DEV`, but Task 009's App.tsx mounts only `<Shell tabs={<TabBar />} />` — the gallery is unreachable at runtime; (2) the never-zero invariant (AC-17) is tested in the store in isolation and TabBar close is tested with ≥2 tabs, but no test exercises TabBar rendering exactly ONE tab → click ✕ → replacement blank end-to-end. Also: a perf finding (unmemoized `tabs.map(toDescriptor)` in TabBar) carried a `[CONSTITUTION-VIOLATION]` tag that the refuter dismissed (constitution §4 mandates per-field selectors, not a useMemo rule) → surfaced `[CONTESTED]`, which forces at least NEEDS WORK per D7.

**How to apply**: A cross-task "this component is mounted from X" doc-comment is a claim to verify against X, not trust — when two tasks split build-vs-wire (one creates a dev surface, another owns the composition root), check the surface is actually mounted. When a store invariant is unit-tested in isolation, add ONE assembled integration test through the consuming organism at the boundary condition (here: single-tab close). Don't tag a perf/style finding `[CONSTITUTION-VIOLATION]` unless a named constitution rule is actually violated — a contested constitution tag blocks the verdict even when the underlying defect is advisory.
