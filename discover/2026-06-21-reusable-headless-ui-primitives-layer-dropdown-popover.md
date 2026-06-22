# Discovery: Reusable headless UI primitives layer (Dropdown/popover, Modal, Toast) plus a project-owned inline SVG Icon component for an Electron+React desktop app; styled via design tokens, build-vs-buy evaluated against headless libraries

**Date**: 2026-06-21
**Topic**: Reusable headless UI primitives layer (Dropdown/popover, Modal, Toast) plus a project-owned inline SVG Icon component for an Electron+React desktop app; styled via design tokens, build-vs-buy evaluated against headless libraries
**Verdict**: Worth pursuing

## Summary

A presentation-only UI primitives layer for the Electron+React renderer: Dropdown/popover, Modal, and Toast overlays plus a project-owned inline SVG Icon, styled exclusively via semantic class names bound to the existing design tokens. The codebase is greenfield for these (renderer is electron-vite boilerplate) and fits well — React 19, a configured @renderer alias, and design tokens already compiled to CSS custom properties (src/renderer/styles/tokens.css) mean styling needs no new infrastructure. Prior-art survey shows the overlay/focus/keyboard behavior the user flagged as bug-prone is exactly what mature headless libraries (Radix, React Aria, Base UI) solve, with Floating UI as the low-level positioning substrate and a native <dialog>+Popover-API path viable given Electron's single Chromium. Recommended direction is HYBRID: buy the overlay behavior/a11y (Radix primitives, restyled via token CSS vars) and build the Icon + Toast queue + styling project-owned. Primary risk: no test framework exists yet, so the automated-interaction-test success criterion requires a constitution-mandated Vitest+Testing-Library setup before the first primitive lands.

## Prior Art

| Reference                                                    | Kind    | Relevance                                                                                                                                                                                                                                                                         | Source                                                       |
| ------------------------------------------------------------ | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Radix UI Primitives                                          | library | Mature unstyled Dialog/DropdownMenu/Popover/Toast with full a11y, keyboard, focus mgmt, RTL; official React 19 support. WorkOS-acquired — velocity slowed for COMPLEX comps (combobox/multiselect, not needed here); Dialog/Dropdown/Popover stable. Heavy prod usage via shadcn. | https://www.radix-ui.com/primitives                          |
| React Aria Components (Adobe)                                | library | Deepest a11y primitives available (ARIA APG-compliant), Modal/Popover/Menu/Toast; more code per component, unstyled. Strongest correctness bar.                                                                                                                                   | https://react-spectrum.adobe.com/react-aria/                 |
| Base UI (MUI team)                                           | library | Emerging primitive layer, now the more actively-maintained Radix alternative; Dialog/Popover/Menu unstyled. Newer = smaller battle-test surface.                                                                                                                                  | https://base-ui.com/                                         |
| Ark UI (Zag.js state machines)                               | library | Cross-framework headless primitives backed by XState machines; predictable complex-component behavior. Heavier abstraction than needed for app-internal React-only layer.                                                                                                         | https://ark-ui.com/                                          |
| Headless UI (Tailwind team)                                  | library | ~10 unstyled comps incl. Dialog/Menu/Popover; simplest API but Tailwind-oriented and no Toast. Smallest scope.                                                                                                                                                                    | https://headlessui.com/                                      |
| Floating UI (+ FloatingFocusManager)                         | library | Best low-level positioning (~3kB, edge-aware flip/shift, virtual elements) + modal/non-modal focus trapping. Used UNDER THE HOOD by Radix/Base UI. The realistic substrate for a hand-rolled overlay path.                                                                        | https://floating-ui.com/docs/react                           |
| Native Popover API + dialog element + CSS anchor positioning | pattern | Electron bundles a single known Chromium → no browser-matrix concern; <dialog> gives free focus trap + scrim + Escape, Popover API gives top-layer + light-dismiss. Anchor-positioning availability is Chromium-version-gated (derisk).                                           | https://developer.mozilla.org/en-US/docs/Web/API/Popover_API |
| shadcn/ui (copy-in over Radix)                               | pattern | Dominant consumption pattern: copy component source (built on Radix) into the repo, own + restyle it. Project-owned source with battle-tested behavior — directly relevant to a token-styled, project-owned layer.                                                                | https://ui.shadcn.com/                                       |

## Integration Surface

