---
name: plan
description: Translate an approved spec into a technical implementation plan with architecture decisions, layer map, file impact, and risk assessment.
argument-hint: "[spec-file]"
disable-model-invocation: true
---

# /plan — Technical Implementation Plan

`/plan` is repeatable per feature. It takes an approved spec authored by `/specify` and produces a technical plan: research findings, optional data model, optional API contracts, architecture decisions, layer map, file impact, and risk assessment. The orchestrator (the LLM following this spec) writes all plan artefacts in the main thread via Write or Edit. Subagent dispatch is reserved for **decision work at two mandatory hooks**: the `architect` agent is invoked at Phase 1.3 (Architecture Decisions) for every run, and at Phase 0 Step 3 when 2+ architectural alternatives are being compared. Outside those hooks, the orchestrator authors directly — no per-phase auto-dispatch. Phase 0's hard gate ensures the one-time setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) has completed before any plan work fires. Produces `specs/NNN-<feature>/plan.md` plus optional supporting docs, and ends with a manual handoff to `/breakdown` — no automated dispatch.

Usage: `/plan [spec-file]` (e.g. `/plan specs/008-prevent-duplicate-config-options/spec.md`, or `/plan` with no argument to use the most-recently-modified spec under `specs/`).

## Outputs of this phase

- `specs/NNN-<feature>/plan.md` — rendered plan markdown (required).
- `specs/NNN-<feature>/research.md` — when 1+ signals detected per Phase 0 (conditional).
- `specs/NNN-<feature>/data-model.md` — when the feature involves new or changed entities (conditional).
- `specs/NNN-<feature>/contracts.md` — when the feature involves new or changed API contracts (conditional).

## Context in the Workflow

```
/research (optional) → /specify → /plan → /breakdown → /implement → /review → /verify → /summarize → /finalize
```

`/plan` runs AFTER the spec is approved, BEFORE task breakdown. It answers technical questions the spec intentionally left open (specs describe WHAT, plans describe HOW).

## PHASE 0a: Spec resolution

`/plan` consumes one approved spec per invocation. Resolve which spec via the helper:

```bash
.devforge/lib/plan_helper pick-spec $ARGUMENTS
```

If `$ARGUMENTS` is non-empty, the helper validates the explicit file path (must be an existing `spec.md` file, not a directory) and prints its absolute path on stdout. If empty, the helper picks the most-recently-modified `specs/*/spec.md` whose shape passes 9-section validation. Exit 2 means no valid spec was found — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

Capture the resolved absolute path. Then render the preview block:

```bash
.devforge/lib/plan_helper render-pick-summary <resolved-path>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block. Then ask the user via `AskUserQuestion`:

- Question: `"Process this spec?"` — single-line text.
- Options: `["yes", "pick-other", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`yes`** → proceed to Phase 0a.5 with the resolved path.
- **`pick-other`** → in the next turn, run `.devforge/lib/plan_helper list-specs` and emit stdout as a numbered list inside a fenced block. The helper output is unbounded (one line per spec, mtime desc). For `AskUserQuestion`, take the first four lines as the four option labels — AskUserQuestion caps at four options, so the LLM truncates client-side, not the helper. Question: `"Which spec to plan against?"` — single-line text. If more than four specs exist, include `other` as the fourth option; on `other`, ask the user via free-text follow-up for the explicit path, then re-run `pick-spec <path>` to validate. On the chosen path, treat it as the resolved path and proceed to Phase 0a.5.
- **`cancel`** → tell the user `"/plan cancelled. Re-run /plan when ready."` and end the turn.

## PHASE 0a.5: Upstream handoff discovery

`/specify` may have written a sibling `handoff.json` next to the spec, which can point upstream to a `/research` or `/discover` handoff carrying the HOW seed. This phase is informational — it surfaces that seed for the planning phases. There is no user gate here; do not invoke `AskUserQuestion`.

Check for a sibling handoff via the helper:

```bash
.devforge/lib/plan_helper read-specify-handoff <resolved-path>
```

- Stdout `no-handoff` → tell the user `"No upstream handoff; planning cold from the spec."` and proceed to Phase 0a.6 with the resolved path.
- A 4-line block (lines `spec-handoff:`, `spec_seeds:`, `upstream_handoff_path:`, `upstream_handoff_kind:`) → read its `upstream_handoff_path` line:
  - value `none` → tell the user `"Spec has no upstream research/discover handoff; planning cold."` and proceed to Phase 0a.6 with the resolved path.
  - a path → render the plan seeds via the helper, passing the `spec-handoff:` value from the 4-line block as the argument:

    ```bash
    .devforge/lib/plan_helper render-plan-seeds <spec-handoff-path>
    ```

    - Stdout `cold-no-plan-seeds` → tell the user `"Upstream handoff carries no plan seeds; planning cold."` and proceed to Phase 0a.6 with the resolved path.
    - A `## Upstream plan-seeds` block → copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). State that this block is the HOW seed and is the authoritative starting point for Phase 0 (Research Evaluation — if it already cites canonical patterns or a recommended approach, you have prior art; calibrate research depth instead of rediscovering), Phase 1 (Technical Design), and Phase 1.3 (Architecture Decisions — where the architect consultation fires and the key design decisions are drafted). If your plan diverges from the upstream recommendation, state the divergence and why in the plan's "Specialist Consultation" section — do not silently discard it. Then proceed to Phase 0a.6 with the resolved path.

