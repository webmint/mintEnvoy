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
## 2026-06-22 — /verify scope pollution (feature 001-ui-primitives)
**Lesson**: /verify computed NEEDS WORK entirely from artifacts, not real defects. Causes: (1) `review.md` was stale — its 7 confirmed findings were already remediated by `/fix` before `/verify` ran (re-run `/review` after `/fix` to refresh); (2) the assembled-diff scope is `main..HEAD`, which here includes framework reformats (a repo-wide `prettier --write .`), `specs/`, `.devforge/`, and `docs/` housekeeping commits → 147 scope-creep + most leftover flags are NON-feature files; (3) the leftover-artifact detector flags ordinary `//` explanatory comments as `commented_code_block` (56 false positives in feature test files). Real feature signal was clean: 24/24 AC PASS, mechanical PASS, src/renderer hygiene clean.
**How to apply**: After `/fix`, re-run `/review` before `/verify` so folded findings aren't stale. Avoid committing repo-wide reformats / unrelated housekeeping onto a feature branch — it pollutes the verify hygiene scope vs the breakdown baseline. Treat `commented_code_block` leftover flags on normal comments as noise.

## 2026-06-23 — /verify NEEDS WORK from artifacts again (feature 002-tabs-primitive)
**Lesson**: Same false-positive pattern as 001 recurred. Verdict NEEDS WORK but BOTH blockers were artifacts, not defects: (1) AC-14 PARTIAL — the spec's own verification command `! grep -rEn 'style=[{][{]' Tabs.tsx` matches the JSDoc comment text at Tabs.tsx:72/264 that DOCUMENTS the "no style={{}}" rule, so the check fails on its own documentation despite zero real inline styles (behavioral AC met). (2) Hygiene: 6 "scope-creep" = the feature's own specs/*.md task records + design/reference.html + the review-driven PrimitivesDemo.test.tsx (all legit, just not in breakdown-handoff touched_files); 32 "leftover artifacts" = ordinary `//` explanatory comments in tests, spec `### Expects/Produces` headers, and design/reference.html commented markup + `// print()` text. Real feature signal clean: 14/15 AC genuine PASS, mechanical PASS, 1 Medium review finding (advisory, non-blocking).
**How to apply**: AC verification commands using `! grep PATTERN file` self-match when the file's JSDoc/comments quote the forbidden PATTERN — author the check to strip comment lines first (e.g. exclude `^\s*\*` / `^\s*//`), or verify behaviorally. Treat `commented_code_block`/`debug_print` hygiene flags on normal comments + markdown headers as noise. specs/*.md task files and the design reference ride main..HEAD and always trip scope-creep vs the src-only breakdown baseline.