| Touchpoint                             | Module/file                    | Why touched                                                                                                                           |
| -------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Primitives directory (atoms/molecules) | src/renderer/src/components/   | greenfield — new atoms/ (Icon) + molecules/ (Dropdown/Modal/Toast) subdirs; grounded by existing components/Versions.tsx              |
| Shared overlay substrate (lib)         | src/renderer/src/              | new lib/ subdir for Portal + focus-trap/click-outside/positioning hooks; grounded by App.tsx/main.tsx prefix                          |
| Design-token stylesheet                | src/renderer/styles/tokens.css | design tokens ALREADY compiled to CSS custom properties here; semantic-class styling via these CSS vars is the established wiring     |
| Test tooling                           | (unverified)                   | unverified path — NO test framework in package.json; automated interaction tests (success_criteria) require adding a runner + RTL/dom |
| Renderer import alias                  | electron.vite.config.ts        | @renderer -> src/renderer/src alias already configured; primitives import surface ready                                               |

## Fit Assessment

| Touchpoint                             | User expected                                                         | Reality (scan)                                                                                                                                  | Effort | Blockers                                                                                                       |
| -------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Primitives directory (atoms/molecules) | atomic-design dirs (atoms/Icon, molecules/overlays) under components/ | greenfield: only components/Versions.tsx exists; clean to add atoms/ + molecules/                                                               | Low    | none                                                                                                           |
| Shared overlay substrate (lib)         | shared overlay/focus/keyboard hooks + positioning helper in lib/      | no lib/ dir yet; clean greenfield add                                                                                                           | Low    | none                                                                                                           |
| Design-token stylesheet                | style via design/tokens.json semantic class names, no inline styles   | tokens already emitted as CSS custom properties in src/renderer/styles/tokens.css — semantic-class approach is the existing pattern; strong fit | Low    | none                                                                                                           |
| Test tooling                           | automated keyboard/focus/dismiss interaction tests gate the feature   | no test runner or component-testing library installed at all                                                                                    | Medium | no test framework — must add vitest + @testing-library/react + jsdom/happy-dom (or Playwright component tests) |
| Renderer import alias                  | primitives importable as a reusable internal layer                    | @renderer alias configured in electron.vite.config.ts                                                                                           | Low    | none                                                                                                           |

**Overall fit**: Good
**Effort estimate**: Medium
**Rationale**: Strong structural fit: greenfield renderer with React 19 + TS + a configured @renderer alias, and design tokens already compiled to CSS custom properties (src/renderer/styles/tokens.css) — exactly the semantic-class styling channel the spec wants, so styling needs no new infrastructure. The atomic-design dirs (atoms/molecules/lib) are clean additions. The one non-trivial gap is test tooling: the automated-interaction-test success criterion has no runner/library installed, so a vitest + @testing-library setup task is required (Medium effort). Both user mechanism guesses hold up: headless-lib-preferred is reasonable (Radix/Base UI/React Aria all support React 19) BUT a native <dialog>+Popover-API+Floating-UI hybrid is a real contender given Electron's single Chromium; Icon-project-owned is sound since the icon set already exists and needs no dependency.

## Design Options

### Option A: Radix primitives + token-styled wrappers

- **Shape**:

```
Thin project-owned PascalCase components wrap Radix Dialog/DropdownMenu/Popover/Toast; behavior, ARIA, focus-trap/return, keyboard nav, and edge-aware positioning come from Radix (official React 19 support). Styling supplied only as semantic class names bound to the existing tokens.css CSS custom properties. Icon stays fully project-owned (typed name union over the ~40 SVG paths). Toast queue lives in a zustand store driving an imperative toast(msg,opts) API.
```

- **Pros**:
  - Least code; the exact a11y/edge-case bug class the user flagged is offloaded to a battle-tested lib
  - Radix Dialog/Dropdown/Popover are stable + React 19 supported; only complex combobox/multiselect lagged (not needed)
  - Styling stays project-owned via semantic classes; no inline styles, fits tokens.css wiring directly
- **Cons**:
  - Runtime dependency on Radix (acceptable per dep policy)
  - Must learn Radix data-attribute/state hooks to style states (open/closed, side)
  - Some bundle weight (minor for desktop Electron)
- **Complexity**: Low

### Option B: Hand-rolled on Floating UI + native dialog

