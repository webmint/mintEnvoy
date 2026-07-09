---
last_indexed: 2026-07-09
source_stamp: fb347874d3755d5f
---


# mintenvoy

A desktop API client built with Electron, React, and TypeScript

---

> Commands named in backticks (e.g. `constitute`, `onboard`) are invoked with the `/` prefix in Claude Code (e.g. `/constitute`).
>
> This file is the project overview. The setup wizard fills in the name and description from Phase 2 answers; `constitute` and `onboard` may append deeper context; the tech-writer agent updates this file as features ship.
>
> For technical stack details (framework, language, build commands, per-package breakdown for monorepos), see the project primer (`CLAUDE.md`). That file is the runtime-facing source of truth for stack facts.
>
> For architecture decisions and per-layer rules, see `docs/architecture.md`.
>
> Feature changes are reflected by tech-writer's surgical updates to the relevant `docs/<package>/` docs (and `docs/architecture.md` for project-wide changes) when a feature ships via `/finalize` — not in a per-feature file.

## What this project is for

mintEnvoy is desktop tooling for composing, sending, and inspecting HTTP API requests — a desktop API client in the Postman/Insomnia space. The intended domain centers on four entities (design intent, not yet implemented in the scaffold): **Request** (an HTTP call definition — method, URL, headers, body), **Response** (status, headers, body, timing), **Collection** (a saved, organized group of Requests), and **Environment** (named variables substituted into Requests at send time).

It is built on Electron's three-process model (main / preload / renderer) so the renderer stays a sandboxed React UI and privileged capability — outbound HTTP via undici, persistence via electron-store, auto-update via electron-updater — lives in the main process, reached only over the preload IPC bridge. The current codebase is an early scaffold: the user-facing request/response flow is not built yet, and work to date establishes the reusable UI-primitive layer (Icon, Dropdown, Modal, Toast over Radix) the interface will be assembled from.

## How it's used

Run the app in development with `npm run dev` (electron-vite dev); build and preview a production bundle with `npm run build` then `npm run start`; package OS installers with `npm run build:mac` / `build:win` / `build:linux`.

Two entry points bootstrap the app: the **main process** (`src/main/index.ts`) creates the single BrowserWindow and drives the app lifecycle, and the **renderer** (`src/renderer/src/main.tsx`) mounts the React `App` into `index.html` under StrictMode. In development, `App` also surfaces a dev-only `PrimitivesDemo` gallery (gated on `import.meta.env.DEV`, tree-shaken from production) for visually exercising the primitive library. Typical end-user request/response flows will land as the domain entities above are implemented.

## Purpose

mintEnvoy is a desktop API client built on Electron, React 19, and TypeScript. It follows Electron's three-process model: a main process owning window creation and app lifecycle, a contextIsolation-safe preload bridge exposing a typed IPC surface, and a renderer holding the entire React UI. Renderer state lives in module-level zustand stores; outbound HTTP runs through undici, local persistence through electron-store, and auto-update through electron-updater. The build is bundled by electron-vite and packaged per-OS by electron-builder.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React |
| Language | TypeScript |
| Build Tool | Vite |
| Testing | Vitest |

## Project Structure