Exit 2 from either helper means the sibling handoff is malformed or the upstream pointer is dangling/unknown — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

## PHASE 0a.6: Spec drift check

The spec may have been written against source files that changed since. This phase is informational/gate only — it surfaces drift in the spec's §4-cited files before planning starts.

Check for drift via the helper:

```bash
.devforge/lib/cbm_sync_helper check-spec <resolved-path>
```

Stdout is one of four forms:

- `current` — the spec's cited files are unchanged since it was stamped. Proceed silently to Phase 0b with the resolved path; no message needed.
- `missing` — no drift stamp exists for this spec. Tell the user `"No drift stamp for this spec; proceeding."` and proceed to Phase 0b with the resolved path.
- `drift <a>..<b> <file-1> <file-2> ...` — one or more spec-cited files changed since the spec was stamped. Tell the user the spec's cited files changed since it was stamped, listing the changed files from the `<file-...>` tokens. If the `drift` token carries no `<file-...>` tokens (only the two SHAs), do not claim specific files changed — tell the user the spec has drifted from its stamp but the cited-file list could not be computed (the spec file may have moved). Then ask via `AskUserQuestion` `"Spec-cited files changed since the spec was written — proceed with planning?"` — single-line text — with options `["proceed", "cancel"]`. On `cancel`, tell the user `"Re-check the spec against the changed files before re-running /plan."` and end the turn. On `proceed`, continue to Phase 0b with the resolved path.
- `not-a-git-repo` (exit 2) — the drift check cannot run (no git repository / no HEAD / git binary missing). Tell the user `"Spec drift check unavailable (not a git repository); proceeding without it."` and proceed to Phase 0b with the resolved path. The drift check is advisory — a non-git target must NOT block planning.

## PHASE 0b: Status flip

The act of running `/plan` constitutes approval of the spec for planning. Flip Draft → Approved structurally via the helper:

```bash
.devforge/lib/plan_helper check-status-and-flip <resolved-path>
```

Stdout is one of five state tokens:

- `flipped` — spec was Draft, now Approved. Tell the user: `"Spec status: Draft → Approved (implicit approval via /plan invocation)."`
- `already-approved` — continue silently; no message needed.
- `complete` — spec is in the post-`/verify` Complete state. Warn the user, then `AskUserQuestion` `"Spec status is Complete — proceed against a shipped spec?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.
- `inserted` — spec lacked a Status line; helper inserted `**Status**: Approved`. Tell the user: `"Spec was missing a Status line; helper inserted **Status**: Approved."`
- `unknown-status:<value>` — spec has a non-standard status. Tell the user the value, then `AskUserQuestion` `"Status is non-standard — proceed?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.

Exit 2 means the spec is malformed (neither Date nor Status frontmatter line). Echo the helper's stderr verbatim as a fenced block and end the turn.

## PHASE 0: Research Evaluation

