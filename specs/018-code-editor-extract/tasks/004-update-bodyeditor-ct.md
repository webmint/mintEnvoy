# Task 004: update-bodyeditor-ct

**Feature**: 018-code-editor-extract
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002, 003
**Blocks**: None
**Spec criteria**: AC-8, AC-19
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx | Modify | Re-home fidelity/AC-6 tests to CodeEditor CT; keep integration + testid + wiring |
| src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx | Modify | Adjust fixtures if raw-slot markup changed (testids preserved) |

## Description

Update the BodyEditor CT and stories after the extraction. Remove the fidelity/alignment tests that moved to the CodeEditor CT (Task 003) — including the identical-body re-arm (`:769`) and scroll-bleed reset (`:811`), now re-homed as molecule-level `resetKey`-driven tests in T003. Retain: the integration coverage (BodyEditor renders the raw editor), the `body-code-editor`/`body-gutter`/`body-pre` data-testid assertions (AC-8), and ONE org-level wiring assertion that BodyEditor passes `resetKey={activeTabId}` to CodeEditor (the AC-6 contract at the organism boundary). No test is deleted without its replacement already existing in T003 — the T003→T004 dependency edge guarantees that ordering. Adjust `BodyEditor.stories.tsx` fixtures only if the raw-slot markup structure changed; the `body-*` testids stay.

**AC-numbering note**: the tests to remove are labeled with **spec-017** AC numbers in the CT — identify them by line anchor (`:769`, `:811`) and assertion content, NOT by the CT's internal `AC-19..24` labels (those are spec-017 numbering and collide with spec-018's ACs).

## Change Details

- In `src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx`:
  - Remove the `:769` identical-body re-arm and `:811` scroll-bleed tests (re-homed to CodeEditor CT in T003) plus the fidelity/color/grid tests now covered at the molecule level.
  - Keep a mount-integration test + the `body-code-editor`/`body-gutter`/`body-pre` testid assertions.
  - Add/keep ONE assertion that the rendered `<CodeEditor>` receives `resetKey` bound to the active tab id.
- In `src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx`:
  - Update raw-slot fixtures only if the markup structure changed; preserve testids.

## Contracts

### Expects (checked before execution)
- `BodyEditor.tsx` renders `<CodeEditor resetKey={activeTabId} …>` (Task 002 Produces).
- `CodeEditor.ct.tsx` covers the row-height equality, fidelity, and `resetKey` reset tests (Task 003 Produces).

### Produces (checked after execution)
- `BodyEditor.ct.tsx` retains assertions referencing `body-code-editor`, `body-gutter`, and `body-pre`.
- `BodyEditor.ct.tsx` contains an assertion that `resetKey` is wired to the active tab id at the BodyEditor boundary.
- `BodyEditor.ct.tsx` no longer contains the molecule-level fidelity/row-height tests (re-homed to the CodeEditor CT).

## Done When

- [x] Fidelity/AC-6 molecule tests removed from BodyEditor CT (replacements exist in CodeEditor CT).
- [x] body-* testid assertions + the `resetKey={activeTabId}` wiring assertion retained.
- [ ] `npm run test:ct` passes for the BodyEditor CT. _(unverified — see Completion Notes)_
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-17T21:30:13Z
**Files changed**: src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx, src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Pruned BodyEditor CT (33→26): removed 8 molecule-level tests (tk-* colors light/dark, token bindings, grid geometry, gutter-height 20.625px, :769 identical-body re-arm, :811 scroll-bleed) re-homed to CodeEditor.ct by Task 003; added 1 org-boundary wiring test proving resetKey={activeTabId} (two identical-body tabs, switch, .tk-key attach→clear→reattach); removed 3 orphaned fixtures (BodyEditorRawJsonDarkFixture, BodyEditorScrollBleedFixture + consts). AC-8 body-* testids retained across kept tests. test:ct Done-When UNVERIFIED: same pre-existing Playwright-CT harness break as Task 003 (BodyEditor.ct fails 32/32 'cannot be mounted' independent of this change); typecheck+eslint+build PASS. NOTE: a diagnostic git-checkout during Task 003 accidentally regressed BodyEditor.tsx/.css to inline in commit 723035; corrective commit 23b04fb restored the rewired version before this task.
