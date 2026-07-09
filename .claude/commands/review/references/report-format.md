# Feature review report format

This is the skeleton the `review_helper render-report` verb produces and writes
to `specs/[feature]/review.md`. The helper owns the actual render
(`src/devforge/lib/_review/_report.py`); this file is orientation only — it
documents the shape so the orchestrator knows what the report will contain. Do
not hand-author the report; call `render-report`.

## Findings only — NO verdict

This report is FINDINGS ONLY. `/review` does not render a verdict. The verdict
is `/verify`'s job: `/review` produces `specs/[feature]/review.md`, and `/verify`
consumes it (folding its findings into the verdict, and warning if it is
missing). Do not add a pass/fail line, an approval line, or a "ready to ship"
judgment — the report ends at the findings.

## Layout + finding partition rule

The report surfaces the findings that survived the refutation pass, partitioned
by what the cross-examination concluded:

1. **CONFIRMED findings are the headline** — the findings the refuter could
   demonstrate, from quoted cross-task code, are a genuine emergent defect.
   These lead the report: a short priority list (force-ranked, fix these first)
   plus a grouped listing (by file, or by Category) of every confirmed finding.
2. **High-stakes `[CONTESTED]` findings are surfaced IN the headline, flagged —
   never buried.** Two paths route a finding here. (a) A high-stakes finding the
   refuter could NOT confirm (a `security` finding, or any finding carrying the
   `[CONSTITUTION-VIOLATION]` tag, that the refuter left uncertain) is too
   high-stakes to drop to an appendix. (b) A `[CONSTITUTION-VIOLATION]` finding
   the refuter explicitly DISMISSED also lands here, not in the Dismissed
   appendix — the constitution carve-out: a dismissed constitution violation is
   too important to bury, so the dismissal is surfaced for a human to
   adjudicate rather than hidden. Either path appears in the headline tagged
   `[CONTESTED]`. A missed cross-task security hole or a wrongly-dismissed
   constitution violation is more costly than a false alarm, so the tie goes to
   surfacing.
3. **Dismissed + low-stakes uncertain findings go to an appendix** — the
   `## Dismissed / Worth a Glance` section. Dismissed findings (the refuter
   showed they are not emergent at feature scope, or are a single-task concern
   the per-task panel already owned) are not deleted, because a dismissal is
   itself a judgment that can be wrong. Low-stakes uncertain findings (a
   non-high-stakes finding the refuter could not decide from the code) ride here
   too. Clearly separated from the headline.

The category is producer-declared — each finder sets the `Category:` field on
every finding (see `.claude/commands/review/references/emergent-issue-checklist.md` and the output
contract). The renderer groups by that declared value; it never infers a
category from which finder produced the finding.

Finding tags: `[CROSS-AGENT]` (raised by ≥2 finders), `[CONSTITUTION-VIOLATION]`
(always Critical), and `[CONTESTED]` (one of two cases — a high-stakes `security`
/ `[CONSTITUTION-VIOLATION]` finding the refutation stage could NOT confirm, OR a
`[CONSTITUTION-VIOLATION]` finding the refutation stage DISMISSED; both are
surfaced in the headline, never buried).

## Skeleton

```markdown
# Feature Review — [feature] — YYYY-MM-DD

**Feature**: specs/[feature]
**Scope**: assembled feature diff (all tasks together) — [N files]
**Finders invoked**: [list, with "skipped (not installed)" for missing]
**Refuters invoked**: [list]
**Source Root**: [from CLAUDE.md]
**Framework / Language**: [from CLAUDE.md]

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
1. [severity] [file:line] — [one-line description] [confidence] [tags]
...

## Confirmed Findings
(Grouped by file — each file with findings gets one `### <file path>` section,
files ordered by path; within a file, findings grouped by `#### <category>` and
sorted by severity Critical → Info. High-stakes `[CONTESTED]` findings appear
here too, flagged.)

### [relative/path/to/FileA.ext]

#### Security
- [F-001] [Critical] :42 — [description]
  Severity: Critical
  File: [relative/path/to/FileA.ext]
  Line: 42
  Pattern: [the matched cross-task pattern, one line]
  Confidence: Certain | Likely | Speculative
  Category: security
  Evidence:
  ```
  [one verbatim snippet copied from the anchor file named in File: above —
  the defect site of the interaction; a verbatim substring of that file]
  ```
  Why it's wrong: [the cross-task interaction that makes it a defect — name the
  partner file by path and line here, e.g. "the auth boundary in src/auth.py:42
  is bypassed by this path"; the partner is referenced in prose, not quoted]
  Remediation: [specific fix]
- [F-007] [High] :88 — [description]
  [same finding format]

#### System Design
[same finding format — findings tagged Category: system_design]

#### Duplication
[same finding format — Category: duplication]

#### Best Practices
[same finding format — Category: best_practice]

