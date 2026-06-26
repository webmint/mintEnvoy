# Task 010: record the 005 contract extension in 002 lineage

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-23
**Review checkpoint**: No
**Context docs**: specs/002-tabs-primitive/spec.md

## Files

| File | Action | Description |
|------|--------|-------------|
| specs/002-tabs-primitive/spec.md | Modify | Append a feature-005 extension block under §10 Contract Lineage |

## Description

Record the task-002 contract change in the 002 spec lineage (the AC-29-of-004 pattern — a contract change is recorded, not a silent prop addition). Append a `### Extension: feature 005-tab-bar-visual-fidelity (<date>)` block under the existing §10 Contract Lineage, mirroring the 004 extension block. Document:

- The new optional `TabDescriptor` fields `method?: string` and `dirty?: boolean` (both default-absent → backward-compatible).
- The dirty-XOR-close render model in the closable branch (dirty → non-focusable clickable `tabs__tab-dirty` span; clean → always-visible `tabs__tab-close` SVG button), and that it replaces the close *control* slot, never the *label* span (004 AC-26 preserved).
- The byte-identical non-closable path guarantee (005 AC-2) — unchanged from the 004 lineage guarantee.
- The global `.method`/`.{METHOD}` class usage inside the BEM Tabs primitive — a documented departure from the BEM-only convention (constitution §2.3), reused from tokens.css's existing method palette.
- The Q-3 accessibility tradeoff: the dirty dot has no accessible name (matches the reference's non-interactive span); assistive-tech close routes via the retained Delete/Backspace keyboard path.

## Change Details

- In `specs/002-tabs-primitive/spec.md`:
  - Under `## 10. Contract Lineage` (after the `### Extension: feature 004-working-tabs-state-machine` block), append a `### Extension: feature 005-tab-bar-visual-fidelity` block with a fields table + the model/guarantee/departure/tradeoff notes above and a Sources list citing this feature's spec ACs.

## Contracts

### Expects (checked before execution)
- `specs/002-tabs-primitive/spec.md` has a `## 10. Contract Lineage` section with a `### Extension: feature 004-working-tabs-state-machine` block.
- Task 002 produced the `method`/`dirty` fields + dirty-XOR-close model this block documents.

### Produces (checked after execution)
- A `### Extension: feature 005-tab-bar-visual-fidelity` block exists under §10 documenting the method/dirty fields, the dirty-XOR-close model, the byte-identical guarantee, the global-`.method` departure, and the Q-3 a11y tradeoff.

## Done When

- [x] A `### Extension: feature 005-tab-bar-visual-fidelity` block exists under §10 of the 002 spec (AC-23)
- [x] The block documents the new fields, dirty-XOR-close, byte-identical path, global-`.method` departure, and Q-3 tradeoff
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (N/A — markdown; no-op)
- [x] Linter passes on changed files (N/A — markdown; no-op)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T14:14:39Z
**Files changed**: specs/002-tabs-primitive/spec.md
**Contract**: Expects 2/2 | Produces 1/1
**Notes**: 002 §10 lineage block appended (AC-23). 1 repair round: corrected AC-10/AC-13 citations + .method.{METHOD} compound notation (code-reviewer cross-checked all claims against impl).
