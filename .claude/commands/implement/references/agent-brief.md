# Implementing-agent brief shape (`/implement` PHASE 3)

This reference defines the brief the orchestrator assembles when it dispatches the implementing agent for a task (PHASE 3 of `main.md`) and re-dispatches it during self-repair (PHASE 5) and review-panel repair legs (PHASE 6). The agent sees ONLY what the brief carries — it does not have the orchestrator's conversation history, its mental model of the architecture, or its knowledge of the task contract (per `feedback_no_underspecification_when_delegating`). A thin brief that makes the agent rediscover known context is the orchestrator's failure, not the agent's.

## Brief sections

Assemble the brief with these sections, sized to the task (a one-file change does not need a 5000-word brief; a multi-file design-decision task does):

- **Goal** — what success looks like for THIS task. Take it from the resolved task's `title` plus the `## Description` of the task body (read the resolved `task_file` path from PHASE 1; do not construct it). State the one clear done condition.
- **Integration context** — where this task fits and what consumes its output. Carry the task's `## Contracts` `Produces` items (what must be true after) and any downstream tasks that depend on them, so the agent knows its output is a contract other tasks read.
- **Constraints** — the conventions the agent must follow: the constitution rules (`constitution.md`), the project architecture (`CLAUDE.md` `## Architecture` + `## Packages`), and the task's `## Contracts` `Expects` items (preconditions it must rely on, not re-create). Pass file paths; the agent inherits the parent session's Read surface and fetches them itself — do not inline file contents (that double-pays context and risks drift).
- **Edge cases** — pitfalls the orchestrator already knows. Carry the relevant entries from `.devforge/memory.md` (the preflight `memory_digest` is a starting point; the agent may read the full file). Do not make the agent rediscover a lesson already recorded.
- **Success criteria** — how the agent knows it is done: the task's `## Done When` conditions. Note that scope-aware type-check + lint + build run after the agent returns (PHASE 5), so the agent's code must pass them.
- **What NOT to do** — the scope constraint: the `touched_files` list from the resolved task is the expected file set; the agent makes ONLY the changes this task describes and must NOT "fix" unrelated code it happens to see (constitution "Never modify outside scope"). Inline documentation (docstrings / JSDoc) on new/changed code IS in scope — `code-reviewer` checks for it in PHASE 6.

## Re-dispatch briefs (self-repair + review repair)

- **Self-repair (PHASE 5)** — when `verify-touched` emits `status: "self_repair"`, the re-dispatch brief is the original brief PLUS the helper's `failed_command` and `output`. The agent's job is to make the named command pass; it must not expand scope beyond the failure.
- **Review repair (PHASE 6)** — when the review panel is not yet clean, the re-dispatch brief is the original brief PLUS the orchestrator-SYNTHESIZED findings drawn from ALL FOUR panel reviewers (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`) — collapsed into one repair brief covering every non-conflicting finding the round surfaced (per `.claude/commands/implement/references/review-loop.md`'s findings-synthesis rule), not just `code-reviewer`'s. When the orchestrator chose a Stage A alternative, a conflict resolution, or a `let me specify` / `send back with direction` direction (PHASE 7), the brief also carries that explicit direction. Contested COMPARABLE-severity regions held back for Stage A are NOT included in the autonomous repair brief (they are repaired only after the human breaks the tie).

## Agent selection

The agent name is the resolved task's `agent` field (assigned by `/breakdown`'s Agent Assignment table). If that field is `architect`, HALT — the architect cannot implement (per `.claude/agents/architect.md` Rule 1); re-run `/breakdown` to get the owning stack's implementer, or add the missing agent. If the assigned agent is absent from `.claude/agents/` (not every project generates every agent), HALT and escalate to the human — split the task or re-run `/breakdown` to assign the owning stack's implementer. Never fall back to `architect`; it cannot write code.
