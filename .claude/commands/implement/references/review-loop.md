# Autonomous review PANEL loop (`/implement` PHASE 6)

This reference defines the bounded autonomous review-panel loop run in PHASE 6 of `main.md`. The loop mirrors the framework's own engineer→reviewer discipline: NO human sits between rounds. It runs a PANEL of FOUR read-only reviewers (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`) over the touched code, converges it to a panel-clean verdict (every reviewer clean) AND records each judgment-level call it made on the user's behalf as a structured decision item, which PHASE 7 Stage A surfaces one at a time. Most tasks record zero decision items — the panel clears findings mechanically and the hard gate is just the Stage B code read.

## Read-only panel ⇒ no write-collisions

All four reviewers are read-only and tools-locked per the standardized roster (`Read, Grep, Glob, Bash`; no `Edit`/`Write`/`Agent`). They cannot modify the tree, so they cannot collide ("step on each other's legs") and the parallel fan-out is safe. The ONLY writer in PHASE 6 is the single implementing agent during a repair leg. A "conflict" therefore means two reviewers proposing INCOMPATIBLE changes to the same code region — a findings-level contradiction (resolved per the severity rule below), never a write race.

## The loop

1. **Fan out the four reviewers in parallel.** In ONE turn, dispatch `code-reviewer` (consumer `.claude/agents/code-reviewer.md`), `qa-reviewer`, `security-reviewer`, and `performance-analyst` via the Task tool — four Task calls in the same turn — each with the same inputs: the `touched_files`, the constitution, and the task body. Each reviewer is independent and sees only its own brief. Results return UNORDERED; key each returned markdown to the agent it was dispatched to. Each returns a markdown verdict carrying a `### Verdict:` line in its own vocabulary.
2. **Write each reviewer's returned markdown to a run-scoped scratch file** under a tmp dir OUTSIDE the repo (`${TMPDIR:-/tmp}/forge-implement-review/<agent>.md`, one per reviewer). A bash subprocess cannot read a subagent's return value, so these files are the bridge to the merge helper.
3. **Merge the verdicts** via `implement_helper merge-review-panel --iteration N --reviewer <agent>:<path>` (one `--reviewer` per reviewer, using the scratch paths). The helper emits `{clean, escalate, iteration, per_reviewer}`.
4. Branch:
   - `clean: true` → exit the loop; carry any warnings into Stage B; proceed to the forcing-functions gate.
   - `clean: false`, `escalate: false` → the orchestrator synthesizes all four reviewers' findings into ONE repair brief, classifies each cleared finding (mechanical vs judgment), identifies conflicts, relaunches the implementing agent once, then re-fans-out the FULL panel at `--iteration` incremented.
   - `clean: false`, `escalate: true` → exit the loop; record a `could-not-converge` decision item.

## Verdict → clean mapping (the helper owns it)

`merge-review-panel` (`_implement/_cmds_review_panel.py`) owns the per-reviewer verdict-token → clean mapping; this is its observable behavior. Each reviewer's `### Verdict:` line is parsed against ITS OWN vocabulary (all four reviewers share the `### Verdict:` heading shape, but their tokens differ):

- `code-reviewer`: `### Verdict: APPROVE` → clean. (`REQUEST CHANGES` / `BLOCK` → not clean.)
- `qa-reviewer`: `### Verdict: ADEQUATE` → clean. (`GAPS FOUND` → not clean.)
- `security-reviewer`: `### Verdict: PASS` → clean. (`FAIL` → not clean.)
- `performance-analyst`: `### Verdict: MEETS TARGETS` → clean. (`BOTTLENECKS FOUND` → not clean.)

An `### Verdict:` token with a parenthetical note (e.g. `APPROVE (with warnings)`) still parses to its base token; the warnings are carried into Stage B, not blocked on.

## panel-clean = ALL-clean; escalate at the shared cap

- **`clean`** is `true` IFF EVERY reviewer returned its own clean token. One dirty reviewer keeps the loop going.
- **`escalate`** is `true` when the iteration count `N` passed to the helper is `>= 3` (`REVIEW_LOOP_CAP`, the same helper-owned cap the PHASE 5 self-repair loop uses — the panel helper imports it as the single source of truth). The orchestrator cannot bypass the cap; the helper computes `escalate` from the counter it is handed.
- **parse error** — if any reviewer's `### Verdict:` line is missing, is the unfilled slash-joined template, or carries a token outside that reviewer's vocabulary, the helper exits 2 with stderr naming WHICH reviewer failed (no JSON). Re-invoke ONLY that named reviewer for a properly-formed verdict, rewrite its scratch file, and re-run `merge-review-panel`. Do not treat a parse error as a verdict.

