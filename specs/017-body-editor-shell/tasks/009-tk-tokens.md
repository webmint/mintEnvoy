# Task 009: tokens.css --tk-* per-theme syntax tokens

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 006, 010
**Spec criteria**: AC-20, AC-21, AC-25
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/styles/tokens.css | Modify | Add `--tk-key/str/num/bool` per-theme tokens set to the design literal hex |

## Description

Add four per-theme syntax-color tokens (`--tk-key`, `--tk-str`, `--tk-num`, `--tk-bool`) set to the design's literal per-theme hex. This is the constitution §4 fidelity-driven token exception: the design pins literal hex for these four colors, so the tokens carry the literals and BodyEditor.css's `.tk-*` classes bind via `var()` — computed style resolves to the literal hex, satisfying both §4 (tokens over literals) and the literal-hex fidelity assertions (AC-20/21). This task adds ONLY the tokens; the `.tk-*` class rules live in BodyEditor.css (task 006).

## Change Details

- In `src/renderer/src/styles/tokens.css`:
  - In the `:root` (light) token block, add:
    - `--tk-key: #0369a1;`
    - `--tk-str: #15803d;`
    - `--tk-num: #b45309;`
    - `--tk-bool: #be185d;`
  - In the `[data-theme="dark"]` token block, add:
    - `--tk-key: #7dd3fc;`
    - `--tk-str: #86efac;`
    - `--tk-num: #fcd34d;`
    - `--tk-bool: #f0abfc;`
  - Do NOT add any `.tk-*` class rule here (BodyEditor.css owns those, task 006). Do NOT add `--tk-null/--tk-punc/--tk-var` (those classes bind to the pre-existing `--text-faint/--text-muted/--accent`).

## Contracts

### Expects (checked before execution)
- `tokens.css` has a `:root` light token block and a `[data-theme="dark"]` token block.

### Produces (checked after execution)
- `tokens.css` defines `--tk-key/--tk-str/--tk-num/--tk-bool` under `:root` with the light hex (#0369a1/#15803d/#b45309/#be185d).
- `tokens.css` defines the same four tokens under `[data-theme="dark"]` with the dark hex (#7dd3fc/#86efac/#fcd34d/#f0abfc).
- No `.tk-*` class rule is added to tokens.css.

## Done When

- [x] `--tk-key/str/num/bool` resolve to the light literals under `:root` (AC-20 basis).
- [x] `--tk-key/str/num/bool` resolve to the dark literals under `[data-theme="dark"]` (AC-21 basis).
- [x] No `.tk-*` class rule added to tokens.css (class rules are task 006).
- [x] The design-token provenance check (AC-25) sees no hardcoded color literal outside these sanctioned per-theme tokens.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-11T08:14:50Z
**Files changed**: src/renderer/styles/tokens.css
**Contract**: Expects 1/1 | Produces 3/3
**Notes**: Added --tk-key/str/num/bool per-theme (light+dark literal hex) to tokens.css. DEVIATION: real file is src/renderer/styles/tokens.css, NOT the handoff's src/renderer/src/styles/tokens.css (alias trap). 'generated from design/tokens.json' header is stale (file absent) so hand-edit is correct. No .tk-* class rules (task 006). All 8 hex verified vs spec. Panel clean iter 0. Unblocks task 006. qa forward note (all four tokens both themes) reinforced in task 010.