**Guard**: Read `constitution.md`. If it contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/plan`."

**This phase always runs.** Scan the spec to determine the research depth needed.

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, resolve all source file references relative to that path.

### Step 1: Codebase Research (always)

- Read relevant source files to understand current patterns.
- Check how similar features are implemented.
- Identify reusable code and patterns.
- For greenfield projects: check the constitution's scaffolding guide for pattern references.
- The spec already incorporates relevant documentation context from `docs/`. Do not re-read docs — use the spec's "Current State" and "Affected Areas" sections as your primary source.

### Step 2: Signal Scan

Read the spec and check for these signals. **Only flag signals for things NOT already in the project's current stack.** If the spec references a library/technology that's already in the project's dependencies (check `CLAUDE.md`, `package.json`, `pubspec.yaml`, `requirements.txt`, etc.), that is NOT a signal — the team has already made that choice.

| Signal | Example | NOT a signal when... |
|--------|---------|---------------------|
| External library/package **not in project dependencies** | "use Stripe SDK" (and Stripe is not in package.json) | Library is already installed |
| New integration with **unconfigured** third-party service | "connect to payment gateway" (no payment config exists) | Service is already integrated |
| Architectural decision where multiple valid approaches exist | "real-time updates" (polling vs SSE vs WebSocket) | Always a signal — requires decision |
| Greenfield pattern not yet present in the codebase | first use of caching, first background job | Pattern already exists in codebase |
| Performance constraints that need benchmarking | "handle 10k concurrent users", "< 200ms response" | Always a signal — requires research |
| Technology **not part of the project's current stack** | new protocol or tool the codebase hasn't used | Technology is already in the stack |

**No signals found** → proceed to Phase 1 with codebase research only.

**1+ signals found** → continue to Step 3.

### Step 3: Deep Research (when signals detected)

For each signal, choose the appropriate research tool:

**For specific libraries named in the spec** (binding):
- **Required**: Use Context7 first (`resolve-library-id` → `query-docs`) to get current documentation. **Do not skip directly to WebSearch.**
- **Fallback condition**: Only fall back to WebSearch if (a) Context7 returns no results for the library, OR (b) the Context7 tool is unavailable in this session. Document the fallback in research.md with the specific reason ("Context7 returned no docs for X" or "Context7 unavailable").
- **Auditability**: The choice is logged in tool-call traces; reviewers can verify which path was taken.

**For comparing alternatives or architectural decisions:**
- Use WebSearch to find current best practices and proven approaches.
- Compare at least 2-3 alternatives with pros/cons.
- Check library options: maintenance status, bundle size, community adoption.

**Seed from upstream plan-seeds (do not relitigate settled alternatives):** If Phase 0a.5 surfaced an `## Upstream plan-seeds` block that already lists alternatives (a research handoff under "Alternatives considered"; a discover handoff under "Design options"), seed the alternatives comparison from those rather than rediscovering them. The 2+-alternatives architect invocation described in this Step 3 fires only for alternatives NOT already settled in the upstream plan-seeds. The Phase 1.3 mandatory architect consultation is unaffected — it fires unconditionally regardless of plan-seeds. When you seed from plan-seeds and therefore skip fresh alternative discovery, record that in the plan's "Specialist Consultation" section, citing the upstream handoff. Do not contradict the upstream recommendation silently — a divergence must be stated with reasoning (this complements the divergence rule in Phase 0a.5).

**Architect consultation: mandatory when 2+ architectural alternatives are being compared.**

After raw findings for each alternative are gathered (pros/cons/maintenance/bundle), invoke the `architect` agent via the Task tool to author the verdict. Brief shape: pass file paths to `specs/<feature>/spec.md`, in-progress research notes, and `CLAUDE.md`; ask which alternative wins for the named decision area and why; expect the architect to return rows verbatim-ready for the research.md "Alternatives Compared" table (verdict column populated per row) plus a one-line decision rationale.

Skip ONLY when alternatives are mechanical (one library is project-default per `CLAUDE.md`, others are non-starters). The skip reason must be recorded as a one-line note in the plan.md "Specialist Consultation" section (see Phase 2 template) — that section is always present in plan.md and is the single source of truth for invocation/skip provenance, regardless of whether research.md was generated. Silent skips are a hard error.

**For all signals:**
- Look at real-world examples of similar implementations.
- Verify external API contracts and limitations.

### Research Output Rule

When 1+ signals are detected, document research findings somewhere visible to the plan reviewer. Two valid paths:

- **Default**: Generate `specs/[feature-name]/research.md` with the structured template below.
- **Skip-with-reference**: If an existing file under `research/` directly addresses ALL detected signals (verified by reading the existing file), you may reference it instead of generating a new file. In this case:
  1. Cite the existing path in the plan's Supporting Documents section
  2. Add a brief "Why no new research" note in the plan's Summary section
  3. Quote 2-3 specific findings from the existing file in the plan body to prove the reference was actually consulted
  4. Do NOT skip without reference — that is a hard error