## The helper aggregates verdicts; the orchestrator synthesizes findings

`merge-review-panel` does the DETERMINISTIC verdict aggregation ONLY — it parses the four verdict lines and emits the `{clean, escalate, iteration, per_reviewer}` gate signal. It does NOT parse, merge, or conflict-detect FINDINGS. That semantic work is the orchestrator's: on a `clean: false`, `escalate: false` round the orchestrator reads the four reviewers' returned markdown directly and:

- **Synthesizes ALL findings** across the four reviewers into ONE implementing-agent repair brief (per `agent-brief.md`'s PHASE 6 re-dispatch shape). One repair pass addresses all non-conflicting findings.
- **Identifies conflicts** — incompatible findings on the same region (the severity rule below decides whether each is auto-resolved or escalated).

## Severity-aware conflict resolution

All four reviewers report on the unified `Critical / High / Medium / Info` severity scale, so severities are directly comparable across reviewers:

- A **CROSS-severity** contradiction is NOT a conflict — the higher-severity finding wins, and the orchestrator applies it and proceeds autonomously (no human needed).
- A **COMPARABLE-severity** genuine conflict (two incompatible findings of the same severity on the same region) is one the orchestrator must NOT decide on the user's behalf → it records a `conflict` decision item for Stage A and does NOT autonomously repair that contested region this round. The human breaks the tie at Stage A; the loop then applies the choice and re-reviews to clean.

## Full-panel re-review each round

On every repair round, re-run the FULL panel over ALL `touched_files` — not just the files the repair changed. This is the zero-hole choice: it cannot miss a cross-file regression a repair introduced. (Delta-scoped intermediate re-review is a deferred future optimization, out of scope.) The cost is bounded: reviewers are read-only and dispatched in parallel, most rounds converge in one, and atomic tasks keep `touched_files` small.

## Mechanical vs judgment classification

During each repair leg, before relaunching the agent, classify what you (the orchestrator) are asking the agent to change to clear a reviewer finding:

- **Mechanical** — resolves silently, NOT recorded. The fix is fully determined by the finding with no shape choice: a missing docstring/JSDoc, an in-scope named type fix, a null guard the reviewer named, a lint/formatting fix, removing a left-behind debug artifact, a missing test the reviewer named. There is one correct way to clear it.
- **Judgment** — recorded as a decision item. The fix changes the _shape_ of the solution and a reasonable engineer could choose differently: a scope-creep call (include this or defer it), an abstraction/module-boundary choice, a constitution-rule interpretation where more than one reading is defensible, a contract change. These are calls the loop made on the user's behalf.

## Bias-toward-recording tie-breaker

When you are unsure whether a cleared finding was mechanical or a judgment call, **record it as a decision item.** A surplus decision question costs the user one click in Stage A; a missed one silently lands a contested decision the user never saw. The asymmetry favors recording.

## The three decision-item shapes

PHASE 6 records three kinds of decision item, all surfaced at PHASE 7 Stage A one at a time:

- **judgment** — a finding the loop FIXED, where a reasonable engineer could have chosen a different shape. Structured as:
  - `finding` — the reviewer's objection, in one line (what was flagged).
  - `agent_resolution` — what the loop did to clear it (becomes Stage A option 1, marked `(recommended)`).
  - `alternative` — the named alternative the loop did NOT take (becomes Stage A option 2).

  A judgment item's finding IS fixed; the human only confirms the SHAPE — so it is NOT an open finding and may reach Stage B.

- **could-not-converge** — recorded when the loop escalated at the cap with one or more reviewers still dirty. It carries the unresolved reviewer objection(s). Stage A surfaces it with the options `send back with direction / skip / stop` (per `main.md` PHASE 7 Stage A) — there is no option to accept the finding as-is, because an open finding must never reach `approve`.
- **conflict** — recorded when the orchestrator found a COMPARABLE-severity contradiction it must not decide on the user's behalf. It carries the contested finding and the two reviewers' incompatible positions. Stage A names the contested finding on one line and offers the two positions as the first two options (plus `let me specify` and `stop`); the chosen resolution becomes a repair direction, after which the loop re-reviews to clean — the conflict is resolved before Stage B, never approved open.

## The cap

The loop is bounded at 3 rounds (helper-owned `REVIEW_LOOP_CAP = 3`). At the cap, the loop stops relaunching and escalates: it records the `could-not-converge` item and exits to PHASE 7. The cap exists so the loop cannot spin indefinitely on a finding the agent and a reviewer disagree on — that disagreement becomes a user decision, not an infinite loop.