```text
mintEnvoy/
├── __snapshots__/  # Playwright CT screenshot baselines
│   └── components/
│       ├── molecules/
│       └── organisms/
├── bugs/  # Filed bug records (/report-bug lifecycle)
│   ├── 001-playwright-ct-harness-broken.md
│   ├── 002-leftover-ping-debug-artifact.md
│   ├── 003-dropdown-ct-click-outside-dismiss.md
│   ├── 004-review-consume-tmp-parser.md
│   ├── 005-active-tab-text-contrast.md
│   ├── 006-inactive-tab-text-contrast.md
│   ├── 007-close-button-icon-contrast.md
│   ├── 008-missing-main-landmark.md
│   ├── 009-kvtable-checkbox-not-dark.md
│   ├── 010-kvtable-header-vs-row-font.md
│   └── 011-design-fonts-inter-and.md
├── design/  # Design reference (reference.html, tokens, screenshot)
│   ├── design-fidelity-contract.md
│   ├── reference-screenshot.png
│   ├── reference.html
│   └── styles.css
├── discover/  # Greenfield discovery reports (/discover)
│   ├── 2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.handoff.json
│   ├── 2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.md
│   ├── 2026-06-22-reusable-horizontal-tab-strip-primitive-for-switching.handoff.json
│   ├── 2026-06-22-reusable-horizontal-tab-strip-primitive-for-switching.md
│   ├── 2026-06-23-single-window-shell-and-layout-for-a-desktop-http-client.handoff.json
│   ├── 2026-06-23-single-window-shell-and-layout-for-a-desktop-http-client.md
│   ├── 2026-06-24-working-tabs-state-machine-request-data-model-requestspec.handoff.json
│   ├── 2026-06-24-working-tabs-state-machine-request-data-model-requestspec.md
│   ├── 2026-06-27-http-client-request-bar-color-coded-method-dropdown.handoff.json
│   ├── 2026-06-27-http-client-request-bar-color-coded-method-dropdown.md
│   ├── 2026-07-04-key-value-table-editor-params-headers-bound-to-the-active.handoff.json
│   ├── 2026-07-04-key-value-table-editor-params-headers-bound-to-the-active.md
│   ├── 2026-07-05-request-pane-sub-tabs-container-a-per-request-tab-switcher.handoff.json
│   └── 2026-07-05-request-pane-sub-tabs-container-a-per-request-tab-switcher.md
├── docs/  # Generated knowledge base (/generate-docs)
│   ├── main/
│   │   └── index.md
│   ├── preload/
│   │   └── index.md
│   ├── renderer/
│   │   ├── src/  # Electron source: main / preload / renderer
│   │   ├── styles/
│   │   └── index.md
│   ├── architecture.md
│   ├── glossary.md
│   ├── overview.md
│   └── structure.md
├── playwright/  # Playwright CT harness (index.html/index.tsx)
│   ├── index.html
│   └── index.tsx
├── playwright-report/  # Playwright HTML run report
│   └── index.html
├── research/  # Research reports + handoffs (/research)
│   ├── 2026-06-25-bring-tab-bar-to/
│   │   └── handoff.json
│   ├── 2026-06-26-reorganize-the-flat-components/
│   │   └── handoff.json
│   ├── 2026-06-27-003-dropdown-ct-click/
│   │   └── handoff.json
│   ├── 2026-06-27-remove-leftover-electron-vite/
│   │   └── handoff.json
│   ├── 2026-06-28-requestbar-009-visual-drift/
│   │   └── handoff.json
│   ├── 2026-06-29-tabbar-tab-grows-with/
│   │   └── handoff.json
│   ├── 2026-06-30-requestbar-visually-drifts-from/
│   │   └── handoff.json
│   ├── 2026-07-01-bug-005-active-tab/
│   │   └── handoff.json
│   ├── 2026-06-25-bring-tab-bar-to.md
│   ├── 2026-06-26-reorganize-the-flat-components.md
│   ├── 2026-06-27-003-dropdown-ct-click.md
│   ├── 2026-06-27-remove-leftover-electron-vite.md
│   ├── 2026-06-28-requestbar-009-visual-drift.md
│   ├── 2026-06-29-tabbar-tab-grows-with.md
│   ├── 2026-06-30-requestbar-visually-drifts-from.md
│   └── 2026-07-01-bug-005-active-tab.md
├── resources/  # App icons / static resources
│   └── icon.png
├── specs/  # Per-feature specs, plans, tasks, verdicts
│   ├── 001-ui-primitives/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── research.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 002-tabs-primitive/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── research.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 003-app-shell-layout/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── grill-state.json
│   │   ├── grill.md
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 004-working-tabs-state-machine/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── data-model.md
│   │   ├── grill-state.json
│   │   ├── grill.md
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 005-tab-bar-visual-fidelity/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── grill-seed.json
│   │   ├── grill-state.json
│   │   ├── grill.md
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 006-reorganize-flat-components/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 007-remove-ping-handler/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 008-dropdown-ct-dismiss/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 009-request-bar/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 010-request-bar-fidelity/
│   │   ├── tasks/
│   │   ├── HANDOFF-head-chip-fix.md
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 011-tab-width-cap/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 012-requestbar-element-fidelity/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 013-tabs-contrast-wcag/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   ├── 014-kv-table-editor/
│   │   ├── tasks/
│   │   ├── breakdown-handoff.json
│   │   ├── design-manifest.json
│   │   ├── grill-seed.json
│   │   ├── grill-state.json
│   │   ├── grill.md
│   │   ├── handoff.json
│   │   ├── plan-handoff.json
│   │   ├── plan.md
│   │   ├── review-state.json
│   │   ├── review.md
│   │   ├── spec.md
│   │   ├── summary.md
│   │   ├── verification.md
│   │   └── verify-state.json
│   └── 015-request-sub-tabs/
│       ├── tasks/
│       ├── breakdown-handoff.json
│       ├── design-manifest.json
│       ├── handoff.json
│       ├── plan-handoff.json
│       ├── plan.md
│       ├── review-state.json
│       ├── review.md
│       ├── spec.md
│       ├── summary.md
│       ├── verification.md
│       └── verify-state.json
├── src/  # Electron source: main / preload / renderer
│   ├── main/
│   │   └── index.ts
│   ├── preload/
│   │   ├── index.d.ts
│   │   └── index.ts
│   └── renderer/
│       ├── src/  # Electron source: main / preload / renderer
│       ├── styles/
│       └── index.html
├── test-results/  # Playwright test-run artifacts
├── CLAUDE.md
├── README.md
├── constitution.md
├── dev-app-update.yml
├── electron-builder.yml
├── electron.vite.config.ts
├── eslint.config.mjs
├── package-lock.json
├── package.json
├── playwright.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── tsconfig.web.json
└── vitest.config.ts
```

