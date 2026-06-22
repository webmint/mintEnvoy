# Spec: ui-primitives

**Date**: 2026-06-21
**Status**: Complete
**Author**: Claude + User

## 1. Overview

A reusable, presentation-only UI primitives layer for the mintEnvoy renderer: a Dropdown/popover, a Modal dialog, a transient Toast, and an inline SVG Icon, plus the thin shared overlay substrate they need. The overlay behavior and accessibility (focus trap/return, keyboard navigation, dismiss, ARIA, edge-aware positioning) are sourced from a headless primitive library (Radix recommended, final pick deferred to /plan); the Icon, the styling, and the Toast queue are project-owned. Every primitive is styled exclusively via semantic class names bound to the existing design-token CSS custom properties, and is consumed only by other renderer feature components — no network, no persistence.

## 2. Current State

Greenfield for UI primitives. The renderer is electron-vite boilerplate: src/renderer/src/App.tsx, src/renderer/src/main.tsx, and a single src/renderer/src/components/Versions.tsx. No Dropdown/Modal/Toast/Icon, no overlay hooks, and no src/renderer/src/lib/ exist (confirmed via the codebase-memory graph). Design tokens are already compiled to CSS custom properties at src/renderer/styles/tokens.css, and the @renderer alias (electron.vite.config.ts) resolves to src/renderer/src. No test framework is installed (package.json declares no runner or testing library), and constitution §3.4 requires picking a renderer test stack before the first feature needing coverage. The visual/behavior reference is the Claude Design export under design/ (look only — never its generated markup/cruft).

## 3. Desired Behavior

Deliver four primitives under the renderer's atomic-design layout — Icon in src/renderer/src/components/atoms/, and Dropdown/popover, Modal, Toast in src/renderer/src/components/molecules/ — with a THIN shared substrate in src/renderer/src/lib/ holding only what the headless library does not provide (Icon helpers, the Toast store, minimal glue). Dropdown/popover anchors to a trigger with keyboard navigation, focus return to the trigger on close, click-outside and Escape dismiss, and edge-aware flip/shift positioning. Modal traps focus, renders a scrim, closes on Escape, and locks body scroll. Toast is fired through an imperative toast(message, opts) API backed by a zustand toastStore that owns a stack of transient notifications with auto-dismiss, manual dismiss, and hover/focus pause. Icon renders an inline 16x16, 1.5px-stroke SVG selected by a typed name from the project-owned 40-icon set, with a safe fallback for an unknown name. Nested overlays compose: Escape closes only the topmost, focus traps and focus-return nest, z-order stays sane. All animations respect prefers-reduced-motion. Dropdown and Modal are controlled via open + onOpenChange props. A dev-only in-app route renders every primitive in its states as the visual + manual-QA surface. Behavior is gated by automated interaction tests (Vitest + Testing Library) plus Playwright component tests for focus/keyboard fidelity.

## 4. Affected Areas

| Area                           | Files                                                                                                                                                | Impact                                                                                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Icon atom                      | src/renderer/src/components/atoms/Icon.tsx, src/renderer/src/components/atoms/icons.ts                                                               | Create new — inline SVG Icon component + project-owned typed icon-path set (40 icons, 1.5px stroke, 16x16)                                 |
| Overlay molecules              | src/renderer/src/components/molecules/Dropdown.tsx, src/renderer/src/components/molecules/Modal.tsx, src/renderer/src/components/molecules/Toast.tsx | Create new — Dropdown/popover, Modal, Toast components wrapping headless behavior, styled via semantic classes                             |
| Shared overlay substrate (lib) | src/renderer/src/lib/toastStore.ts, src/renderer/src/lib/icons-glue.ts                                                                               | Create new — THIN lib: zustand toastStore + imperative toast() API + minimal glue; relies on the headless lib for focus-trap/positioning   |
| Token-bound stylesheets        | src/renderer/styles/tokens.css, src/renderer/src/components/atoms/, src/renderer/src/components/molecules/                                           | Create new per-component stylesheets using semantic class names bound to existing tokens.css CSS custom properties; no inline styles       |
| Test tooling + config          | package.json, vitest.config.ts, playwright.config.ts                                                                                                 | Create new — add Vitest + @testing-library/react + user-event (jsdom) and Playwright component tests; record stack in docs/architecture.md |
| Demo / QA route                | src/renderer/src/components/PrimitivesDemo.tsx                                                                                                       | Create new — dev-only in-app route rendering every primitive in its states                                                                 |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The project shall own an inline SVG icon-set module under the atoms directory.
  > Verification: test -f src/renderer/src/components/atoms/icons.ts
