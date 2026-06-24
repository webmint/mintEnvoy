# Discovery: Single-window shell and layout for a desktop HTTP client: titlebar (logo, workspace pill, sidebar toggle, command-palette search trigger, environment selector, account pill), left sidebar with draggable divider (width clamped 200-520px), main area split into request/response panes by draggable horizontal divider (ratio clamped 0.15-0.85), and statusbar. Theme (light/dark), accent, method-style toggles as data attributes on root; persistence of sidebar width/pane ratio/theme via settings store. Mounting points for sidebar, tabs, panes, modals (contents are separate tasks). Cmd-B toggles sidebar. Visual reference design/reference.html for look/behavior only; rebuild with semantic class names; colors/spacing from design/tokens.json.

**Date**: 2026-06-23
**Topic**: Single-window shell and layout for a desktop HTTP client: titlebar (logo, workspace pill, sidebar toggle, command-palette search trigger, environment selector, account pill), left sidebar with draggable divider (width clamped 200-520px), main area split into request/response panes by draggable horizontal divider (ratio clamped 0.15-0.85), and statusbar. Theme (light/dark), accent, method-style toggles as data attributes on root; persistence of sidebar width/pane ratio/theme via settings store. Mounting points for sidebar, tabs, panes, modals (contents are separate tasks). Cmd-B toggles sidebar. Visual reference design/reference.html for look/behavior only; rebuild with semantic class names; colors/spacing from design/tokens.json.
**Verdict**: Promising with caveats

## Summary

A single-window app shell + layout for the mintEnvoy desktop HTTP client: titlebar, a resizable left sidebar (200-520px), a request/response split with a horizontal divider (ratio 0.15-0.85), and a statusbar — with named mount slots whose CONTENTS are separate tasks. The shell sets theme/accent/method-style as root data-attributes and holds sidebar width + pane ratio + view prefs in a net-new in-memory zustand settingsStore (mirroring the existing toastStore). Internal scan found the visual contract already done — tokens.css implements [data-theme] dark overrides + 6 [data-mstyle] method variants on <html> — so the shell EXTENDS that contract by setting attributes rather than defining palettes. Fit is Good with no refactor; the one open design decision is the resizable dividers (hand-roll vs react-resizable-panels vs allotment), where both libraries owning layout state internally conflicts with the requirement that the settings store be the single source of truth. Primary risk: a data-accent attribute is visually inert today (no [data-accent] CSS), so accent is persisted but drives no visuals this task.

## Prior Art

| Reference                                         | Kind    | Relevance                                                                                                                                                                                                                                                                                                                                                                                   | Source                                                |
| ------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| tokens.css (theme + method-style CSS contract)    | pattern | internal — EXISTING implementation of theme + method-style application: :root light + [data-theme='dark'] overrides + 6 [data-mstyle] method variants. Header states data-theme + data-mstyle live on <html>. Shell EXTENDS by setting attributes; CSS already done. NOTE attr is data-mstyle not data-method-style; NO data-accent block exists.                                           | internal:src/renderer/styles/tokens.css               |
| toastStore.ts (zustand store pattern)             | pattern | internal — existing zustand store the new settingsStore mirrors (create() + selector hooks + reset for tests). No settings store exists yet; settingsStore is net-new but follows this shape.                                                                                                                                                                                               | internal:src/renderer/src/lib/toastStore.ts           |
| react-resizable-panels (bvaughn)                  | library | Most battle-tested React split lib (shadcn/ui Resizable wraps it). Flexbox PERCENTAGE model + accessible WAI-ARIA separator + onLayoutChanging/onLayoutChanged batching. Tension: % model awkward for the px sidebar clamp (200-520px), and the lib owns layout state internally — duplicates the requirement that the zustand settings store own width/ratio (controlled mode needs glue). | https://github.com/bvaughn/react-resizable-panels     |
| allotment (johnwalley)                            | library | VS Code-derived split-view; supports px min/max sizes natively (better for the 200-520px sidebar clamp than %), IDE snap UX. Heavier/opinionated; also owns layout state internally (same single-source-of-truth tension with settings store).                                                                                                                                              | https://github.com/johnwalley/allotment               |
| shadcn/ui Resizable                               | product | Reference for idiomatic API shape over react-resizable-panels; copy-paste component pattern, not a dep — confirms react-resizable-panels is the mainstream React choice.                                                                                                                                                                                                                    | https://ui.shadcn.com/docs/components/radix/resizable |
| Hand-rolled pointer-event divider (rAF + CSS var) | pattern | Zero-dep pattern: useRef + pointer events writing a CSS custom property (no setState-per-move), clamp px/ratio exactly in JS, ARIA separator role + aria-valuenow by hand. Cheap for a fixed 2-divider layout; keeps the zustand settings store the single source of truth (no lib-owned layout state).                                                                                     |                                                       |

