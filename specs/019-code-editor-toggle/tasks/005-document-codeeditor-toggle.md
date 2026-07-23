# Task 005: Document CodeEditor edit/preview toggle in architecture.md

**Feature**: 019-code-editor-toggle
**Agent**: tech-writer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-20
**Review checkpoint**: No
**Context docs**: docs/architecture.md

## Files

| File | Action | Description |
|------|--------|-------------|
| docs/architecture.md | Modify | Rewrite CodeEditor description: overlay → edit/preview toggle |

## Description

Update the CodeEditor molecule description in `docs/architecture.md` from "three-layer overlay code editor" to an edit/preview toggle: an `editing` prop owned by BodyEditor, single-layer conditional mount (textarea XOR pre), and tokenize-on-switch-to-preview via a `{value,lang}` snapshot-cache gate. Surgical edit — touch only the CodeEditor description, no unrelated doc changes.

## Change Details

- In `docs/architecture.md`:
  - Find the CodeEditor description (currently "three-layer overlay code editor" / debounced highlighting / scroll-sync).
  - Rewrite it to: CodeEditor is an edit/preview toggle molecule — `editing` boolean owned by BodyEditor (controlled molecule), single-layer conditional mount (textarea XOR highlighted pre, never both), highlighting runs on switch-to-preview via a `{value,lang}` snapshot-cache gate (not per keystroke). Note the toggle control, caret-at-click entry, and keyboard entry with focus-on-mount.

## Contracts

### Expects (checked before execution)
- CodeEditor is implemented as an edit/preview toggle (tasks 001, 002 complete).
- `docs/architecture.md` currently describes CodeEditor as a three-layer overlay.

### Produces (checked after execution)
- `docs/architecture.md` describes CodeEditor as an edit/preview toggle whose highlighting runs on switch-to-preview.

## Done When

- [x] `docs/architecture.md` CodeEditor description reflects the edit/preview toggle + tokenize-on-preview (AC-20)
- [x] No unrelated doc sections changed
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section) — N/A for a markdown file
- [x] Linter passes on changed files (see Development Commands section) — N/A for a markdown file
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-22T10:59:11Z
**Files changed**: docs/architecture.md
**Contract**: Expects 2/2 | Produces 1/1
**Notes**: Rewrote CodeEditor molecule clause in architecture.md: three-layer overlay → edit/preview conditional-mount toggle (editing owned by BodyEditor, textarea XOR pre, synchronous tokenize-on-switch-to-preview snapshot-cache useMemo, toggle/caret/keyboard entry + focus-on-mount, blur/toggle exit). Removed stale claims (three-layer, transparent-textarea scroll-source, debounced invalidation). Surgical — one clause. Markdown edit done main-thread.