- [x] **AC-20**: The build shall include a configured Vitest test runner with Testing Library plus Playwright component tests.
  > Verification: grep -q vitest package.json
- [x] **AC-21**: The renderer shall provide the primitives under the atoms and molecules component directories.
  > Verification: test -d src/renderer/src/components/atoms && test -d src/renderer/src/components/molecules

### 5.2 Behavior preservation

N/A — Greenfield feature — no existing behavior to preserve; renderer has no prior primitives.

### 5.3 Behavior change

- [x] **AC-2**: WHEN an open dropdown has focus and the user presses the Arrow, Home, or End keys, the dropdown shall move focus between its menu items.
- [x] **AC-3**: WHEN a dropdown or modal closes, the component shall return focus to the trigger element that opened it.
- [x] **AC-4**: WHEN the user clicks outside an open dropdown or presses the Escape key, the dropdown shall dismiss.
- [x] **AC-5**: WHILE an open dropdown would overflow the viewport, the dropdown shall flip or shift its position to remain fully visible.
- [x] **AC-6**: WHILE a modal is open, the modal shall confine keyboard focus within its content, render a scrim, and lock body scroll.
- [x] **AC-7**: WHEN the user presses the Escape key in an open modal, the modal shall close and return focus to its trigger.
- [x] **AC-8**: WHEN a toast auto-dismiss duration elapses, the toast shall be removed from the stack.
- [x] **AC-9**: WHILE a toast is hovered or focused, the toast shall pause its auto-dismiss timer.
- [x] **AC-10**: WHEN the user dismisses one stacked toast, the toast layer shall remove only that toast and leave the others.
- [x] **AC-11**: WHEN a controlled Dropdown or Modal open prop changes, the component shall reflect the open state and invoke onOpenChange on user-driven changes.
- [x] **AC-12**: WHEN the Escape key is pressed while nested overlays are open, the system shall close only the topmost overlay.
- [x] **AC-13**: IF the Icon name is not present in the icon set, THEN the Icon component shall render a safe fallback instead of throwing.
- [x] **AC-14**: WHILE the prefers-reduced-motion setting is active, the primitives shall suppress their open and close animations.
- [x] **AC-22**: WHEN the imperative toast API is invoked, the toastStore shall enqueue a transient notification in the toast stack.
- [x] **AC-23**: The Icon component shall render a known icon name as an inline SVG using the 16x16 viewBox and stroke width defined by the icon set.

### 5.4 CI / pipeline

N/A — No CI pipeline changes in scope; tests run via npm scripts, not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates introduced by this feature.

### 5.6 Documentation

- [x] **AC-15**: The exported primitive components and their public prop types shall carry documentation comments.
- [x] **AC-24**: WHEN the renderer test stack is added, the system shall record the chosen test stack in the architecture docs.

### 5.7 Hygiene

- [x] **AC-16**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-17**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-18**: The primitive component sources shall contain no inline style attributes.
  > Verification: ! grep -rEn 'style=[{][{]' src/renderer/src/components/atoms src/renderer/src/components/molecules
