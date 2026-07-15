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
- **[Task 001 / 008-dropdown-ct-dismiss]**: Gate Dropdown click-outside CT tests on overlay readiness — completed. _(Task 001)_
- **[Task 001 / 009-request-bar]**: add-httpmethods-source-and-retype-method — completed. _(Task 001)_
- **[Task 002 / 009-request-bar]**: add-tabsstore-updateactivespec-action — completed. _(Task 002)_
- **[Task 003 / 009-request-bar]**: amend-constitution-sole-subscriber-rule — completed. _(Task 003)_
- **[Task 004 / 009-request-bar]**: build-requestbar-organism — completed. _(Task 004)_
- **[Task 005 / 009-request-bar]**: add-requestbar-component-test — completed. _(Task 005)_
- **[Task 006 / 009-request-bar]**: mount-requestbar-in-app-request-pane — completed. _(Task 006)_
- **[Task 001 / 010-request-bar-fidelity]**: restyle-requestbar-markup-labels-keycap — completed. _(Task 001)_
- **[Task 002 / 010-request-bar-fidelity]**: rewrite-requestbar-css-fidelity — completed. _(Task 002)_
- **[Task 003 / 010-request-bar-fidelity]**: add-ct-fidelity-suite — completed. _(Task 003)_
- **[Task 001 / 011-tab-width-cap]**: relocate-width-cap-to-tab-cell — completed. _(Task 001)_
- **[Task 002 / 011-tab-width-cap]**: ct-cap-assertion-and-no-growth-test — completed. _(Task 002)_
- **[Task 001 / 012-requestbar-element-fidelity]**: restructure requestbar markup — completed. _(Task 001)_
- **[Task 002 / 012-requestbar-element-fidelity]**: rebind requestbar css fidelity — completed. _(Task 002)_
- **[Task 003 / 012-requestbar-element-fidelity]**: rebind shared dropdown open-panel css — completed. _(Task 003)_
- **[Task 004 / 012-requestbar-element-fidelity]**: computed-style fidelity ct suite — completed. _(Task 004)_
- **[Task 001 / 013-tabs-contrast-wcag]**: Sync drifted muted and faint token values — completed. _(Task 001)_
- **[Task 002 / 013-tabs-contrast-wcag]**: Swap active-tab accent-on-light sites to text token — completed. _(Task 002)_
- **[Task 003 / 013-tabs-contrast-wcag]**: Add Tabs contrast CT assertions and re-baseline screenshots — completed. _(Task 003)_
- **[Task 001 / 014-kv-table-editor]**: varTokens tokeniser — completed. _(Task 001)_
- **[Task 002 / 014-kv-table-editor]**: envVars validVars selector — completed. _(Task 002)_
- **[Task 003 / 014-kv-table-editor]**: KVTable component + styles — completed. _(Task 003)_
- **[Task 004 / 014-kv-table-editor]**: KVTable component tests + fixtures — completed. _(Task 004)_
- **[Task 001 / 015-request-sub-tabs]**: tabsStore activeSubTab state and action — completed. _(Task 001)_
- **[Task 002 / 015-request-sub-tabs]**: Tabs opt-in panel-linkage prop — completed. _(Task 002)_
- **[Task 003 / 015-request-sub-tabs]**: RequestSubTabs organism — completed. _(Task 003)_
- **[Task 004 / 015-request-sub-tabs]**: RequestSubTabs section 6 fidelity CSS and CT — completed. _(Task 004)_
- **[Task 005 / 015-request-sub-tabs]**: App compose request pane (KVTable live) — completed. _(Task 005)_
- **[Task 001 / 016-load-design-fonts]**: Add @fontsource dependencies — completed. _(Task 001)_
- **[Task 002 / 016-load-design-fonts]**: Create fonts.css @font-face and import it in main.tsx — completed. _(Task 002)_
- **[Task 003 / 016-load-design-fonts]**: Reorder --font-sans + base.css body at token — completed. _(Task 003)_
- **[Task 004 / 016-load-design-fonts]**: Document self-hosted fonts — completed. _(Task 004)_
- **[Task 005 / 016-load-design-fonts]**: Font-load fidelity CT and regenerate baselines — completed. _(Task 005)_
- **[Task 001 / 017-body-editor-shell]**: Migrate RequestSpec body to tagged record — completed. _(Task 001)_
- **[Task 002 / 017-body-editor-shell]**: Re-export Body types from tabsStore — completed. _(Task 002)_
- **[Task 003 / 017-body-editor-shell]**: JSON tokenizer lib + two-pass compose — completed. _(Task 003)_
- **[Task 004 / 017-body-editor-shell]**: CT fidelity util — assertComputedStyle / assertResolvesToToken — completed. _(Task 004)_
- **[Task 005 / 017-body-editor-shell]**: KVTable controlled-mode prop union — completed. _(Task 005)_
- **[Task 007 / 017-body-editor-shell]**: RequestSubTabs body slot — completed. _(Task 007)_
- **[Task 009 / 017-body-editor-shell]**: tokens.css --tk-* per-theme syntax tokens — completed. _(Task 009)_
- **[Task 006 / 017-body-editor-shell]**: BodyEditor organism + CSS — completed. _(Task 006)_
- **[Task 008 / 017-body-editor-shell]**: App composition — wire BodyEditor into the body slot — completed. _(Task 008)_
- **[Task 010 / 017-body-editor-shell]**: BodyEditor CT — fidelity + behavior — completed. _(Task 010)_
- **[Task 011 / 017-body-editor-shell]**: KVTable CT regression — field + controlled modes — completed. _(Task 011)_
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

