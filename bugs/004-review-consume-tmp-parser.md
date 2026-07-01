# Bug 004: review consume-tmp parser drops findings on field-label format variants

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-29
**Fixed**:

## Description

review_helper consume-tmp parses 0 findings when a finder/refuter writes its ## Finding N fields with dash-bullet labels ('- Severity:'), bold-markdown labels ('**Severity**:'), or when validate-findings receives a backtick-wrapped File path (e.g. `src/.../RequestBar.css`, reported as file_missing). Observed across three /review rounds on feature 010-request-bar-fidelity: qa-reviewer (dash bullets) and design-auditor (bold labels + backtick paths) each had real, confirmed findings silently dropped to 0 until the orchestrator manually normalized the tmp files before re-running consume-tmp / validate-findings. Impact: without manual intervention /review renders a false findings-empty report, which /verify would then fold into a wrongly-APPROVED verdict. Fix direction: harden consume-tmp's ## Finding N field regex to tolerate leading '- ', surrounding '**...**', and strip surrounding backticks from the File value (and ideally normalize Evidence) before the anti-hallucination grounding check. Related project memory: review-finder-dash-prefix-parse.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File                        | Detail |
| --------------------------- | ------ |
| .devforge/lib/review_helper |        |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
