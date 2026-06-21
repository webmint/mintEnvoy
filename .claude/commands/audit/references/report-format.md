# Audit report format

This is the skeleton the `audit_helper render-report` verb produces and writes to `audits/YYYY-MM-DD-audit.md`. It is **orientation only** — the helper owns the actual render (`src/devforge/lib/_audit/_report.py`); this file documents the shape so the orchestrator knows what the report contains. Do not hand-author the report; call `render-report`.

## Layout + finding bucketing rule

The body is organized **by file** (`## Findings by File`): each audited file with findings gets one `### <file path>` section, files ordered by path (so files in the same directory group together). Within a file, findings are grouped into `#### <category>` sub-sections, and within each sub-section sorted by severity (Critical → Info). Severity is shown inline on every finding line (there is no per-severity section header — `## Top 10 Priorities` carries the cross-cutting severity ranking).

Each finding's `####` sub-section is chosen by this priority:

1. `[CONSTITUTION-VIOLATION]` tag → **Constitution Violations** (a cross-cutting override; it wins regardless of the finding's declared category — a `system_design` finding tagged constitution lands here, not in System Design).
2. Otherwise the finding's declared `Category` maps to its sub-section: `system_design` → **System Design**, `best_practice` → **Best Practices**, `duplication` → **Duplication**, `security` → **Security**, `mislogic` → **Mislogic**.
3. A missing or unrecognized category defaults to **Mislogic**. (`blind_spot` findings share the Mislogic display bucket here; the dedicated `## Logic Blind Spots` section below is sourced separately from the qa-reviewer pass.)

The category is producer-declared — each agent sets the `Category:` field on every finding (see `.claude/commands/audit/references/adversarial-preamble.md` and the output contract). The renderer buckets by that declared value; it never infers a category from which agent produced the finding.

Empty sub-sections and files with no findings are omitted entirely; the `## Summary` section always renders.

Finding tags: `[CROSS-AGENT]` (raised by ≥2 agents), `[RECURRING]` (matches an unresolved finding from a past `specs/*/review.md`), `[CONSTITUTION-VIOLATION]` (overrides the bucket as above), `[CONTESTED]` (a high-stakes `security` / `[CONSTITUTION-VIOLATION]` finding the refutation stage could not confirm — surfaced in the headline, never buried in the appendix), and — only on multi-pass runs (`--passes >= 2`) — `[MULTI-PASS:k]` on a finding corroborated across `k` (≥2) of the run's passes.

A finding line carries a trailing `(raised by N)` annotation when `N` duplicate reports of the same `(file, line, category)` were deduplicated into it (omitted when `N == 1`); it appears on both `## Top 10 Priorities` entries and `## Findings by File` finding lines.

The `## Top 10 Priorities` and `## Findings by File` sections draw from CONFIRMED findings plus high-stakes `[CONTESTED]` findings only — the refutation stage's headline set (Phase 4.2.5). Dismissed findings and low-stakes uncertain findings are NOT shown there; they render in the `## Dismissed / Worth a Glance` appendix below.

## Skeleton

```markdown
# Audit Report — YYYY-MM-DD

**Scope**: [full / uncommitted / path]
**Files audited**: [count]
**Agents invoked**: [list, with "skipped (not installed)" for missing]
**Recurring-issue reviews consulted**: [list of specs/*/review.md, or "none"]
**Source Root**: [from CLAUDE.md]
**Framework / Language**: [from CLAUDE.md]

## Top 10 Priorities
Force-ranked across all buckets. Fix these first.
1. [severity] [file:line] — [one-line description] [confidence] [tags]
...

## Findings by File

### [relative/path/to/FileA.ext]

#### Mislogic
- [F-001] [Critical] :42 — [description]
  Evidence:
  ```
  [verbatim quoted code/comment]
  ```
  Why it's wrong: [the contradiction]
  Remediation: [specific fix]
  Confidence: Certain | Likely | Speculative
  Tags: [CROSS-AGENT] [RECURRING] [CONSTITUTION-VIOLATION] [CONTESTED] [MULTI-PASS:k]
- [F-014] [High] :88 — [description]
  [same finding format]

#### System Design
[same finding format — findings tagged Category: system_design]

#### Best Practices
[same finding format — Category: best_practice]

#### Duplication
[same finding format — Category: duplication]

#### Security
[same finding format — Category: security]

#### Constitution Violations
[same finding format — any finding with the [CONSTITUTION-VIOLATION] tag; always Critical]

### [relative/path/to/FileB.ext]
[same `#### <category>` sub-sections, only the non-empty ones]

## Logic Blind Spots (Untested Branches)
[from qa-reviewer]

## Recurring Issues Status
| Past Review | Finding | Status |
|---|---|---|
| specs/003-foo/review.md | Null check bypass in X | STILL PRESENT, SPREAD TO 4 FILES |
| specs/005-bar/review.md | Race condition in Y | RESOLVED |

## Next Candidates (Hotspot)
(Hotspot mode only.) Files ranked just outside the top hotspots — consider for next run.
1. [file] · score=0.NN · (churn=N, callers=N, size=N)
...

## Not Audited
- Runtime behavior (no dynamic analysis)
- Dependency CVEs (run `npm audit` / `pip audit` separately)
- Runtime performance profiling (out of scope — use /review); static performance-idiom smells are in scope
- UI/design consistency (out of scope)
- Infrastructure / deployment config

## Summary
- Critical: N | High: N | Medium: N | Info: N
- Confirmed: N | Contested: N | Dismissed: N | Uncertain: N
- Passes run: N | Multi-pass-confirmed findings: <count>   (only when the resolved `passes >= 2`; omitted when `passes == 1`. Count = findings with `pass_count >= 2`.)
- Cross-agent consensus findings: N
- Recurring (unresolved): N
- Agents skipped (not installed): [list]
- Agents failed (ran but errored): [list with reasons]
- **Findings discarded by validation**: N total
  - Failed file-exists check: N
  - Failed line-number sanity: N
  - Failed verbatim-quote check: N (likely hallucination)
  - Failed evidence-non-empty check: N
  - Failed pattern-field check: N

## Dismissed / Worth a Glance
(Findings the refutation stage knocked out of the headline — not deleted, because a dismissal is itself a judgment that can be wrong. Clearly separated from the headline above; the whole section is omitted when both lists are empty.)

### Dismissed
- [Medium] [relative/path/to/File.ext]:NN — [description]
  Why dismissed: [the counter-quote / code path that makes the finding wrong, when one exists]

### Uncertain (low-stakes)
- [Info] [relative/path/to/File.ext]:NN — [description]
  Unresolved: [what the refuter could not decide from the code]

## Methodology
Findings are grounded — every finding carries a verbatim quote from the actual
code, and Phase 4 validation discards ungrounded ones. A refutation stage then
cross-examines each grounded finding before ranking: a finding earns its place
only by surviving an adversary. Confirmed findings reach the headline; dismissed
findings and low-stakes uncertain findings drop to the Dismissed / Worth a Glance
appendix; high-stakes contested findings (`security` / `[CONSTITUTION-VIOLATION]`
the refuter could not confirm) are surfaced in the headline, flagged
`[CONTESTED]`, never buried. Confidence tiers indicate certainty; "Speculative"
findings are hypotheses, not verdicts.

If "Failed verbatim-quote check" count is high (>5), the agents are
hallucinating evidence — review the agent prompts for tone drift.
```