## 2026-06-28 — Assembled /review caught the cross-surface SSOT duplication a per-task panel can't (feature 009-request-bar)

**Lesson**: All 30 ACs passed (code-read) + assembled type-check/lint/build passed → APPROVED, but the value came from `/review`'s emergent-cross-task pass. Task 001 introduced `lib/httpMethods.ts` as the HTTP-method SSOT, but a pre-existing `KNOWN_METHODS` duplicate in `molecules/Tabs.tsx` (built in an earlier feature) was left un-migrated — invisible to the per-task `/implement` panel (Tabs.tsx is not in any 009 task's diff), it flagged it at task 001 only as out-of-scope info. The assembled `/review` confirmed it as the real cross-task duplication/divergence defect (a method added to METHODS would color in the RequestBar dropdown but silently not in the Tabs chip). Two `/review→/fix` rounds drove confirmed findings 4→1→0. Also non-obvious: a feature whose spec declares `Design source: none` but the repo still has a `design/reference.html` trips the file-existence-keyed design-manifest gate in `/breakdown` + `/review` — an EMPTY `design-manifest.json` (0 elements, 0 gap-list) satisfies `validate-manifest` and `design-auditor` returns 0, so the gate passes with no per-element fidelity contract.

**How to apply**: When a feature establishes a "single source of truth" constant/type, grep the WHOLE repo for pre-existing duplicates of that list — the per-task gate only sees the feature's own diff, so an un-migrated copy in an untouched file is exactly the emergent defect `/review` exists to catch; carry it as a `/fix` item even though the duplicate lives outside the feature's task files. For a non-UI feature with `Design source: none` in a repo that has `design/reference.html`, produce an EMPTY design-manifest in `/breakdown` PHASE 2.5 (resolve-reference finds no `data-ref` elements → empty manifest validates) to satisfy the file-existence gate cleanly.

## 2026-06-29 — Runtime design-fidelity only works when the MCP's target CDP port is live; static diffs miss px/weight drift (feature 010-request-bar-fidelity)

