# Bug 004: review consume-tmp parser drops findings on field-label format variants

**Status**: Fixed
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-29
**Fixed**: 2026-07-01

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

Verified resolved (2026-07-01). The shared parser `.devforge/lib/_shared/_consume.py` now runs a fence-aware `_normalize_label_lines` pass at the top of `_parse_finding_block` (called at line 278). It rewrites decorated `## Finding N` label lines to canonical `Label: value` form before the existing field regexes run: `_RE_DECORATED_LABEL_LINE` tolerates leading indent, one optional list bullet (`- Severity:`), and surrounding bold (`**Severity**:` / `**Severity:**`); for the six single-line fields (Severity, File, Line, Pattern, Confidence, Category) `_strip_inline_code` strips surrounding backticks from the value (e.g. `` `src/.../RequestBar.css` `` → `src/.../RequestBar.css`). Fence-aware so evidence code bodies are never rewritten. Since `/review` consume-tmp and `/audit` share this parser, both label-format variants and backtick-wrapped File paths now parse instead of silently dropping to 0 findings.
