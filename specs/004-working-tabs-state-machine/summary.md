# Feature Summary — 004-working-tabs-state-machine

**Verdict** (from `/verify`): **APPROVED** · **Acceptance criteria**: 29/29 PASS

## What was built

A working tabs system for the mintEnvoy HTTP client: users can open, switch, and close request tabs in a strip above the workspace, each tab tracking its own in-flight request and a dirty (unsaved-changes) marker. Opening the same request twice reuses the existing tab instead of duplicating it, closing the active tab moves focus to a sensible neighbor, and closing the last tab always leaves a fresh blank request open — the tab count is never zero. The strip is now mounted into the app shell and renders live, replacing the previous test placeholder.

## Changes

- **RequestSpec domain model** — typed request shape (method, url, name, params, headers, body, auth) with a `none | bearer` discriminated-union auth type, a type guard, and a `makeBlankRequest()` seed factory (GET, `Accept: application/json`, bearer `{{apiKey}}` placeholder).
- **tabsStore** — renderer-only zustand slice holding `tabs[]` + `activeTabId` with the lifecycle state machine: open-from-collection (id-then-exact-url dedupe), new-blank, never-zero close with right-then-left neighbor selection, select-active, per-tab `dirty` + `markClean`.
- **Tabs primitive extension** — opt-in `closable`/`onClose` props (default-off, byte-identical for existing selection-only consumers): a sibling ✕ button (non-roving `tabIndex=-1`), a Delete/Backspace close path on the focused tab, and focus restoration to the neighbor on close. `onClose` is signal-only — the store owns the lifecycle.
- **TabBar organism** — composes the Tabs primitive against the store via per-field selectors: label precedence (name → `method url` → "Untitled"), dirty marker via the badge slot, `+` new-tab via the actions slot.
- **Shell wiring** — `App.tsx` mounts the real `<TabBar/>` into Shell's existing tabs slot.
- **Tests** — full Vitest unit suite for the store, closable-primitive unit + Playwright CT (keyboard/focus), TabBar gesture/label/marker tests, and an App-mount assertion; a shared `makeSpec`/`makeTab` test fixture.
- **Contract lineage** — appended a feature-004 extension record to the 002 Tabs spec.
- **Dev gallery** — a closable-Tabs variant registered in `PrimitivesDemo` (dev-only, tree-shaken from production) for manual visual-fidelity QA.

## Files changed

`54 files changed, 6689 insertions(+), 646 deletions(-)` (includes planning artifacts under `specs/`).

Source code (`src/renderer/src/`):
- `lib/` — `requestSpec.ts`, `tabsStore.ts` (+ `__tests__/tabsStore.test.ts`)
- `components/molecules/` — `Tabs.tsx`, `Tabs.css` (+ `__tests__/Tabs.test.tsx`, `Tabs.ct.tsx`, `Tabs.stories.tsx`)
- `components/organisms/` — `TabBar.tsx`, `TabBar.css` (+ `__tests__/TabBar.test.tsx`)
- `components/` — `PrimitivesDemo.tsx`, `App.tsx`
- `__tests__/fixtures/requestSpec.ts` (shared test factories), `__tests__/app-toast-mount.test.tsx`

## Key decisions

- **Flat slice shape** — `{ tabs: Tab[]; activeTabId }`, array order IS tab order, the `RequestSpec` embedded in each `Tab`.
- **Close lives in the Tabs primitive** as opt-in `closable`/`onClose` (default-off); ✕ is a sibling `tabIndex=-1` button, keyboard close is Delete/Backspace on the focused tab.
- **`onClose` is signal-only** — emits the tab id, mutates no list; the store owns the lifecycle, the primitive's only post-close job is roving-focus integrity.
- **Dirty-close is a silent unconditional drop** — clean and dirty tabs close through the same path (no confirm in this feature); the only close branch is the structural never-zero spawn.
- **RequestSpec is plain-serializable** — no class/Symbol/function on the data shape, pinned by a `JSON.parse(JSON.stringify(spec))` round-trip contract test.
- **Per-field store selectors** — subscribe to `tabs` and `activeTabId` separately, actions as stable refs; no whole-store read.
- **Tab ids via `crypto.randomUUID()`** at create time (new-blank / dedupe-append / never-zero spawn).

## Acceptance criteria

All 29 ACs **PASS (code)** per `verification.md`:

- AC-1–AC-10 — artifact presence + tooling: tabsStore / requestSpec / TabBar modules exist, zustand reused (no new state lib), strict typing (no `any`), lint/build clean, no node/electron imports, no inline styles.
- AC-11–AC-12 — `closable=false` byte-identical regression; exactly one roving tab stop.
- AC-13–AC-21 — store lifecycle: id-then-url dedupe (leg precedence, empty-url-distinct), new-blank seed defaults, never-zero close + replacement, right/left neighbor selection, dirty-close silent, markClean, selectActive.
- AC-22–AC-23 — ✕ click + Delete/Backspace fire `onClose`; focus restoration after close (positive + non-close guard).
- AC-24–AC-27 — TabBar gesture routing, label precedence (all 3 branches), dirty badge, App→Shell→TabBar mount.
- AC-28–AC-29 — JSDoc on new exports; 002 contract-lineage record.
