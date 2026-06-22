# Task 009: build the dev-only primitives demo route

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 003, 005, 006, 007
**Blocks**: None
**Spec criteria**: AC-21
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                                           | Action | Description                                                |
| ---------------------------------------------- | ------ | ---------------------------------------------------------- |
| src/renderer/src/components/PrimitivesDemo.tsx | Create | Dev-only route rendering every primitive in all its states |

## Description

Build the demo/QA surface: a dev-only in-app route that renders Icon, Dropdown, Modal, and Toast in every state (open/closed, stacked toasts, nested overlays, reduced-motion). This is the visual + manual-QA surface from the spec's success criteria. Convergence task (depends on all four primitives) → review checkpoint. The route MUST be dev-only / route-guarded so it tree-shakes from (or is unreachable in) packaged production builds (plan §9 risk: demo ships to prod).

## Change Details

- In `src/renderer/src/components/PrimitivesDemo.tsx`:
  - Render a gallery: each Icon name; Dropdown open + closed; Modal open + closed; Toast triggers (single, stacked, rapid-fire).
  - Gate the route behind a dev-only conditional (e.g. `import.meta.env.DEV`) so it is unreachable / tree-shaken in packaged builds.
  - Import all primitives via the `@renderer` alias; presentation only, no business logic.

## Contracts

### Expects (checked before execution)

- `Icon` (003), `Toast`/`ToastViewport` (005), `Modal` (006), `Dropdown` (007) are exported and importable via `@renderer`.

### Produces (checked after execution)

- `PrimitivesDemo.tsx` exports a demo component rendering every primitive in its states.
- The demo is dev-only / route-guarded (e.g. behind `import.meta.env.DEV`) so it does not reach packaged production builds.

## Done When

- [x] The demo renders Icon, Dropdown, Modal, and Toast in their states (visual + manual-QA surface)
- [x] The route is dev-only-guarded and unreachable / tree-shaken in a production build
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-22T14:02:17Z
**Files changed**: src/renderer/src/components/PrimitivesDemo.tsx, src/renderer/src/components/PrimitivesDemo.css, src/renderer/src/components/__tests__/PrimitivesDemo.test.tsx, src/renderer/src/App.tsx
**Contract**: Expects 1/1 | Produces 2/2
**Notes**: Dev-only PrimitivesDemo gallery (all 4 primitives in states). DEV-gated dynamic import -> JS+CSS absent from prod bundle. Scrollable via position:fixed scroll container (fixed user-reported no-scroll bug without touching global body rule). Production-safety guard tested. 118 tests + build.
