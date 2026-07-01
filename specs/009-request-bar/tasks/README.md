# Tasks: 009-request-bar

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/009-request-bar/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/009-request-bar/plan.md
**Generated**: 2026-06-28
**Total tasks**: 6

## Dependency Graph

```
001 (httpMethods source + retype method) ──→ 002 (tabsStore updateActiveSpec) ──┐
003 (amend constitution §4) ────────────────────────────────────────────────────┤
001 ───────────────────────────────────────────────────────────────────────────┤
                                                                                 ├─→ 004 (RequestBar organism) ──→ 005 (RequestBar CT)
                                                                                 │                              └─→ 006 (mount in App)
```

Linear reading: `001 → 002`; `003` independent (sequenced before `004`); `004` converges `{001, 002, 003}`; `005` and `006` both depend on `004`.

## Task Index

| #   | Title                                    | Agent             | Depends on    | Status   |
| --- | ---------------------------------------- | ----------------- | ------------- | -------- |
| 001 | add-httpmethods-source-and-retype-method | frontend-engineer | None          | Complete |
| 002 | add-tabsstore-updateactivespec-action    | frontend-engineer | 001           | Complete |
| 003 | amend-constitution-sole-subscriber-rule  | frontend-engineer | None          | Complete |
| 004 | build-requestbar-organism                | frontend-engineer | 001, 002, 003 | Complete |
| 005 | add-requestbar-component-test            | frontend-engineer | 004           | Complete |
| 006 | mount-requestbar-in-app-request-pane     | frontend-engineer | 004           | Complete |

## Additions to Spec

None — every task file traces to a plan File Impact row. The plan's Documentation Impact rows (docs/renderer/index.md, docs/architecture.md) are deliberately NOT breakdown tasks; they are `/finalize` tech-writer work.

## Risk Assessment

| Task | Risk | Reason                                                                                                                                                                                                       |
| ---- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 001  | Low  | Narrowing `method` string→HttpMethod; CBM-confirmed sole writer is makeBlankRequest (GET) — typecheck gate catches any stray non-listed assignment.                                                          |
| 002  | Med  | The no-op-no-dirty contract is subtle — over-dirtying breaks the non-dirty Save no-op (AC-10/AC-15). Covered by dedicated unit cases.                                                                        |
| 003  | Low  | Prose-only constitution edit; sequenced before 004 to avoid a code-vs-rule contradiction window (architect revision).                                                                                        |
| 004  | Med  | Largest task (organism + css + unit, 19 ACs); risks: a stray `requestSpec` import (§5.2), 2nd-subscriber over-render. Mitigated by `HttpMethod`+primitive typing and per-field selectors. Review checkpoint. |
| 005  | Med  | CT flakiness from the Radix dismiss arm-race + styling-context fixtures — mitigated by the two-step gate + tokens.css/data-mstyle fixture scoping.                                                           |
| 006  | Low  | One-line app-composition edit; layer-boundary integration. Review checkpoint.                                                                                                                                |

### Deferred gate findings

- **Contract-chain (verify-contract-chain, advisory)**: the gate reports orphan-Produces and unsatisfied-Expects across all 6 tasks. Every one is a literal-matcher false negative — each orphan Produces maps to a spec AC the gate cannot see (e.g. `METHODS`/`HttpMethod` → AC-2/AC-22, `updateActiveSpec` → AC-9/AC-10, `RequestBar` export → AC-1), and each unsatisfied Expects is either existing-codebase state (`RequestSpec`, `Dropdown`, `Icon`, `markClean`, `ShellPanes`) or an upstream Produces phrased differently (004 Expects "METHODS from 001" ↔ 001 Produces "exports METHODS const"). The Phase-2 architect explicitly validated contract-chain integrity (every Produces feeds a downstream Expects or a spec AC; every Expects traces to an upstream Produces or existing state). Accepted as a documented deferral.

## Review Checkpoints

| Before Task | Reason                                                                             | What to Review                                                                                                                                                            |
| ----------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 004         | convergence (depends on 001, 002, 003) + layer-boundary crossing into presentation | httpMethods type + updateActiveSpec contract + amended §4 are all in place before the organism is built; RequestBar reaches the method type without importing requestSpec |
| 006         | layer-boundary crossing into app composition (integration)                         | RequestBar mounts cleanly into the request pane; build succeeds; TabBar/Toast wiring unchanged                                                                            |

## Specialist Consultation

| Specialist | Sub-question                                                                 | Input summary                                                                                                                                                                                             | Verdict  | Cites                                                  |
| ---------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------ |
| architect  | Atomicity, dependency ordering, contract-chain integrity of the 6-task draft | Approved; required: sequence the constitution amendment before the RequestBar component (avoid code-vs-rule window); precision: markClean is pre-existing not produced by 002, 002→001 is an ordering dep | modified | specs/009-request-bar/plan.md; constitution.md §4/§5.2 |