If signals are detected and neither path is taken, the plan is incomplete.

### Research output:

Save to `specs/[feature-name]/research.md`:

```markdown
# Research: [Feature Name]

**Date**: [YYYY-MM-DD]
**Signals detected**: [list which signals triggered deep research]

## Questions Investigated
1. [Question] → [Finding + decision]
2. [Question] → [Finding + decision]

## Alternatives Compared

### [Decision Area] (e.g., "Payment processor", "WebSocket library")
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| [option A] | [pros] | [cons] | Chosen / Rejected |
| [option B] | [pros] | [cons] | Chosen / Rejected |
| [option C] | [pros] | [cons] | Chosen / Rejected |

**Decision**: [chosen option] — [one-line rationale]

## References
- [links to docs, examples, or source files consulted]
```

If no deep research was needed (no signals), skip the research.md file.

## PHASE 1.5: Findings from Spec (REQUIRED INTERMEDIATE OUTPUT — v2)

Before writing any of the plan's tables (Layer Map, File Impact, Key Design Decisions, Risk Assessment), produce a structured intermediate output enumerating what the spec contains. This is a hard requirement.

Render the skeleton via the helper:

```bash
.devforge/lib/plan_helper render-findings-from-spec <resolved-path>
```

The helper enumerates every §3 / §4 / §5 / §6 / §7 / §8 / §9 item with an identifying snippet plus a per-section fill marker. Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). In the SAME message, replace each marker inline with your coverage decision:

- `[PLAN COVERAGE: ?]` on §3 / §4 / §5 lines → `[PLAN COVERAGE: <layer/file/decision>]` or `[PLAN COVERAGE: covered by Layer Map: <area>]`.
- `[must not contradict]` on §6 lines → leave as-is, OR append ` → confirmed: <why>` if the plan touches a related area.
- `[LANDS IN: ?]` on §7 lines → `[LANDS IN: Constitution Compliance]` or `[LANDS IN: Risk Assessment]`.
- `[RESOLUTION: ?]` on §8 lines → `[RESOLUTION: <decision>]` if resolved by the plan, or `[RESOLUTION: carry-forward to /breakdown]`.
- `[MITIGATION CARRIED: ?]` on §9 lines → `[MITIGATION CARRIED: yes — Risk Assessment row <N>]` or `[MITIGATION CARRIED: no — out-of-scope per §6]`.

When a planning decision actually resolves a §8 open question — here at Phase 1.5, or later when a Phase 1 / Phase 2 decision settles one — record the resolution in specify-state via the helper, passing the spec's question id and `--resolution-phase plan`:

```bash
.devforge/lib/specify_helper resolve-open-question --question-id <question-id> --resolution-text "<how the plan resolves it>" --resolution-phase plan
```

This appends a resolution audit entry to specify-state; the spec re-render strikes through the resolved entry. It is conditional — run it only when the plan actually resolves an open question. Unresolved questions stay open for `/breakdown` (`[RESOLUTION: carry-forward to /breakdown]`) or carry into the plan's Risk Assessment.

**Each section requires concise bullet enumeration** — reference, don't restate. Goal is a ~15–30-line output that proves every spec section was read and accounted for.

This intermediate output forces every spec section to be acknowledged before plan tables are written. Same purpose as /specify Phase 1.5: convert implicit recall into explicit enumeration. Skipping or compressing this step is a hard error.

After this intermediate output is complete, proceed to Phase 1 (Technical Design). The "1.5" numbering is preserved verbatim from parity-validated `/plan` v2 — the section runs after Phase 0 and before Phase 1 despite the numeric ordering, because it gates both the Phase 1 technical artefacts (data model, contracts, architecture decisions — per the Prerequisite at the top of Phase 1) and the Phase 2 plan tables (Layer Map, File Impact, Key Design Decisions, Risk Assessment — per the preamble above).

## PHASE 1: Technical Design

**Prerequisite**: Phase 1.5 must be complete before any technical-design artefacts (data model, contracts, architecture decisions) are drafted.

### 1.1: Data Model (if applicable)

If the feature involves data entities, define them. Save to `specs/[feature-name]/data-model.md`:

```markdown
# Data Model: [Feature Name]

## Entities

### [EntityName]
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier |
| ... | ... | ... | ... |

### Relationships
- [Entity A] → [Entity B]: [relationship type and description]

### Validation Rules
- [Field]: [constraint]
```

