# Tasks: 018-code-editor-extract

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/018-code-editor-extract/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/018-code-editor-extract/plan.md
**Generated**: 2026-07-16
**Total tasks**: 5

## Dependency Graph

```
001 (create-codeeditor-molecule) ──→ 002 (wire-bodyeditor-consumer) ──→ 004 (update-bodyeditor-ct)
                                 ──→ 003 (codeeditor-fidelity-ct) ─────→ 004
                                                                    002 ──→ 005 (docs-codeeditor-molecule)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | create-codeeditor-molecule | frontend-engineer | None | Complete |
| 002 | wire-bodyeditor-consumer | frontend-engineer | 001 | Complete |
| 003 | codeeditor-fidelity-ct | frontend-engineer | 001 | Complete |
| 004 | update-bodyeditor-ct | frontend-engineer | 002, 003 | Complete |
| 005 | docs-codeeditor-molecule | tech-writer | 002 | Complete |

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Atomicity / ordering / contract-chain / implementability of the 5-task decomposition | Approved with 4 revisions: R1 move fidelityAssert Expect T001→T003 (§7 test-only); R2 T003 inline fixtures + resetKey-driver harness; R3 port :769/:811 to T003 as resetKey-driven, T004 removes them + keeps org-level wiring assertion; R4 spec-017-vs-018 AC-number namespace note | modified | specs/018-code-editor-extract/plan.md; src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx:769,811 |
| (none) | — | — | — | — |

All four architect revisions (R1–R4) were applied to the task files before writing.

## Additions to Spec

None — all task files map to the plan's File Impact rows (7 source/test files + 2 docs files), no cascading files discovered in Phase 1.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | High | Overlay pixel-grid alignment (transparent textarea over highlighted pre) is fidelity-sensitive; the `resetKey` effect port + `--code-line-h` single-sourcing must preserve exact geometry and the AC-17 T7a contract. |
| 002 | Med | Removing the two `activeTabId` effects + inline overlay from BodyEditor must not disturb mount-all/none/urlencoded/mode-strip behavior; the `resetKey={activeTabId}` wire is the sole AC-6 restore point. |
| 003 | Med | CT green-but-wrong if the fixture omits the full styling context (tokens.css + data-mstyle + `.code-editor` scope); AC-6 tests must drive `resetKey` directly, not via tabsStore. |
| 004 | Med | Convergence (deps 002+003); must not open an AC-6/AC-8 coverage window — no `:769`/`:811` test removed before its T003 replacement exists (T003→T004 edge enforces). |
| 005 | Low | Surgical docs update only. |
| chain | Deferred (advisory) | `verify-contract-chain` reports orphan Produces / unsatisfied Expects because it does literal string-matching and cannot link prose contracts across tasks or to spec ACs / existing-codebase state. The chain is logically intact — architect-validated at Phase 2: T002/T003 Expect `CodeEditor exported` ← T001 Produces it; T004 Expects ← T002 (`BodyEditor renders <CodeEditor>`) + T003 (`CodeEditor CT covers fidelity`); T005 Expects ← T002; and T001's two Expects are existing-codebase state (`BodyEditor.tsx:296-327` overlay, `compose` exported in `jsonTokens.ts`). No real orphan or gap. |

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 001 | Design-decision + high-risk overlay | CodeEditor API `{value,lang,onChange,validVars,resetKey?}`, `resetKey` effect port fidelity, `--code-line-h` single-sourcing, testid preservation, no organism/tabsStore import |
| 002 | Layer boundary crossing (org consumes molecule) | Inline overlay + both `activeTabId` effects removed; `resetKey={activeTabId}` wired; mount-all/none/urlencoded unchanged |
| 004 | Convergence (2 deps) | Fidelity/AC-6 tests re-homed cleanly; body-* testid + wiring assertions retained; no coverage window |
