# Plan: UI Primitives Layer

**Date**: 2026-06-21
**Spec**: specs/001-ui-primitives/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — alternatives were already settled in `research.md` (§Alternatives Compared, seeded from the discovery report); no fresh 2+-alternative discovery was run.
- Phase 1.3 architecture decisions: yes (mandatory).
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — architect reported no sub-specialist needed (renderer-internal, presentation-only, no auth/PII/schema/perf-budget/IPC surface).

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: all rows
- Key Design Decisions: all rows (a)–(f)
- Risk Assessment seeds: rows 6–9 (architect) appended to spec §9 risks 1–5
- Constitution Compliance flags: §2.3, §3.1, §3.2, §4, §6.3

| Specialist | Sub-question                                                                                                     | Input summary                                                                                                                                     | Verdict  | Cites                                                                |
| ---------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------- |
| architect  | Layer map, key design decisions, risks, constitution flags, minimal change, OOS-respect for the primitives layer | Authored all Phase 2 table rows; Radix-backed overlays + project-owned Icon/Toast-queue/styling; thin lib/; no departures; all decisions in-scope | accepted | specs/001-ui-primitives/spec.md, specs/001-ui-primitives/research.md |

## Summary

Implement a presentation-only UI primitives layer in the mintEnvoy renderer: an Icon atom, Dropdown/Modal/Toast molecules wrapping Radix UI behavior, and a thin `lib/` substrate (a zustand `toastStore` + imperative `toast()` API + minimal Icon glue). Overlay focus/keyboard/a11y is delegated to the Radix unified `radix-ui` package; the Icon, all styling (semantic classes bound to the existing `tokens.css` CSS custom properties), and the Toast queue are project-owned. The renderer has no test infrastructure, so the gating first step adds Vitest + @testing-library/react + user-event (jsdom) plus Playwright component tests, recorded in docs per constitution §3.4.

## Technical Context

**Architecture**: Renderer process only (React 19) — a presentation layer (atoms/molecules + a dev demo route) over a thin support sublayer (`lib/`). No main/preload/IPC surface; dependencies flow presentation → support, never reverse.
**Error Handling**: Thrown exceptions per constitution §3.2; the Icon unknown-name path returns a fallback (never swallows / never throws); toastStore timer + dismiss paths handle both success and miss.
**State Management**: A single module-level zustand `toastStore` owns the toast queue (enqueue / auto-dismiss / manual-dismiss / hover-focus-pause); all mutation through store actions (§4). Dropdown/Modal are controlled via `open` + `onOpenChange` props (caller-owned state). No other shared state.

## Constitution Compliance

- §2.3 Module Organization — compliant: renderer-only; all intra-renderer imports via the `@renderer` alias, no deep relative paths; `lib/` must not import from `components/`.
- §3.1 Type Safety — compliant: `IconName` is a typed string-literal union; the Icon `name` is narrowed before SVG lookup; no `any`. Gated by AC-16 (`typecheck:web`).
- §3.2 Error Handling — compliant: Icon unknown-name returns a safe fallback (AC-13), no empty catch.
- §3.3 Naming — compliant: PascalCase components (Icon/Dropdown/Modal/Toast), use-prefixed hooks, `toastStore` (Store suffix).
- §3.4 Testing — requires attention (intended): no test stack exists; this feature establishes it (Vitest + Testing Library + Playwright) and records it in `docs/architecture.md` (AC-24).
- §4 Patterns — compliant: toast queue in a zustand store, mutated only via actions; no node/electron import in renderer (AC-19).
- §6.3 Search-before-building — compliant: `lib/` stays thin; Radix's focus-trap/positioning are reused, not re-implemented.

## Implementation Approach

### Layer Map

