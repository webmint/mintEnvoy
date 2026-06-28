# Task 003: amend-constitution-sole-subscriber-rule

**Feature**: 009-request-bar
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 004
**Spec criteria**: AC-24
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| constitution.md | Modify | reword §4 "TabBar.tsx is the sole subscriber" of tabsStore |

## Description

Amend the constitution's §4 rule that currently names TabBar the *sole* subscriber of tabsStore, so it admits RequestBar as the spec-edit subscriber. Sequenced BEFORE the RequestBar component (task 004) so the code lands against an already-amended governance rule — otherwise shipped code would contradict the standing §4 and the `/implement` code-reviewer would flag it. Documentation-only; no behavior change to TabBar.

## Change Details

- In `constitution.md`, §4 (Patterns & Anti-Patterns → Always Do (Project-Specific)) and §5.2 (Domain Invariants) where the wording appears:
  - Reword the extracted rule "Working-tabs lifecycle (open, dedupe, close, dirty) lives exclusively in tabsStore — TabBar.tsx is the sole subscriber wiring store actions to the Tabs molecule" so that TabBar owns the lifecycle wiring (open/dedupe/close/select) while RequestBar is the spec-edit subscriber (reads the active spec, writes method+url via `updateActiveSpec`). Keep it accurate: TabBar's runtime behavior is unchanged; the only change is acknowledging a second, spec-edit subscriber.
  - Keep the edit minimal and prose-only — do not restructure the section.

## Contracts

### Expects (checked before execution)
- `constitution.md` §4 / §5.2 contain the phrase naming `TabBar.tsx` as the sole subscriber of tabsStore.

### Produces (checked after execution)
- `constitution.md` no longer asserts TabBar is the *sole* tabsStore subscriber; it records RequestBar as the spec-edit subscriber.

## Done When

- [x] §4 (and §5.2 if it repeats the claim) reworded to admit the spec-edit subscriber
- [x] Edit is prose-only; TabBar runtime behavior description unchanged
- [x] No debug artifacts left in changed files
- [ ] Type checker passes on changed files (see Development Commands section) — N/A (markdown), no type surface _(unverified — see Completion Notes)_
- [ ] Linter passes on changed files (see Development Commands section) — N/A (markdown) _(unverified — see Completion Notes)_
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-28T10:37:35Z
**Files changed**: constitution.md
**Contract**: Expects 1/1 | Produces 1/1
**Notes**: Reworded §4: TabBar=lifecycle subscriber, RequestBar=spec-edit subscriber. §5.2 untouched (its requestSpec-pure-data rule still true). Note: task Expects over-specified §5.2 (only §4 had the phrase) — no harm.
