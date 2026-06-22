# Project Constitution — mintenvoy

Generated: 2026-06-21
Last updated: 2026-06-21
Mode: Existing Codebase

> Sections marked `[universal]` are pre-populated with rules that apply to ALL projects.
> Sections marked `[project-specific]` are populated by `/constitute` based on your codebase or interview answers.

---

## 1. Project Identity

**Name**: mintenvoy
**Type**: desktop app
**Domain**: Desktop tooling for composing, sending, and inspecting HTTP API requests
**Stack**: TypeScript on Electron + React, three-process model (main / preload / renderer), bundled by electron-vite and packaged by electron-builder

---

## 2. Architecture Rules (NON-NEGOTIABLE)

These rules MUST be followed in every code change. Violating these rules requires explicit user approval.

### 2.1 Process Boundaries

mintEnvoy runs as three Electron processes — main (Node.js), preload (bridge), and renderer (React UI) — that communicate only over IPC; the renderer never touches Node APIs directly.

| Process  | Path              | Contains                                                          | Imports from                        |
| -------- | ----------------- | ----------------------------------------------------------------- | ----------------------------------- |
| Main     | src/main/         | Lifecycle, windows, native APIs, electron-store, electron-updater | Node.js, electron                   |
| Preload  | src/preload/      | contextBridge IPC surface                                         | electron, @electron-toolkit/preload |
| Renderer | src/renderer/src/ | React 19 UI, zustand state                                        | react, @renderer alias              |

- [project-specific] Main process owns app lifecycle, windows, native APIs, persistence (electron-store), and auto-update (electron-updater).
- [project-specific] Renderer is sandboxed React UI; it reaches privileged capability only through the preload bridge.
- [project-specific] Outbound HTTP (undici) runs in main, not the renderer; the renderer requests it over IPC.

### 2.2 IPC & Security

All main-renderer communication crosses the preload contextBridge; contextIsolation stays on and nodeIntegration stays off.

- [project-specific] Expose the IPC surface from src/preload via contextBridge.exposeInMainWorld; never enable nodeIntegration in the renderer.
- [universal] Validate and narrow every IPC payload at the boundary before use.

**CORRECT** — preload exposes a typed API surface

```ts
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('api', {
  sendRequest: (req: ApiRequest) => ipcRenderer.invoke('http:send', req)
})
```

**WRONG** — renderer reaching electron directly bypasses isolation

```ts
// in renderer code
const { ipcRenderer } = require('electron')
ipcRenderer.invoke('http:send', req) // nodeIntegration must be OFF
```

### 2.3 Module Organization & Imports

Renderer modules resolve through the @renderer alias defined in electron.vite.config.ts.

- [enforced] @renderer resolves to src/renderer/src (electron.vite.config.ts); import renderer modules via the alias, not deep relative paths.
- [project-specific] Keep code in its process dir: src/main, src/preload, src/renderer — no cross-process imports except the preload-exposed API.

---

## 3. Code Quality Standards

### 3.1 Type Safety [project-specific]

TypeScript runs in strict mode (@electron-toolkit/tsconfig base) across node + web configs.

- [enforced] strict is on; do not weaken it per-file. Type-check via 'npm run typecheck' (node + web) before completing a task.
- [enforced] No 'any'. Type external/IPC input as 'unknown' and narrow with a type guard.

**CORRECT** — narrow unknown with a guard

```ts
function parse(input: unknown): ApiRequest {
  if (!isApiRequest(input)) throw new Error('invalid request')
  return input
}
```

**WRONG** — any disables type checking

```ts
function parse(input: any) {
  return input
}
```

### 3.2 Error Handling [project-specific]

The project uses thrown exceptions.

- [universal] Never swallow errors — no empty catch; handle, re-throw, or log with reason.
- [universal] Handle both success and error paths of every fallible operation.
- [project-specific] IPC handlers in main catch and convert errors into structured results the renderer can render — don't leak raw stack traces across the bridge.

### 3.3 Naming Conventions [universal]

Consistent naming across React, hooks, stores, and IPC channels.

| What            | Convention              | Example         |
| --------------- | ----------------------- | --------------- |
| React component | PascalCase              | Versions        |
| Hook            | camelCase, use-prefix   | useRequestStore |
| zustand store   | camelCase, Store suffix | requestStore    |
| Component file  | PascalCase.tsx          | App.tsx         |
| IPC channel     | namespaced colon        | http:send       |

