# Feature Review — specs/018-code-editor-extract — 2026-07-19

**Feature**: specs/018-code-editor-extract
**Scope**: assembled feature diff (all tasks together) — 31 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst
**Refuters invoked**: architect
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
(no confirmed findings)

## Confirmed Findings
(none)

## Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 0
- Confirmed: 0 | Contested: 0 | Dismissed: 1 | Uncertain: 0
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable emergent defect at feature scope; uncertain findings could not be resolved from the code alone. A reviewer may want to glance at them before closing the review.

### Dismissed
- [D-001] [Medium] src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx:489 — Cross-task duplication — two tasks each added an identical module-scope scroll-body constant that should be unified

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

## Design Fidelity

Coverage: CLEAN (carried forward from the prior /review pass's live design-auditor run — the three /fix commits touched ONLY test files + comments + one static aria attribute; zero production CSS/geometry change, so the runtime fidelity result is unchanged).

All three manifest pairs (body-code-editor / body-gutter / body-pre) matched every computed-style axis against design/reference.html on the prior live run (grid 36px 1fr, --code-line-h 20.625px on gutter/pre/textarea, tk-* token colors, spacing, min-height). Gutter aria-hidden confirmed in the DOM.

Deferred (pre-existing feature-017, not 018 defects): textarea does not auto-resize to content height (~41px vs full pre extent) — lines 3+ miss the textarea hit area. Fix = min-height:100% or JS auto-resize.

## Accessibility

Coverage: CARRIED FORWARD — the three /fix commits touched ONLY test files + one static aria-hidden attribute, so the accessibility result is unchanged from the prior live pass.

### Accessibility
| Check | Severity | Status | Details |
|-------|----------|--------|---------|
| Gutter line numbers in a11y tree | Critical | Resolved (this feature) | aria-hidden="true" on the .gutter div (confirmed in live DOM). |
| textarea accessible name / pre aria-hidden / keyboard | Info | Pass | aria-label "Request body"; decorative pre hidden; roving-tabIndex radiogroup; no trap. |
| Focus ring contrast (2.4.11) | Medium | Fail (pre-existing 017, deferred) | var(--accent) #10b981 on light bg = 2.43:1 (< 3:1). Dark passes. |
| tk-var / tk-var.missing contrast (light) | Critical | Fail (pre-existing 017, deferred) | 2.43:1 / 3.61:1 (< 4.5:1). Extraction preserved the tokens. |
| Core syntax tokens + dark theme | Info | Pass | All ≥ 4.5:1 (light core) / ≥ 4.6:1 (dark). |

### Responsive
| Item | Severity | Status | Details |
|------|----------|--------|---------|
| 720px Electron min | Info | Pass | toolbar flex-wrap; 36px 1fr grid adapts. |
| Textarea height coverage | High | Fail (deferred, 017) | textarea ~41px vs full pre extent — lines 3+ unclickable. Pre-existing. |
