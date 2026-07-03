# Feature Review — specs/013-tabs-contrast-wcag — 2026-07-03

**Feature**: specs/013-tabs-contrast-wcag
**Scope**: assembled feature diff (all tasks together) — 22 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst, design-auditor
**Refuters invoked**: architect
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
1. [Info] src/renderer/src/components/molecules/Tabs.css:149 — Cross-task divergence: Task 002 inline "departure from convention" comment overstates uniqueness after the F1-fix commit drops 6 more fallbacks from the same file without any comment [Likely]

## Confirmed Findings

### src/renderer/src/components/molecules/Tabs.css

#### Mislogic
- [F-001] [Info] :149 — Cross-task divergence: Task 002 inline "departure from convention" comment overstates uniqueness after the F1-fix commit drops 6 more fallbacks from the same file without any comment  [Likely]
  Severity: Info
  File: src/renderer/src/components/molecules/Tabs.css
  Line: 149
  Pattern: Cross-task divergence: Task 002 inline "departure from convention" comment overstates uniqueness after the F1-fix commit drops 6 more fallbacks from the same file without any comment
  Confidence: Likely
  Category: mislogic
  Evidence:
  ```
  color: var(--text); /* var(--text) with no fallback literal: the design-token provenance gate forbids var(--x, <literal>) on token-bound sites (deliberate departure from this file's fallback convention). */
  ```
  Why it's wrong: The assembled diff contains two commits that both modify `Tabs.css`: Task 002 added inline "departure from this file's fallback convention" comments at lines 149 and 233; the F1-fix commit removed fallback literals from 6 additional sites — lines 97, 174, 183, 222, 326, and 388 — without any corresponding "departure" comment. The per-task reviewer of Task 002 could not see the F1-fix result (applied later), and the per-task reviewer of the F1 fix would see the file-header claim ("Every var() call includes a defensive fallback literal") was stale, but would not naturally connect it to Task 002's inline "convention" framing. Read assembled, lines 149/233's "deliberate departure from this file's fallback convention" now implies those two sites are the only exceptions, while the six F1-fix-modified sites (97, 174, 183, 222, 326, 388) also lack fallbacks and have no comment to indicate their departure. The file-level header comment (lines 5–7) still states the convention; it is now incorrect for 8 sites. No functional defect results — the tokens load reliably in both the app (tokens.css is always present) and the CT harness (playwright/index.tsx imports tokens.css globally) — but the assembled comment state will mislead a future developer who reads lines 149/233 as the exhaustive list of convention departures.
  Remediation: Update the two inline comments at lines 149 and 233 to say "deliberately no fallback literal (design-token provenance gate requirement; note: the muted/faint sites — inactive label, disabled text, close icon, dirty dot — also omit fallbacks after the F1 contrast fix)" and update the file-level header comment (lines 5–7) to reflect that several token-bound sites intentionally omit the defensive fallback. Alternatively, add a brief "no fallback — per F1 contrast fix" comment to each of the six muted/faint bare-ref sites so the rationale is uniform across all departures.


## Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 1
- Confirmed: 1 | Contested: 0 | Dismissed: 0 | Uncertain: 0
- Finders skipped (not installed): none

## Methodology
Findings are grounded — every finding carries a verbatim quote from the actual
cross-task code, and validation discards ungrounded ones. A refutation stage
then cross-examines each grounded finding before it reaches the report: a
finding earns the headline only by surviving an adversary who default-dismisses
anything not demonstrable as emergent at feature scope. Confirmed findings reach
the headline; dismissed findings and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; contested findings (a high-stakes `security`
/ `[CONSTITUTION-VIOLATION]` finding the refuter could not confirm, or a
`[CONSTITUTION-VIOLATION]` finding the refuter dismissed) are surfaced in the
headline, flagged `[CONTESTED]`, never buried. This report is findings only —
the verdict is `/verify`'s.
