# Task 004: KVTable component tests + fixtures

**Feature**: 014-kv-table-editor
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 003
**Blocks**: None
**Spec criteria**: AC-8, AC-10, AC-11, AC-13, AC-14, AC-18, AC-19, AC-20, AC-21, AC-23, AC-24, AC-25, AC-26, AC-33
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx | Create | Playwright CT: behaviour scenarios + fidelity computed-style asserts. |
| src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx | Create | CT fixture components (full styling context). |

## Description

Author the Playwright component tests for KVTable. KVTable is NOT mounted into the running app this feature, so the CT is the ONLY runtime vehicle for its behaviours and fidelity — coverage here is load-bearing.

**Fixture scoping (memory lesson — mandatory)**: the CT fixtures in `KVTable.stories.tsx` MUST reproduce the full production styling context or fidelity asserts are meaningless — import `tokens.css`, scope `box-sizing: border-box` to the fixture inline (do NOT global-import `base.css` — it breaks screenshot baselines), and wrap the component in its production class context. Provide mock `Row[]` data + a mount that lets the test pass `field` and `validVars`.

**CT-run note for /implement**: `npm run test:ct` is a long silent command — run it in the main thread (background bash), not inside a stalling subagent (600s watchdog memory lesson).

### Required scenarios

- **Auto-promote** on first key/value edit into the trailing row → a real row appended + a fresh trailing row (AC-8); and NO promote when only the checkbox is toggled or description edited on the otherwise-empty trailing row (AC-26).
- **Hover-delete** removes the row + focus moves to an adjacent cell, never `document.body` (AC-18, AC-13).
- **Checkbox** toggle flips `enabled` + applies `.disabled` (AC-14, AC-16-adjacent); delete control is a real focusable `<button>` (AC-14).
- **Variable highlight — injected non-empty `validVars`**: a known name renders `.var`, an absent name renders `.var.missing` (AC-19). Inject the set via the `validVars` prop (the F1 seam).
- **Degradation — ∅-default path (R11, mandatory)**: mount WITHOUT the `validVars` prop (or with an empty set) → EVERY `{{var}}` token renders neutral `.var`, ZERO `.var.missing`. This asserts the AC-20 degradation the injected path would otherwise mask.
- **Description-cell no-tokenise (R10)**: a `{{var}}` typed into the description cell renders verbatim (no `.var` span) — description is never tokenised (AC-11).
- **Paste (R9)**: a multi-line paste into a cell collapses newlines to spaces and creates NO extra rows; a rapid/large paste into the trailing row spawns exactly ONE new trailing row (AC-23, AC-24).
- **External mutation**: replacing the bound array underneath the component (simulated cURL import) → reactive re-render with no stale local edits (AC-21).
- **Two mounts independent**: a params mount and a headers mount edit their own arrays without cross-contamination (AC-10).
- **Tab traversal**: checkbox→key→value→description→next row (AC-25).
- **Fidelity computed-style asserts** (var→token, per design/styles.css `.kv` block): grid-template-columns `22px 1fr 1fr 1fr 24px`; `.kv-header` height 30px; `.kv-row` min-height 32px; checkbox 12px; `.kv-cell` mono font 12px; `.var` color = `var(--accent)`; `.var.missing` color = `var(--m-delete)` + `line-through`; `.kv-row.disabled` opacity 0.55. Assert across the default/disabled/hover/var/var-missing states.

## Change Details

- In `src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx`:
  - Export fixture components mounting `KVTable` with mock `Row[]`, a `field` prop, and an optional injected `validVars` set; import `tokens.css`; scope `box-sizing: border-box` inline.
- In `src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx`:
  - Playwright CT mounting the fixtures and asserting every required scenario above, including BOTH the injected-`validVars` path (AC-19) AND the omitted-prop ∅-default path (AC-20).

## Contracts

### Expects (checked before execution)
- `KVTable.tsx` exports `KVTable` with props `{ field: 'params' | 'headers'; validVars?: ReadonlySet<string> }` (task 003).
- `KVTable.css` defines the `.kv*`/`.var`/`.var.missing`/`.disabled` classes bound to `tokens.css` (task 003).
- The Playwright `@playwright/experimental-ct-react` stack is configured (feature 001).

### Produces (checked after execution)
- `KVTable.stories.tsx` exports fixture components reproducing the full styling context (tokens.css import + border-box scope) and injecting `field` + `validVars`.
- `KVTable.ct.tsx` asserts the auto-promote, delete-focus, checkbox, variable-highlight (BOTH injected non-empty AND ∅-default neutral), description-no-tokenise, paste (multi-line + rapid), external-mutation, two-mount-independence, Tab-traversal, and fidelity computed-style scenarios.
- The CT suite passes under `npm run test:ct` (KVTable spec).

## Done When

- [x] `KVTable.ct.tsx` asserts BOTH the injected non-empty `validVars` path (`.var.missing`, AC-19) AND the omitted ∅-default path (all neutral `.var`, zero `.var.missing`, AC-20).
- [x] The paste (R9/AC-23/24) and description-no-tokenise (R10/AC-11) scenarios are present and pass.
- [x] Fidelity computed-style asserts lock the pinned `.kv` values (var→token) across states.
- [x] Fixtures reproduce the full styling context (tokens.css import + inline border-box scope; no global base.css import).
- [x] The KVTable CT suite passes (`npm run test:ct`).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-05T12:13:23Z
**Files changed**: src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx, src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx
**Contract**: Expects 3/3 | Produces 3/3
**Notes**: 21 CT tests + 10 fixtures, playwright exit 0 (run in main thread per watchdog lesson). Both validVars paths locked (R11: ∅-default zero-.missing + injected .var.missing). Fidelity var→token proof. Panel-clean in 2 rounds; round-1 qa 3 gaps (AC-25 Tab-traversal, AC-23 collapse-to-spaces, AC-14 button-tag) + code 1 (middle-delete containment) fixed by test additions.
