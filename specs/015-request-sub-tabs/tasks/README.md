# Tasks: 015-request-sub-tabs

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/015-request-sub-tabs/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/015-request-sub-tabs/plan.md
**Generated**: 2026-07-06
**Total tasks**: 5

## Dependency Graph

```
001 (tabsStore activeSubTab state + action) ──┐
                                              ├─→ 003 (RequestSubTabs organism) ──→ 004 (§6 fidelity CSS + CT) ──┐
002 (Tabs opt-in panel-linkage prop) ─────────┘                                └──────────────────────────────┴─→ 005 (App compose request pane)
```

- 001 and 002 are independent (parallel-ready) — both feed 003.
- 003 → 004 (CSS/CT target the organism DOM).
- 003 + 004 → 005 (App wiring converges the organism and its passing go/no-go CT; takes KVTable live).

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | tabsStore activeSubTab state and action | frontend-engineer | None | Complete |
| 002 | Tabs opt-in panel-linkage prop | frontend-engineer | None | Complete |
| 003 | RequestSubTabs organism | frontend-engineer | 001, 002 | Complete |
| 004 | RequestSubTabs §6 fidelity CSS and CT | frontend-engineer | 003 | Complete |
| 005 | App compose request pane (KVTable live) | frontend-engineer | 003, 004 | Complete |

## Additions to Spec

- **`src/renderer/src/__tests__/App.test.tsx`** (task 005) — a composed-pane mount smoke test. The plan's File Impact lists only 3 test files (RequestSubTabs.test.tsx, RequestSubTabs.ct.tsx, tabsStore.test.ts); this 4th is a breakdown-level addition mitigating Risk 5 (integration regression when the pane goes live). Flagged plan-additive.
- **`makeCollectionTab` seed** (task 001, same file `tabsStore.ts`) — the plan named only `makeBlankTab` for the `activeSubTab` seed; `makeCollectionTab` (tabsStore.ts:153) also constructs a `Tab`, so it must seed the field too or the type breaks. No new file — same File Impact row.
- **tokens.css path correction** (task 004, verify-only) — spec §4 + plan Layer Map cite `src/renderer/src/styles/tokens.css`, which does not exist; the real path is **`src/renderer/styles/tokens.css`**. Verify-only; no edit. All 6 §6 tokens confirmed present in both themes.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low | Additive store field + action; risk is breaking existing TabBar/RequestBar consumers (spec Risk 4) — mitigated by type-check both configs + the unit test. Both tab constructors must seed the field. |
| 002 | Low | Opt-in, byte-identical-when-off Tabs extension; risk is regressing the off-path selection-only contract (AC-5) — mitigated by the off-path CT assertion. |
| 003 | High | The core organism: mount-all + `hidden` toggle must preserve KVTable state (spec Risk 1) and literal focus (Risk 6, refocus-on-reshow); per-tab state must not leak (Risk 2); read-only badge selector must avoid over-render (AC-26). Convergence of 001+002. |
| 004 | High | §6 computed-style fidelity in both themes (spec Risk 3/7 — incomplete `.pane-tabs` neutralization drifts silently); focus-survives-switch CT is the R1 go/no-go gate before App wiring. |
| 005 | Med | Mounting the composed pane + taking KVTable live in the running shell (spec Risk 5) — mitigated by the composed-pane smoke test + running the full existing suite. |

_Auth-badge false-positive (spec Risk 8, High-likelihood/Low-impact): the bearer seed makes the Auth `•` show on every fresh tab. Truthful to the seed; a "meaningful-auth" heuristic and a seed change are both out of scope (§6). No task action — accepted, recorded here per the deferral convention._

_**Contract-chain gate deferral**: `verify-contract-chain` reports ORPHAN PRODUCES / UNSATISFIED EXPECTS on every task. All are the advisory false-positive class — the helper does literal Produces↔Expects text matching and structurally cannot see (a) terminal Produces that map to a spec AC (e.g. task 004 → AC-2/AC-27, task 005 → AC-11/AC-18) or (b) Expects that describe existing-codebase state (e.g. `Tab`/`makeBlankTab` in tabsStore.ts, the two Tabs button branches, KVTable/RequestBar/Shell). The real chain is intact and was confirmed clean by the Phase 2 architect validation: T001 Produces {SubTabKey/VALID_KEYS/activeSubTab/setActiveSubTab} → T003 Expects; T002 Produces {linkPanels} → T003 Expects; T003 Produces {RequestSubTabs + slot props + tabpanels} → T004 + T005 Expects; T004/T005 terminal Produces → AC-2/AC-27/AC-11/AC-18. Carried as a documented deferral per the Phase 3.5 convention._

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 003 | Convergence (depends on 001 + 002) + High risk | The store contract (SubTabKey/activeSubTab/setActiveSubTab) and the Tabs `linkPanels` prop are correctly consumed; badge selector reads the spec ref (no over-render); defensive reads (normalization + no-active-tab) hold; no organism/unbuilt-panel import. |
| 004 | Layer-boundary (first fidelity/CSS task) + High risk | The `.pane-tabs` scope hits every §6 computed target in both themes; the focus-survives-switch CT (R1 gate) is green before the pane is wired live. |
| 005 | Convergence (003 + 004) + integration (KVTable goes live) | The composed pane mounts in the shell without regression; KVTable is live in Params/Headers via root slot injection; RequestSubTabs still imports no organism. |

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate task atomicity, dependency ordering, contract-chain integrity, implementability, agent assignment for the 5-task decomposition | Approved T001–T005 with no restructuring; pinned 4 clarifications (named slot props not a Record map, auth glyph literal `•`, tokens path `src/renderer/styles/tokens.css`, App.test.tsx as a dedicated plan-additive smoke file); confirmed all Expects/Produces seams against source | accepted | tabsStore.ts:138,153; Tabs.tsx:370,544,605,428-436; App.tsx:23; design/styles.css:877-927 |
| design-auditor | (via architect) §6 fidelity + auth-glyph — re-consult? | Not re-requested; resolved at /plan from the `.tabbar` precedent, and double-gated downstream (design-manifest + task-004 computed-style CT) | no-response | own-reasoning (Tabs.css .tabbar block) |
