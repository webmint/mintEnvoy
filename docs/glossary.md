---
generated_by: /generate-docs (Phase B — glossary)
last_indexed: 2026-06-22
total_terms: 36
---

# Project Glossary

Terms surfaced in `docs/` and cross-referenced against the CBM-indexed code graph. Code-anchored entries link to a canonical definition; prose-only entries have no code symbol but appear in narrative.

## App

App.tsx, the renderer's root component. It mounts the single ToastProvider + ToastViewport and dev-gates the PrimitivesDemo gallery behind import.meta.env.DEV.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: Toast, Renderer, DEV

## BrowserWindow

The single Electron window the main process creates (900x670, hidden until ready-to-show), with the preload script attached and sandbox-tuned webPreferences.

- **Used in**: `architecture.md`, `main/index.md`, `overview.md`
- **Related**: Main, Electron, contextBridge

## Build

Build tooling — electron-vite (Vite) bundles the main/preload/renderer targets; electron-builder packages OS installers.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Vite, Commands

## className

A space-separated CSS class string. The renderer composes these with the cx() helper, which drops falsy tokens, instead of open-coded filter/join or template literals.

- **Used in**: `architecture.md`, `renderer/index.md`
- **Related**: Icon, Build

## CLAUDE

CLAUDE.md — the per-project primer holding stack facts (language, framework, build/lint/typecheck commands) and working guidance for Claude Code.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Commands

## Code

[TODO: human-define]

- **Used in**: `architecture.md`, `overview.md`

## Commands

The project's npm scripts (dev, build, typecheck, lint, test, test:ct, build:mac/win/linux) for running, checking, and packaging the app.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Build, Vite

## contextBridge

The Electron preload API that exposes privileged main-world globals (window.electron, window.api) to the renderer, only when context isolation is enabled.

- **Used in**: `architecture.md`, `preload/index.md`
- **Related**: contextIsolation, Renderer, Electron

## contextIsolation

Electron's security boundary keeping the preload and renderer JS contexts separate. The preload is the only place permitted to expose APIs across it, via contextBridge.

- **Used in**: `architecture.md`, `overview.md`, `preload/index.md`
- **Related**: contextBridge, Electron, Renderer

## Cross

Shorthand for the docs' cross-cutting concerns and Cross-Module Dependencies sections — renderer isolation, dev-only elimination, and the outbound dependency graph.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Module, Renderer

## DEV

import.meta.env.DEV — Vite's build-time dev flag. Replaced with false in production so dev-only code (the PrimitivesDemo gallery) is statically unreachable and tree-shaken out.

- **Used in**: `architecture.md`, `renderer/index.md`
- **Related**: Vite, App

## Dropdown

A molecule wrapping Radix DropdownMenu — a controlled menu with keyboard navigation, click-outside/Escape dismiss, focus return, and edge-aware positioning.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: Radix, Modal, UI

## Electron

The desktop runtime mintEnvoy is built on. It enforces a three-process model — a Node.js main process, a contextIsolation-safe preload bridge, and a Chromium renderer — for security isolation.

- **Used in**: `architecture.md`, `glossary.md`, `main/index.md` (and 3 others)
- **Related**: Main, Renderer, contextIsolation, BrowserWindow

## Icon

Presentation atom: an inline-SVG component with a typed IconName union over the project-owned 40-icon set. Decorative (aria-hidden) by default; announced when given a label.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: UI, className

## IPC

Inter-process communication between Electron's main and renderer processes. The main process is the IPC host; the renderer reaches it through preload-exposed globals.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Main, contextBridge, Renderer

## Main

The Electron main process (src/main/index.ts) — Node.js lifecycle, native window creation, and IPC host. It never imports renderer code.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Electron, BrowserWindow, IPC, Renderer

## mintEnvoy

The project: a desktop API client built on Electron, React 19, and TypeScript, bundled by electron-vite and packaged by electron-builder.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Electron, Renderer

## Modal

A molecule wrapping Radix Dialog — a controlled dialog with focus trap, Escape-to-close, focus return, an overlay scrim, and body scroll lock.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: Radix, Dropdown, UI

## Module

Module Map / Module Structure — the project-overview grouping of source areas into infrastructure (main, preload) and core (renderer).

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Packages, Main, Renderer

## No

[TODO: human-define]

- **Used in**: `architecture.md`, `glossary.md`

## Package

A workspace/build unit. mintEnvoy is single-root with one root package; the docs treat main/preload/renderer as source modules rather than separate packages.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Packages, Module

## Packages

The project-overview section listing mintEnvoy's top-level source areas (main, preload, renderer). Single-root project, so these are modules, not separate workspace packages.

- **Used in**: `architecture.md`, `overview.md`, `structure.md`
- **Related**: Package, Module, mintEnvoy

## Project

The project-tier scope of the docs and spec workflow; the CLAUDE.md primer is its entrypoint for stack facts.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md`
- **Related**: CLAUDE, mintEnvoy

## Purpose

[TODO: human-define]

- **Used in**: `main/index.md`, `overview.md`, `preload/index.md` (and 1 others)

## Radix

The radix-ui unified package providing the headless overlay substrate — focus-trap, keyboard navigation, and positioning — that Dropdown, Modal, and Toast wrap with project styling.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: Dropdown, Modal, Toast

## Renderer

The React 19 process hosting the user-facing UI. It carries no Node/Electron imports and reaches the platform only through preload-exposed window globals.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Electron, contextBridge, UI

## Stack

Tech Stack — the project's technologies (React, TypeScript, Vite, Vitest); the Renderer Test Stack is its testing subset.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Vite, Vitest, Testing

## Structure

[TODO: human-define]

- **Used in**: `architecture.md`, `main/index.md`, `overview.md` (and 3 others)

## Test

Test files: *.{test,spec}.{ts,tsx} (Vitest) and *.ct.{ts,tsx} (Playwright CT), co-located under src/renderer/src/**/__tests__/.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Vitest, Testing

## Testing

The renderer test approach: Vitest + testing-library (jsdom) for interaction, and Playwright component tests for real-browser focus/keyboard fidelity. No main/preload test infra yet.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Vitest, Test

## The

[TODO: human-define]

- **Used in**: `architecture.md`, `glossary.md`, `overview.md` (and 1 others)

## This

[TODO: human-define]

- **Used in**: `architecture.md`, `overview.md`

## Toast

A molecule rendering the notification queue via Radix Toast.Root/Toast.Viewport. A single ToastProvider + ToastViewport is mounted once at the App root; multiple instances would split the queue.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: Radix, App, Renderer

## UI

The renderer's UI Primitives Layer (feature 001-ui-primitives): the Icon atom plus Dropdown, Modal, and Toast molecules — reusable, accessible building blocks for the desktop client's interface.

- **Used in**: `architecture.md`, `overview.md`, `renderer/index.md`
- **Related**: Renderer, Icon, Dropdown, Modal, Toast

## Vite

The bundler underlying electron-vite. It builds the three process targets and applies build-time DEV substitution for dead-code elimination.

- **Used in**: `architecture.md`, `main/index.md`, `overview.md`
- **Related**: DEV, Build, Commands

## Vitest

The unit/interaction test runner for the renderer, paired with @testing-library/react and user-event under jsdom.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: Testing, Test, Renderer