- [x] **AC-19**: The renderer primitive code shall not import the electron or node modules directly.
  > Verification: ! grep -rEn "from '(electron|node:)" src/renderer/src/components src/renderer/src/lib

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Any network / request-response or persistence logic — the primitives are presentation-only. — F-2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover-10
- NOT included: UI elements beyond the four named primitives (buttons, inputs, tabs, tables, etc.).
- NOT included: A theming engine, runtime theme switcher, or authoring/editing of design token files — primitives only consume existing tokens.
- NOT included: Reproducing the design/reference.html markup or its generated cruft (data-om-\*, \_\_OmT wrappers, inline styles, tweaks-panel).
- NOT included: Published-package API-stability guarantees — the layer is app-internal only.

## 7. Technical Constraints

- Must follow: Shared renderer state (the Toast queue) lives in a zustand toastStore; never mutate store state outside its actions (constitution §4 Always-Do).
- Must follow: Primitives are renderer-only and presentation-only — no main/preload/IPC involvement; never import node or electron in renderer code (constitution §4). Primitives live under src/renderer/src/components and the styling consumes tokens under design/.
- Must follow: Style exclusively via semantic class names bound to the existing tokens.css CSS custom properties; no inline styles. design/reference.html is a look/behavior reference only — never reproduce its markup.
- Must follow: Radix is the recommended headless library for the overlay behavior; this spec stays behavior-only and the final library pick is deferred to /plan.
- Must follow: Keep the lib/ substrate thin: do not hand-roll focus-trap or positioning that the headless library already provides (constitution §6.3 search-before-building).
- Must follow: Meet WCAG 2.1 AA keyboard and focus expectations for every primitive (focus trap/return, Escape, ARIA roles).
- Must not break: The Icon stays project-owned — no icon-library dependency is introduced (the SVG path set already exists).
- Must follow constitution §3.1: strict is on; do not weaken it per-file. No 'any' — type external input as 'unknown' and narrow with a guard. The Icon name must be a typed string-literal union.
- Must follow constitution §2.3: Renderer modules resolve through the @renderer alias; import via the alias, not deep relative paths. Keep code in its process dir — no cross-process imports.
- Must follow constitution §3.4: Pick a renderer test stack (Vitest + Testing Library) before the first feature that needs coverage; record it in docs/architecture.md.
- Must follow constitution §3.3: Components PascalCase; hooks camelCase use-prefixed; zustand stores Store-suffixed.
- Must follow constitution §3.2: Never swallow errors — no empty catch; handle both success and error paths of every fallible operation.

## 8. Open Questions

- **Q-1**: Final headless-library selection (Radix vs Base UI vs React Aria) is deferred to /plan; discovery recommends Radix.
- **Q-2**: Confirm Icon stays project-owned vs pulling an icon dependency — discovery resolved this as sound since the ~40 SVG paths already exist.
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes

## 9. Risks

| Risk                                                                                                                                    | Likelihood | Impact | Mitigation                                                                                                       |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| Radix Toast may not natively cover stacking + hover/focus pause + rapid-fire queue.                                                     | Med        | Med    | Derisk spike; if it falls short, the zustand toastStore owns the queue and Radix Toast renders individual items. |
| No test framework exists, so the Vitest + Playwright setup is a gating prerequisite that could slip and block all interaction-test ACs. | High       | Med    | Make the test-stack setup the first task; record the stack in docs/architecture.md per constitution §3.4.        |
| Nested-overlay composition (Escape topmost-only, nested focus-trap/return) is the most failure-prone behavior.                          | Med        | Med    | Prototype nested behavior early; cover with dedicated interaction + Playwright tests.                            |
| Styling Radix component state (open/closed, side) via semantic classes may fight the token-driven stylesheet approach.                  | Med        | Low    | Spike a Radix Dialog + DropdownMenu styled solely via token CSS vars before broad rollout.                       |
| jsdom may not faithfully reproduce focus/keyboard behavior, hiding real a11y defects.                                                   | Low        | Med    | Run Playwright component tests in a real browser for focus/keyboard fidelity.                                    |
