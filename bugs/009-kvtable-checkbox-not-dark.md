# Bug 009: KVTable checkbox not dark-gray custom style

**Status**: Fixed
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-06
**Fixed**: 2026-07-09

## Description

KVTable row checkboxes render as native Chromium checkboxes (appearance:auto); accent-color:var(--accent) only tints the checked fill green, so the unchecked box is the browser default (light), not the dark-gray custom checkbox the design intends. Neither design/styles.css §.kv nor KVTable.css implements a custom unchecked appearance — this is an unimplemented design detail, newly visible since 015 mounted KVTable live. Needs the exact design target (dark-gray border? filled box? which token) before fixing.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File | Detail |
|------|--------|
| src/renderer/src/components/organisms/KVTable.css |  |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

Resolved as **not a defect — app already conforms to the documented design**. No code change.

Investigation (`/research`, 2026-07-09) checked every design source for the kv-check checkbox:

| Source | Checkbox spec |
|--------|---------------|
| `design/design-fidelity-contract.md:160` | `.kv-row input[type="checkbox"]` → `accent-color: var(--accent)`, `width: 12px`, `height: 12px` |
| `design/styles.css:990` | identical rule |
| `design/reference.html` (embedded `<style>`) | identical rule; zero `type="checkbox"` custom markup, one unrelated `appearance:none` (`select.input-field`), no custom checkbox pseudo-elements |
| App `KVTable.css:8` | `accent-color: var(--accent)`, `width: 12px`, `height: 12px` — **same** |

`--accent` = `#10b981` in both app (`tokens.css:10`) and design (`styles.css:4`).

No "dark-gray custom" checkbox style exists in any design artifact — the contract specifies a **native** checkbox tinted with `accent-color`. `accent-color` only colors the *checked* fill; an unchecked/disabled native box stays browser-default (light), which is the "default white" originally observed (empty/virtual rows). The reference screenshot's checkbox column is occluded by the open method dropdown and is inconclusive.

A dark-gray custom checkbox would be a **new design decision** (update the fidelity contract + `styles.css`, then `/specify`), not a fidelity fix. Closing until such a design change is made.
