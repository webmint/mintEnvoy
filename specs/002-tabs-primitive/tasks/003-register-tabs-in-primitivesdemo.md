# Task 003: register-tabs-in-primitivesdemo

**Feature**: 002-tabs-primitive
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: None
**Spec criteria**: AC-4
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/PrimitivesDemo.tsx | Modify | Add a TabsSection registering the Tabs primitive for manual visual verification |

## Description

Register the `Tabs` primitive in the dev-only PrimitivesDemo gallery so its visual fidelity can be checked manually against `design/reference.html`. Add a `TabsSection` function mirroring the existing `DropdownSection`/`ModalSection` pattern (a `<section className="demo-section">` with a `<h2 className="demo-section__title">`), rendering both the request-pane (6-tab: Params/Auth/Headers/Body/Tests/Code) and response-pane (4-tab: Body/Headers/Cookies/Test Results) sets with local `activeId` state, and invoke it in the PrimitivesDemo root render.

## Change Details

- In `src/renderer/src/components/PrimitivesDemo.tsx`:
  - Import `Tabs` (and `TabDescriptor` if needed for typing) from `@renderer/components/molecules/Tabs`.
  - Add a `TabsSection(): React.JSX.Element` function rendering two `Tabs` instances — a 6-tab request-pane set and a 4-tab response-pane set — each with `useState`-held `activeId` updated via `onChange`.
  - Invoke `<TabsSection />` in the PrimitivesDemo root render alongside the existing section invocations (the gallery stays behind the existing `import.meta.env.DEV` dynamic-import guard at the App level — no change to that gating).

## Contracts

### Expects (checked before execution)
- `Tabs.tsx` exports `Tabs` and `TabDescriptor`, importable via `@renderer/components/molecules/Tabs`.
- `PrimitivesDemo.tsx` exists and follows the per-primitive `XSection()` registration pattern.

### Produces (checked after execution)
- `PrimitivesDemo.tsx` imports `Tabs` from `@renderer/components/molecules/Tabs`.
- `PrimitivesDemo.tsx` defines a `TabsSection` component and invokes it in the root render (mirroring `DropdownSection`), so `grep -q Tabs src/renderer/src/components/PrimitivesDemo.tsx` matches and the section is actually mounted.

## Done When

- [x] `PrimitivesDemo.tsx` renders a `TabsSection` with the 6-tab request-pane and 4-tab response-pane sets (AC-4)
- [x] Clicking/keyboarding tabs in the demo updates the shown active tab (local controlled state)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T08:10:06Z
**Files changed**: src/renderer/src/components/PrimitivesDemo.tsx, src/renderer/src/components/__tests__/PrimitivesDemo.test.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Added TabsSection (6-tab request + 4-tab response sets, module-scope TabDescriptor[] consts, local useState/onChange) mirroring DropdownSection; mounted in root render (AC-4). Extended PrimitivesDemo.test.tsx smoke suite with Tabs heading assertions (DEV-present + production-absent) to guard the mount, mirroring the four existing primitives.