### 3.4 Testing Requirements [universal]

No test infrastructure exists yet (testings: N/A).

- [universal] When adding tests, cover acceptance criteria including edge + error paths; follow the chosen runner's existing patterns once established.
- [project-specific] Pick a renderer test stack (e.g. Vitest + Testing Library) before the first feature that needs coverage; record it in docs/architecture.md.

### 3.5 Documentation [universal]

Code discovery routes through codebase-memory-mcp; new code carries clear docs.

- [enforced] Structural code queries use codebase-memory-mcp tools (search_graph / trace_path / get_code_snippet / search_code / query_graph), not raw Read/Grep/Glob over source — CBM hooks block raw discovery on first match per session.
- [universal] docs/ is LLM-context-source first, dev-greppable second; structural metadata stays in CBM, not embedded in docs/.
- [universal] All new functions and exported types carry clear documentation.

### 3.6 Function Length & Complexity [universal]

Keep units small and single-purpose.

- [universal] One responsibility per function; extract when a function grows past ~40 lines or mixes concerns.
- [universal] SOLID, DRY (don't repeat logic 3+ times), KISS.

---

## 4. Patterns & Anti-Patterns

### Always Do (Universal)

- [universal] Validate inputs at module boundaries; trust internal code.
- [universal] Read a file before modifying it.
- [universal] Handle both success and error paths of every fallible operation.

### Always Do (Project-Specific)

- [project-specific] Shared renderer state lives in a zustand store.
- [project-specific] Reach privileged capability only through the preload-exposed API.
- [project-specific] Run outbound HTTP (undici) in main; the renderer requests it over IPC.

### Never Do (Universal)

- [universal] Never swallow errors (no empty catch).
- [universal] Never commit secrets, API keys, or tokens.
- [universal] Never leave debug artifacts (console.log, debugger) behind.

### Never Do (Project-Specific)

- [project-specific] Never enable nodeIntegration in the renderer.
- [project-specific] Never import Node or electron directly in renderer code.
- [project-specific] Never mutate zustand state outside its store actions.

### Prefer (Universal)

- [universal] Prefer composition over inheritance.
- [universal] Prefer small, pure, single-purpose functions.

### Prefer (Project-Specific)

- [project-specific] Prefer zustand selectors over reading the whole store.
- [project-specific] Prefer the @renderer alias over deep relative imports.
- [project-specific] Prefer typed IPC wrappers over raw ipcRenderer calls in components.

---

## 5. Domain Rules

### 5.1 Key Entities

The API-client domain centers on a small set of entities (design intent — not yet implemented in the scaffold).

- [project-specific] Request — an HTTP call definition (method, URL, headers, body).
- [project-specific] Response — the result of sending a Request (status, headers, body, timing).
- [project-specific] Collection — a saved, organized group of Requests.
- [project-specific] Environment — a named set of variables substituted into Requests at send time.

---

## 6. Workflow Rules

### 6.1 Minimal Changes

Keep every change as small as possible.

- [universal] Every change impacts as little code as possible; don't fix unrelated code you happen to see.

### 6.2 Read Before Write

Understand a file before changing it.

- [universal] Always read a file before modifying it.

### 6.3 Search Before Building

Reuse before reinventing.

- [universal] Before writing anything generic/reusable, search the codebase for an existing utility, helper, or component that already does it.

### 6.4 One Task At A Time

Sequential execution along the dependency graph.

- [universal] Execute tasks sequentially along the dependency graph; finish and verify one before starting the next.

### 6.5 Pre-flight Check

Load context before each task.

- [universal] Before each task, read constitution.md + .devforge/memory.md so the task starts with the right context.

### 6.6 Spec-Driven Workflow

Enforcement level: Strict — every pipeline step requires explicit approval.

- [project-specific] Follow /specify, /plan, /breakdown, /implement, /review, /verify, /finalize; each hard gate needs explicit approval before advancing.
- [project-specific] Commits follow Conventional Commits; WIP commits squash into one clean feature commit at /finalize.
- [project-specific] Commit messages include the AI attribution footer.