For existing codebases, reference existing types/interfaces instead of redefining them. Only document NEW or CHANGED entities.

### 1.2: API Contracts (if applicable)

If the feature involves API calls (REST, GraphQL, etc.), define contracts. Save to `specs/[feature-name]/contracts.md`:

```markdown
# API Contracts: [Feature Name]

## [Endpoint/Query/Mutation Name]
- **Type**: [GET/POST/Query/Mutation]
- **Input**: [type definition or reference to existing type]
- **Output**: [type definition or reference to existing type]
- **Errors**: [error cases and response format]
```

For existing codebases, reference existing GraphQL queries/mutations or REST endpoints. Only document NEW or CHANGED contracts.

### 1.3: Architecture Decisions

Document HOW the feature maps to the project's architecture. This is the core of the plan.

**Architect consultation: mandatory.**

Before drafting the Phase 2 plan.md tables (Layer Map, Key Design Decisions, File Impact, Risk Assessment), invoke the `architect` agent via the Task tool. The architect's `think`-tier reasoning is the specialization point for layer-mapping, dependency-direction, package-boundary, and constitution-compliance calls. Orchestrator-direct authoring of these tables without consultation is a hard error at this phase.

**Orchestrator-mediated consultation relay (the architect emits requests; it does NOT invoke anyone):** subagents cannot spawn subagents, so the architect cannot consult a specialist itself. Instead the architect returns zero-or-more **consultation requests** alongside its table rows, and the orchestrator (the LLM running this spec) performs the invocations. Run the loop:

1. Invoke the `architect` agent (mandatory, per above). It returns the table rows (Layer Map / Key Design Decisions / File Impact / Risk seeds / Constitution flags) AND zero-or-more consultation requests, each carrying a named specialist + a sub-question + context.
2. For each consultation request: invoke the named specialist via the Task tool with the architect's sub-question + context, capture the specialist's response, then **re-invoke the `architect`** with the relayed response so the architect can synthesize it into its decision. The architect never invokes the specialist — the orchestrator relays both directions.
3. The orchestrator MAY also consult a specialist directly when this spec calls for it, not only on the architect's request.

Any planning-relevant specialist may be named: `architect`, `frontend-engineer`, `backend-engineer`, `security-reviewer`, `db-engineer`, `migration-engineer`, `api-designer`, `performance-analyst`, `design-auditor`, `mobile-engineer`, `devops-engineer`, `qa-engineer`.

**Brief shape (pass file paths, NOT inlined content):**

- `specs/<feature>/spec.md`
- `specs/<feature>/research.md` (if exists)
- `specs/<feature>/data-model.md` (if drafted at 1.1)
- `specs/<feature>/contracts.md` (if drafted at 1.2)
- `CLAUDE.md` (architect reads `## Architecture` + `## Packages` directly)
- `constitution.md`

The architect inherits the parent session's Read tool surface and will fetch these itself. Do not summarize their content in the brief — that double-pays context and risks drift.

**Sub-questions (always asked):**

1. Which architectural layers does this feature touch? Return as Layer Map table rows (`layer | what | files`).
2. Are there architectural decisions with multiple valid approaches not resolved by Phase 0 research? Return as Key Design Decisions table rows (`decision | chosen | why | rejected`).
3. Any dependency-direction or package-boundary risks? Return as Risk seeds (likelihood / impact / mitigation hint).
4. Any constitution rules at risk under this approach? Return as one-line flags for the Constitution Compliance section.
5. What is the MINIMAL change that satisfies the in-scope ACs? Return as a one-line statement of the smallest design that meets the §5 acceptance criteria — the baseline the Key Design Decisions must not exceed without justification.
6. For each Key Design Decision, is the concern it addresses in scope per the spec's §6 Out of Scope? Return one line per decision, in one of two conditional forms — in-scope: `decision → in-scope: <AC/constraint cited>` (the OOS half is omitted); OOS-reaching: `decision → OOS: <§6 entry> → escalate` (the in-scope half is omitted). A decision whose concern §6 excludes must NOT be silently solved — the architect escalates it to the user per its Rule 6 (termination), triggered by its Rule 9 OOS-respect check, and the orchestrator surfaces the escalation to the user rather than transcribing the decision.