- **Shape**:

```
Project-owned components with minimal deps: Modal built on native <dialog> (free focus trap, scrim, Escape, top-layer); Dropdown/popover positioned by Floating UI (flip/shift, ~3kB) with FloatingFocusManager; Toast via a zustand queue + Portal. Shared lib/ hooks (useClickOutside, useFocusReturn, useKeyboardNav) supply the rest. One small positioning dep.
```

- **Pros**:
  - Minimal dependency surface; full source ownership
  - Leverages the platform — single known Chromium makes <dialog>/Popover-API/top-layer reliable
  - Floating UI is version-agnostic and tiny
- **Cons**:
  - Re-incurs the exact a11y/edge-case risk the user called out: menu typeahead, roving tabindex, nested focus-trap composition, ARIA wiring
  - Largest test + maintenance burden
  - Toast stacking/hover-pause + nested-overlay Escape ordering are all hand-built
- **Complexity**: High

### Option C: shadcn-style copy-in over Radix

- **Shape**:

```
Copy Radix-based component source (shadcn-style) directly into components/, own and restyle it with token CSS vars rather than depending on a wrapper library. Behavior is Radix's, but the source lives in-repo with no release-cadence coupling. Icon + Toast store remain project-authored.
```

- **Pros**:
  - Project-owned source AND battle-tested behavior
  - Full styling control; no opaque wrapper layer
  - No runtime coupling to a wrapper lib release cadence
- **Cons**:
  - More component code to maintain in-repo
  - Must manually track upstream a11y/security fixes
  - Still carries the underlying Radix dependency
- **Complexity**: Med

**Recommended option**: Radix primitives + token-styled wrappers — Best matches the stated intent and constraints. The user explicitly framed overlay/focus/keyboard as the bug-prone area and the dep policy permits a well-maintained headless library — so offloading that behavior to Radix (stable Dialog/Dropdown/Popover/Toast, React 19 supported) buys the most correctness for the least code, while semantic-class styling against the existing tokens.css keeps presentation fully project-owned. Icon stays project-owned (no icon dependency) since the SVG set already exists. Tradeoffs acknowledged: a Radix runtime dep and learning its state/data-attribute styling hooks; if a zero-overlay-dependency rule ever emerges, fall back to 'Hand-rolled on Floating UI + native dialog', or choose 'shadcn-style copy-in over Radix' if in-repo source ownership outweighs the maintenance cost.

## Build vs Buy

| Build                                                                                                                                                                                                                                                                                                  | Buy/Adopt                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Build project-owned: the Icon component (typed name union over the ~40 hand-authored SVG paths, unknown-name fallback), all styling (semantic class names -> tokens.css CSS vars), the Toast queue (zustand store + imperative toast() API), and thin wrappers/composition around the bought behavior. | Adopt Radix Primitives for the overlay behavior/a11y of Dropdown/popover, Modal (Dialog), and Toast — focus trap/return, keyboard nav, ARIA roles, edge-aware positioning, light-dismiss — restyled via semantic classes. (Alternatives if Radix is rejected: React Aria for deepest a11y, or Floating UI for a hand-rolled positioning substrate.) |

**Recommendation**: Hybrid — Buy the behavior that is expensive and risky to get right (the overlay/focus/keyboard correctness the user flagged), build the parts that are cheap, project-specific, and dependency-free (Icon, styling, Toast queue). Pure build re-incurs the flagged bug class; pure buy would fight the token-styled, project-owned, no-inline-styles requirement. Hybrid satisfies both.

## Derisk Plan

1. Spike: render a Radix Dialog + DropdownMenu styled SOLELY via semantic classes bound to tokens.css CSS vars — confirm zero inline styles and a look matching the design reference
2. Stand up the renderer test stack (Vitest + @testing-library/react + user-event + jsdom/happy-dom) and write one keyboard/focus interaction test as a smoke proof; record the stack in docs/architecture.md per constitution 3.4
3. Verify Radix Toast covers stacking + hover/focus pause + rapid-fire queue; if not, scope the small project-owned zustand toast queue instead
4. Prototype nested-overlay behavior (modal opens a dropdown; toast over modal) to confirm Escape closes topmost-only and focus-trap/return compose correctly
5. Author the Icon contract: derive the typed name union from the ~40 SVG paths, define size/stroke props and the unknown-name fallback, confirm prefers-reduced-motion handling

