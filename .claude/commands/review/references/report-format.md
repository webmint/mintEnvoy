# Feature review report format

This is the skeleton that the `review_helper render-report` verb WILL produce
and write to `specs/[feature]/review.md` once Phase 5 builds it. **Neither the
`render-report` verb nor its render module (`src/devforge/lib/_review/_report.py`)
exists yet** — Phase 5 registers the verb and creates the module; until then
this file is **orientation only**, documenting the shape so the orchestrator
knows what the report will contain. Once Phase 5 lands, the helper owns the
actual render: do not hand-author the report; call `render-report`.

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