| Layer                                   | What                                                                                                                           | Files (existing or new)                                                                                                                              |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Renderer presentation — atoms           | Inline SVG Icon component + project-owned typed icon-path set (40 icons, 16x16, 1.5px stroke)                                  | src/renderer/src/components/atoms/Icon.tsx, src/renderer/src/components/atoms/icons.ts                                                               |
| Renderer presentation — molecules       | Dropdown/popover, Modal, Toast wrapping Radix behavior, styled via semantic classes                                            | src/renderer/src/components/molecules/Dropdown.tsx, src/renderer/src/components/molecules/Modal.tsx, src/renderer/src/components/molecules/Toast.tsx |
| Renderer support sublayer — lib/ (thin) | zustand toastStore (queue + auto/manual/pause) + imperative toast() API + minimal Icon glue — only what Radix does not provide | src/renderer/src/lib/toastStore.ts, src/renderer/src/lib/icons-glue.ts                                                                               |
| Renderer presentation — demo/QA surface | Dev-only in-app route rendering every primitive in all states                                                                  | src/renderer/src/components/PrimitivesDemo.tsx                                                                                                       |
| Styling (token-bound)                   | Per-component semantic-class stylesheets bound to existing CSS custom properties; no inline styles; no token authoring         | src/renderer/styles/tokens.css (consume only), per-component CSS under atoms/ + molecules/                                                           |
| Tooling / config                        | Add Vitest + @testing-library/react + user-event (jsdom) + Playwright component tests; record stack in docs                    | package.json, vitest.config.ts, playwright.config.ts, docs/architecture.md                                                                           |

### Key Design Decisions

| Decision                     | Chosen Approach                                                                                                                                        | Why                                                                                                                                                                  | Alternatives Rejected                                                                                                                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| (a) Headless overlay library | Radix unified `radix-ui` package — `import { Dialog, DropdownMenu, Popover, Toast } from "radix-ui"`                                                   | Mature Dialog/DropdownMenu/Popover/Toast; official React 19; unstyled + className styling; best correctness-per-line for bug-prone focus/keyboard/a11y (research.md) | React Aria (more code/heavier API); Base UI (smaller battle-test surface); Ark UI (heavier XState abstraction); Headless UI (Tailwind-oriented, no Toast); hand-rolled Floating UI + `<dialog>` (re-incurs the a11y bug class) |
| (b) lib/ substrate           | THIN: only toastStore + toast() API + minimal Icon glue; Radix owns focus-trap/positioning                                                             | constitution §6.3 + §7 "keep lib/ thin"; hand-rolling focus-trap/positioning duplicates Radix                                                                        | Hand-rolled overlay substrate (focus-trap/positioning utilities) — duplicates Radix, largest test burden                                                                                                                       |
| (c) Toast queue              | zustand `toastStore` owns the stack (enqueue/dequeue/auto-dismiss/manual-dismiss/hover-focus-pause); drives Radix `Toast.Root`/`Toast.Viewport` render | constitution §4 shared-state-in-zustand; Radix Toast is a render/a11y primitive, not a queue. Covers AC-8/AC-9/AC-10/AC-22                                           | Radix-only Toast (cannot own stacking/rapid-fire/pause — §9 risk 1); component-local useState queue (violates §4)                                                                                                              |
| (d) Icon                     | Project-owned typed string-literal-union `IconName` over the 40-icon set + safe fallback for unknown name                                              | constitution §3.1 typed union, no any; §7 Icon project-owned. Covers AC-23 (known → render) + AC-13 (unknown → fallback, no throw)                                   | Icon-library dependency (violates §7); untyped `name: string` (violates §3.1); throw on unknown (violates AC-13)                                                                                                               |
| (e) Styling                  | Semantic class names bound to existing tokens.css CSS custom properties; per-component stylesheets; zero inline styles                                 | constitution §7 + AC-18; Radix parts accept className, satisfying the constraint directly                                                                            | Inline styles (violates AC-18); CSS-in-JS runtime (new dep, not token-bound); token authoring/switching (§6 OOS theming engine)                                                                                                |
| (f) Test stack               | Vitest + @testing-library/react + user-event (jsdom) for interaction; Playwright component tests for real-browser focus/keyboard fidelity              | constitution §3.4; jsdom focus/keyboard gaps covered by Playwright (research.md). Set up first per §9 risk 2; record in docs per AC-24                               | happy-dom (less complete focus/range API); jsdom-only (focus/keyboard fidelity gaps hide a11y defects)                                                                                                                         |

### File Impact

