# Task 005: docs-codeeditor-molecule

**Feature**: 018-code-editor-extract
**Agent**: tech-writer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-18
**Review checkpoint**: No
**Context docs**: docs/architecture.md

## Files

| File | Action | Description |
|------|--------|-------------|
| docs/renderer/src/index.md | Update | Add CodeEditor to the molecules roster; note BodyEditor as consumer |
| docs/architecture.md | Update | Describe CodeEditor as a reusable molecule + the consume relationship |

## Description

Document the extracted `CodeEditor` as a reusable molecule and `BodyEditor` as its consumer (AC-18). In `docs/renderer/src/index.md`, add `CodeEditor` to the molecules roster line/tree with a one-line description (self-contained overlay editor; `resetKey` reset-on-change signal; reuses `jsonTokens.compose()`). In `docs/architecture.md`, note in the renderer tier table / patterns that `CodeEditor` is a domain-agnostic molecule consumed by `BodyEditor` (and reusable by a future response-body organism), and that its line-box height is single-sourced via a local `--code-line-h` var. Keep edits surgical — do not restructure the docs.

## Change Details

- In `docs/renderer/src/index.md`:
  - Add `CodeEditor.tsx` / `CodeEditor.css` to the molecules section of the structure tree with a one-line role note; mention BodyEditor consumes it.
- In `docs/architecture.md`:
  - Add `CodeEditor` to the molecules row of the UI Primitives Layer table (or Patterns) as a reusable domain-agnostic editor consumed by BodyEditor via the `resetKey` signal.

## Contracts

### Expects (checked before execution)
- `BodyEditor.tsx` consumes `CodeEditor` (Task 002 Produces).

### Produces (checked after execution)
- `docs/renderer/src/index.md` mentions `CodeEditor` in the molecules roster.
- `docs/architecture.md` describes `CodeEditor` as a reusable molecule and `BodyEditor` as its consumer.

## Done When

- [x] Both docs describe CodeEditor as a reusable molecule + BodyEditor as consumer (AC-18).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-17T21:35:55Z
**Files changed**: docs/architecture.md, docs/renderer/src/index.md
**Contract**: Expects 1/1 | Produces 2/2
**Notes**: Documented CodeEditor as a reusable domain-agnostic molecule + BodyEditor as consumer (AC-18) in docs/architecture.md (molecules layer-table row + overview + structure tree) and docs/renderer/src/index.md (Purpose roster + structure tree with role note). Surgical additive edits; code-reviewer accuracy check claim-by-claim all PASS.
