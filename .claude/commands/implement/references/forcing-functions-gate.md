# Forcing-functions gate (`/implement` PHASE 6)

This reference defines the forcing-functions gate run after verify + the review panel, BEFORE the hard gate (PHASE 6 of `main.md`). The gate runs the consumer-side mechanical detectors that back constitution rules LLMs systematically violate. It is a single helper call:

```bash
.devforge/lib/implement_helper run-forcing-functions-gate
```

## What the gate does

The helper (`_implement/_cmds_gate.py`) reads the `forcing_functions` block from `.devforge/constitute.json` and, for each rule with `enabled: true`, invokes the matching `constitute_helper verify-<rule>` verb as a subprocess. The rule-key → verb mapping is owned by `constitute_helper` (`_constitute._forcing_functions._setters.RULE_TO_VERB`):

- `magic_enum_duplication` → `verify-magic-enum`
- `cross_layer_imports` → `verify-cross-layer-imports`
- `any_with_generated_available` → `verify-any-leak`
- `design_token_provenance` → `verify-design-tokens`

The gate walks the `forcing_functions` block, so a new rule registered in `RULE_TO_VERB` runs through the same single `run-forcing-functions-gate` call with no orchestrator change.

### The design-token provenance check (`verify-design-tokens`)

`verify-design-tokens` is the static, write-time PROVENANCE half of the framework's design-fidelity mechanism, backing the constitution's Design Fidelity principle in its Code Quality Standards material. Over component styles it checks: no hardcoded hex / `rgb()` / `hsl()` / named colors; no `var(--x, <literal>)` fallbacks; an undefined token FAILS LOUDLY rather than silently rendering a fallback; token-binding is required on the MATCH elements of the feature's disposition manifest; every interactive element declares both `:hover` and `:focus-visible`.

It is config-gated like every other rule — when `forcing_functions.design_token_provenance.enabled` is `true` the gate dispatches it; when the rule block is absent or `enabled: false` it is skipped (no-op). The rule block, when present, carries the feature-scoped inputs as config fields (`manifest_path` → the `specs/[feature]/design-manifest.json` that `/breakdown` produces; `token_source_css` → the design token source). `verify-design-tokens` loads those itself: when `manifest_path` resolves it runs the MATCH-keyed token-binding check; when no manifest is configured (a non-UI feature) that check is skipped while the literal-color and undefined-token checks still run. The orchestrator passes no manifest argument — the helper reads everything from `.devforge/constitute.json`. The block's shape is owned by `constitute_helper`'s `set-forcing-functions` setter (`_constitute._forcing_functions._setters`); writing it into `.devforge/constitute.json` is the forcing-functions config-capture's job, so until that capture populates an enabled `design_token_provenance` block this gate skips the rule as a no-op.

This static provenance check is ORTHOGONAL to `/review`'s runtime design conformance check, and neither covers the other's defect class: a hardcoded `#e8e6e3` and a `var(--border)` that resolves to the same value are indistinguishable at runtime (only the static grep catches the token bypass), while a correct token binding can still produce the wrong rendered spacing (only the runtime check catches that). Do not treat one as covered by the other.

The gate aggregates each rule's exit code and stdout report and emits one JSON object on stdout:

```
{
  "gate": "forcing_functions",
  "rules_run": [<verb names that ran>],
  "rules_failed": [<verb names that exited non-zero>],
  "reports": {"<verb>": "<that rule's stdout text>", ...},
  "aggregate_exit": 0 | 2
}
```

## Exit semantics

- **exit 0** → no enabled rule failed, OR no rules are enabled (then `rules_run` is empty). Continue to the hard gate (PHASE 7).
- **exit 2** → one or more enabled rules failed. The task is gate-blocked: it never reaches the `approve` prompt. Continue to PHASE 7's gate-blocked path (`repair` / `skip` / `stop` only).
- **exit 1** → config I/O or parse error: `.devforge/constitute.json` is malformed, or it enables a rule with no known verb in `RULE_TO_VERB`. This is a configuration problem, not a finding — copy the helper's stderr VERBATIM into a fenced code block and resolve it (fix or disable the rule) before re-running.

## Relay the stdout JSON, not stderr

On exit 2, copy the helper's **stdout JSON** VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The per-rule finding reports live under the `reports` key on stdout. Do NOT relay stderr for the findings: a finding line is shaped `path:line: KIND`, which is ambiguous when a path itself contains `:` (per `_shared.emit_findings` Known Limitations — stderr is for human eyeballing, stdout JSON is the machine-relayable report). Each per-rule `constitute_helper verify-<rule>` call writes its own stderr straight to the terminal; the gate captures only stdout for relay.

## Triage

When the gate blocks (exit 2), the relayed `reports` name which rule(s) failed and where. Triage with the user via the PHASE 7 gate-blocked `AskUserQuestion`:

- **`repair`** → relaunch the implementing agent with the failing rule's report so it removes the violation (e.g. replace a magic-enum duplication with the generated enum, remove a cross-layer import, replace an `any` where a generated type exists, or bind a hardcoded color literal to its design token), then re-run verify → review panel → this gate.
- **`skip`** → reset to the checkpoint, mark the task `Skipped`, advance (PHASE 7 `skip` path).
- **`stop`** → keep `wip.md` + working tree; end the loop.

There is no `approve` past a failed forcing-functions gate — the change is not green, and no content has been committed, so there is nothing to roll back; the working tree holds the partial work.