## Entry Points

| Entry Point | Path | Purpose |
|---|---|---|
| Main process | `src/main/index.ts` | Electron entry: window creation + app lifecycle |
| Preload bridge | `src/preload/index.ts` | contextIsolation-safe IPC surface to the renderer |
| Renderer app | `src/renderer/src/main.tsx` | React root mount for the UI |

## Key Commands

| Command | Description |
|---|---|
| `npm run format` | prettier --write . |
| `npm run lint` | eslint --cache . |
| `npm run typecheck:node` | tsc --noEmit -p tsconfig.node.json --composite false |
| `npm run typecheck:web` | tsc --noEmit -p tsconfig.web.json --composite false |
| `npm run typecheck` | npm run typecheck:node && npm run typecheck:web |
| `npm run start` | electron-vite preview |
| `npm run dev` | electron-vite dev |
| `npm run dev:audit` | electron-vite dev --remote-debugging-port 50757 |
| `npm run build` | npm run typecheck && electron-vite build |
| `npm run postinstall` | electron-builder install-app-deps |
| `npm run build:unpack` | npm run build && electron-builder --dir |
| `npm run build:win` | npm run build && electron-builder --win |
| `npm run build:mac` | electron-vite build && electron-builder --mac |
| `npm run build:linux` | electron-vite build && electron-builder --linux |
| `npm run test` | vitest run |
| `npm run test:ct` | playwright test -c playwright.config.ts |

## Module Map

### Infrastructure Packages

| Package | Purpose |
|---|---|
| `main` | Electron main process — window + app lifecycle |
| `preload` | contextIsolation-safe IPC bridge |

### Core Package

| Package | Purpose |
|---|---|
| `renderer` | React 19 UI + design-token styling |

## Cross-Module Dependencies

```text
mintenvoy
  +-- @electron-toolkit/preload
  +-- @electron-toolkit/utils
  +-- electron-store
  +-- electron-updater
  +-- radix-ui
  +-- undici
  +-- zustand
```

## Application Routes

| Route | Component | Description |
|---|---|---|

## Navigation Guards



## Test Files

- `__snapshots__/components/molecules/__tests__` — test directory
- `__snapshots__/components/organisms/__tests__` — test directory
- `specs` — test directory
- `src/renderer/src/__tests__` — test directory
- `src/renderer/src/components/__tests__` — test directory
- `src/renderer/src/components/atoms/__tests__` — test directory
- `src/renderer/src/components/molecules/__tests__` — test directory
- `src/renderer/src/components/organisms/__tests__` — test directory
- `src/renderer/src/components/organisms/shell/__tests__` — test directory
- `src/renderer/src/lib/__tests__` — test directory

## Packages

- main; docs/main/
- preload; docs/preload/
- renderer; docs/renderer/
