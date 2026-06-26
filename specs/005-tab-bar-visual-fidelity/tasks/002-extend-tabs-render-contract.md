# Task 002: extend Tabs render contract (method chip + dirty-XOR-close)

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003, 004, 007, 010
**Spec criteria**: AC-2, AC-3, AC-6, AC-9, AC-10, AC-12, AC-13, AC-24, AC-25, AC-26, AC-28, AC-29
**Review checkpoint**: Yes
**Context docs**: specs/002-tabs-primitive/spec.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/Tabs.tsx | Modify | Extend TabDescriptor; render method chip + dirty-XOR-close + active-wrapper modifier |

## Description

Extend the Tabs primitive (Decisions (c), (f), and the active-wrapper part of (a)) — the shared 002 contract change. All additions are opt-in; the non-closable render path stays byte-identical to the 002 contract (002 AC-11 → 005 AC-2). Note: this task carries the highest fan-out (feeds 003/004/007/010) and the 002 contract mutation — hence the review checkpoint.

1. **Descriptor** — add optional `method?: string` and `dirty?: boolean` to `TabDescriptor` (both optional → non-closable/legacy consumers omit; `badge?` stays). JSDoc both new fields (AC-24).
2. **Method chip** — before the label span in BOTH render branches, gated on `method !== undefined`, render `<span className={cx('method', knownMethodClass)}>{method}</span>`. Add a module-level `KNOWN_METHODS` const (`GET POST PUT PATCH DELETE OPTIONS HEAD`); `knownMethodClass` is `method` when it is in `KNOWN_METHODS` (uppercased), else `undefined` → an uncolored chip that inherits text color (AC-10). The chip uses the GLOBAL `.method`/`.{METHOD}` classes (documented departure from BEM — recorded in 002 lineage by task 010).
3. **Dirty-XOR-close** — in the `closable` branch, after the `role="tab"` button, render mutually-exclusively: when `dirty` → `<span className="tabs__tab-dirty" onClick={e => { e.stopPropagation(); onClose?.(tab.id) }} />` (7px dot, no role, NOT focusable, NOT added to `buttonRefs`); else → the existing close `<button type="button" tabIndex={-1} aria-label={\`Close ${label}\`} className="tabs__tab-close">` but swap the unicode `✕` glyph for `<Icon name="x" size={11} />`. Exactly one of dot/close renders. The dirty span is never a roving stop (AC-3) and never replaces the label span (AC-4 preserved). Delete/Backspace close path in `handleKeyDown` stays gated on `closable` (NOT `dirty`) so a dirty tab stays keyboard-closable (AC-6).
4. **Active wrapper modifier** — add `tabs__tab-wrapper--active` to the closable-branch wrapper div's className when the tab is active (compose via `cx`), so Tabs.css (task 003) can scope the active accent to the full tab cell.
5. **Icon import** — `import { Icon } from '@renderer/components/atoms/Icon'` (molecule→atom, allowed).

## Change Details

- In `src/renderer/src/components/molecules/Tabs.tsx`:
  - Add `method?: string` + `dirty?: boolean` (JSDoc'd) to the `TabDescriptor` interface.
  - Add `const KNOWN_METHODS = ['GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD'] as const`.
  - Import the Icon atom.
  - In both branches: insert the gated `.method` chip span before `<span className="tabs__tab-label">`.
  - In the closable branch: add the `--active` wrapper modifier; replace the always-rendered close button with the dirty-XOR-close conditional; swap `✕` → `<Icon name="x" size={11} />`.
  - Leave the non-closable branch's DOM byte-identical except the (gated, absent when `method` undefined) chip — a legacy consumer passing no `method` renders identically.

## Contracts

### Expects (checked before execution)
- `TabDescriptor` is `{ id; label; badge?; disabled? }` and the closable branch renders a unicode `✕` close button at `tabIndex={-1}` (002/004 contract).
- The Icon atom exports `Icon` and its icon set includes `x` (`src/renderer/src/components/atoms/icons.ts`).
- Task 001 produced the `.method.HEAD` / base `.method` rules the HEAD chip resolves against.

### Produces (checked after execution)
- `TabDescriptor` carries optional `method` and `dirty` fields.
- A `KNOWN_METHODS` const exists in `Tabs.tsx`.
- The closable branch emits `tabs__tab-wrapper--active` on the active wrapper, a `tabs__tab-dirty` span when dirty, and a `tabs__tab-close` button (with `<Icon name="x">`) when clean — mutually exclusive.
- The non-closable branch is byte-identical to the 002 path when `method`/`dirty` are absent (no dirty/close node, no extra roving stop).

## Done When

- [x] `TabDescriptor.method?` and `TabDescriptor.dirty?` exist and are JSDoc'd (AC-24)
- [x] Method chip renders before the label gated on `method !== undefined`; an unknown method gets no color class (AC-9, AC-10)
- [x] Dirty tab renders `tabs__tab-dirty` (clickable→onClose), clean tab renders `tabs__tab-close` with `<Icon name="x">` — never both (AC-12, AC-13)
- [x] The dirty span is not focusable and not in `buttonRefs`; exactly one roving stop per tab (AC-3); Delete/Backspace closes a dirty tab (AC-6)
- [x] closable=false DOM byte-identical to the 002 path (AC-2)
- [x] No inline `style={{}}`; no `electron`/`node:` import (AC-28, AC-29)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (AC-25)
- [x] Linter passes on changed files (AC-26)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T07:40:24Z
**Files changed**: src/renderer/src/components/molecules/Tabs.tsx
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Added AC-9/AC-10 to task 007 Spec criteria for downstream /verify traceability (qa panel note).
