=== BEST-PRACTICES & SYSTEM-DESIGN CHECKLIST ===

In addition to the Mislogic Hunt Checklist, systematically hunt for these
patterns. These are EXAMPLES of what to look for, NOT a list of bugs you
should find. If the codebase has none of these patterns, report none.

Many examples below are tagged with a stack — `EXAMPLE (TS):`, `EXAMPLE (Vue):`,
`EXAMPLE (Python):`, `EXAMPLE (Go):`. Apply a stack-tagged example only if the
project under audit uses that stack. A Python or Go project simply reports none
of the TS/Vue examples, and vice versa. Match the generic pattern, then quote
the actual code that matches it.

Every finding from this checklist MUST set its `Category:` field. Each section
below states which Category its findings map to. The available Category values
are: mislogic | system_design | best_practice | duplication | security |
blind_spot. Use only these.


System design  (Category: system_design)
- Layering / dependency-direction violation — a presentation/UI layer reaching
  directly into the data/persistence layer, or an inner layer importing an
  outer one (dependency inversion the wrong way). Quote the offending import or
  call that crosses the boundary.
- SOLID-at-scale — a class/module/component with many unrelated
  responsibilities (a god component); a single unit that would have to change
  for several independent reasons.
- Low cohesion — business logic or data-access logic embedded inside a
  presentation/UI component that should only render. Quote the logic and the
  component it is trapped in.
- EXAMPLE (component frameworks — Vue/React/Angular/Svelte): prop-drilling
  through a pure pass-through wrapper — a wrapper that forwards N props/events to
  a child and adds no behavior of its own (objective cases only: it must
  demonstrably forward and nothing else). Quote the forwarding.


Language / framework best practices  (Category: best_practice)
- Type-safety suppression — a static safety mechanism silenced to bury a real
  defect instead of fixing it. The tell: the suppression makes a compiler or
  linter error disappear while the unsafe value still flows downstream. Quote
  BOTH the suppression AND the value it launders.
  - EXAMPLE (TS): `as any`, or a double-cast `x as unknown as T` /
    `x as never as T`, over a null/shape error.
  - EXAMPLE (TS): `@ts-ignore` / `@ts-expect-error` placed on a live error.
  - EXAMPLE (TS): a non-null assertion (`x!`) on a value the type system marks
    nullable.
  - EXAMPLE (Python): `# type: ignore` or a bare `cast(...)` hiding a real
    mismatch.
  - EXAMPLE (Go): an unchecked type assertion `x.(T)` (no comma-ok form), so a
    wrong type panics at runtime instead of being handled.
- Untyped boundary where a concrete type exists — a prop, parameter, field, or
  return declared as a permissive catch-all (`any`, `Object`, `object`, a bare
  `Array`/`list`/`dict`) when the producer already exports a precise type that
  could have been used. Quote the loose declaration and name the concrete type
  that exists.
- Framework reactivity / lifecycle misuse:
  - EXAMPLE (Vue/React): capturing a snapshot of a reactive source as a plain
    value, so later updates are lost (reactivity loss).
  - EXAMPLE (Vue): a watcher used where a computed/derived value is the correct
    tool.
  - EXAMPLE (Vue/React): a side effect performed inside a computed getter (a
    getter should be pure).
  - EXAMPLE (Vue/React): calling a composable/hook outside its required context
    (e.g. a composable invoked outside component setup, or a hook called
    conditionally).
  - EXAMPLE (any stack): a timer, subscription, listener, or other resource
    created without a matching cleanup/teardown.
- Perf-idiom smell — heavy computation (e.g. a `reduce`/`filter`/`map` chain,
  a sort, an object rebuild) run on every render inside a template or render
  path, where it should be a memoized/derived/cached value computed once. Quote
  the computation and the render path it sits in. (Runtime profiling is out of
  scope — this is the static idiom only.)


Duplication & divergence  (Category: duplication)
- Copy-pasted logic blocks — the same non-trivial logic appearing verbatim (or
  near-verbatim) in multiple places. Quote both occurrences.
- DIVERGED variant copies — the worst case: the same logic copied into N files
  where at least one copy has already drifted from the others. A fix must now
  land in N places and one of them is already wrong. Quote the copies and point
  out the drift.
- Repeated domain logic that belongs in a shared helper/layer (DRY) — the same
  domain rule open-coded in 3+ places, or already diverged. Quote the
  repetitions. (Two occurrences alone are not yet a DRY finding unless they have
  already diverged.)


Constitution-principle adherence  (Category: matches the violated dimension;
also add the [CONSTITUTION-VIOLATION] tag)
- Read the constitution rules provided in your brief (the orchestrator supplies
  constitution excerpts as brief context for this audit). For each named
  principle, hunt the code for a concrete violation of it and quote the code
  that breaks the principle. If no constitution rules are present in your brief,
  report none from this section.
- A constitution violation is BOTH a categorized finding AND a constitution
  violation: set `Category:` to whichever dimension the defect belongs to (for
  example a layering breach that the constitution forbids is
  `Category: system_design`), and ALSO add the [CONSTITUTION-VIOLATION] tag.
- Per the adversarial preamble, constitution violations are ALWAYS Critical and
  carry the [CONSTITUTION-VIOLATION] tag regardless of your confidence — never
  downgraded.


Judgment rule (mandatory)
A finding that is an OPINION or best-practice PREFERENCE rather than a
demonstrable defect MUST be marked Confidence `Likely` or `Speculative` — never
`Certain`. `Certain` is reserved for defects provable from the code alone (a
suppression over a real error, a layering import that demonstrably crosses the
boundary, a diverged copy). "This watcher should be a computed" or "this module
has too many responsibilities" is a judgment call: mark it `Likely` or
`Speculative`. The verbatim quote stops fabrication; the Confidence tier is what
keeps subjective best-practice findings honest.


For each finding from this checklist, state:
- Pattern matched
- Category (mislogic | system_design | best_practice | duplication | security |
  blind_spot — and add the [CONSTITUTION-VIOLATION] tag if a constitution
  principle is violated)
- Confidence (Certain | Likely | Speculative — see the Judgment rule above)
- Evidence (verbatim quoted code from the file)
- Why it's wrong
- Remediation
