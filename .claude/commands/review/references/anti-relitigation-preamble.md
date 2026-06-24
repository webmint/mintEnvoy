=== EMERGENT CROSS-TASK REVIEW — SCOPE DISCIPLINE ===

Every task in this feature was ALREADY reviewed in isolation before it
reached you. `/implement` runs a per-task review PANEL of four read-only
reviewers — code-reviewer, qa-reviewer, security-reviewer, and
performance-analyst — over each task's own diff, merged to a single verdict,
behind an all-findings-fixed gate: a task is approved ONLY from a fully-clean
panel, with every finding fixed and no unresolved finding or conflict
remaining. So per-task code quality, security depth, test adequacy, and
performance ON EACH TASK'S OWN DIFF are already handled. Those reviewers
already had their shot at every line inside any single task.

YOUR JOB IS NARROW. Report ONLY issues that EMERGE from the INTERACTION of
MULTIPLE tasks — defects that are invisible when you look at any one task's
diff in isolation, and that only appear once the tasks are ASSEMBLED into the
full feature. You are looking at the assembled feature diff (every task's
changes together) precisely because that composed surface is the one thing the
per-task panel structurally never saw — it never reviews two tasks' diffs at
once.

THE OUT-OF-SCOPE RULE:
- If a finding is fully contained within ONE task's changes, it is OUT OF
  SCOPE. The per-task panel already owned it and forced it clean. Do not
  re-flag it.
- If a finding requires reading TWO OR MORE tasks' changes together to even
  state it — task A establishes something task B then breaks, or two tasks each
  add a copy that diverges, or a data flow that only N-pluses once the tasks
  compose — it is IN SCOPE. This is the work nothing else in the pipeline does.

THIS IS A BEHAVIORAL INSTRUCTION, NOT A MECHANICAL FILTER. There is no
persisted list of the per-task panel's findings to dedup against — `/implement`
drives each task's findings to clean and writes nothing to disk for this run to
compare with. So nothing here mechanically blocks a re-flag; the discipline is
yours. The downstream refutation pass will DISMISS any re-flag that cannot be
demonstrated as emergent at feature scope — a finding contained in a single
task cannot survive cross-examination here, because the refuter will see it is
a single-task concern the panel already owned. Do not waste a finding on
something one task already owns; spend every finding on the cross-task surface.

When in doubt, ask: "Could the per-task panel have seen this while reviewing
exactly one task's diff?" If yes, it is out of scope. If it takes two tasks
side by side to see it, it is yours.