## Integration Surface

| Touchpoint                             | Module/file                        | Why touched                                                                                                                                                               |
| -------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| tokens.css theme/method-style contract | src/renderer/styles/tokens.css     | existing CSS contract for [data-theme] + [data-mstyle] on <html> — shell sets these attributes; candidate for reuse over fresh build. accent NOT attribute-switched here. |
| toastStore zustand pattern             | src/renderer/src/lib/toastStore.ts | existing zustand store shape — new settingsStore mirrors it; candidate for reuse over fresh build                                                                         |
| App.tsx mount root                     | src/renderer/src/App.tsx           | current renderer mount (renders PrimitivesDemo) — shell organism mounts here, attribute-set on <html> root                                                                |

## Fit Assessment

| Touchpoint                             | User expected                                                                                    | Reality (scan)                                                                                                                                                                                                                                                                                                                                                                                                     | Effort | Blockers                                                                                                                                                                                   |
| -------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| toastStore zustand pattern             | Persist sidebar width / pane ratio / theme via the EXISTING settings store                       | No settings store exists. CBM scan shows only toastStore.ts; electron-store appears solely in config/docs, not src. settingsStore is net-new, mirroring toastStore's zustand shape; persistence is in-memory this task.                                                                                                                                                                                            | Low    | user belief of an existing settings store is incorrect — store must be created net-new; disk persistence (electron-store/IPC) does not exist and is deferred                               |
| tokens.css theme/method-style contract | Set theme + accent + method-style as data attributes on root; all three drive visuals via tokens | tokens.css already implements [data-theme='dark'] overrides and 6 [data-mstyle] method variants on <html> — theme + method-style fully wired (attr is data-mstyle, NOT data-method-style). BUT accent is a single --accent var with NO [data-accent] switch block: setting data-accent has zero CSS effect today, and defining accent palettes is a non_goal. So accent persistence is store-only/inert this task. | Low    | accent data-attribute is visually inert — no [data-accent] CSS exists; persist the value but expect no visual change; naming: use data-mstyle to match existing CSS, not data-method-style |
| App.tsx mount root                     | Shell mounts as the top-level renderer chrome                                                    | App.tsx currently renders PrimitivesDemo. Swap to the Shell organism is a small, contained edit; attributes set on <html> via effect from settingsStore.                                                                                                                                                                                                                                                           | Low    | none                                                                                                                                                                                       |

**Overall fit**: Good
**Effort estimate**: Medium
**Rationale**: Fit is Good: the shell drops cleanly into the existing renderer as a net-new components/organisms/ tier plus a net-new settingsStore.ts that mirrors the existing toastStore zustand pattern, and it consumes an ALREADY-COMPLETE CSS contract (tokens.css implements [data-theme] dark overrides + 6 [data-mstyle] method variants on <html>). No existing code is refactored — App.tsx swaps PrimitivesDemo for the Shell. Two belief-vs-reality corrections, both minor: (1) there is no existing settings store to persist 'via' — it is created net-new and in-memory this task (disk/electron-store deferred); (2) accent is not attribute-switched in tokens.css, so a data-accent attribute is visually inert today and defining accent palettes is out of scope — the store persists the choice but it drives no CSS this task. Effort is Medium: integration is Low, but the resizable dividers (px + ratio clamp, smooth drag without re-render storms, ARIA separators, drag-release-outside-window) plus the slot API are the real build cost, and the divider build-vs-buy (hand-roll vs react-resizable-panels vs allotment) is the one open design decision — complicated by both libs owning layout state internally, which conflicts with the requirement that the settings store be the single source of truth for width/ratio.

## Design Options

### Option A: Single settings store + CSS-var layout, hand-rolled dividers

- **Shape**:

```
One zustand settingsStore is the single source of truth: { theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed } + actions. The Shell organism writes sidebarWidth/paneRatio to CSS custom properties on its own root and sets data-theme/data-accent/data-mstyle on <html> via effect. Dividers are hand-rolled pointer-event components that clamp px/ratio in JS and write to a CSS var during drag (rAF-batched, store committed on release). Slots are named React children/context mount points.
```

