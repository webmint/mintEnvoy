# Plan: CodeEditor Extraction

**Date**: 2026-07-16
**Spec**: specs/018-code-editor-extract/spec.md
**Status**: Approved

> **Grill-revision (cycle 1)**: this plan replaces the prior draft to address the confirmed `/grill` finding (F-001, High). The prior D3 gave CodeEditor a props-only API `{value,lang,onChange,validVars}` and removed BodyEditor's `activeTabId`-keyed reset/re-arm effects with no substitute, so AC-6's tab-switch reset could not fire when two tabs held identical raw text+lang. **D5** (below) adds a `resetKey` prop that ports those effects into CodeEditor, driven by `resetKey={activeTabId}`. See `specs/018-code-editor-extract/grill.md`.

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: no — N/A. Alternatives settled upstream in the research handoff (verbatim lift-and-shift rejected); the reset-trigger fix alternatives (D5) were compared by the architect at Phase 1.3, not by fresh web research.
- Phase 1.3 architecture decisions: yes (mandatory; re-consulted for the grill-revision)
- Specialists consulted (orchestrator-relayed or direct): none (see table)

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: rows 1-5 (rows 1-2 revised for D5)
- Key Design Decisions: rows D1-D5 (D3 revised, D5 new)
- Risk Assessment seeds: rows 1-6 (row 6 new — resetKey port risk)
- Constitution Compliance flags: §2.2, §2.3, §3.6 (all satisfied, no departure)

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| (none) | — | — | — | — |

Behavior-preserving renderer-only extraction; the D5 reset-trigger fix is a renderer React prop/boundary design within generalist-director scope. Architect validated D5 against BodyEditor.tsx:104-128 + the two AC-6 regression CTs; no security/schema/perf/UX depth required, no consultation request emitted.

## Summary

Extract the raw-mode code editor inlined in `BodyEditor` into a new self-contained, reusable `CodeEditor` molecule. Reuse `jsonTokens.compose()` unchanged; replace the two duplicated line-box literals with ONE local CSS var `--code-line-h` (= `calc(12.5px * 1.65)` = 20.625px) driving textarea/pre/gutter rows. Because two request tabs can hold identical raw text+lang, CodeEditor exposes an optional `resetKey` prop — a generic reset-on-change signal — and BodyEditor passes `resetKey={activeTabId}` so the ported tab-switch scroll reset + colored-snapshot invalidation (AC-6) still fires when value+lang are unchanged. BodyEditor's raw slot becomes a `<CodeEditor resetKey={activeTabId} …>` consumer; `body-*` testids and the T7a fidelity contract are preserved. No research signals; alternatives settled upstream.

## Technical Context

**Architecture**: renderer atomic-design tiers — new `CodeEditor` at the molecules tier (domain-agnostic primitive), consumed downward by the `BodyEditor` organism (§2.2, no sibling-organism import). `jsonTokens` (lib/) reused read-only. CodeEditor holds zero tabsStore/activeTabId awareness — the consumer maps its domain key onto the opaque `resetKey` scalar.
**Error Handling**: renderer-pure graceful degrade preserved — `compose()`'s `JSON.parse` malformed-JSON detector untouched (AC-17 degrade-to-plain path).
**State Management**: `CodeEditor` is self-contained — owns its 100ms compose debounce + colored snapshot; core props `{value, lang, onChange, validVars}` plus optional `resetKey`. No new zustand store; body value stays owned by `tabsStore` via BodyEditor's existing `updateActiveSpec` write.

## Constitution Compliance