### [relative/path/to/FileB.ext]
[same `#### <category>` sub-sections, only the non-empty ones]

## Summary
- Critical: N | High: N | Medium: N | Info: N
- Confirmed: N | Contested: N | Dismissed: N | Uncertain: N
- Finders skipped (not installed): [list]

## Dismissed / Worth a Glance
(Findings the refutation stage knocked out of the headline — not deleted,
because a dismissal is itself a judgment that can be wrong. Clearly separated
from the headline above; the whole section is omitted when both lists are
empty.)

### Dismissed
- [Medium] [relative/path/to/File.ext]:NN — [description]
  Why dismissed: [the counter-quote / single-task scope that makes the finding
  not emergent at feature scope, when one exists]

### Uncertain (low-stakes)
- [Info] [relative/path/to/File.ext]:NN — [description]
  Unresolved: [what the refuter could not decide from the code]

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
```

## Optional `## Design Fidelity` section

The report carries an OPTIONAL `## Design Fidelity` section — present ONLY when
`design-auditor` was dispatched for the runtime design-fidelity check (`/review`
PHASE 2.5, which fires only when the feature has a `design/reference.html` and a
valid `specs/[feature]/design-manifest.json` binding). `render-report
--design-section` appends it AFTER `## Methodology` — as the last section when
no `## Accessibility` section is also present, or immediately before
`## Accessibility` when PHASE 2.5b also ran (see the `## Optional Accessibility
section` block below for the ordering) — embedding the agent's fidelity output
VERBATIM. It sits ENTIRELY OUTSIDE the
refutation partition: it is never parsed into findings, never counted in any
confirmed / dismissed / contested / uncertain bucket, and never included in any
headline or `## Summary` total — a deterministic probe measurement is not a
hypothesis to cross-examine. When PHASE 2.5 is skipped the `--design-section`
flag is omitted and the section is absent; `review.md` then renders exactly as it
would without the design-fidelity check.

```markdown
## Design Fidelity
Coverage: NOT-COVERED / CLEAN / DEFECT — state which, and why.

| Kind | Selector | Property/Axis | Expected | Actual | Severity |
|------|----------|---------------|----------|--------|----------|
| [overflow/clip/font_not_loaded/value_mismatch/geometry_mismatch] | [built testid or anchor selector] | [property/axis] | [expected] | [actual] | Critical/High/Medium/Info |

### Advisory (non-gating)
[holistic "looks wrong" notes from a visual pass over screenshots, or "none"]
```

## Optional `## Accessibility` section

The report carries an OPTIONAL `## Accessibility` section — present ONLY when
`design-auditor` was dispatched for the accessibility / responsive / native
audit (`/review` PHASE 2.5b, which fires when the feature touches UI, as
determined by the recall-biased `resolve-ui-scope` verb). It is ORTHOGONAL to
the `## Design Fidelity` section: 2.5 fires on a design reference + binding,
2.5b fires on any UI-touching feature, so a feature can carry one section, both,
or neither. `render-report --a11y-section` appends it AFTER `## Methodology` and
AFTER any `## Design Fidelity` section — so when both ran, Design Fidelity comes
first, then Accessibility. It sits ENTIRELY OUTSIDE the refutation partition: it
is never parsed into findings, never counted in any confirmed / dismissed /
contested / uncertain bucket, and never included in any headline or `## Summary`
total — a deterministic probe measurement is not a hypothesis to cross-examine.
When PHASE 2.5b is skipped the `--a11y-section` flag is omitted and the section
is absent; `review.md` then renders exactly as it would without the
accessibility check.

The agent writes ONLY the section body — a `Coverage:` line (present only on
NOT-COVERED, when Chrome MCP is unavailable or the platform is non-web/non-mobile)
followed by the `### Accessibility` / `### Responsive` / (mobile only) `### Native`
tables it emits — using `###` or deeper so it nests under the `## Accessibility`
heading `render-report` supplies. There is no `### Verdict` line (the verdict is
`/verify`'s).

```markdown
## Accessibility
Coverage: NOT-COVERED — [reason]   (this line present ONLY on NOT-COVERED)

### Accessibility
| Check | Element/Selector | Expected | Actual | Severity |
|-------|------------------|----------|--------|----------|
| [semantic HTML / ARIA / keyboard / contrast / alt-text / live-region] | [selector] | [expected] | [actual] | Critical/High/Medium/Info |

### Responsive
| Breakpoint | Issue | Detail | Severity |
|------------|-------|--------|----------|
| [320/768/1024/1440] | [overflow / touch-target / readability / scaling] | [detail] | Critical/High/Medium/Info |

### Native
(mobile targets only — omitted for web)
| Convention | Element | Expected | Actual | Severity |
|------------|---------|----------|--------|----------|
| [HIG / Material / safe-area / nav-pattern / touch-target] | [element] | [expected] | [actual] | Critical/High/Medium/Info |
```
