# Summary: request-bar

**Feature**: 009-request-bar
**Verdict**: APPROVED (see verification.md — `/verify` owns the verdict)
**Date**: 2026-06-28

## What was built

A RequestBar for the active request tab — the top row of the HTTP client where you pick a method and type a URL. It shows a color-coded method dropdown (GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD), a URL field bound to the active tab, and Send / Save / Share buttons. Send is disabled until the URL is non-blank and fires a send-intent (no HTTP yet — that's a later feature); Save persists the tab via its dirty flag; ⌘↵ sends and ⌘S saves from anywhere in the app. Editing the method or URL marks the tab dirty; switching tabs swaps the bar's contents with no bleed between tabs.

## Changes

- **HTTP-method single source** — added `lib/httpMethods.ts` (`METHODS` list + `HttpMethod` type) and re-typed `RequestSpec.method` from a loose `string` to `HttpMethod`, so every method consumer draws from one list.
- **Tab spec-edit action** — added `tabsStore.updateActiveSpec(patch)`: merges method/url into the active tab and sets dirty only when a value actually changes (a no-op edit leaves the tab clean).
- **Governance** — amended the constitution so RequestBar is recognized as the tab store's spec-edit subscriber alongside TabBar.
- **RequestBar organism** — built the component (method Dropdown + URL input + Send/Save/Share + ⌘↵/⌘S shortcuts), styled against design tokens, with reactive per-field reads so unrelated tab changes don't re-render it.
- **Tests** — Vitest unit suite + Playwright component tests for the bar, store-action coverage, and an App-mount test proving the bar lands in the request pane.
- **Wiring** — mounted RequestBar into the app shell's request pane.

## Files changed

12 source files (`src/`) + the constitution; `git diff --stat`: 32 files changed, 4341 insertions(+), 16 deletions(-) (includes the feature's spec/plan/task planning artifacts).

- `src/renderer/src/lib/` — `httpMethods.ts` (new), `requestSpec.ts` (method re-typed), `tabsStore.ts` (+ `updateActiveSpec`), `__tests__/tabsStore.test.ts`
- `src/renderer/src/components/organisms/` — `RequestBar.tsx` + `RequestBar.css` (new), `__tests__/RequestBar.test.tsx` + `.ct.tsx` + `.stories.tsx` (new)
- `src/renderer/src/components/molecules/Tabs.tsx` — deduped to import the shared `METHODS`
- `src/renderer/src/App.tsx`, `src/renderer/src/__tests__/app-toast-mount.test.tsx` — request-pane mount + its test
- `constitution.md` — §4 sole-subscriber rule amended

## Key decisions

- **Generic store mutator** — one `updateActiveSpec(patch)` (shallow-merge + dirty-on-change) instead of per-field setters, so it scales to future request fields without new actions.
- **Single-source method type** — `lib/httpMethods.ts` is the one method list/type; `requestSpec.method` and the dropdown both reference it (avoids drift between the bar and the tab chip).
- **Controlled URL input, no remount** — caret/buffer survive a method change; tab-switch swaps the value via the per-field selector.
- **One shared `canSend` guard** — `url.trim() !== ''` drives the button, the click handler, and ⌘↵ identically, so the keyboard and button paths can't diverge.
- **Global shortcuts via one document keydown effect** — mirrors the existing Shell pattern; reads live state via `getState()` and acts on the active tab regardless of focus; ⌘S calls `preventDefault` to suppress native save.
- **Per-field selectors** — RequestBar subscribes to the active tab's method/url/dirty individually, so background-tab edits don't re-render it.
- **`onSend` callback prop** — Send fires a default-no-op `onSend` (tab id + method + url); the real HTTP consumer is a later task, and the bar mounts/tests standalone.
- **Flat placement + §4 amendment** — RequestBar stays a flat organism (no `organisms/request/` yet, per the ≥2-component rule); the constitution's sole-subscriber rule was reworded to admit it.

## Deviations from plan

- **Task 005** added `RequestBar.stories.tsx` beyond the planned files — the project's Playwright CT pattern requires component fixtures in a sibling stories file.
- **Task 006** added an AC-21 mount test to `app-toast-mount.test.tsx` (later strengthened to a semantic-content assertion) — covering the request-pane wiring the typecheck alone couldn't.

## Acceptance criteria

All 30 ACs **PASS** (per verification.md, `tests` mode + assembled type-check/lint/build):

- 5.1 Tooling: AC-1, AC-2, AC-3 ✅
- 5.2 Behavior preservation: AC-4, AC-5, AC-6 ✅
- 5.3 Behavior change: AC-7 … AC-22 (16) ✅
- 5.6 Documentation: AC-23, AC-24 ✅
- 5.7 Hygiene: AC-25, AC-26, AC-27, AC-28, AC-29, AC-30 ✅

30/30 passed · 0 failed/partial · 0 unverified.
