# Spec: tabs-primitive

**Date**: 2026-06-22
**Status**: Complete
**Author**: Claude + User

## 1. Overview

A reusable, controlled, horizontal-only tab-strip primitive (Tabs) for the mintEnvoy renderer that switches between panels within a pane. It renders a row of tab buttons (label + optional badge + active state) from a flat tabs array, marks the caller-supplied activeId, and emits onChange(id) on click or keyboard selection — selection only; it never renders or owns the panels it switches. It wraps the already-adopted radix-ui Tabs namespace behind a flat tabs-array + activeId + onChange API, extending the established molecules wrapper pattern (Dropdown/Modal/Toast) with no new dependency and no second accessibility library.

## 2. Current State

Greenfield for the Tabs primitive — no tab-strip exists in the renderer (codebase-memory search for 'Tabs' under src/renderer returns zero matches). Feature 001-ui-primitives established the layer Tabs extends: thin Radix wrappers live in src/renderer/src/components/molecules/ (Dropdown.tsx, Modal.tsx, Toast.tsx with co-located **tests**), the shared cx() className helper at src/renderer/src/lib/cx.ts:18, the Icon atom under src/renderer/src/components/atoms/, and the dev-only gallery src/renderer/src/components/PrimitivesDemo.tsx:32 (imports + registers each primitive). The canonical controlled items-array precedent is Dropdown: src/renderer/src/components/molecules/Dropdown.tsx:90 (DropdownItemDescriptor interface) and :204 (Dropdown function). radix-ui ^1.1.3 is already declared in package.json and exposes a Tabs namespace (Tabs.Root/List/Trigger) supplying controlled value/onValueChange, roving tabindex, List loop keyboard wrap, Trigger disabled-skip, activationMode, and full WAI-ARIA. Renderer test stack (per docs/architecture.md): Vitest + @testing-library/react + user-event (jsdom) for interaction tests, Playwright CT (@playwright/experimental-ct-react) for real-browser focus/keyboard; tests co-located under **tests**/ split .test.tsx / .ct.tsx. Styling is semantic class names bound to src/renderer/styles/tokens.css with a per-component sibling .css file — no inline styles. design/reference.html is the visual/behavior reference (look only).

## 3. Desired Behavior

Deliver a single Tabs primitive at src/renderer/src/components/molecules/Tabs.tsx with a sibling Tabs.css, registered in PrimitivesDemo for manual visual verification. The component renders a horizontal row of tab buttons from a flat tabs array of descriptors, each with an id, a label, an optional badge (string or number), and an optional disabled flag. It is controlled-only: the caller supplies activeId and an onChange(id) handler, and owns the active state — there is no uncontrolled/defaultActiveId mode. Clicking an enabled tab, or selecting it via keyboard, fires onChange(id) once with that tab's id. Keyboard navigation uses automatic activation: ArrowLeft/ArrowRight (and Home/End) move selection immediately across enabled tabs with wrap-around, skipping disabled tabs. The strip exposes WAI-ARIA tablist/tab semantics with aria-selected reflecting activeId and roving tabindex on the tab row. When activeId matches no tab id, the tabs array is empty, or every tab is disabled, the strip renders with no active selection and auto-picks nothing. An optional right-aligned actions slot renders caller-supplied content at the end of the strip. The component is renderer-only (pure React + radix-ui + cx, no Node/electron imports), styled exclusively via semantic class names bound to tokens.css with no inline styles, and animations respect prefers-reduced-motion. Behavior, keyboard navigation, and ARIA semantics are gated by interaction tests; visual fidelity to design/reference.html is verified manually via the PrimitivesDemo route.

## 4. Affected Areas

| Area                     | Files                                                                                                                      | Impact                                                                                                                |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| molecules primitives dir | src/renderer/src/components/molecules                                                                                      | home of Dropdown/Modal/Toast; new Tabs.tsx + Tabs.css land here following the same wrapper pattern                    |
| cx helper                | src/renderer/src/lib/cx.ts                                                                                                 | semantic-class composer Tabs reuses for BEM class assembly                                                            |
| Icon atom                | src/renderer/src/components/atoms/Icon.tsx                                                                                 | reused if a per-tab leading icon is ever added; consistent with Dropdown item icons                                   |
| PrimitivesDemo route     | src/renderer/src/components/PrimitivesDemo.tsx                                                                             | Tabs registered here for manual visual fidelity check vs design/reference.html                                        |
| radix-ui dependency      | package.json                                                                                                               | radix-ui ^1.1.3 already declared; Tabs namespace available with no new dependency                                     |
| Tabs interaction tests   | src/renderer/src/components/molecules/**tests**/Tabs.test.tsx, src/renderer/src/components/molecules/**tests**/Tabs.ct.tsx | Create new — Vitest + Testing Library interaction tests and Playwright CT keyboard/focus tests for the Tabs primitive |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide a Tabs primitive component module under the molecules component directory.
  > Verification: test -f src/renderer/src/components/molecules/Tabs.tsx