- §2.2 Renderer Tier Org: compliant — CodeEditor lands in `molecules/`; BodyEditor→CodeEditor is a legal downward import; `resetKey` is a generic scalar signal so the molecule holds no tab/tabsStore/activeTabId awareness (stays reusable, AC-15).
- §2.3 Import & Path Rules: compliant — `resetKey` adds no import; CodeEditor's lib imports and BodyEditor's CodeEditor import use the `@renderer` alias, no deep relative paths.
- §3.6 Simplicity & Reuse: compliant — `compose()` reused byte-unchanged; the reset/re-arm effects are moved and parameterized (`activeTabId`→`resetKey`), not reimplemented; `--code-line-h` collapses a duplicated literal (DRY).
- Styling (soft `Prefer` tokens over literals, constitution:199): compliant, not a departure — `--code-line-h` single-sources literals `.code-editor` already hardcodes; §6 bars promoting it to `tokens.json`.
- fidelityAssert test-only (§7 constraint): compliant — imported only by `CodeEditor.ct.tsx`, never by the production component.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Presentation — molecules | NEW reusable `CodeEditor`: three-layer overlay (gutter + aria-hidden `<pre>` + transparent `<textarea>`, single scroll source) owning `compose()`+100ms debounce+colored snapshot, `gutterDivs`/`tokenSpans` memos, onScroll sync; scroll-reset + `setColored(null)` invalidation AND the compose-debounce re-arm keyed on the **`resetKey` prop** (verbatim port of BodyEditor.tsx:104-128, parameterized off `activeTabId`→`resetKey`); local `--code-line-h` drives all three grid row heights | `src/renderer/src/components/molecules/CodeEditor.tsx` (new), `src/renderer/src/components/molecules/CodeEditor.css` (new) |
| Presentation — organisms | `BodyEditor` consumes `<CodeEditor resetKey={activeTabId} value/lang/onChange/validVars>` in the raw slot (296-327); inline overlay markup + editor state/memos + BOTH `activeTabId`-keyed effects (reset 104-114, re-arm 122-128) + code-area CSS removed — the reset now fires via `resetKey={activeTabId}`; toolbar/radiogroup/lang-pill/mount-all panels retained | `src/renderer/src/components/organisms/BodyEditor.tsx` (modify), `src/renderer/src/components/organisms/BodyEditor.css` (modify) |
| Support — lib | `jsonTokens.compose()` reused UNCHANGED (import only — AC-11 + JSON.parse detector); `varTokens.isMissingVar`, `envVars` unchanged | `src/renderer/src/lib/jsonTokens.ts` (read-only) |
| Test — molecules CT | NEW `CodeEditor.ct.tsx`: relocated AC-23 live/debounced guard + row-height equality (textarea/pre/gutter all = 20.625px) via computed-style channel; the AC-6 reset contracts (identical-body re-arm + scroll-bleed reset) driven via `resetKey`; full styling context (tokens.css import + data-mstyle + `.code-editor` scope) | `src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx` (new) |
| Test — organisms CT | `BodyEditor` CT/stories retain integration + `body-*` testid assertions + the AC-6 `resetKey={activeTabId}` wiring assertion; fidelity/alignment ACs move to CodeEditor CT | `src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx` (modify), `.../BodyEditor.stories.tsx` (modify) |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| D1 Placement | `CodeEditor` in `molecules/` | §2.2 domain-agnostic → molecules; lets BodyEditor (and a future response-body organism) consume it downward with no sibling-organism import (AC-9, AC-15). Follows Dropdown/Tabs/Divider precedent — not a departure. | `organisms/` (forces sibling-organism import — §2.2 violation); `atoms/` (owns compose+debounce+state, not a primitive) |
| D2 Line-box unit | ONE local CSS var `--code-line-h = calc(12.5px * 1.65)` = 20.625px scoped to `CodeEditor.css`, driving textarea + pre + gutter row heights | Single-sources the duplicated literal → DRY (AC-12); absolute px keeps the gutter off the `1.65em` trap that drifts against the 11.5px gutter font (AC-13, AC-20, AC-21). Component-internal metric → local var, NOT `tokens.json` (§6). | `tokens.json` global token (OOS §6); `1.65em` on gutter (the original bug); per-element repeated literals (breaks DRY + AC-13) |
| D3 API shape | Self-contained `CodeEditor`, props `{value, lang, onChange, validVars, resetKey?}`; owns `compose()`+debounce(100ms)+colored snapshot; reuses `jsonTokens.compose()` UNCHANGED | §3.6 reuse-not-reimplement (AC-11); self-contained controlled-molecule matches Tabs precedent (AC-14 — the 4 core props still mount stand-alone; `resetKey` is additive/optional). `compose()` JSON.parse malformed-degrade detector untouched (AC-17). `colored` nullable preserved — `null` plain-degrade exercised by AC-2/AC-17 and by AC-6 invalidation; `{snapshot,tokens}` colored by AC-11/AC-23. | Passing composed tokens in as a prop (leaks internals, defeats reuse); forking/editing `compose()` (regresses AC-11 + AC-17 detector) |
| D5 Tab-switch reset trigger | Add optional `resetKey?: string \| number`; CodeEditor keys its scroll-reset + `setColored(null)` effect AND its compose-debounce re-arm effect on `resetKey` (verbatim port of BodyEditor.tsx:104-128). BodyEditor passes `resetKey={activeTabId}` | AC-6 (reset scroll + invalidate colored on tab switch) needs a consumer-driven signal: `value`+`lang` are identical when two tabs hold the same raw body, so a props-only `{value,lang,onChange,validVars}` molecule gets no trigger (grill F-001). A generic `resetKey` keeps CodeEditor domain-agnostic (§2.2 — no tabsStore/activeTabId awareness). Restores BodyEditor.ct.tsx:769 (identical-body re-arm) + :811 (scroll-bleed reset). Not a DEPARTURE — establishes the standard React reset-on-change idiom (no prior pattern for signalling an extracted editor). | `key={activeTabId}` remount (full unmount/remount per switch — discards textarea DOM, resets uncontrolled focus/IME/selection, re-runs compose from cold; heavier for the same result); retain reset effect in BodyEditor + expose imperative scroll-reset via ref (splits AC-6 ownership across the org/molecule boundary — contradicts AC-14 self-contained); bake `activeTabId`/tabsStore into CodeEditor (domain leak — §2.2 violation, defeats AC-15) |
| D4 testids | Preserve `body-code-editor` / `body-gutter` / `body-pre` on `CodeEditor` | Zero CT churn; existing BodyEditor CTs stay green (AC-8) | Renaming to `code-*` (churns every existing CT, breaks AC-8) |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| `src/renderer/src/components/molecules/CodeEditor.tsx` | Create | Self-contained overlay editor: gutter/pre/textarea + compose+debounce+colored state + scroll-sync + memos; props `{value, lang, onChange, validVars, resetKey?}`; scroll-reset + `setColored(null)` + debounce re-arm keyed on `resetKey`; `body-*` testids |
| `src/renderer/src/components/molecules/CodeEditor.css` | Create | Code-area CSS moved from BodyEditor.css; `--code-line-h` var drives textarea/pre/gutter row heights; tk-* + overlay + focus rules |
| `src/renderer/src/components/molecules/__tests__/CodeEditor.ct.tsx` | Create | Fidelity + alignment CT (row-height equality all three = 20.625px, AC-23 live/debounced guard, tk-* colors via computed-style channel); AC-6 reset via `resetKey` change (identical-body re-arm + scroll-bleed reset); full styling-context fixture |
| `src/renderer/src/components/organisms/BodyEditor.tsx` | Modify | Remove inline raw-slot overlay markup + editor state/memos + BOTH `activeTabId`-keyed effects (104-114, 122-128); render `<CodeEditor resetKey={activeTabId} …>` in the raw slot; keep toolbar/radiogroup/lang-pill/mount-all |
| `src/renderer/src/components/organisms/BodyEditor.css` | Modify | Remove relocated code-area/overlay rules; keep toolbar/radio/lang-pill styles |
| `src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx` | Modify | Move fidelity/alignment ACs to CodeEditor CT; retain integration + `body-*` testid assertions + the `resetKey={activeTabId}` wiring assertion (AC-6 at the org level) |
| `src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx` | Modify | Adjust fixtures if raw-slot markup structure changes (testids preserved) |

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| `docs/renderer/src/index.md` | Update | Add `CodeEditor` to the molecules roster (with the `resetKey` reset-on-change signal); note BodyEditor as its consumer |
| `docs/architecture.md` | Update | Note CodeEditor as a reusable molecule + the consume relationship + the `resetKey` idiom (AC-18) |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Overlay pixel-grid desync (transparent textarea over highlighted pre) during the move | Med | High | Move padding/box-sizing/font verbatim; assert textarea/pre/gutter row-height equality + tk-* colors via the live-renderer computed-style channel (fidelityAssert); UNVERIFIED-not-PASS when channel absent |
| `resetKey` reset+re-arm ported imperfectly, stranding AC-6 (identical-body tabs) | Low | High | Port BodyEditor.tsx:104-128 verbatim, swapping only the `activeTabId` dep → `resetKey`; keep BOTH effects (reset AND debounce re-arm); regression-guarded by BodyEditor.ct.tsx:769 + :811 relocated to the CodeEditor CT |
| CodeEditor CT green-but-wrong because the fixture omits full styling context | Med | Med | CT fixture reproduces tokens.css import + data-mstyle + `.code-editor`/production className scope (alias-trap lesson) |
| Static/CT fidelity reports CLEAN yet layout drift persists | Low | Med | DOM-verify gutter, pre, AND textarea computed row heights are all equal, not just the gutter guard |
| `jsonTokens.compose()` accidentally edited (would regress AC-11 reuse + AC-17 JSON.parse detector) | Low | High | Reuse by import only; compose() stays byte-unchanged — do NOT touch |
| CodeEditor back-imports a sibling organism / uses a deep relative path / gains tabsStore awareness | Low | Med | CodeEditor imports only lib/ + atoms via `@renderer`, never `organisms/`; `resetKey` stays an opaque scalar (§2.2, §2.3) |

## Dependencies

None. No packages to install, no services, no env vars. React 19, `@playwright/experimental-ct-react`, and `jsonTokens` are all already in the stack.

## Supporting Documents

- No research.md — no research signals (all tech already in stack; alternatives settled upstream).
- No data-model.md — no data entities.
- No contracts.md — no API changes.
