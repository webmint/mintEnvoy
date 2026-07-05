# Task 003: KVTable component + styles

**Feature**: 014-kv-table-editor
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001, 002
**Blocks**: 004
**Spec criteria**: AC-1, AC-4, AC-5, AC-6, AC-7, AC-8, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29, AC-30, AC-31, AC-32
**Review checkpoint**: Yes
**Context docs**: docs/renderer/index.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/KVTable.tsx | Create | Controlled key-value grid organism (flat placement). |
| src/renderer/src/components/organisms/KVTable.css | Create | Token-bound `.kv*` semantic classes matching the design/styles.css `.kv` block. |

## Description

Build KVTable — the controlled key-value grid editing the active tab's RequestSpec `params[]`/`headers[]`. FLAT placement at `organisms/KVTable.tsx` (matching Sidebar/TabBar/RequestBar — constitution §2.2; do NOT create an `organisms/request/` subfolder). Mirrors the RequestBar controlled-subscriber precedent (`docs/renderer/index.md`).

**Props**: `{ field: 'params' | 'headers'; validVars?: ReadonlySet<string> }`. `validVars` defaults to `envVars()` (task 002) — production mounts omit it (∅-default); a CT injects a non-empty set (this is the F1/R11 test seam). One component, two mounts distinguished only by `field` (AC-10).

**State ownership (no local copy)**: read the bound `Row[]` via a per-field zustand selector `s => activeTab?.spec[field] ?? EMPTY_ROWS`, where `EMPTY_ROWS` is a module-level frozen constant (R7 — a fresh `[]` per call loops on `Object.is`). Derive the virtual trailing row in the RENDER BODY, never in the selector. Every edit computes a fresh `Row[]` and writes via `tabsStore.updateActiveSpec({ [field]: nextRows })` — a new array ref flips dirty through the existing no-op guard (AC-6, AC-15). No new store action (AC-7). External array replacement (cURL import) re-renders reactively with no stale local edits (AC-21).

**Rendering**: a `.kv-header` label row, one `.kv-row` per Row, then exactly one derived virtual trailing `.kv-row.empty`. Per row: a real `<input type="checkbox">` toggling `Row.enabled` (row gets `.disabled` when off — AC-14, AC-16, AC-17); three `.kv-cell` mono `<input>`s for key/value/description; a hover-revealed 24px `.kv-actions` slot holding a real `<button>` delete (AC-14, AC-18). The virtual trailing row has no delete affordance.

**Auto-promote**: typing into the key OR value cell of the virtual trailing row appends a real Row and a fresh virtual trailing row spawns (AC-8). Toggling the checkbox or editing description alone on the otherwise-empty trailing row does NOT promote (AC-26).

**Highlighting (display-only)**: key and value cell text is tokenised via `tokenizeVars` (task 001) into `.var` spans; description is NOT tokenised (AC-11 / R10 — gate the tokenise call by cell kind). A `.var` whose name is absent from `validVars` renders `.var.missing` ONLY when `validVars.size > 0`; when `validVars` is ∅ every token is neutral `.var`, none `.missing` (AC-19, AC-20). Never resolves/substitutes (AC-12).

