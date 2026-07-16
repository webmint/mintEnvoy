# Formalization guidance — worked NL→IR examples

The orchestrator injects this file into the `spec-formalizer` Task prompt in
PHASE 2, after the machine OUTPUT CONTRACT the `render-formalize-brief` verb
emits. The agent's own body (`.claude/agents/spec-formalizer.md`) carries the
translation RULES; this file grounds them with concrete AC → IR examples.

Every example shows the acceptance criterion text and the exact JSON IR it
formalizes to. The IR is one object with three top-level arrays — `variables`,
`constraints`, `coverage` — using the flat atom shapes: numeric
`{"var","op","value"}`, Bool `{"var","negated"}`, Enum `{"var","op","value"}`.

## Three load-bearing rules (the agent enforces these; the examples show them)

- **Skip honestly, never force.** A subjective/non-logical AC → `skipped_prose`;
  an AC whose logic the IR cannot express (e.g. arithmetic over 2+ variables) →
  `skipped_unsupported`. Both carry a `reason`. A forced bad translation produces
  a false verdict and is worse than an honest skip.
- **Co-refer.** The SAME real-world quantity across different ACs MUST become the
  SAME variable `name`, declared once in `variables[]` and reused — that is
  exactly how the solver sees a cross-AC conflict. Splitting one quantity across
  two names hides the conflict.
- **The `gloss` is the human's check.** Each variable's `gloss` is the
  plain-English meaning the human reads to catch a mistranslation. Treat it as
  required substance, not decoration.

## Example 1 — a numeric threshold AC → `assertion`

AC text: *"AC-3: The system shall respond to a delete request within 100ms."*

```json
{
  "variables": [
    {"name": "response_ms", "sort": "Real", "gloss": "delete-request response latency in milliseconds"}
  ],
  "constraints": [
    {"ac_id": "AC-3", "kind": "assertion", "consequent": [{"var": "response_ms", "op": "<", "value": 100}]}
  ],
  "coverage": [
    {"ac_id": "AC-3", "status": "formalized"}
  ]
}
```

A plain `shall` invariant with no trigger is a `kind: assertion` — the
`consequent` is the outcome that must always hold. If a second AC asserted
`response_ms > 200` over the same `response_ms` variable, the solver would return
`unsat` with the two conflicting `ac_id`s as the core.

## Example 2 — an EARS trigger AC → `implication`

AC text: *"AC-4: WHEN the cart is empty, checkout shall be disabled."*

```json
{
  "variables": [
    {"name": "cart_empty", "sort": "Bool", "gloss": "the shopping cart contains zero items"},
    {"name": "checkout_enabled", "sort": "Bool", "gloss": "the checkout action is available to the user"}
  ],
  "constraints": [
    {"ac_id": "AC-4", "kind": "implication", "antecedent": [{"var": "cart_empty", "negated": false}], "consequent": [{"var": "checkout_enabled", "negated": true}]}
  ],
  "coverage": [
    {"ac_id": "AC-4", "status": "formalized"}
  ]
}
```

An EARS trigger/condition form (`WHEN`, `WHILE`, `WHERE`, `IF…THEN`) is a
`kind: implication` — the trigger/condition is the `antecedent` (a multi-atom
conjunction is allowed), the required outcome is the `consequent`. Here "checkout
shall be disabled" is `checkout_enabled` = false, so the Bool atom is
`{"var": "checkout_enabled", "negated": true}`.

## Example 3 — a permission GRANT vs a restriction (the D9 case)

Two ACs, formalized together so the shared variables co-refer:

- AC text: *"AC-6: Only admins can delete a record."*
- AC text: *"AC-7: A support agent (a non-admin) can delete a stuck record."*

```json
{
  "variables": [
    {"name": "can_delete", "sort": "Bool", "gloss": "the acting user is permitted to delete a record"},
    {"name": "is_admin", "sort": "Bool", "gloss": "the acting user holds the admin role"}
  ],
  "constraints": [
    {"ac_id": "AC-6", "kind": "implication", "antecedent": [{"var": "can_delete", "negated": false}], "consequent": [{"var": "is_admin", "negated": false}]},
    {"ac_id": "AC-7", "kind": "assertion", "consequent": [{"var": "can_delete", "negated": false}, {"var": "is_admin", "negated": true}]}
  ],
  "coverage": [
    {"ac_id": "AC-6", "status": "formalized"},
    {"ac_id": "AC-7", "status": "formalized"}
  ]
}
```

The RESTRICTION "only admins can delete" is a rule → `implication`
(`can_delete ⇒ is_admin`). The GRANT "a non-admin can delete" asserts a reachable
case → an `assertion` of `can_delete ∧ ¬is_admin`, NOT another implication. This
is the load-bearing move: the solver detects the clash (`unsat`, core
`{AC-6, AC-7}`) ONLY because the permitting scenario is ASSERTED reachable. If
BOTH were formalized as pure implications, the solver would correctly return
`sat` — a rule set that merely permits is genuinely consistent until a permitted
case is asserted. Formalize a permission-grant statement ("<role> can <action>")
as an assertion of the reachable case; if a statement is genuinely a conditional
rule rather than a reachable grant, formalize it as an implication and let it
stand.

## Example 4 — a subjective prose AC → `skipped_prose`

AC text: *"AC-5: The UI should feel responsive and uncluttered."*

```json
{
  "variables": [],
  "constraints": [],
  "coverage": [
    {"ac_id": "AC-5", "status": "skipped_prose", "reason": "'feel responsive and uncluttered' is subjective — no logical quantity to formalize"}
  ]
}
```

A subjective or non-logical criterion has no real-world quantity to name. Record
it as `skipped_prose` with a reason — never force it into a constraint.

## Example 5 — arithmetic over two variables → `skipped_unsupported`

AC text: *"AC-9: The order total shall equal the subtotal plus tax."*

```json
{
  "variables": [],
  "constraints": [],
  "coverage": [
    {"ac_id": "AC-9", "status": "skipped_unsupported", "reason": "arithmetic relating three variables (total = subtotal + tax) — the flat-atom IR cannot express multi-variable arithmetic"}
  ]
}
```

The flat atom shape is one variable, one op, one value — it cannot express an
equation over 2+ variables. Record such an AC as `skipped_unsupported` with a
reason; it is outside the check by design, and the coverage ledger makes that
honest to the reader.