- [x] **AC-2**: The Tabs primitive shall ship a sibling token-bound stylesheet alongside the component.
  > Verification: test -f src/renderer/src/components/molecules/Tabs.css
- [x] **AC-3**: The build shall reuse the existing radix-ui dependency without introducing a second accessibility library.
  > Verification: grep -q '"radix-ui"' package.json
- [x] **AC-4**: The Tabs primitive shall be registered in the dev-only PrimitivesDemo route.
  > Verification: grep -q Tabs src/renderer/src/components/PrimitivesDemo.tsx

### 5.2 Behavior preservation

N/A — Greenfield primitive — no existing Tabs behavior to preserve; the renderer has no prior tab-strip.

### 5.3 Behavior change

- [x] **AC-5**: WHEN the user clicks an enabled tab, the Tabs primitive shall invoke onChange exactly once with that tab's id.
- [x] **AC-6**: WHEN a tab has focus and the user presses ArrowLeft, ArrowRight, Home, or End, the Tabs primitive shall move the active selection to the adjacent enabled tab with wrap-around at the ends, skip disabled tabs, and invoke onChange with the selected tab's id.
- [x] **AC-7**: WHILE the activeId equals a tab's id, the Tabs primitive shall mark that tab with aria-selected and expose WAI-ARIA tablist and tab roles with roving tabindex on the tab row.
- [x] **AC-8**: WHEN an optional actions slot is supplied, the Tabs primitive shall render it right-aligned at the end of the tab strip.
- [x] **AC-9**: IF the user activates a disabled tab by click or keyboard, THEN the Tabs primitive shall leave the selection unchanged and shall not invoke onChange.
- [x] **AC-10**: IF the activeId does not match any enabled tab in the array, THEN the Tabs primitive shall render no active selection and select nothing automatically.

### 5.4 CI / pipeline

N/A — No CI pipeline changes in scope; tests run via existing npm scripts, not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates introduced by this feature.

### 5.6 Documentation

- [x] **AC-11**: The exported Tabs component and its public tab-descriptor and props types shall carry documentation comments.

### 5.7 Hygiene

- [x] **AC-12**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-13**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-14**: The Tabs primitive source shall contain no inline style attributes.
  > Verification: ! grep -rEn 'style=[{][{]' src/renderer/src/components/molecules/Tabs.tsx | grep -vqE ':[[:space:]]\*(\*|//|/\*)'
  > (the trailing filter drops JSDoc/comment lines that merely document the rule, so the check matches only real JSX inline-style attributes)
- [x] **AC-15**: The Tabs primitive source shall not import the electron or node modules directly.
  > Verification: ! grep -rEn "from '(electron|node:)" src/renderer/src/components/molecules/Tabs.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: The panels / panel content the strip switches — Tabs is selection-only and never renders or owns panels.
- NOT included: Wiring Tabs into the request authoring pane and response pane — those panes do not exist yet; Tabs ships decoupled with only PrimitivesDemo as its consumer.
- NOT included: An uncontrolled / defaultActiveId self-managed state mode — Tabs is controlled-only (caller owns activeId).
- NOT included: Manual keyboard activation mode — automatic activation only (arrow keys move selection immediately).
- NOT included: Vertical tab orientation — horizontal-only primitive.
- NOT included: ReactNode badges or a render-slot actions option (discovery option C) — badge stays string|number. — F-2026-06-22-reusable-horizontal-tab-strip-primitive-for-switching-11
- NOT included: Tab-row overflow handling (scroll / wrap / truncate for too-many-tabs) — deferred (see Open Questions).
- NOT included: Selected-tab routing, URL sync, or persistence.
- NOT included: An animated selected-tab indicator or sliding-underline transition — static selected styling only.
- NOT included: Reproducing design/reference.html markup or its generated cruft (data-om-\*, \_\_OmT wrappers, inline styles, tweaks-panel).
- NOT included: Repo-wide reformatting or unrelated housekeeping commits on this feature branch (pollutes the verify hygiene scope). — F-memory-2

## 7. Technical Constraints

