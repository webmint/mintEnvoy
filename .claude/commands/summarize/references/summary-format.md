# summary.md artifact shape

This documents the shape of `specs/[feature]/summary.md`, the artifact `/summarize` writes (PHASE 4). Unlike `/verify`'s report, there is **no `render-report` helper verb** — the orchestrator composes the summary INLINE in PHASE 3 (agent-free, D1) and writes it with the Write tool. This file is **orientation only**, documenting the shape so the orchestrator knows what to produce. Do not treat it as a verbatim fill-in template — the synthesis is human-facing prose, not a mechanical substitution.

## Findings-free + verdict-free — UNLIKE /verify

This summary contains NO verdict and NO findings. `/verify` owns the verdict (APPROVED / NEEDS WORK / REJECTED); `/review` owns findings. `/summarize` owns the PR-ready narrative. The summary may REFERENCE the verdict `/verify` already rendered (read from `verification.md`), but it never computes or renders one. Do not add a verdict line, a findings list, or a refutation pass — those belong to `/verify` and `/review`.

## Inputs that shape the summary

The orchestrator composes the summary from four scratch inputs captured during the run (see `main.md` PHASE 1–2):

1. **The change data** (`gather-change-data` → `$WORKDIR/changes.json`) — `files`, `file_count`, `scope_block`, `by_directory`, `insertions`, `deletions`, `stat_summary`, and `source_changes` (non-null in wrapper mode). Drives the Files-changed section.
2. **The verification report** (`read-verification` → `$WORKDIR/verification.json`) — `ac_list` (one dict per AC with `id`, `status`, `evidence`) and `verdict`. The `ac_list` status is AUTHORITATIVE — it drives the Acceptance-criteria section and is never re-derived from the spec (D3).
3. **The task completion notes** (`parse-completion-notes` → `$WORKDIR/notes.json`) — a JSON array, one dict per task (`files_changed`, `notes`, `completed_at`, …). Drives the Changes section and the Deviations section.
4. **The plan decisions** (`read-plan-decisions` → `$WORKDIR/decisions.json`) — `decisions` (one dict per decision with `decision`, `chosen`, `rationale`, `rejected`). Drives the Key-decisions section.

## Skeleton

```markdown
## Feature Summary: [NNN — feature name]

### What was built

[2-3 sentences in user terms, synthesized from the spec overview + the plan.
Focus on what the user gets, not implementation details.]

### Changes

[One line per task, in user terms — what it accomplished, not the raw files:]

- [Task title] — [1-line what it did]
- ...

### Files changed

[Grouped by directory/area from changes.json's by_directory, with counts:]

- `src/components/` — N file(s)
- `src/utils/` — N file(s)
- `tests/` — N file(s)
  [Total: X files changed, Y insertions, Z deletions]

(In wrapper mode, when changes.json.source_changes is non-null, add a parallel
"Source repo changes" grouping for the code repo alongside the wrapper-side
specs/docs changes.)

### Key decisions

[The most important decisions from decisions.json. One line each:]

- [Decision]: [what was chosen and why]
- ...

### Deviations from plan

[OMIT THIS WHOLE SECTION when no task noted a deviation — i.e. no task in
notes.json has a non-empty `notes`. When present, one line per deviating task:]

- [Task title]: [what deviated and why]
- ...

### Acceptance criteria

[Compact checklist. Each AC's status is taken VERBATIM from verification.json's
ac_list (NOT re-derived from the spec). A passed AC ticks `- [x]`; a non-passed
AC is left `- [ ]` and annotated with its status:]

- [x] AC-1: [short label]
- [ ] AC-2: [short label] — PARTIAL

(When verification.md is absent — the read-verification missing-fallback in PHASE
2.1 — replace this section with: "_No verification report found — run `/verify`
to populate AC status._")
```

## Composition rules (so the summary reads correctly)

- **Concise** — each section targets 1-5 lines; the summary is a 1-page narrative, not a report.
- **User-facing** — behavior and outcomes, not implementation mechanics.
- **Deduplicate** — group files by area in Files changed rather than listing each.
- **Omit empty sections** — the Deviations section is omitted entirely when no task deviated.
- **AC status is authoritative** — taken from `verification.md`, never re-derived from the spec (D3).
- **No verdict, no findings** — `/summarize` narrates; it does not verify or judge.