**Return shape:** architect MUST author table rows verbatim-ready for Phase 2 transcription (no orchestrator paraphrasing) and the architect's standard output already carries a `### Specialists Consulted` block (per its Output Format); the orchestrator transcribes those entries — plus any specialists it consulted directly — into the plan's **Specialist Consultation** table (one row each, with Verdict + Cites).

**Halt rule:** if you reach Phase 2 without having completed this consultation, halt, invoke the architect now, then write the Specialist Consultation section at the top of plan.md (per the Phase 2 template) before drafting any of the Phase 2 tables. Provenance recording is part of the contract — Phase 2 tables drafted without a corresponding Specialist Consultation entry are a hard error.

## PHASE 2: Write the Plan

Save to `specs/[feature-name]/plan.md`. The Layer Map below shows a Domain/Data/Presentation example consistent with Clean Architecture; the actual layer rows MUST match the project's architecture as declared in `CLAUDE.md` (the `## Architecture` section + the per-package `## Packages` table for multi-stack projects). For monorepos, the layer column may instead be per-package (e.g., `apps/web`, `services/api`) — follow whatever shape the project's `CLAUDE.md` establishes.

```markdown
# Plan: [Feature Name]

**Date**: [YYYY-MM-DD]
**Spec**: [path to spec.md]
**Status**: Draft

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: [yes — see research.md §Alternatives Compared | no — N/A (no 2+ alternatives compared, OR alternatives were mechanical per CLAUDE.md project-defaults — one-line reason: ___)]
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): [see Specialist Consultation table]

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: [rows N-M]
- Key Design Decisions: [rows N-M]
- Risk Assessment seeds: [rows N-M]
- Constitution Compliance flags: [list | none]

[Specialist Consultation table — emit via `plan_helper render-consultation-block` per the instruction below this template, then fill rows]

## Summary

[2-3 sentences: what this plan implements and the technical approach]

## Technical Context

**Architecture**: [from constitution — which layers are involved]
**Error Handling**: [pattern to use]
**State Management**: [approach for this feature]

## Constitution Compliance

[Verify the planned approach doesn't violate any NON-NEGOTIABLE rules]
- Rule X: [compliant / requires attention]
- Rule Y: [compliant / requires attention]

## Implementation Approach

### Layer Map

[Which architectural layers this feature touches and what happens in each]

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Domain | [types, interfaces, use cases] | [file paths] |
| Data | [repositories, API calls] | [file paths] |
| Presentation | [components, views, state] | [file paths] |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| [decision] | [approach] | [rationale] | [alternatives] |

### Established-Convention Departures

[Include this subsection ONLY if ≥1 Key Design Decision is flagged "DEPARTURE" in its Why column (per architect Rule 3). Omit the entire subsection — heading and table — when there are no departures (e.g. greenfield or first-touch concerns).]

| Departure | Established Pattern Left | Why Necessary |
|-----------|--------------------------|---------------|
| [new pattern chosen] | [what the codebase already does for this concern] | [why the established pattern genuinely doesn't work here] |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| [path] | Create/Modify | [brief description] |
| [path] | Create/Modify | [brief description] |

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| docs/<package>/overview.md | Update/Create | [what needs documenting at the package level] |
| docs/<package>/architecture.md | Update | [if package-level layer patterns change] |
| docs/<package>/<concern>/index.md | Update/Create | [if a concern's Purpose or Structure changes] |
| docs/architecture.md | Update | [if cross-package architecture patterns change] |

[If no documentation impact: "No documentation changes expected — internal implementation only."]

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [risk] | Low/Med/High | Low/Med/High | [how to handle] |

## Dependencies

[Any external dependencies: packages to install, services to configure, environment variables]

## Supporting Documents

- [Research](research.md) — if research was performed
- [Data Model](data-model.md) — if data entities are involved
- [Contracts](contracts.md) — if API changes are involved
```

For the `## Specialist Consultation` section's consultation table, emit the controlled-shape skeleton via the helper and fill its rows — one row per specialist consulted (Verdict from the enum `accepted` / `modified` / `rejected` / `no-response`; Cites required; the `(none)` row stays when no specialist was consulted):

```bash
.devforge/lib/plan_helper render-consultation-block
```

The helper takes no arguments and owns the column names and verdict enum. Copy its stdout into the `## Specialist Consultation` section of `plan.md` and fill the rows; this table is the single source of truth for consultation provenance.

## PHASE 2.5: Plan-Spec Cross-Reference Check

Before presenting the plan to the user, verify completeness:

