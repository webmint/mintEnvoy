---
last_indexed: 2026-06-22
source_stamp: 0b70347c45e28304
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

mintEnvoy is a desktop API client built on Electron, React 19, and TypeScript. It follows Electron's three-process model: a Node.js main process owning the app lifecycle and native window, a contextIsolation-safe preload bridge, and a React renderer that hosts the user-facing UI. The current codebase centers on a reusable headless UI-primitive library (Icon, Dropdown, Modal, Toast over Radix) with a zustand toast queue and design-token styling. Bundled by electron-vite, packaged by electron-builder.

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
├── design/  # Design mockup + token source export
│   ├── mintenvoy — a friendly API client.html
│   ├── styles.css
│   └── tokens.json
├── discover/  # Greenfield discovery reports
│   ├── 2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.handoff.json
│   └── 2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.md
├── docs/  # Generated knowledge base (this tree)
│   ├── main/
│   │   └── index.md
│   ├── preload/
│   │   └── index.md
│   ├── renderer/
│   │   └── index.md
│   ├── architecture.md
│   ├── glossary.md
│   ├── overview.md
│   └── structure.md
├── playwright/  # Playwright component-test harness mount
│   ├── index.html
│   └── index.tsx
├── playwright-report/  # Playwright HTML test reports
│   ├── data/
│   │   └── 2f481f89c44a472d10ea2bbf76d848ef01408737.md
│   └── index.html
├── resources/  # App icons / static resources
│   └── icon.png
├── specs/  # Spec-driven feature artifacts (spec/plan/tasks)
│   └── 001-ui-primitives/
│       ├── tasks/
│       ├── breakdown-handoff.json
│       ├── handoff.json
│       ├── plan-handoff.json
│       ├── plan.md
│       ├── research.md
│       ├── review-state.json
│       ├── review.md
│       ├── spec.md
│       ├── summary.md
│       ├── verification.md
│       └── verify-state.json
├── src/  # Electron source — main, preload, renderer processes
│   ├── main/
│   │   └── index.ts
│   ├── preload/
│   │   ├── index.d.ts
│   │   └── index.ts
│   └── renderer/
│       ├── src/  # Electron source — main, preload, renderer processes
│       ├── styles/
│       └── index.html
├── test-results/  # Test-runner output artifacts
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
| Main process | `src/main/index.ts` | Electron entry; creates BrowserWindow and drives app lifecycle |
| Renderer app | `src/renderer/src/main.tsx` | React root; mounts App into index.html under StrictMode |

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
| `main` | Node.js main process — window creation, app lifecycle, IPC |
| `preload` | contextIsolation-safe bridge exposing electron + api globals |

### Core Package

| Package | Purpose |
|---|---|
| `renderer` | React UI — primitive library, toast store, design tokens |

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

- `specs` — test directory
- `src/renderer/src/__tests__` — test directory
- `src/renderer/src/components/__tests__` — test directory
- `src/renderer/src/components/atoms/__tests__` — test directory
- `src/renderer/src/components/molecules/__tests__` — test directory
- `src/renderer/src/lib/__tests__` — test directory

## Packages

- main; docs/main/
- preload; docs/preload/
- renderer; docs/renderer/