## Constitution Constraints

| Rule                                                                                       | Impact                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| §3.4 Testing Requirements                                                                  | No test infrastructure exists; the rule mandates picking a renderer test stack (Vitest + Testing Library) before the first feature needing coverage and recording it in docs/architecture.md. This feature IS that first feature — its automated-interaction-test success criterion makes the test-stack setup a required, gating prerequisite, not optional. |
| §3.1 Type Safety                                                                           | Strict mode, no 'any'. The Icon 'name' prop must be a typed string-literal union over the ~40-icon set (not a bare string); all primitive props strictly typed; any external/parsed value typed as 'unknown' and narrowed. Enables a compile-time guard against unknown icon names.                                                                           |
| §2.3 Module Organization & Imports                                                         | Primitives live under src/renderer/src and are imported via the @renderer alias, not deep relative paths; code stays in the renderer process dir with no cross-process import. Reinforces the presentation-only / renderer-only boundary (no IPC, no main/preload involvement).                                                                               |
| §4 Always (project): shared renderer state in zustand + Never mutate outside store actions | The imperative Toast queue should be a zustand store (toastStore) with actions, not an ad-hoc context/global — the project already depends on zustand 5. Toast enqueue/dismiss/pause go through store actions.                                                                                                                                                |
| §3.3 Naming Conventions                                                                    | Component files PascalCase (Dropdown.tsx, Modal.tsx, Toast.tsx, Icon.tsx); hooks camelCase with use- prefix (useFocusTrap, useClickOutside); the toast store is toastStore.                                                                                                                                                                                   |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied mechanism guess (confirm via Phase 2 fit-check): keep Icon project-owned rather than pulling an icon dependency (icon set already exists as hand-authored SVG paths)]

## Recommendation

**Action**: Proceed to /specify for the primitives layer, scoped to the Hybrid recommended option: Radix-backed overlays restyled via token CSS vars + a project-owned Icon and zustand Toast queue. Make the Vitest+Testing-Library test-stack setup the first task (constitution 3.4).
**Next**: Run /specify to author the feature spec with EARS acceptance criteria for each primitive's behavior + a11y.

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

```
/specify "Reusable presentation-only renderer primitives — Dropdown/popover, Modal, Toast (Radix-backed, token-styled) + a project-owned SVG Icon — for app-internal use, verified by keyboard/focus interaction tests."

Discovery reference: discover/2026-06-21-reusable-headless-ui-primitives-layer-dropdown-popover.md
Key facts:
- Functional scope: A reusable presentation-only primitives layer for the Electron+React renderer, delivering four user-facing components plus their shared overlay substrate. Components: (1) Dropdown/popover anchored to a trigger — keyboard navigation, focus return, click-outside + Escape dismiss, edge-aware positioning; (2) Modal dialog — focus trap, scrim/backdrop, Escape close, body scroll lock; (3) transient Toast — stacked, auto + manual dismiss, hover-pause; (4) inline SVG Icon driven by a project-owned ~40-icon set (1.5px stroke, 16x16 viewBox). First-class shared substrate (in lib/): a Portal, a focus-trap/focus-return hook, a click-outside hook, centralized Escape/keyboard handling, and an edge-aware positioning helper — reusable by future primitives. An explicit build-vs-buy evaluation (headless libs Radix/React Aria/Ark/Headless UI vs hand-rolled) governs the overlay substrate. Styling via semantic class names mapped to design/tokens.json; visual/behavior reference is the design export, never its markup.
- Users: App-internal only. Direct consumers are mintEnvoy renderer feature components (and the developers wiring them) — these primitives are an internal building-block layer, not a published package. End-users of the desktop app interact with the rendered overlays (dropdown menus, modals, toasts) and icons. No external-consumer API-stability concern.
- Success criteria: All four primitives (Dropdown/popover, Modal, Toast, Icon) render per the visual reference look and behave correctly: keyboard nav, focus trap + focus return, click-outside + Escape dismiss, edge-aware positioning, scrim, toast auto-dismiss — meeting WCAG keyboard/focus expectations. Gated by automated interaction tests (keyboard/focus/dismiss). A demo/gallery harness exercises every primitive in its states as the visual + manual-QA surface.
- Recommended option: Radix primitives + token-styled wrappers
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
```