- Must follow: Controlled-only: the caller owns activeId and updates it via onChange; the strip holds no internal active state (matches the 001 Dropdown/Modal controlled pattern).
- Must follow: Style exclusively via semantic class names bound to tokens.css; no inline styles; animations gated behind prefers-reduced-motion; never reproduce design/reference.html markup.
- Must follow: Implement the WAI-ARIA Tabs pattern — tablist/tab roles, aria-selected, roving tabindex, and Arrow/Home/End keyboard navigation.
- Must follow: Commits follow Conventional Commits; WIP commits squash into one clean feature commit at /finalize (constitution §6.6).
- Must follow constitution §3.1: Type Safety — strict on, no any; type external input as unknown and narrow with a guard. The Tabs/Tab descriptor, props, and onChange are fully typed and exported.
- Must follow constitution §2.1: Process Boundaries — Tabs is renderer-only; never import Node or electron in renderer code.
- Must follow constitution §2.3: Module Organization & Imports — resolve renderer modules through the @renderer alias, not deep relative paths.
- Must follow constitution §3.4: Testing Requirements — gate behavior/keyboard/ARIA with Vitest + Testing Library interaction tests and Playwright CT, following the existing molecules **tests** patterns.
- Must follow constitution §6.3: Search Before Building — reuse radix-ui, cx(), the Icon atom, and the molecules wrapper pattern; introduce no second accessibility library.

## 8. Open Questions

- **hq-1**: RESOLVED (Phase 3 codebase analysis): the headless library to reuse is radix-ui — feature 001-ui-primitives adopted radix-ui ^1.1.3, and its Tabs namespace is reused here with no second accessibility library.
- **DP-ui_ux_details-2** [deferred to open question]: Tab-row overflow handling when tab count exceeds available pane width (Tab-row overflow is a pure visual detail driven by design/reference.html and verified manually via PrimitivesDemo; exact mechanism deferred to /plan)
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk                                                                                                                                                                                                           | Likelihood | Impact | Mitigation                                     |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ---------------------------------------------- |
| Spike: render Radix Tabs.Root+List+Trigger as a selection-only strip WITHOUT Tabs.Content; run axe/a11y to check for dangling aria-controls and decide share-one-Root vs hand-rolled tablist                   | Med        | Med    | address before implementation; see derisk plan |
| Contract test against both panes tab sets: click + arrows/Home/End wrap (List loop), disabled-skip, onChange(id) fires once, aria-selected/tablist roles correct, invalid/absent activeId renders no selection | Med        | Med    | address before implementation; see derisk plan |
| Register in PrimitivesDemo.tsx and visually compare to design/reference.html at the request-pane (six-tab) and response-pane (four-tab) widths                                                                 | Med        | Med    | address before implementation; see derisk plan |
| Radix Tabs couples Trigger->Content via aria-controls; a standalone selection-only strip risks dangling aria-controls unless panels join the same Tabs.Root or the tablist is hand-rolled                      | High       | High   | must resolve before implementation             |

## 10. Contract Lineage

### Extension: feature 004-working-tabs-state-machine (2026-06-25)

Feature `004-working-tabs-state-machine` extended this primitive with two opt-in, **default-off** props:

| Prop | Type | Default | Description |
| --- | --- | --- | --- |
| `closable` | `boolean` | `false` | When `true`, renders a per-tab sibling `<button tabIndex={-1}>` ✕ close control alongside each tab trigger. |
| `onClose` | `(id: string) => void` | `undefined` | Signal-only callback — emits the closed tab's `id`; mutates no list (the caller owns tab state). |

**What the extension adds (closable=true path only):**

- A per-tab sibling `<button tabIndex={-1}>` ✕ close control rendered next to each tab trigger; it receives pointer events independently of the tab trigger.
- A Delete/Backspace keyboard shortcut on the focused tab that calls `onClose(id)`; the shortcut is active only when `closable` is `true`.
- No extra roving tab stop — the close button uses `tabIndex={-1}` and is reached by pointer or via the keyboard shortcut, not by Tab or Arrow navigation, preserving the existing roving-tabindex model.

**Backward-compatibility guarantee:**

When `closable` is `false` (the default), the 002 selection-only path is byte-identical to the original implementation:

- No extra DOM node is rendered.
- No Delete/Backspace handler is attached.
- No extra roving tab stop is introduced.

This guarantee is proven by the AC-11/AC-12 regression tests in feature 004 (see `specs/004-working-tabs-state-machine/spec.md` AC-11 and AC-12), which assert that the original 002 interaction contract is unaffected when `closable` is omitted or set to `false`.

**Sources:**

- Close-control API: `specs/004-working-tabs-state-machine/spec.md` AC-22 (`closable` prop) and AC-23 (`onClose` signal contract).
- Keyboard close path (Delete/Backspace): `specs/004-working-tabs-state-machine/spec.md` AC-22.
- No-extra-tab-stop constraint and departure from Radix's built-in close handling: `specs/004-working-tabs-state-machine/plan.md` — "Established-Convention Departures" section.