- **Pros**:
  - Settings store is the single source of truth — no lib-owned layout state to sync (satisfies the stated requirement)
  - Exact px (200-520) + ratio (0.15-0.85) clamp control; full ARIA-separator + keyboard control
  - Zero new dependency (constraint: prefer zero-dep hand-roll if cheap)
  - Mirrors existing toastStore + extends existing tokens.css contract directly
- **Cons**:
  - Must hand-write ARIA separator + keyboard resize + drag-release-outside-window handling (the lib gives these free)
  - More component code to test than adopting a lib
- **Complexity**: Med

### Option B: Library-backed panels + thin settings store

- **Shape**:

```
Adopt react-resizable-panels (or allotment) for the split/resize surfaces. settingsStore holds only { theme, accent, mstyle } plus the library's serialized layout string; the library owns sidebar/pane sizing internally and is driven controlled-mode from the store. Dividers/ARIA come from the library.
```

- **Pros**:
  - Accessible WAI-ARIA separators + keyboard + edge-case drag handling come built-in and battle-tested
  - Less custom layout/drag code to write and maintain
- **Cons**:
  - Two layout-state owners (library internal + settings store) need sync glue — violates the single-source-of-truth requirement
  - react-resizable-panels % model is awkward for the px sidebar clamp (allotment fits px better but is heavier/opinionated)
  - New dependency must be vetted (constraint) and adds bundle weight to an Electron renderer
- **Complexity**: Med

### Option C: Slot-registry layout reducer

- **Shape**:

```
A layout context exposes a register/unregister slot API (a registry of named mount points) backed by a reducer, instead of fixed named-children slots; settings still in the zustand store. Future panes/tabs/modals attach dynamically by id.
```

- **Pros**:
  - Most extensible slot API for future dynamic panes/tabs
  - Decouples shell from knowing its slot set at build time
- **Cons**:
  - Over-engineered for the current fixed slot set (sidebar/tabs/panes/modals) — adds a registry abstraction with no current consumer needing it
  - More indirection to test; risks YAGNI against the minimal scope
- **Complexity**: High

**Recommended option**: Single settings store + CSS-var layout, hand-rolled dividers — Best fit to the stated constraints. The requirement that the settings store own sidebar width + pane ratio makes a library-owned layout state (react-resizable-panels / allotment) a net liability — both would need controlled-mode sync glue and duplicate the source of truth. This option EXTENDS existing internal:src/renderer/src/lib/toastStore.ts (the zustand pattern settingsStore mirrors) and EXTENDS the already-complete CSS contract in internal:src/renderer/styles/tokens.css (which the existing implementation covers for [data-theme] + [data-mstyle] but does NOT cover for accent — no [data-accent] block exists, so this option persists accent in the store while accepting it is visually inert until accent palettes are added in a later task). The hand-roll cost (ARIA separator, keyboard resize, drag-release-outside-window) is bounded for a fixed 2-divider layout and is the price of exact px/ratio clamp control + zero new dependency. Acknowledged tradeoff: more divider/a11y code to write and test than option B; mitigated by the derisk spike below, with react-resizable-panels documented as the fallback if the hand-rolled a11y proves costly.

## Build vs Buy

| Build                                                                                                                                                                                                                                         | Buy/Adopt                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hand-roll the shell: net-new components/organisms/ Shell + Sidebar/PaneSplit/Titlebar/Statusbar, net-new settingsStore.ts (mirrors toastStore), dividers as pointer-event components writing CSS vars. Consumes existing tokens.css contract. | Adopt react-resizable-panels (mainstream React choice, wrapped by shadcn/ui Resizable) or allotment (VS Code-derived, native px sizing) for the resize surfaces only; still build the titlebar/statusbar/store by hand. |

**Recommendation**: Build — Build (hand-roll dividers). The constraint set explicitly prefers a zero-dep hand-roll when cheap, and the single-source-of-truth requirement (settings store owns width/ratio) actively penalizes the library path, which keeps its own layout state. The shell is a fixed 2-divider layout — bounded enough that hand-rolling the clamp + drag + ARIA is cheaper end-to-end than adopting, vetting, and sync-gluing a controlled-mode panel library. react-resizable-panels stays the documented fallback if the hand-rolled accessibility/edge-cases prove more expensive than the derisk spike predicts.

## Derisk Plan