1. Read every AC from the spec's Acceptance Criteria section.
2. For each AC, verify the plan addresses it:
   - Check the plan's "Layer Map" and "File Impact" for files/components related to this AC.
   - Check "Key Design Decisions" for approach decisions relevant to this AC.
3. If any AC has no clear implementation path in the plan:
   - Revise the plan to add the missing coverage.
   - If you cannot determine the implementation path, add it to the plan's Risk Assessment as: "AC-[N] has no clear implementation path — requires clarification during breakdown".
4. Check the reverse: does the plan's File Impact list files NOT in the spec's Affected Areas? If yes, note them as additions discovered during planning (add to the plan's File Impact table with a note).
5. **Surface departures.** If any Key Design Decision is flagged `DEPARTURE` in its Why column (per architect Rule 3), fill the `### Established-Convention Departures` subsection — one row per departure — and include the departures line in the Phase 3 approval summary. If there are no departures, omit both the subsection and the summary line entirely; do not emit an empty section or a "none" line (greenfield stays silent).
6. **Out-of-scope-respect trace.** For each Key Design Decision, read its `Why` rationale and confirm it traces to an in-scope AC or constraint — and that it does NOT reference a term the spec marked Out of Scope in §6, nor an unverified hypothesis carried in from the user's prompt or upstream handoff. Flag any decision whose rationale reaches into §6 OOS: a decision solving an excluded concern is an over-solve. On a flag, do not silently keep the decision — re-enter Phase 1.3, have the architect either re-scope the decision to the in-scope baseline (its Phase 1.3 sub-question 5 minimal change) or escalate the §6 concern to the user per its Rule 6 (termination), triggered by its Rule 9 OOS-respect check. This is the read-side backstop for the §6-respect the architect's sub-question 6 asks at Phase 1.3 (defense in depth — sub-question 6 prevents an OOS-reaching decision; this step catches one that slipped through). **v1 is an LLM-prose step** the orchestrator performs by reading each decision's rationale against the spec's §6 entries (the same §6 lines `render-findings-from-spec` enumerated at Phase 1.5). The mechanized form — a `plan_helper` token-overlap scan of decision rationales against the §6 OOS terms (the same token-overlap technique `/specify`'s `verify-scope-coherence` already uses to warn when a §5 AC / §4 affected-area mandates a concern the §6 Out-of-Scope excludes — structurally identical: §6 OOS as the source term-set, a second text body as the scan target) — is **DEFERRED** to a later pass, built only after empirical miss-rate justifies it; it is NOT part of v1.

## PHASE 3: User Approval

**Mode-dependent execution path** (Patch 4 per PLAN-COMMAND-REDESIGN-PLAN.md — auto vs interactive paths, verbatim from parity-validated `/plan` v2):

- **If auto mode is active** (detect via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously): do not pause for clarifying questions during plan creation. Apply model's recommended defaults to any decision the spec left as `[default applied]` or that the plan surfaces fresh. Document each in a "Decision Points Resolved" subsection of the plan summary, marked `[default applied]`. The user reviews defaults at the approval gate below.
- **If auto mode is NOT active** (interactive mode, default): if the plan surfaces decision points the spec didn't resolve (e.g., between filter patterns, single-target invocation methods, or override mechanisms), pause and ask the user via `AskUserQuestion` (or fallback to numbered markdown list) before writing. Do not silently apply defaults in interactive mode.
- **When uncertain about mode**: prefer pausing (interactive default). Asking and waiting is reversible; proceeding without input is not.

**HARD GATE**: The plan MUST be approved before `/breakdown` can generate tasks.

Present a summary. The block below is LLM-authored (not helper-driven — plan state lives on disk in `plan.md`, not in a state JSON; there is no `render-plan-summary` subcommand to invoke):

"I've created the technical plan at `specs/[feature-name]/plan.md`.

**Approach**: [1-2 sentences]
**Files affected**: [count] ([N] new, [M] modified)
**Key decisions**: [list the most important ones]
**Departures from convention**: [include this line ONLY if ≥1 departure flagged: "[N] flagged — review §Established-Convention Departures before approving"; omit the entire line when none]
**Risks**: [high-risk items if any]
**Supporting docs**: [list what was generated]"

Then ask via `AskUserQuestion`:

- Question: `"Approve this plan?"` — single-line text.
- Options: `["approve", "request-changes", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`approve`** → proceed to Phase 4 (manual handoff block).
- **`request-changes`** → in the next turn, ask the user which section or decision to revise. Re-enter the relevant phase (Phase 0 Research Evaluation if research signals changed / Phase 1 / Phase 1.5 / Phase 2 / Phase 2.5 as needed); re-render the affected portion of `specs/[feature-name]/plan.md` via Write or Edit; re-present the summary above and re-issue this approval prompt. The state lives in the rendered file on disk; this loop mutates it in place.
- **`cancel`** → tell the user `"/plan cancelled. Plan draft preserved at specs/[feature-name]/plan.md."` and end the turn.

## PHASE 4: Manual handoff to /breakdown

On `approve`, first write the structured plan→breakdown handoff via the helper. The `<plan-path>` for the calls below is the absolute path to the plan written in Phase 2 — `specs/NNN-<feature>/plan.md` (the same path shown in the Phase 3 approval summary).

```bash
.devforge/lib/plan_helper finalize-handoff <plan-path>
```

The helper parses the rendered `plan.md` and atomic-writes `specs/NNN-<feature>/plan-handoff.json` (a structured handoff carrying the breakdown seeds — layer map, file impact, decisions, risks, specialist consultation, dependencies — plus provenance to the sibling `/specify` handoff). Handle the exit code:

- Exit 0 → the helper wrote `specs/NNN-<feature>/plan-handoff.json` and printed its path on stdout. Surface the written path to the user in one line, e.g. `"Structured plan handoff written: <path> (for /breakdown to consume once its reader is built)."`
- Non-zero exit (Exit 2 → `plan.md` not found or rendered content failed schema validation; Exit 1 → I/O error writing `plan-handoff.json`, e.g. permissions or disk-full) → the helper could not write or validate the handoff. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Do NOT abort — continue to the `render-breakdown-handoff` text block below. The structured handoff is best-effort; the manual text block is the guaranteed human bridge.

The `plan-handoff.json` is the **producer side** of the plan→breakdown handoff. The `/breakdown` consumer/reader does not exist yet — it will conform to this producer when it is built. There is no auto-dispatch and no auto-consume: the manual text block below remains how the user launches `/breakdown`.

Then emit the deterministic handoff block via the helper:

```bash
.devforge/lib/plan_helper render-breakdown-handoff <resolved-path> <plan-path>
```

Handle the exit code:

- Exit 2 → the spec or plan file could not be read. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), tell the user to verify `specs/NNN-<feature>/plan.md` exists and re-run `/plan`, and end the turn. Unlike `finalize-handoff`'s non-blocking exit 2 above (which continues to this block), a failure here DOES end the turn — this block is the guaranteed human bridge, and if it cannot render there is no fallback next-step to fall through to.
- Exit 0 → stdout is the deterministic manual-next-step block — copy it VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The block heading reads `## Manual next step — run /breakdown`; it carries the spec AC count, plan file-impact count, plan risk count, and the literal `/breakdown <plan-path>` invocation. The block also instructs the user to **restart Claude Code** before running `/breakdown` so any newly-installed command is picked up.

After the block lands in the user-facing message, end the turn with one short confirmation: `"/plan is done. Plan status: Draft — plan stays Draft until /breakdown runs (forward reference: /breakdown spec — not yet ported into this framework). Restart Claude Code, then copy the /breakdown command above to continue."` Do NOT restate the `/breakdown` invocation in your closing sentence — the block already contains the literal `/breakdown <plan-path>` line.

## IMPORTANT RULES

1. **Plans describe HOW, not WHAT** — the spec already defines WHAT. Don't repeat requirements, translate them into technical decisions.
2. **Constitution compliance is mandatory** — verify before presenting to user. If the plan would violate a rule, redesign or flag it.
3. **Reference existing code** — for existing codebases, always reference actual file paths and existing patterns. Don't propose new patterns when existing ones work.
4. **Greenfield: follow the scaffolding guide** — the constitution's Section 7 defines where things go. Follow it.
5. **Minimal supporting docs** — only create research.md, data-model.md, contracts.md if they're actually needed. Don't create empty files.
6. **Memory check** — consult MEMORY.md for lessons about similar technical decisions.
7. **Keep it scannable** — tables over paragraphs, decisions over discussions.
8. **Docs context comes from the spec** — the spec already incorporates `docs/` knowledge. Do not re-read docs; use the spec's "Current State" and "Affected Areas" sections. If the spec notes stale or missing docs, carry that forward as a plan risk.