| File                                               | Action | What Changes                                                                                               |
| -------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/atoms/Icon.tsx         | Create | Inline SVG Icon component (typed `name`, size, className; fallback on unknown)                             |
| src/renderer/src/components/atoms/icons.ts         | Create | Project-owned typed icon-path set (40 icons) + `IconName` union                                            |
| src/renderer/src/components/molecules/Dropdown.tsx | Create | Dropdown/popover wrapping Radix DropdownMenu/Popover, semantic-class styled                                |
| src/renderer/src/components/molecules/Modal.tsx    | Create | Modal wrapping Radix Dialog (focus trap, scrim, Escape, body scroll lock)                                  |
| src/renderer/src/components/molecules/Toast.tsx    | Create | Toast rendering Radix Toast.Root/Viewport driven by toastStore                                             |
| src/renderer/src/lib/toastStore.ts                 | Create | Module-level zustand store + `toast()` imperative API (queue/auto/manual/pause)                            |
| src/renderer/src/lib/icons-glue.ts                 | Create | Minimal Icon lookup/fallback helper                                                                        |
| src/renderer/src/components/PrimitivesDemo.tsx     | Create | Dev-only route exercising every primitive in all states                                                    |
| (per-component CSS under atoms/ + molecules/)      | Create | Semantic-class stylesheets bound to tokens.css custom properties                                           |
| package.json                                       | Modify | Add `radix-ui` dep; add vitest/@testing-library/react/user-event/jsdom/Playwright dev deps + `test` script |
| vitest.config.ts                                   | Create | Vitest + jsdom config for renderer interaction tests                                                       |
| playwright.config.ts                               | Create | Playwright component-test config                                                                           |
| docs/architecture.md                               | Modify | Record the chosen renderer test stack (AC-24)                                                              |
| (App root) src/renderer/src/App.tsx                | Modify | Mount the single Radix Toast.Provider/Viewport + portal container once                                     |

### Documentation Impact

| Doc File             | Action | What Changes                                                                                                                                                                 |
| -------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| docs/architecture.md | Update | Record the renderer test stack (Vitest + Testing Library + Playwright) per constitution §3.4 / AC-24; note the primitives layer + layering (presentation → thin lib support) |
| docs/overview.md     | Update | Note the UI primitives layer as a building block once it lands                                                                                                               |

## Risk Assessment

| Risk                                                                                                                                    | Likelihood | Impact | Mitigation                                                                                                              |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------- |
| Radix Toast may not natively cover stacking + hover/focus pause + rapid-fire queue                                                      | Med        | Med    | The zustand toastStore owns the queue; Radix Toast renders individual items. Derisk spike before broad rollout          |
| No test framework exists — Vitest + Playwright setup is a gating prerequisite that could slip                                           | High       | Med    | Make test-stack setup the first task; record the stack in docs/architecture.md (§3.4)                                   |
| Nested-overlay composition (Escape topmost-only, nested focus-trap/return) is the most failure-prone behavior                           | Med        | Med    | Prototype nested behavior early; dedicated interaction + Playwright tests                                               |
| Styling Radix component state (open/closed, side) via semantic classes may fight the token-driven stylesheet                            | Med        | Low    | Spike a Radix Dialog + DropdownMenu styled solely via token CSS vars before broad rollout                               |
| jsdom may not faithfully reproduce focus/keyboard behavior, hiding real a11y defects                                                    | Low        | Med    | Run Playwright component tests in a real browser for focus/keyboard fidelity                                            |
| Dependency-direction leak: molecules using deep relative imports, or lib/ importing from components/ (support → presentation inversion) | Med        | Med    | Mandate `@renderer` alias; lib/ must not import from components/; lint/CBM import-direction check                       |
| Toast singleton boundary: multiple toastStore instances split the queue                                                                 | Low        | Med    | Single module-level store export; `toast()` calls `toastStore.getState().enqueue(...)`, never instantiates per-consumer |
| Radix portal mount point not established at renderer root — detached node breaks z-order/scrim                                          | Med        | Low    | Mount the single Provider/Viewport + portal container at App root once; document it                                     |
| Demo route (PrimitivesDemo) ships in the production bundle                                                                              | Low        | Low    | Gate behind a dev-only conditional / route guard so it is unreachable / tree-shaken in packaged builds                  |

## Dependencies

- **Runtime**: `radix-ui` (unified package — Dialog, DropdownMenu, Popover, Toast).
- **Dev (test stack)**: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, Playwright component testing (`@playwright/experimental-ct-react` or `@playwright/test`).
- **Existing (reused)**: `zustand` (toastStore), React 19, the `@renderer` alias, and `src/renderer/styles/tokens.css`.
- No services, env vars, or main/preload changes.

## Supporting Documents

- [Research](research.md) — alternatives comparison + Radix/test-stack decisions