**Lesson**: `/review`'s `design-auditor` ran static-only ("runtime NOT machine-covered") on every pass because the chrome-devtools MCP is pinned to a FIXED browser endpoint (`127.0.0.1:50757`) and the Electron app was launched without that debug port — even though the app was running (renderer on Vite `:5173`) and a second CDP port (8080) was later exposed, the MCP cannot be repointed per-call (its `new_page`/`list_pages` take no browserURL arg). Only once the app was relaunched with remote debugging on the MCP's exact port (50757) did `design-auditor` attach to the live renderer and run real `getComputedStyle` diffs — which immediately caught 3 fidelity misses the static CSS-vs-`design/styles.css` passes had silently let through across the whole feature: actions-group `gap: 4px` (ref 8px), Save/Share missing `font-weight: 500`, keycap missing `letter-spacing: 0.02em`. The `/fix` then added CT computed-style assertions LOCKING each value (the qa panel correctly held the fix dirty until they existed). Also: an empty `design-manifest.json` `elements` array means design-auditor has NO per-element MATCH/DEVIATE targets even with runtime access — it falls back to a whole-component check. Also `consume-tmp`/`validate-findings` silently drops a finding when fields use a blank line after `## Finding N`, an inline `Evidence:` (not a fenced block), a `Line:` range, or a non-verbatim evidence quote — normalize to integer-line + fenced verbatim before re-consuming.

**How to apply**: For runtime design-fidelity to actually run, the Electron app must be launched with `--remote-debugging-port=<P>` where `<P>` is the EXACT port the chrome-devtools MCP server is configured to attach to — confirm with `curl -s http://127.0.0.1:<P>/json/version` before dispatching `design-auditor`; a running app on a different port is not reachable. Never trust a green static fidelity pass as proof of visual conformance — px gaps, inherited font-weights, and letter-spacing only surface under live `getComputedStyle`. Every fidelity value a fix corrects MUST get a CT computed-style assertion locking it, or it silently regresses. Populate the design-manifest `elements` (a `/breakdown` PHASE-2.5 task) so the runtime audit has scoped MATCH/DEVIATE targets instead of a coarse whole-component check.

## 2026-07-01 — 012-requestbar-element-fidelity: runtime design-auditor is load-bearing for fidelity features
APPROVED after 4 /fix rounds. The round-1 /review design-auditor DIED (API error) before its runtime pass, so /verify's first run was NEEDS-WORK-blind to real visual defects. Once the runtime design-auditor (Chrome MCP vs the live app + rendered reference) actually ran, it caught a chain of default-mode-invisible fidelity gaps that static review + CT computed-style asserts all missed: method chevron inheriting the per-method color (should be dark --text), method button 29px vs 33px (text node not a .method chip span), then chip-mode button 31px (border:none on the chip counter-rules removes 2px). Lesson: for a design-fidelity feature, the runtime design-auditor is not optional — if it fails/dies, re-run it before trusting a clean /verify. Also: a CSS shortcut (justify-content, line-height, caret color override) can fix the one axis you're looking at while leaving sibling axes (height, inherited color, per-variant delta) drifted; each fidelity fix needs its own computed-style CT lock across ALL mstyle variants (not just the default). The 4-round tail was the runtime auditor surfacing one more per-variant delta each pass — real, but a signal to weigh "match reference exactly" vs "accept documented deviation" once the default mode is pixel-correct.

## 2026-07-03 — 013-tabs-contrast-wcag: APPROVED; hygiene false-positives on comment-dense CT files
Clean 3-task WCAG contrast fix (token sync + 2 accent→var(--text) swaps + CT assertions). /verify APPROVED, 10/10 ACs PASS (code), mechanical pass. Notable: /verify's check-hygiene flagged 38 "leftover_artifacts" (kind=commented_code_block) + 1 scope-creep — ALL false positives: the 38 were ordinary `//` explanatory comments in Tabs.ct.tsx/Tabs.stories.tsx (comment-dense CT files), and the scope-creep was Tabs.stories.tsx (a panel-approved test fixture added post-breakdown-baseline). compute-verdict correctly treated hygiene as advisory/non-blocking, so the verdict stayed APPROVED. Lesson: hygiene's commented_code_block detector over-fires on comment-rich test files; it's advisory-only so it doesn't block, but don't chase it. Process win: after /fix remediated /review findings, re-ran /review (findings→0 Critical/High/Medium, 1 Info) BEFORE /verify — avoided the stale-review false-NEEDS-WORK trap (fix-then-rereview-before-verify).

