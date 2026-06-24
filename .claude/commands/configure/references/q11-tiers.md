# Q11 — Claude tier model picks

`/configure` Phase 4 asks three sequential AskUserQuestion calls — one per tier (think / do / verify). Each picks a Claude model from `Opus | Sonnet | Haiku | Other`. Persist each answer via its setter before issuing the next question.

## Q11.1 — Think tier

Use AskUserQuestion: "Which Claude model handles the 'think' tier (architecture, plan, breakdown)?"
- `Opus` (Recommended) — most capable; default for design-heavy work
- `Sonnet` — balanced; cheaper than Opus, more capable than Haiku
- `Haiku` — fastest + cheapest; suitable for very small projects only
- `Other` — let me name a different model

If the user picks `Other`, follow up with a plain free-text prompt: "Which model name?", then save the free-text answer via `.devforge/lib/configure_helper set-claude-tier-think <answer>`.

If the user picks `Opus`, `Sonnet`, or `Haiku`, save via `.devforge/lib/configure_helper set-claude-tier-think <choice>`.

## Q11.2 — Do tier

Use AskUserQuestion: "Which Claude model handles the 'do' tier (code execution, edits, refactors)?"
- `Sonnet` (Recommended) — balanced cost/capability for execution work
- `Opus` — overkill for most do-tier tasks; use only for very complex implementations
- `Haiku` — too limited for most engineering work; suitable for simple edits only
- `Other` — let me name a different model

If the user picks `Other`, follow up with a plain free-text prompt: "Which model name?", then save the free-text answer via `.devforge/lib/configure_helper set-claude-tier-do <answer>`.

If the user picks `Sonnet`, `Opus`, or `Haiku`, save via `.devforge/lib/configure_helper set-claude-tier-do <choice>`.

## Q11.3 — Verify tier

Use AskUserQuestion: "Which Claude model handles the 'verify' tier (review, audit, ac-verification)?"
- `Haiku` (Recommended) — fast + cheap; mechanical verification work
- `Sonnet` — when verification needs more judgment (security, architecture review)
- `Opus` — heavy review work only
- `Other` — let me name a different model

If the user picks `Other`, follow up with a plain free-text prompt: "Which model name?", then save the free-text answer via `.devforge/lib/configure_helper set-claude-tier-verify <answer>`.

If the user picks `Haiku`, `Sonnet`, or `Opus`, save via `.devforge/lib/configure_helper set-claude-tier-verify <choice>`.

## Defaults rationale

Recommended defaults: `think = Opus`, `do = Sonnet`, `verify = Haiku`. The triple matches each tier's role to the cost/capability sweet spot — design-heavy work benefits from Opus's reasoning depth; execution work benefits from Sonnet's balance of speed and capability; mechanical verification rarely needs more than Haiku and is a high-volume tier where token cost matters. The defaults are starting points; users override per project (e.g., a security-critical project may move verify up to Sonnet, a small prototype may pull think down to Sonnet).
