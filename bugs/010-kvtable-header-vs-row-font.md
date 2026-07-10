# Bug 010: KVTable header vs row font color perceived mismatch

**Status**: Fixed
**Severity**: Info
**Source**: manual
**Feature**: 016-load-design-fonts
**AC**: N/A
**Reported**: 2026-07-06
**Fixed**: 2026-07-10

## Description

User reports the header vs row font-color relationship in KVTable does not match the intended design. Live inspection: header text is --text-faint (gray), key cells --text (near-black), value cells --text-muted (medium gray), header font-weight 600 — all of which MATCH the checked-in design spec design/styles.css §.kv (lines 951-1035). Not a code-vs-spec defect; the checked-in design/styles.css may differ from the intended mockup. Needs confirmed target header/row colors (and weight) to act on.

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

Resolved by feature 016-load-design-fonts (see [[011-design-fonts-inter-and]], which supersedes/explains this bug). The perceived KVTable header-vs-row font mismatch was rooted in the app never loading Inter/JetBrains Mono (bug 011) — the KVTable rendered in system-fallback faces (SF Mono/Menlo), not the intended JetBrains Mono, so weight/letterform read differently from the design. With the fonts now self-hosted and load-verified (016), KV cells compute JetBrains Mono and the header/row relationship renders as the design intends. The checked-in colors/weights already matched design/styles.css §.kv, so no KVTable.css color change was needed.
