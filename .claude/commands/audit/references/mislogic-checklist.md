=== MISLOGIC HUNT CHECKLIST ===

In addition to your normal review, systematically hunt for these patterns.
These are EXAMPLES of what to look for, NOT a list of bugs you should find.
If the codebase has none of these patterns, report none.

Naming lies
- Function name promises X but body does Y (validate* that doesn't validate,
  is* that returns non-boolean, get* with side effects, set* that also reads,
  pure* that mutates)
- Variable name contradicts the value (`count` holding a list, `enabled`
  defaulting to true but used as "disabled")

Comment lies
- Comments describing behavior that no longer matches the code
- "TODO: fix X" where X is now broken differently
- Doc comments listing parameters the function no longer accepts
- "Returns null on error" comments where the code throws

Control-flow mislogic
- Off-by-one (< vs <=, exclusive-vs-inclusive range bugs)
- Inverted conditions (if (!isValid) proceed-happy-path)
- Unreachable branches (if (x) ... else if (x && y) ...)
- Dead defaults
- Early-return that skips cleanup
- Truthiness collapse bugs (0, "", [], null, undefined treated alike)
- Boolean operator confusion (&& vs || in guard chains)

Cross-file contradictions
- Two files encoding the same business rule with different thresholds
- Config A says one value, code B hardcodes a different value
- Enum in one file missing cases the consumer assumes exist
- Type X defined in two places with drifted shapes
- Same constant redeclared with different values
- Import graph claims acyclic but contains a cycle

Configuration mislogic
- Config that contradicts itself (prod=true + debug=true)
- Feature flag checked but never set, or set but never checked
- Env var referenced in code but missing from .env.example
- Default in code differs from default in docs

Error-handling mislogic
- try/catch that swallows errors and logs "success"
- Error path returning the same shape as success path with no discriminator
- Catch that re-throws but loses the stack
- Error message that doesn't match the error it describes

Validation mislogic
- Validation after use (validate(x) called after const y = x.foo)
- Client-side check with no server-side enforcement
- Allowlist that is actually a denylist (check the operator)
- Sanitization on output but not input, or vice versa

Dead / zombie code
- Functions never called
- Imports never used
- Branches unreachable given the type system
- Parameters always passed the same value

Scope creep residue
- Code for cut features whose plumbing remains
- Comments referring to removed systems
- Abstractions with one consumer that never grew the second one

For each mislogic finding, state:
- Pattern matched
- Evidence (verbatim quoted code/comment from the file)
- Why it's wrong (the contradiction)
- Remediation
