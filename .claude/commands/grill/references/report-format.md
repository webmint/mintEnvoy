# Plan-grill report layout

This is the skeleton the `grill_helper render-report` verb produces and writes to
`specs/[feature]/grill.md`. It is **orientation only** — the helper owns the
actual render (`src/devforge/lib/_grill/_report.py`); this file documents the
shape so the orchestrator knows what the report contains. Do not hand-author the
report; call `render-report`.

## Findings PLUS a recommended disposition

Unlike `/review` (findings only, because `/verify` owns its verdict downstream),
`/grill` carries a LIGHT recommended **disposition** — there is no downstream
design-`/verify` to own it. The disposition is one of four: PROCEED / REVISE-PLAN
/ RE-ENTER-UPSTREAM / KILL. It is a RECOMMENDATION — the human makes the final
call at the existing `/breakdown` approval gate. The disposition (verdict +
rationale, and for RE-ENTER-UPSTREAM the target stage) is computed by the
orchestrator's PHASE 5 CLASSIFY reasoning and passed to `render-report` via
`--disposition` / `--rationale` / `--re-entry-target`; this helper RENDERS the
disposition, it does not decide it.

## Layout + finding partition rule

The report surfaces the findings that survived the refutation pass, partitioned by
what the cross-examination concluded:

1. **CONFIRMED findings are the headline** — the findings the refuter could
   demonstrate, from quoted design / spec / code / constitution / web-citation
   evidence, are a genuine design defect. These lead the report: a short
   force-ranked priority list (fix these first) plus a grouped listing (by file,
   then by Category) of every confirmed finding.
2. **High-stakes `[CONTESTED]` findings are surfaced IN the headline, flagged —
   never buried.** Two paths route a finding here. (a) A high-stakes finding the
   refuter could NOT confirm (a `security` finding, or any finding carrying the
   `[CONSTITUTION-VIOLATION]` tag, that the refuter left uncertain) is too
   high-stakes to drop to an appendix. (b) A `[CONSTITUTION-VIOLATION]` finding the
   refuter explicitly DISMISSED also lands here, not in the Dismissed appendix —
   the constitution carve-out: a dismissed constitution violation is too important
   to bury, so the dismissal is surfaced for a human to adjudicate. Either path
   appears in the headline tagged `[CONTESTED]`. A missed design-time security
   hole or a wrongly-dismissed constitution violation is more costly than a false
   alarm, so the tie goes to surfacing.
3. **Dismissed + low-stakes uncertain findings go to an appendix** — the
   `## Dismissed / Worth a Glance` section. Dismissed findings (the refuter showed
   they are not a demonstrable design defect, or are relitigation of a settled
   decision) are not deleted, because a dismissal is itself a judgment that can be
   wrong. Low-stakes uncertain findings ride here too. Clearly separated from the
   headline.

The category is producer-declared — the adversary sets the `Category:` field on
every finding (see `.claude/commands/grill/references/design-attack-checklist.md` and the output
contract). The renderer groups by that declared value; it never infers a category
from which agent produced the finding.

Finding tags: `[CROSS-AGENT]` (raised by ≥2 finders — rare for `/grill`, which
dispatches a single `devils-advocate` finder), `[CONSTITUTION-VIOLATION]` (always
Critical), and `[CONTESTED]` (a high-stakes `security` / `[CONSTITUTION-VIOLATION]`
finding the refutation stage could NOT confirm, OR a `[CONSTITUTION-VIOLATION]`
finding it DISMISSED; both are surfaced in the headline, never buried).

## Skeleton

```markdown
# Plan Grill — [feature] — YYYY-MM-DD

**Feature**: specs/[feature]
**Scope**: plan.md + referenced specs — [N files]
**Finders invoked**: [list, with "skipped — not installed" for missing]
**Refuters invoked**: [list]
**Source Root**: [from CLAUDE.md]
**Framework / Language**: [from CLAUDE.md]

## Disposition

**Verdict**: PROCEED | REVISE-PLAN | RE-ENTER-UPSTREAM (target: `spec` | `discovery` | `research`) | KILL

**Rationale**:

[the orchestrator's CLASSIFY rationale — why this disposition]

> [verdict-specific guidance — the helper renders one of:]
>
> - PROCEED — the grill attack found no disqualifying plan-level defect; the plan is sound to execute (run `/breakdown`).
> - REVISE-PLAN — the defects are real but correctable at the plan level; revise `plan.md`, then re-run (re-`/plan` / hand-patch, optionally re-`/grill`).
> - RE-ENTER-UPSTREAM — the defect is rooted upstream; re-enter at the named stage (`/specify` for `spec`, `/discover` for `discovery`, `/research` for `research`) with the emitted `grill-seed.json` so the re-run is directed, not a repeat.
> - KILL — the defect is fundamental; the plan should be abandoned (re-`/plan` with a wholly different approach).

## Confirmed — Top Priorities

Force-ranked across the confirmed findings. Fix these first.

1. [severity] [file:line] — [one-line description] [confidence] [tags]
   ...

## Confirmed Findings

(Grouped by file — each file with findings gets one `### <file path>` section,
files ordered by path; within a file, findings grouped by `#### <category>` and
sorted by severity Critical → Info. High-stakes `[CONTESTED]` findings appear here
too, flagged.)

