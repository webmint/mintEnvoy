# Feature Summary: 014-kv-table-editor

**Verdict**: APPROVED (`/verify`) · **Status**: Complete · **Date**: 2026-07-05

## What was built

KVTable — a hand-rolled, controlled key-value grid for editing a request's query params and headers. One reusable component is instanced twice (bound to `params` and to `headers`) via a `field` prop. It renders an enable checkbox, mono key/value/description cells, a hover-revealed delete button, and an auto-promoting trailing empty row, and it highlights `{{variable}}` tokens in the key/value cells — flagging unknown ones against the active environment (display-only; it never *resolves* a variable). It reads and writes exclusively through the existing `tabsStore.updateActiveSpec` action (no local copy), matches `design/styles.css` to pixel fidelity, and ships built + component-tested in isolation (it is not yet mounted into the running app — the parent pane-tabs container is a separate feature).

## Changes

- **Variable tokeniser** (`lib/varTokens.ts`) — pure non-greedy `{{…}}` tokeniser: empty `{{}}` and unclosed `{{` are plain text; names may hold unicode/dots/dashes; returns typed segments carrying a trimmed `name` (for lookup) and the verbatim `raw` match (for faithful display).
- **Environment selector** (`lib/envVars.ts`) — thin `validVars` selector returning a stable frozen ∅ set until the env store (T14) lands, so the highlight gate degrades to neutral rather than false-flagging.
- **KVTable component + styles** (`organisms/KVTable.tsx` + `KVTable.css`) — the controlled grid: derived virtual trailing row, auto-promote on key/value edit, hover-delete with focus recovery, checkbox toggle, multi-line-paste collapse, external-mutation reactivity, and token highlighting bound to design tokens (no inline styles).
- **Component + unit tests** (`KVTable.ct.tsx` + `KVTable.stories.tsx`, `varTokens.test.ts`, `envVars.test.ts`) — Playwright CT for grid behaviour + computed-style fidelity asserts (the sole runtime vehicle, since the component is unmounted this feature), plus Vitest suites for the tokeniser edge rules and the ∅-default selector.

## Files changed

28 files, +4220 (no deletions — greenfield feature):
- **`src/`** (8 files) — the shipped code: `lib/varTokens.ts`, `lib/envVars.ts`, `organisms/KVTable.tsx` + `KVTable.css`, and the four co-located test files.
- **`specs/014-kv-table-editor/`** (18 files) — spec, plan, grill, breakdown, 4 task files, and the review/verification records.
- **`discover/`** (2 files) — the pre-spec discovery report + handoff.

## Key decisions

- **(a) State ownership** — controlled grid: derive rows from the store each render, write a fresh `Row[]` via `updateActiveSpec`; no local copy (guarantees external-mutation reactivity).
- **(b) Trailing empty row** — a render-time *virtual* row, not a stored one (no phantom rows persist).
- **(c) Tokeniser placement** — a separate pure `lib/varTokens.ts` module (independently unit-testable, reusable by a future resolver).
- **(d) One component / two mounts** *(departure)* — a single `KVTable.tsx` with a `field: 'params'|'headers'` prop instead of two components.
- **(e) Caret / focus preservation** *(departure)* — stable numeric row keys with the virtual trailing row keyed at its future index, plus `useLayoutEffect` focus recovery (no focus loss on promote/delete).
- **(f) ∅-default validVars** — `KVTable` accepts `validVars?: ReadonlySet<string>` defaulting to `envVars()`, so the highlight seam is injectable and degrades cleanly before the env store exists.

## Deviations from plan

- **(d) + (e)** above were plan-time departures adopted during `/grill` (single component + flat placement; index-keyed caret preservation) — carried into the build.
- **Post-verify remediation (`/review` → `/fix`)**: the feature-level `/review` caught an emergent cross-task defect the per-task panel structurally could not see — the overlay repainted the *trimmed* token name over the untrimmed transparent input, drifting the caret for padded tokens like `{{ x }}`. Fixed by carrying the verbatim `raw` match in the tokeniser and rendering it in the overlay (dropping a redundant trim), locked by a padded-token + value-cell CT. The clean re-review + `/verify` APPROVED reflect the remediated state.

## Acceptance criteria

33/33 PASS (from `verification.md`; `tests` mode, code-read + assembled suite):

- **Artifacts (AC-1–4)**: component + styles, tokeniser, selector present; no new table/combobox/autocomplete dependency. ✅
- **Behavior preservation (AC-5–7)**: unmounted → app unchanged; writes flow through the existing `updateActiveSpec` no-op-guarded merge; no tabsStore/requestSpec modification. ✅
- **Behavior (AC-8–26)**: auto-promote, non-greedy tokenising, two-mount independence, key/value-only highlighting, verbatim render (no resolution), focus recovery, real checkbox + button, disabled styling, both validVars paths, external-mutation reactivity, unicode/dot/dash names, paste collapse, Tab traversal, virtual-row inertness. ✅
- **Docs (AC-27)**: KVTable props + tokeniser + selector documented. ✅
- **Hygiene (AC-28–33)**: strict type-check, ESLint, clean build, no inline styles, no electron/node imports, unit + component suites pass (vitest 20/20 + Playwright CT green). ✅
