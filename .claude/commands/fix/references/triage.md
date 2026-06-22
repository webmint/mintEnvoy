# /fix triage + scope-estimate

This file is read by the orchestrator at PHASE 1 of `/fix`. It is **decision guidance**, not a template the helper renders and not a brief injected into an agent — the orchestrator reads it to classify each working-list item and to decide whether to bounce to `/specify` (the D7 bounce). Apply it before calling `fix_helper resolve-scope`.

## What /fix may remediate vs what it may not

`/fix` exists to remediate a **defect** — code that is wrong against its own intent — with `/implement`'s gates, without re-running spec → plan → breakdown. It does NOT exist to change WHAT the feature does. The triage decision for every working-list item is binary:

| Class                             | Stays in `/fix`                | Examples                                                                                                                                                                                                                                                                                                                                                                           |
| --------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Defect repair**                 | yes                            | A logic bug; a missing/incorrect case in existing behavior; a contract violation (a function does not do what its callers/spec assume); a security hole in code that already exists; a leftover artifact (debug print, dead branch); a name/comment that lies about what the code does; a regression a cross-task interaction introduced. The fix makes EXISTING behavior correct. |
| **Feature / architecture change** | no — bounce to `/specify` (D7) | The fix would ADD behavior not in the spec; change a data model / schema; introduce or remove a dependency; restructure a layer or module boundary; change a public API contract; alter an architectural decision. The change grows or reshapes the feature, it does not correct it.                                                                                               |

The discriminator is **correctness vs. scope**: a defect repair restores the feature to what it was already supposed to do; a feature/architecture change moves the goalposts. If remediating the finding requires deciding something the spec never decided (a new behavior, a new contract, a new structure), it is out of scope for `/fix`.

## The D7 bounce — when to stop and recommend /specify

STOP and recommend `/specify` when ANY working-list item is a feature/architecture change rather than a defect repair. Surface the bounce to the user naming:

- WHICH item triggered the bounce (its `title`).
- WHY it is a scope change, not a defect repair (which row of the table above it falls under — e.g. "this adds a new validation rule the spec never specified" or "this changes the data model").
- That the right home is a fresh `/specify` → `/plan` → `/breakdown` cycle, because the change needs a spec decision + plan + atomic breakdown, not a gated in-place fix.

Do NOT partially remediate around a bounced item. `/fix` either remediates a working list of pure defect repairs, or it bounces.

### Mixed working lists

When the working list MIXES defect repairs with a scope change, surface the scope change as the bounce and let the USER decide:

- **Drop the scope change and re-run** — the user removes the scope-change finding from consideration and re-runs `/fix`; `/fix` then remediates the defect-only remainder.
- **Take the whole set through `/specify`** — when the defects are entangled with the scope change (fixing the defect only makes sense alongside the new behavior), the whole set goes through the full chain.

`/fix` does not silently drop the scope item and proceed — the user owns that call.

## Scope-estimate sizing (informational)

After classifying every item as a defect repair, the touched-file set is whatever the findings cite — `fix_helper resolve-scope` computes the narrow union of `files_cited` across the working list (NOT the assembled-feature diff; that breadth is `/verify`'s job). Two sizing checks worth a glance before dispatching:

- **Empty scope** — if the findings cite no files, `/fix` has no file target to verify against. The PHASE-1 empty-scope guard stops the run and points the user back to the report to add the missing location. A defect with no file citation is not yet remediable by a gated fix.
- **Wide scope** — if a single "defect" touches many files across several layers, re-examine the classification: a fix that ripples broadly is often a feature/architecture change wearing a defect's clothes (it is reshaping, not correcting). When in doubt, treat breadth as a signal to re-check the defect-vs-change call above, and bounce if it is really a change.