### [plan.md OR relative/path/to/source.ext]

#### Security

- [F-001] [Critical] :42 — [description]
  Severity: Critical
  File: [plan.md or the anchor file named above]
  Line: 42
  Pattern: [the attack name, one line]
  Confidence: Certain | Likely | Speculative
  Category: security
  Evidence:
```

[one verbatim snippet copied from the anchor file named in File: above]

```
Why it's wrong: [the design defect this instance triggers — name any partner
artifact by path and line here, e.g. "duplicates the existing helper in
src/util/foo.py:12"; the partner is referenced in prose, not quoted]
Remediation: [specific design change]
- [F-007] [High] :88 — [description]
[same finding format]

#### System Design
[same finding format — Category: system_design]

#### Best Practices
[same finding format — Category: best_practice]

#### Mislogic
[same finding format — Category: mislogic; blind_spot findings share this bucket]

#### Duplication
[same finding format — Category: duplication]

#### Constitution Violations
[same finding format — any finding with the [CONSTITUTION-VIOLATION] tag; always Critical]

### [relative/path/to/FileB.ext]
[same `#### <category>` sub-sections, only the non-empty ones]

## Summary
- Critical: N | High: N | Medium: N | Info: N
- Confirmed: N | Contested: N | Dismissed: N | Uncertain: N
- Disposition: PROCEED | REVISE-PLAN | RE-ENTER-UPSTREAM | KILL
- Finders skipped (not installed): [list]

## Dismissed / Worth a Glance
(Findings the refutation stage knocked out of the headline — not deleted, because
a dismissal is itself a judgment that can be wrong. Clearly separated from the
headline above; the whole section is omitted when both lists are empty.)

### Dismissed
- [D-001] [Medium] [plan.md]:NN — [description]

### Uncertain (low-stakes)
- [U-001] [Info] [plan.md]:NN — [description]

## Methodology
Findings are grounded — every finding carries a verbatim quote from the actual
plan/spec/research artefacts (or a re-fetchable external citation for a web
claim). A refutation stage then cross-examines each grounded finding before it
reaches the report: a finding earns the headline only by surviving an adversary
who default-dismisses anything not demonstrable as a real plan-level defect.
Confirmed findings reach the headline; dismissed findings and low-stakes uncertain
findings drop to the Dismissed / Worth a Glance appendix; high-stakes `[CONTESTED]`
findings (a `security` / `[CONSTITUTION-VIOLATION]` finding the refuter could not
confirm) are surfaced in the headline, flagged `[CONTESTED]`, never buried.
```

## The re-entry seed (RE-ENTER-UPSTREAM only)

When and only when the disposition is RE-ENTER-UPSTREAM, the orchestrator ALSO
calls `grill_helper write-seed`, which writes `specs/[feature]/grill-seed.json` —
the structured backward handoff the named upstream command (`/specify`,
`/discover`, or `/research`) consumes on re-entry so the re-run is DIRECTED, not a
repeat. The seed is NOT part of `grill.md`; it is a sibling JSON artifact. It
carries `target_stage` (`spec` | `discovery` | `research`), `prior_conclusion`
(what the upstream stage concluded that is now invalidated), `invalidating_evidence`
(the grounded grill finding that invalidates it), `must_satisfy` (what the re-run
must additionally satisfy), `cycle_count` (the bounded-compounding-loop counter),
`carried_findings` (prior findings carried forward, monotonic), and `provenance`
(a pointer to this `grill.md` / the plan). The schema is owned by
`src/devforge/lib/_grill/seed_schema.py` (`ReEntrySeed`); the helper validates and
atomically writes it — do not hand-author the seed.