**Focus (R-caret)**: index-based React keys (`key={index}` for real rows; the virtual trailing row keyed at its FUTURE index `key={rows.length}` so promotion reuses the same DOM node → native caret preservation mid-type). Imperative refocus via **`useLayoutEffect` + a pending-focus `{rowIndex, column}` ref** ONLY on discrete delete (refocus adjacent) and Enter-commit (focus the new row's cell); never `document.body` (AC-13, AC-18, AC-25). Tab traverses checkbox→key→value→description→next row (AC-25).

**Paste**: single-line paste = literal; multi-line paste collapses `\n`→spaces and does NOT explode into rows; a rapid/large paste into the trailing row spawns exactly ONE new trailing row — make promote a pure function of the RESULTING rows, not of event count (AC-23, AC-24 / R9).

**Row type**: `import type { Row } from '@renderer/lib/requestSpec'` — TYPE-ONLY (constitution §2.2/§5.2; never a value import). **Styling**: semantic `.kv*` classes in `KVTable.css` bound to `tokens.css`, matching the design/styles.css `.kv` block to pixel fidelity; no inline styles (AC-31), none of the design-export cruft (`data-om-*`, `__OmT`, tweaks-panel).

Not mounted into the app this feature (AC-5) — no App/Shell edit.

## Change Details

- In `src/renderer/src/components/organisms/KVTable.tsx`:
  - Hoist `const EMPTY_ROWS: readonly Row[] = Object.freeze([])`.
  - `export function KVTable({ field, validVars = envVars() }: { field: 'params' | 'headers'; validVars?: ReadonlySet<string> }): JSX.Element`.
  - Per-field selector reading the active tab's `spec[field]`; render-body virtual-trailing-row derivation; per-row controlled inputs; `useLayoutEffect` + pending-focus ref for delete/Enter refocus; `tokenizeVars` on key/value cells only; write path via `updateActiveSpec`.
  - JSDoc on the component + its props (AC-27).
- In `src/renderer/src/components/organisms/KVTable.css`:
  - `.kv`, `.kv-header`, `.kv-row`, `.kv-row.empty`, `.kv-row.disabled`, `.kv-check`, `.kv-cell` (`.key`/`.value`), `.kv-cell input`, `.var`, `.var.missing`, `.kv-actions` — values bound to `tokens.css` matching design/styles.css: grid `22px 1fr 1fr 1fr 24px`; `.kv-header` height 30px, font 10.5px uppercase letter-spacing 0.04em `var(--text-faint)` weight 600; `.kv-row` min-height 32px border-bottom `var(--border-faint)` color `var(--text)`; checkbox 12px `accent-color: var(--accent)`; `.kv-cell` padding 6px 10px mono `var(--font-mono)` 12px; `.kv-cell.value` color `var(--text-muted)`; `.var` `var(--accent)`; `.var.missing` `var(--m-delete)` + `line-through dotted`; `.kv-actions` display none → flex on `.kv-row:hover`; `.kv-row.disabled` opacity 0.55.

## Contracts

### Expects (checked before execution)
- `varTokens.ts` exports `tokenizeVars(text: string): VarSegment[]` and `type VarSegment = { kind: 'plain'; text: string } | { kind: 'var'; name: string }` (task 001).
- `envVars.ts` exports `envVars(): ReadonlySet<string>` returning a frozen empty set (task 002).
- `requestSpec.ts` exports the `Row` type `{ enabled: boolean; key: string; value: string; description: string }` (feature 004, existing).
- `tabsStore` exposes `updateActiveSpec(patch: Partial<RequestSpec>)` and a subscribable active-tab spec (feature 004/009, existing).

### Produces (checked after execution)
- `KVTable.tsx` exports `KVTable` with props `{ field: 'params' | 'headers'; validVars?: ReadonlySet<string> }`, `validVars` defaulting to `envVars()`.
- `KVTable.tsx` imports `Row` via `import type` only (no value import of `requestSpec`), reads rows via a per-field selector with a frozen `EMPTY_ROWS` fallback, and writes via `updateActiveSpec` (no new store action).
- `KVTable.css` defines `.kv`, `.kv-header`, `.kv-row`, `.kv-cell`, `.var`, `.var.missing`, `.kv-actions`, `.kv-row.disabled` bound to `tokens.css` custom properties, with no inline `style={{` in `KVTable.tsx`.

## Done When

- [x] `KVTable` renders header + rows + one virtual trailing row; checkbox/key/value/description cells + hover-delete are real `<input type=checkbox>` / `<button>` elements.
- [x] Auto-promote fires on key/value edit only; delete/Enter refocus uses `useLayoutEffect` + pending-focus ref and never lands on `document.body`.
- [x] `{{var}}` highlight in key/value cells only; `.var.missing` gated on `validVars.size > 0`; ∅-default → all neutral.
- [x] Writes go through `updateActiveSpec` with a fresh array; no local copy; `import type { Row }` only.
- [x] `KVTable.tsx` contains no inline `style={{` and no `data-om-*`/`__OmT` cruft.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-05T11:44:33Z
**Files changed**: src/renderer/src/components/organisms/KVTable.tsx, src/renderer/src/components/organisms/KVTable.css
**Contract**: Expects 4/4 | Produces 3/3
**Notes**: Panel-clean in 2 rounds; round-1 code-reviewer High (virtual-row description input silent data loss) fixed via readOnly/disabled on inert virtual inputs. R7 frozen selector, future-index virtual-row key, useLayoutEffect delete-clamp, overlay highlight, ∅-gate all verified. type-check+lint+build clean. (2 agent watchdog stalls recovered by re-dispatch with inlined context.)