1. Spike a hand-rolled divider (pointer events + rAF + CSS custom property) and measure drag smoothness vs a setState-per-move baseline before committing
2. Prototype the clamp/resize math against the window-resize edge case (sidebar 200-520px + pane ratio 0.15-0.85 re-clamp on shrink) to confirm no negative/overflow panes
3. Run an axe + keyboard/screen-reader pass on the divider (ARIA separator role, aria-valuenow, keyboard resize) to validate accessibility before the lib-vs-handroll decision is locked
4. Mount one real consumer (e.g. the existing Tabs molecule) into the tab slot to prove the slot API is genuinely content-decoupled
5. Confirm the accent reality with the user/spec: persist the value but mark data-accent visually inert until a later accent-palette task (or pull accent into scope explicitly)

## Constitution Constraints

| Rule                                           | Impact                                                                                                                                                                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| §3.1 Type Safety                               | No 'any'; type IPC/external input as 'unknown' and narrow. The settingsStore state + slot props must be fully typed; any future disk-load values (deferred) are validated at the boundary.                               |
| §3.3 Naming                                    | zustand store is camelCase + Store suffix -> settingsStore.ts (matches recommended option); React components PascalCase (Shell, Sidebar, PaneSplit, Titlebar, Statusbar).                                                |
| §5 State Management                            | Shared renderer state lives in a zustand store; never mutate state outside store actions; prefer selectors over reading the whole store. Drag handlers commit width/ratio via store actions, not direct mutation.        |
| §2 Process boundaries (electron-store in main) | Persistence (electron-store) is a MAIN-process responsibility — confirms the renderer settingsStore stays in-memory this task; disk persistence later goes through a typed IPC wrapper, not the renderer store directly. |
| §6 Reuse-before-build                          | Search for existing utilities before building generic ones — honored: reuses toastStore zustand pattern + the existing tokens.css [data-theme]/[data-mstyle] contract rather than re-defining either.                    |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied placement guess (confirm via Phase 2 fit-check): persistence of sidebar width / pane ratio / theme via the existing settings store]

## Recommendation

**Action**: Run /specify for the app-shell + layout feature, locking: net-new components/organisms/ Shell tree + net-new in-memory settingsStore (mirror toastStore), hand-rolled clamped dividers (Build), consuming the existing tokens.css contract. Resolve the accent-inert caveat in the spec (persist value, data-accent visually inert this task) and treat the divider build-vs-buy as decided (Build, lib fallback documented).
**Next**: Author the spec with the derisk spikes as early acceptance-criteria checks.

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

```
/specify "Single-window app shell + layout: titlebar, resizable sidebar (200-520px) + request/response split (0.15-0.85), statusbar, named mount slots, root theme/method-style data-attrs, in-memory zustand settingsStore."

Discovery reference: discover/2026-06-23-single-window-shell-and-layout-for-a-desktop-http-client.md
Key facts:
- Functional scope: App-shell + layout component tree: titlebar (logo, workspace pill, sidebar toggle, command-palette trigger, environment selector, account pill), resizable left sidebar (clamped 200-520px) with draggable divider, main area split into request/response panes by a draggable horizontal divider (ratio clamped 0.15-0.85), statusbar. Theme(light/dark)/accent/method-style applied as root data-attributes. Cmd-B toggles sidebar. Empty named mount slots for sidebar/tabs/panes/modals (slot CONTENTS out of scope). A new zustand settings store (mirroring toastStore.ts) holds sidebar width + pane ratio + theme + accent + method-style IN-MEMORY only; disk persistence (electron-store wiring) deferred to a later persistence-port task. Styled from design/tokens.json with semantic class names per design/reference.html (markup never copied).
- Users: Co-primary consumers: (1) Human end users — developers/API testers operating the mintEnvoy desktop window; the shell is the top-level chrome they see every session (titlebar, sidebar, panes, statusbar). (2) Downstream feature tasks — code that mounts content into the shell's named slots (sidebar tree, tab bodies, request/response editors, modal bodies); for them the shell is an integration contract (a stable slot API), not just visuals.
- Success criteria: (1) Visual fidelity: rendered shell matches design/reference.html layout and design/tokens.json colors/spacing under design-auditor review (look/behavior only, never markup). (2) Behavior: both dividers drag and clamp to range (200-520px, 0.15-0.85); Cmd-B toggles sidebar; view settings (theme/accent/method-style) + sidebar width + pane ratio survive within the session via the settings store — all covered by component tests. (3) Decoupled slots: sidebar/tabs/panes/modals mount slots accept arbitrary children and render them without the shell knowing their contents. (4) Gates green: typecheck + lint + build + existing test suite pass; zero reference-export cruft (no data-om-*, __OmT, inline styles, tweaks-panel) anywhere in the build.
- Recommended option: Single settings store + CSS-var layout, hand-rolled dividers
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
```
