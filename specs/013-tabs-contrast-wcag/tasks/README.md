# Tasks: 013-tabs-contrast-wcag

**Spec**: specs/013-tabs-contrast-wcag/spec.md
**Plan**: specs/013-tabs-contrast-wcag/plan.md
**Generated**: 2026-07-02
**Total tasks**: 3

## Dependency Graph

```
001 (Sync muted/faint tokens) ──┐
                                 ├──→ 003 (Contrast CT + re-baseline)
002 (Swap active-tab accent) ───┘

001 ∥ 002  (independent — no edge)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | Sync drifted muted and faint token values | frontend-engineer | None | Complete |
| 002 | Swap active-tab accent-on-light sites to text token | frontend-engineer | None | Complete |
| 003 | Add Tabs contrast CT assertions and re-baseline screenshots | qa-engineer | 001, 002 | Complete |

## Additions to Spec

- **`design/tokens.json` — dark `textFaint` sync (Task 001).** The plan's File Impact lists only `tokens.css`. Phase 1 discovered that `design/tokens.json` (the DTCG artifact the `tokens.css` header names as its source) declares dark `textFaint: #71717a` — the stale value — disagreeing with `design/styles.css` (#787881, the spec's declared source of truth). No generator wires tokens.json → tokens.css (the header's "regenerate" note is stale). Because dark faint IS one of the three in-scope sync values, the architect (Finding A) ruled the one-line JSON fix in scope to keep the two design artifacts consistent. AC-1 greps `tokens.css` only, so this adds no acceptance check.
- **Stale fallback literals at Tabs.css:97/326/388 — noted, NOT changed.** Post-sync, the defensive fallback literals on the unchanged muted/faint sites (`, #71717a` / `, #a1a1aa`) no longer match the resolved token values. Spec §6 / plan keep these lines untouched (fixed by the token sync at runtime); left as-is deliberately. Not a task.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Med | Token darkening shifts muted/faint text app-wide across ~9 components (Modal, Toast, Dropdown, RequestBar, TabBar, Titlebar, Statusbar, PrimitivesDemo) — intended design-source-authoritative change, but the 3 committed screenshot baselines shift and are re-based in Task 003 (spec R1). |
| 002 | Low | Two-line color-only swap; the `.tabbar` variant inherits line 149 (confirmed: Tabs.css:480-481 sets only box-shadow+background — spec R3). No-fallback departure is gate-required (architect Finding B). |
| 003 | Med | Dark-theme CT mount (`data-theme='dark'`) is a new harness technique (spec R2 — single-variant baseline previously missed dark); re-baseline correctness depends on visual confirmation of the 3 regenerated PNGs, not blind `--update-snapshots`. |

_AC coverage: all 10 ACs covered (verified Phase 3.5). Agent roster: all installed. Design manifest: present-and-valid (empty — reference.html carries no `data-ref` elements)._

_**Contract chain — advisory findings, deferred (documented).** `verify-contract-chain` (a verbatim string-matcher blind to AC-mapping and codebase state) flagged every T001/T002 `Produces` as an "orphan" and every `Expects` as "unsatisfied". These are false positives by construction: (a) each `Produces` maps to a covered spec AC — `verify-ac-coverage` passed 10/10 — and feeds T003's "Task NNN landed" `Expects` (phrased narratively, so not string-matched); (b) each `Expects` traces to existing-codebase state (T001/T002) or an upstream `Produces` (T003 depends on 001+002). The Phase-2 architect independently confirmed the chain is sound. No structural gap — deferred._

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 002 | Layer boundary (token → component) + carries Risk R3 | Confirm the `.tabbar` active variant inherits the swapped label color (no `color` in Tabs.css:480-481); confirm no fallback literal on the two swapped sites. |
| 003 | Convergence (depends on 001 + 002) | Confirm both upstream edits landed; confirm the 3 regenerated baselines show only the intended text darkening; confirm dark-theme assertions actually toggle `data-theme`. |

## Specialist Consultation

Record one row per specialist consulted during breakdown planning. The architect is the decision-authority and synthesizer; specialists supply domain input only.

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate atomicity / ordering / contract-chain / implementability of the 3-task set; rule Finding A (tokens.json drift) and Finding B (fallback vs provenance gate) | Confirmed 3-task decomposition, no bundle (different layers), no T003 split, DAG `001∥002→003` correct. Ruled Finding A → add tokens.json dark-faint sync to T001; Finding B → `var(--text)` no fallback on 149/233; required T003 contract-specificity (named selectors/properties, computed-color equality not ratio, 3 snapshot ids, dark-theme mount). | modified | own-reasoning; Tabs.css:120,149,233,480-481; design/tokens.json; design/styles.css:19-20,62 |
