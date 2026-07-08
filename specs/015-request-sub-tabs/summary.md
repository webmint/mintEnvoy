# Summary: request-sub-tabs

**Verdict**: APPROVED (`/verify`) · **Status**: Complete · 27/27 acceptance criteria passed

## What was built

The request pane now has a proper editor: a horizontal strip of six sub-tabs — **Params, Auth, Headers, Body, Tests, Code** — that switches which editor panel shows below the request bar, with live count badges (params/headers row counts, an auth indicator). The Params and Headers tabs are now **live and editable** — the key/value table (KVTable, built in feature 014) is wired in and goes live in the running app for the first time; the other four tabs show a shared "Panel not yet available" placeholder until their editors ship. Each request tab remembers its own active sub-tab, and switching sub-tabs preserves the panel's state — input focus, scroll position, and half-typed rows survive, so you never lose your place.

## Changes

- **Sub-tab state** — added a per-request-tab `activeSubTab` field + a `setActiveSubTab` action to the tabs store, so every open request remembers which sub-tab it was on.
- **Tabs molecule extension** — added an opt-in `linkPanels` prop to the shared Tabs component that emits the ARIA `id`/`aria-controls` linkage a tabpanel needs; off by default, so existing tab strips are byte-identical.
- **RequestSubTabs organism** — the new switcher: composes Tabs for the 6-tab strip, owns six always-mounted panels toggled by CSS, derives read-only badges, and wires the tabpanel ARIA and defensive reads.
- **Visual fidelity** — a `.pane-tabs`-scoped stylesheet matching the design's §6 pane-tab spec in both light and dark themes, backed by computed-style component tests.
- **App wiring** — the composed request pane (request bar above the sub-tabs) is mounted into the app, taking KVTable live through the Params/Headers slots.

## Files changed

43 files changed, +5858 / −623 (assembled feature branch).

- `src/renderer/` (14) — the feature code + tests: `lib/tabsStore.ts` (sub-tab state), `components/molecules/Tabs.tsx` (linkPanels), `components/organisms/RequestSubTabs.{tsx,css}` (new organism + fidelity CSS), `App.tsx` (composition), plus Vitest + Playwright CT suites and shared test fixtures.
- `specs/015-request-sub-tabs/` (16) — spec, plan, tasks, handoffs, review/verification reports.
- `bugs/` (3) — pre-existing KVTable defects surfaced once it went live: native checkbox styling (009), header/row font (010), and the app-wide missing design fonts Inter/JetBrains Mono (011).
- `discover/` (2), `.devforge/` (8) — discovery report + pipeline state.

## Key decisions

- **Compose, don't fork** — RequestSubTabs reuses the existing Tabs molecule (keyboard/ARIA engine) and adds no tab-library dependency.
- **Per-request-tab state** — `activeSubTab` lives on each Tab record, so two open requests keep independent active sub-tabs.
- **Mount-all + CSS hide** — all six panels stay mounted and toggle via the `hidden` attribute (never unmounted) so KVTable edit state survives a switch.
- **Slot injection at the root** — App injects KVTable into the Params/Headers slots; RequestSubTabs imports no sibling organism (keeps the organism→molecule tier-flow clean).
- **Route B ARIA linkage** — a minimal opt-in Tabs extension supplies the tab↔panel `aria-controls`/`aria-labelledby` linkage, resolving the AC-14-vs-"no Tabs change" tension without breaking the selection-only contract.
- **Fidelity via scoped CSS** — §6 pane-tab styling is hit by a `.pane-tabs`-scoped override of the Tabs DOM (zero molecule change), asserted as computed styles, not screenshots.

## Deviations from plan

- **Task 001** — also seeded `activeSubTab` in `makeCollectionTab` + the `makeTab` test fixture (every Tab constructor must seed the additive field).
- **Task 003** — a real AC-9 scroll/focus-preservation defect surfaced later; the CSS placeholder was filled and production reopened in task 004.
- **Task 004** — reopened RequestSubTabs.tsx (production) to fix an AC-9 scroll-preservation defect the CT caught (`display:none` drops scrollTop + `focus()` clobbers it → synchronous capture + `focus({preventScroll:true})`); also fixed a wrong `tokens.css` import that broke the CT build.
- **Post-verify remediation** — two `/review` → `/fix` cycles cleared emergent cross-task bugs the per-task gate couldn't see: a **per-request-tab scroll leak** (the mount-all component persists across request-tab switches; fix clears the preservation maps + resets panel DOM scrollTop on tab change) and an **incomplete badge-render-cascade fix** (completed with scalar store selectors so a KVTable keystroke no longer re-renders the tab strip). Both `/review` passes ended clean.

## Acceptance criteria

All 27 verified PASS (code-read, mode `tests`) by `/verify`; mechanical type-check / lint / build pass.

- [x] AC-1..AC-3 — RequestSubTabs module + sibling stylesheet present; no third-party tab library added
- [x] AC-4, AC-5 — additive store field doesn't break TabBar/RequestBar; Tabs composed via its public API
- [x] AC-6..AC-10 — click + Arrow/Home/End switch; persistence via `setActiveSubTab`; per-tab restore; mount-all state preservation; external write == click
- [x] AC-11..AC-14 — KVTable in Params/Headers slots; shared empty-state; all 6 reachable, none disabled; tabpanel ARIA linkage
- [x] AC-15..AC-18 — 99+ badge clamp; invalid key → params; no-active-tab empty region; App mounts the composed pane
- [x] AC-19, AC-26, AC-27 — doc comments; reactive badges; §6 fidelity both themes
- [x] AC-20..AC-25 — strict type-check, lint clean, no inline styles / electron-node imports / `updateActiveSpec` / unbuilt-panel imports in the organism source
