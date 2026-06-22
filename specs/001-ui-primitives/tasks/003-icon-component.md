# Task 003: build the inline SVG Icon component

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: 009
**Spec criteria**: AC-23, AC-13, AC-14, AC-18, AC-15, AC-21
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                                       | Action | Description                                                  |
| ------------------------------------------ | ------ | ------------------------------------------------------------ |
| src/renderer/src/components/atoms/Icon.tsx | Create | Inline SVG Icon component (typed `name`, size, className)    |
| (Icon stylesheet under atoms/)             | Create | Semantic-class styling bound to tokens.css custom properties |

## Description

Build the `Icon` atom: renders an inline 16x16, 1.5px-stroke SVG for a known `IconName`, and a safe fallback for an unknown name (via `resolveIcon`). First presentation-layer task after the data layer — review checkpoint. Styling via semantic class names bound to `tokens.css` CSS custom properties; no inline styles. Animations (if any) respect `prefers-reduced-motion`.

## Change Details

- In `src/renderer/src/components/atoms/Icon.tsx`:
  - Props: `name: IconName`, `size?` , `className?` (typed; no `any`).
  - Render `<svg>` with a 16x16 viewBox and the path from `resolveIcon(name)`; unknown name renders the fallback, never throws (AC-13).
  - Apply a semantic class (e.g. `icon`) bound to tokens; no `style={{ }}` (AC-18).
  - Document the exported component and its public props (AC-15).
- In the Icon stylesheet:
  - Semantic classes referencing tokens.css custom properties; gate any animation behind `@media (prefers-reduced-motion: reduce)` (AC-14).

## Contracts

### Expects (checked before execution)

- `IconName` and `resolveIcon` are exported (task 002).

### Produces (checked after execution)

- `Icon.tsx` exports an `Icon` component rendering an inline SVG with a 16x16 viewBox for a known name.
- Unknown name renders the fallback without throwing.
- The component carries no inline `style={{ }}`; styling is via semantic classes bound to tokens.
- The exported `Icon` and its props are documented (AC-15).

## Done When

- [x] Interaction test: a known name renders an `<svg>`; an unknown name renders the fallback (AC-23, AC-13)
- [x] No `style={{` in the component source (AC-18)
- [x] Exported component + props have doc comments (AC-15)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-21T17:36:25Z
**Files changed**: src/renderer/src/components/atoms/Icon.tsx, src/renderer/src/components/atoms/Icon.css, src/renderer/src/components/atoms/**tests**/Icon.test.tsx, src/renderer/src/components/atoms/**tests**/Icon.ct.tsx
**Contract**: Expects 1/1 | Produces 4/4
**Notes**: Icon: attribute-driven size (no inline styles), a11y modes, reduced-motion. SECURITY: review panel caught + fixed a title->dangerouslySetInnerHTML XSS (title now escaped JSX child; only geometry injected). Vitest 31/31 + Playwright CT 4/4 (AC-14 reduced-motion verified in real Chromium).