- **014-kv-table-editor** (verify APPROVED, 33/33 AC): emergent cross-task defect the per-task /implement panel structurally could not see — a tokeniser that NORMALIZES (`tokenizeVars` trims the var name) + a consumer that RECONSTRUCTS the display from the normalized value (`{{${seg.name}}}`) painted a shorter string over a transparent input → caret/overlay desync for padded tokens `{{ x }}`. Fix: tokeniser carries verbatim `raw` (match[0]); consumer renders `seg.raw` for display, keeps trimmed `name` for lookup. Lesson: when a producer normalizes a value, the display consumer must render the VERBATIM source, not reconstruct from the normalized form. Caught by /review (architect+code converged), not the per-task panel.

- **015-request-sub-tabs** (2026-07-07, verify APPROVED, 27/27 AC PASS(code), mechanical pass): required TWO /review→/fix cycles to reach clean — the per-task /implement panel structurally could not see the emergent bugs. (1) The task-004 scroll-preservation fix (mount-all + hidden panels) introduced a PER-REQUEST-TAB scroll leak: RequestSubTabs stays mounted across request-tab switches (App has no key={activeTabId}), and preservation Maps keyed by SubTabKey alone leaked tab A's scroll onto tab B; the shared #panel DOM node also physically retained scrollTop when both tabs shared the same activeSubTab (display:none never fired to reset it). Fix: useEffect([activeTabId]) clears the Maps AND resets panelRefs scrollTop to 0. (2) The first badge-cascade fix was INCOMPLETE — scalar useMemo DEPS stopped the recompute but the component still subscribed to the full spec OBJECT ref, so it re-rendered (Tabs fn body ran) on every KVTable keystroke; complete fix = three scalar SELECTORS returning primitives. Lessons: [a] scroll/focus preservation across a hidden-toggle needs BOTH map-clear AND live-DOM reset when the component persists across an outer context; [b] a memo-deps fix doesn't stop a re-render if the SELECTOR still returns an object ref — fix the selector, not just the deps. Process: /review's qa findings were twice dropped by validate-findings for quote_mismatch (non-verbatim test-line quotes) — reminding the finder to copy EXACT verbatim evidence got them validated on re-run. Hygiene again over-fired (~70 commented_code_block false positives on doc-comment-dense files + 3 test-fixture scope-creep) — advisory, non-blocking, ignored.

- **016-load-design-fonts** (2026-07-09, verify APPROVED, 13/13 AC PASS(code), mechanical pass): self-hosted Inter+JetBrains Mono. Emergent gap the per-task panel + static review + CT all MISSED, caught only by /review's runtime design-auditor (Accessibility-scoped, Chrome MCP): `<button>`/`<input>`/`<select>`/`<textarea>` do NOT inherit `font-family` from `body` per the browser UA stylesheet — so a self-hosted-font feature that only sets `body { font-family: var(--font-sans) }` leaves every form control rendering the UA default (Arial), silently defeating the feature's goal on Titlebar buttons + the KVTable delete button. Fix = one DRY global reset in base.css: `button, input, select, textarea { font-family: inherit }` (covers all controls + future ones; loses to any explicit component `font-family` like `.kv-cell input { var(--font-mono) }`, so no regression). Lesson: any font-family change on `body`/`:root` MUST pair with a form-element inherit reset, or buttons/inputs silently keep the UA font. Regression-testing that reset in CT needs the rule INLINED in a scoped `<style>` fixture (base.css is deliberately absent from the playwright harness — importing it breaks screenshot baselines, see [[ct-borderbox-harness-import-breaks-screenshots]]); a control button proves it's the reset (not ambient CSS) doing the work. Process win: re-ran /review AFTER /fix (2 commits) BEFORE /verify — the re-review's 2 new Medium findings (reset duplication + input/textarea CT coverage) were both dismissed on refutation, so review.md went clean and /verify folded 0 findings → clean APPROVED (avoided the stale-review false-NEEDS-WORK trap, [[fix-then-rereview-before-verify]]). Pre-existing a11y items the audit surfaced (focus-visible, aria-labels, 2.36:1 method-chip contrast, 720px titlebar overflow) filed as bugs 012-015, out of 016 scope.
