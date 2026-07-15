# Task 003: JSON tokenizer lib + two-pass compose

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 006
**Spec criteria**: AC-1, AC-9, AC-10, AC-16, AC-17, AC-26, AC-27, AC-28
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/jsonTokens.ts | Create | Renderer-pure JSON tokenizer + two-pass `compose` (var-pass-wins) + perf ceiling |
| src/renderer/src/lib/__tests__/jsonTokens.test.ts | Create | Unit tests: {{var}}-inside-JSON-string tie-break, empty, malformed |

## Description

Create a renderer-pure, JSON-only syntax tokenizer plus a two-pass `compose` helper that overlays the language-agnostic `{{var}}` pass (reusing `tokenizeVars`) on the JSON structural pass, with the var pass winning inside JSON strings. This is a pure, sync, renderer-external-import-free lib module (constitution §2.2 — lib never imports components). Highlighting is display-only; it never resolves variable values or serializes the body.

## Change Details

- In `src/renderer/src/lib/jsonTokens.ts` (new):
  - Export typed token segments (a discriminated union over the JSON token kinds `tk-key`/`tk-str`/`tk-num`/`tk-bool`/`tk-null`/`tk-punc`, plus `tk-var` and plain).
  - Export `compose(text, lang, validVars)`:
    - Runs the `{{var}}` pass (via `tokenizeVars` from `@renderer/lib/varTokens`) for ALL raw languages; `{{var}}` substrings lift to `tk-var`.
    - Runs the JSON structural pass ONLY when `lang === 'json'`; non-JSON langs get the var pass only, everything else plain `var(--text)` (AC-10).
    - **var-pass-wins**: when a `{{var}}` overlaps a JSON string, the `tk-var` segment takes precedence inside the string (AC-9).
    - Empty input → zero tokens, no throw (AC-16).
    - Malformed JSON → a single plain `var(--text)` segment, no throw, no error signal (AC-17).
    - **Perf ceiling**: above a tunable threshold constant (default `50000` chars) skip the JSON structural pass and degrade to plain `var(--text)`; export/name the constant (not a magic literal).
  - `compose` stays a pure sync function — NO debounce, timers, or React here (the debounce lives in BodyEditor, task 006).
  - Carry a module + `compose` contract doc comment (AC-26): renderer-pure, display-only, JSON-only structural vocab, two-pass ordering, degrade paths.
- In `src/renderer/src/lib/__tests__/jsonTokens.test.ts` (new):
  - `{{var}}`-inside-a-JSON-string fixture pinning var-pass-wins tie-break.
  - Empty string → `[]`.
  - Malformed JSON → single plain segment, no throw.
  - Non-JSON lang (e.g. `xml`) → var pass only, no structural tokens.
  - Above-threshold input → degrades to plain.

## Contracts

### Expects (checked before execution)
- `tokenizeVars(text)` returns `VarSegment[]` (plain/var) from `@renderer/lib/varTokens` (existing, unchanged).

### Produces (checked after execution)
- `src/renderer/src/lib/jsonTokens.ts` exports `compose` and its token-segment type(s).
- `compose('', 'json', …)` returns zero tokens; malformed JSON returns a single plain segment; both never throw.
- The JSON structural pass runs only for `lang === 'json'`; the `{{var}}` pass runs for all langs.
- A named perf-ceiling threshold constant (default 50000) gates the JSON pass.
- `jsonTokens.test.ts` covers the tie-break, empty, malformed, non-JSON, and above-threshold cases.

## Done When

- [x] `compose` exists in `jsonTokens.ts`, is pure/sync, and imports nothing renderer-external besides `varTokens` (AC-1, §2.2).
- [x] Two-pass var-pass-wins tie-break unit test passes (AC-9).
- [x] Non-JSON lang yields var-pass-only output (AC-10).
- [x] Empty → zero tokens; malformed → single plain segment; neither throws (AC-16, AC-17).
- [x] `compose` and the module carry contract doc comments (AC-26).
- [x] The JSON tokenizer passes type-check and lint before completion (AC-28).
- [x] No debug artifacts left in changed files (AC-27).
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-11T06:26:03Z
**Files changed**: src/renderer/src/lib/jsonTokens.ts, src/renderer/src/lib/__tests__/jsonTokens.test.ts
**Contract**: Expects 1/1 | Produces 5/5
**Notes**: New renderer-pure jsonTokens.ts: compose() two-pass tokenizer (JSON structural + {{var}} overlay, var-pass-wins in strings), ComposeToken union, JSON_HIGHLIGHT_MAX_CHARS=50000. Degrade paths: empty->[], malformed->single plain (no throw), >50k/non-json->var-pass-only. 30 tests. 1 review-panel repair round added 5 tests (name-trim, tk-var.text raw, known-default, empty {{}}) + 2 cosmetic nits. Handoff: task 006 consumer must escape token.text (not raw HTML).
