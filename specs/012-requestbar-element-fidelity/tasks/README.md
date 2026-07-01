# Tasks: 012-requestbar-element-fidelity

**Spec**: specs/012-requestbar-element-fidelity/spec.md
**Plan**: specs/012-requestbar-element-fidelity/plan.md
**Generated**: 2026-07-01
**Total tasks**: 4

## Dependency Graph

```
001 (restructure requestbar markup) ──→ 002 (rebind requestbar css) ──→ 004 (fidelity ct suite)
003 (rebind dropdown panel css) ─────────────────────────────────────→ 004 (fidelity ct suite)
                                                             001 ──────→ 004
```

- 001 and 003 are independent (parallelizable).
- 002 depends on 001 (CSS references the `.url-bar` container the markup produces).
- 004 (all fidelity CT + screenshot rebaselines) converges on 001 + 002 + 003.

## Task Index

| #   | Title                                 | Agent             | Depends on    | Status   |
| --- | ------------------------------------- | ----------------- | ------------- | -------- |
| 001 | restructure requestbar markup         | frontend-engineer | None          | Complete |
| 002 | rebind requestbar css fidelity        | frontend-engineer | 001           | Complete |
| 003 | rebind shared dropdown open-panel css | frontend-engineer | None          | Complete |
| 004 | computed-style fidelity ct suite      | qa-engineer       | 001, 002, 003 | Complete |

## Specialist Consultation

| Specialist | Sub-question                                                                                                                   | Input summary                                                                                                                                                                                                                                                                                                                                                         | Verdict  | Cites                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------- |
| architect  | Atomicity/bundling, dependency direction, contract-chain integrity, implementability, and agent assignment of the 4-task draft | Sound with 2 revisions: move the Dropdown fidelity CT out of frontend T3 into qa T4 (T3 → Dropdown.css only; add T4→T3 edge, consolidating all AC-11 CT + screenshot rebaselines in T4); AC-1's Dropdown side assigned to T3 as no-op-satisfied. No consultation requests. Q-2 runtime fidelity check is handled by `/review`'s design-auditor, not a breakdown task. | modified | docs/architecture.md:240-275 (method-select cascade hazard); own-reasoning |
| (none)     | —                                                                                                                              | —                                                                                                                                                                                                                                                                                                                                                                     | —        | —                                                                          |

## Additions to Spec

None — every touched file was enumerated in the plan's File Impact table; no cascading files discovered in Phase 1. The `link` Icon atom (icons.ts:72) is reused unchanged.

## Risk Assessment

| Task | Risk | Reason                                                                                                                                                                                                                                                                                                                                   |
| ---- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 001  | Low  | Presentational markup only; the one hazard — dropping Share's visible label — is mitigated in-task by the restored `aria-label="Share"` and the `getByRole` name assert.                                                                                                                                                                 |
| 002  | Med  | Method-trigger CSS edit could reintroduce the white-on-white chip regression (counter-rules drift from `METHODS`) or kill all per-method colours (accidental `color` decl). Mitigated by keeping `color` unset, keeping the seven `(0,5,0)` counter-rules in lockstep, and per-method colour asserts across mstyle variants in task 004. |
| 003  | Low  | Shared Dropdown panel rebind ripples to dev-only (tree-shaken) PrimitivesDemo + visual snapshots; edit bounded to box-shadow + item padding + panel gap, snapshot deliberately rebaselined in task 004.                                                                                                                                  |
| 004  | Med  | CT flakiness — Radix dismiss arm-race, keycap-mount no-reflow baseline confound, jsdom cannot resolve computed/pseudo styles. Mitigated by real-browser Playwright CT, two-step dismiss gate, non-empty-URL no-reflow baseline, and fixture-scoping per MEMORY lessons.                                                                  |

_AC coverage: all AC-1..AC-19 covered (verify-ac-coverage ok). Agent roster: frontend-engineer + qa-engineer both installed (verify-agent-roster ok). Design manifest: present + valid (verify-manifest-present ok; empty — reference.html carries no data-ref anchors, so per-element fidelity values live in design/styles.css, enforced by the static token-provenance check + `/review` design-auditor)._

_Contract chain (documented deferral): verify-contract-chain exits 2 with 34 ADVISORY findings, all resolved by inspection — the checker does literal string-matching and self-notes it cannot see spec ACs or existing-codebase state. Every "orphan Produces" maps to a spec AC or feeds a downstream Expects (T1 `.url-bar`/placeholder/Share → AC-7/8/12 + T2/T4 Expects; T2 method/Save rules → AC-9/13 + T4 Expects; T3 panel rules → AC-10 + T4 Expects; T4 CT → AC-10/11/19). Every "unsatisfied Expects" is verified existing state (link icon icons.ts:72; placeholder `Enter URL` RequestBar.tsx:290; `justify-content:center` RequestBar.css:87; `box-shadow var(--shadow-md)` Dropdown.css:45; tokens/METHODS defined) or an upstream Produces (T2←T1, T4←T1/T2/T3). No real orphan or gap._

## Review Checkpoints

| Before Task | Reason                                                              | What to Review                                                                                                                                                                                                                              |
| ----------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 002         | High-risk (method-trigger cascade / chip regression)                | Confirm `color` stays unset on `.request-bar__method.method`, `justify-content:center` removed, seven chip counter-rules intact and in lockstep with `METHODS`; Save rest+hover bound to reference tokens.                                  |
| 004         | Convergence (depends on 001+002+003) + deliberate visual rebaseline | Confirm computed-style asserts match `design/styles.css` values, screenshot threshold `0.01/0.1`, mstyle variants beyond soft covered, non-empty-URL no-reflow baseline, and the Dropdown panel snapshot rebaseline is the intended change. |
