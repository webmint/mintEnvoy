# Research: UI Primitives Layer

**Date**: 2026-06-21
**Signals detected**: external library not in dependencies (`radix-ui`); new tooling not in stack (Vitest, @testing-library/react, Playwright); architectural decision with multiple valid approaches (headless-library selection — spec §8 Q-1).

> Alternatives were already compared in the discovery report (`discover/2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.md`, §Prior Art + §Build vs Buy). This file seeds from that comparison rather than relitigating it; the verdict column is confirmed by the architect at Phase 1.3.

## Questions Investigated

1. What is Radix's current package + React 19 status? → As of mid-2026 Radix ships a unified `radix-ui` package (`import { Dialog, DropdownMenu, Popover, Toast } from "radix-ui"`) with official React 19 support; Dialog/DropdownMenu/Popover/Toast are stable (only complex Combobox/multiselect lagged — not needed here). Confirmed via Context7 (`/websites/radix-ui_primitives`).
2. Can Radix be styled with project semantic classes bound to design tokens? → Yes. Primitives are fully unstyled; each part takes a `className`, and functional styles (e.g. overlay covering the viewport) are the consumer's responsibility. Semantic classes bound to `src/renderer/styles/tokens.css` CSS custom properties satisfy the spec's no-inline-styles constraint directly.
3. How should the imperative Toast API compose with Radix Toast? → Radix Toast is a render/a11y primitive (`Toast.Provider` / `Toast.Root` / `Toast.Viewport`); the documented imperative pattern uses a ref. The spec's zustand `toastStore` owns the queue + `toast(message, opts)` API and drives Radix `Toast.Root` rendering — store owns state (constitution §4), Radix owns a11y/animation.
4. What test stack fits Electron-renderer React 19 with no prior infra? → Vitest + @testing-library/react + user-event on jsdom for interaction tests; Playwright component tests for real-browser focus/keyboard fidelity (jsdom does not faithfully model focus). Matches constitution §3.4's "Vitest + Testing Library" steer.

## Alternatives Compared

### Headless overlay library (Dropdown/Modal/Toast behavior + a11y)

| Option                                        | Pros                                                                                                      | Cons                                                                                          | Verdict                  |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------ |
| Radix UI (`radix-ui`)                         | Mature Dialog/DropdownMenu/Popover/Toast; official React 19; unstyled + className styling; heavy prod use | WorkOS-acquired (velocity slowed for complex combobox/multiselect — not needed); runtime dep  | Chosen                   |
| React Aria Components                         | Deepest a11y (ARIA APG)                                                                                   | More code per component; heavier API for an app-internal layer                                | Rejected                 |
| Base UI (MUI)                                 | Actively maintained, modern                                                                               | Newer, smaller battle-test surface                                                            | Rejected                 |
| Ark UI                                        | Cross-framework, XState machines                                                                          | Heavier abstraction than a React-only internal layer needs                                    | Rejected                 |
| Headless UI                                   | Simplest API                                                                                              | Tailwind-oriented; no Toast primitive                                                         | Rejected                 |
| Hand-rolled (Floating UI + native `<dialog>`) | Minimal deps, full ownership                                                                              | Re-incurs the exact a11y/edge-case bug class the feature exists to avoid; largest test burden | Rejected (fallback only) |

**Decision**: Radix UI (`radix-ui` unified package) — best correctness-per-line for the bug-prone overlay/focus/keyboard behavior the dep policy permits; Icon, styling, and the Toast queue stay project-owned (Hybrid build-vs-buy).

### Renderer test stack

| Option                            | Pros                                         | Cons                               | Verdict                   |
| --------------------------------- | -------------------------------------------- | ---------------------------------- | ------------------------- |
| Vitest + RTL + user-event (jsdom) | Fast, Vite-native, matches constitution §3.4 | jsdom focus/keyboard fidelity gaps | Chosen (unit/interaction) |
| + Playwright component tests      | Real-browser focus/keyboard fidelity         | Heavier setup                      | Chosen (fidelity layer)   |
| happy-dom instead of jsdom        | Faster DOM                                   | Less complete focus/range API      | Rejected                  |

**Decision**: Vitest + @testing-library/react + user-event (jsdom) for interaction tests, plus Playwright component tests for focus/keyboard fidelity.

## References

- Context7: `/websites/radix-ui_primitives` — getting-started, styling guide, Toast component docs (unified `radix-ui` package, className styling, imperative Toast pattern).
- Discovery report: `discover/2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.md` (§Prior Art, §Build vs Buy, §Derisk Plan).
- Spec: `specs/001-ui-primitives/spec.md` (§7 Constraints, §8 Q-1).
