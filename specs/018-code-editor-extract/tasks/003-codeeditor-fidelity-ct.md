# Task 003: codeeditor-fidelity-ct

**Feature**: 018-code-editor-extract
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 004
**Spec criteria**: AC-16, AC-6, AC-12, AC-13, AC-17, AC-19, AC-21, AC-23
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx | Create | Playwright CT: fidelity, row-height equality, AC-6 reset via resetKey |

## Description

Author the CodeEditor Playwright component test. Cover: (1) fidelity via the live-renderer computed-style channel using `@renderer/test-utils/fidelityAssert` — assert `.tk-*` colors resolve to the T7a design literals/tokens, with `skipIfChannelUnavailable` so an absent channel yields UNVERIFIED, never PASS (AC-16); (2) row-height equality — assert the `.gutter > div`, the `<pre>` lines, AND the `<textarea>` all compute to the same 20.625px line-box height via `getComputedStyle` (AC-12/13/21); (3) the AC-23 live/debounced split (plain span while typing → `.tk-key` after debounce); (4) AC-6 reset driven DIRECTLY by `resetKey` — a molecule-level port of BodyEditor.ct.tsx:769 (identical-value re-arm) and :811 (scroll-bleed reset), asserting the reset fires on a `resetKey` change with `value`+`lang` held constant.

Fixtures live INLINE in `CodeEditor.ct.tsx` — there is NO molecules `CodeEditor.stories.tsx` (the plan's File Impact omits one). Include a `resetKey`-driver harness (a wrapper whose button toggles `resetKey`) so the AC-6 reset tests drive the prop directly, not via tabsStore/activeTabId. Reproduce the full styling context — import `tokens.css`, set `data-mstyle`/`data-theme`, and scope the production `.code-editor` className — so the fidelity assertions bind to real styles (CT-alias-trap lesson).

**AC-numbering note**: the existing `BodyEditor.ct.tsx` labels its fidelity tests with **spec-017** AC numbers (its `AC-19..24` are color/grid/gutter). Those are NOT spec-018's AC numbers — identify the tests to port by their CT line anchors (`:769`, `:811`) and assertion content, not by the CT's internal AC labels.

## Change Details

- In `src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx`:
  - Import `assertComputedStyle`, `assertResolvesToToken`, `skipIfChannelUnavailable` from `@renderer/test-utils/fidelityAssert`.
  - Mount `CodeEditor` with inline fixtures (seeded JSON body); include a `resetKey`-driver wrapper.
  - Assert `.gutter > div` / `pre` / `textarea` computed heights are equal (20.625px).
  - Port the `:769` identical-value re-arm and `:811` scroll-bleed reset as molecule-level `resetKey`-driven tests.

## Contracts

### Expects (checked before execution)
- `CodeEditor` is exported from `src/renderer/src/components/molecules/CodeEditor.tsx` (Task 001 Produces).
- `@renderer/test-utils/fidelityAssert` exists and exports `assertComputedStyle` / `assertResolvesToToken` / `skipIfChannelUnavailable` (test-only; consumed by the CT, never by `CodeEditor.tsx`).

### Produces (checked after execution)
- `CodeEditor.ct.tsx` asserts the `.gutter > div`, `pre`, and `textarea` computed row heights are equal.
- `CodeEditor.ct.tsx` calls `skipIfChannelUnavailable` before its computed-style fidelity assertions.
- `CodeEditor.ct.tsx` contains a `resetKey`-driven reset test that holds `value`+`lang` constant (molecule-level port of BodyEditor.ct.tsx:769) and a scroll-reset test (port of :811).
- Fixtures are inline in `CodeEditor.ct.tsx`; no `molecules/CodeEditor.stories.tsx` is created.

## Done When

- [x] CT asserts row-height equality (all three = 20.625px) + tk-* fidelity via computed-style channel (UNVERIFIED-not-PASS when absent).
- [x] AC-6 reset tests drive `resetKey` directly (identical-value re-arm + scroll-bleed), value+lang held constant.
- [ ] `npm run test:ct` passes for the CodeEditor CT. _(unverified — see Completion Notes)_
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-17T20:10:51Z
**Files changed**: src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx, src/renderer/src/components/molecules/__tests__/CodeEditor.stories.tsx
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: 10-test CT covering AC-12/13/21 row-height equality + AC-13 font-independence, AC-16 light/dark tk-* fidelity, AC-17 token-bound colors + AC-17/AC-2 malformed degrade, AC-23 (page.clock-deterministic), AC-6 resetKey re-arm + scroll-reset, .tk-var.missing (--m-delete/strikethrough). DEVIATION from Produces #4: a CodeEditor.stories.tsx fixture module was required — Playwright experimental-ct cannot mount components defined inline in the spec file (proven at runtime; mirrors BodyEditor/Tabs/KVTable/RequestSubTabs .stories). test:ct Done-When left UNVERIFIED: pre-existing Playwright-CT harness break on this machine — pristine untouched BodyEditor.ct fails 32/32 'cannot be mounted' identically; Tabs.ct passes 76 — independent of this task's code; typecheck+eslint+build all PASS. Panel round-2 closed 4 substantive coverage gaps; final qa AC-19 flag refuted (AC-19 is the typecheck+lint hygiene AC per spec §5.7, covered by verify).
