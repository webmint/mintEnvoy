# Task 004: TabBar descriptor mapping + actions row

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: 005, 008
**Spec criteria**: AC-4, AC-5, AC-20
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/TabBar.tsx | Modify | Map method/dirty into descriptor; replace badge dot; build the +/spacer/chevron actions row |

## Description

Wire the store data into the extended descriptor and build the reference actions row (Decision (f) wiring + the actions part of the plan). The store lifecycle is NOT touched — only the descriptor mapping and the actions slot.

1. **toDescriptor** — add `method: tab.spec.method` and `dirty: tab.dirty` to the returned `TabDescriptor`, and REMOVE the `badge: tab.dirty ? '●' : undefined` mapping. `deriveLabel` stays byte-for-byte unchanged (AC-5) — the method appears in the chip AND (for unnamed-URL tabs) inside the label, which is intentional/reference-faithful.
2. **Actions slot** — replace the single `+` text button with: a `+` new-tab button using `<Icon name="plus" size={13} />`, a `<span className="tabbar__spacer" />` (flex:1 spacer), and a static "More tabs" chevron button using `<Icon name="chevronDown" size={13} />`. The chevron is a VISUAL affordance only — wire NO overflow behavior; add a `// TODO(overflow)` marker. Both buttons keep `type="button"` and an `aria-label`.

## Change Details

- In `src/renderer/src/components/organisms/TabBar.tsx`:
  - In `toDescriptor`: add `method: tab.spec.method`, `dirty: tab.dirty`; delete the `badge: tab.dirty ? '●' : undefined` line; keep `id`/`label`.
  - Import the Icon atom if not already imported.
  - Replace the `actions={<button>+</button>}` content with the `+` (Icon plus) / `tabbar__spacer` / "More tabs" chevron (Icon chevronDown) markup; add `// TODO(overflow)` on the chevron.
  - Leave `deriveLabel` unchanged.

## Contracts

### Expects (checked before execution)
- Task 002 added `method`/`dirty` to `TabDescriptor`.
- `toDescriptor` currently sets `badge: tab.dirty ? '●' : undefined` (TabBar.tsx) and the actions slot is a single `+` button.
- The Icon atom's icon set includes `plus` and `chevronDown`.

### Produces (checked after execution)
- `toDescriptor` sets `method` and `dirty` and no longer emits `badge: '●'`.
- `deriveLabel` is unchanged from its 004 form.
- The actions slot renders a `+` button (Icon `plus`), a `tabbar__spacer`, and a static "More tabs" chevron button (Icon `chevronDown`) carrying a `TODO(overflow)` marker and no overflow logic.

## Done When

- [x] `toDescriptor` passes `method`/`dirty` and emits no `'●'` badge (AC-4 — dirty surfaced via the dot, label text untouched)
- [x] `deriveLabel` is byte-identical to its prior form (AC-5)
- [x] Actions slot = `+` (Icon plus) + flex spacer + static "More tabs" chevron (Icon chevronDown) with `TODO(overflow)`, no overflow behavior (AC-20)
- [x] No inline `style={{}}`; no `electron`/`node:` import
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T08:50:14Z
**Files changed**: src/renderer/src/components/organisms/TabBar.tsx
**Contract**: Expects 3/3 | Produces 3/3
**Notes**: Removed badge:'●' → TabBar.test '●' assertions red until task 008 migrates (Risk-3, accepted). Added AC-5 to task 008 Spec criteria (qa panel).
