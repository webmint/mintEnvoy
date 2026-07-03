# Plan: tabs-contrast-wcag

**Date**: 2026-07-02
**Spec**: specs/013-tabs-contrast-wcag/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A. The mechanism (token sync vs new token) was settled by a verified user correction, not a fresh alternatives comparison.
- Phase 1.3 architecture decisions: yes (mandatory) — the `architect` was consulted during the original `/plan` run (contrast math, layer mapping, `--text-secondary` proposal).
- Re-consultation on revision: not performed — a verified user correction (`design/styles.css` already carries AA-darkened `--text-muted`/`--text-faint`; the app tokens are merely stale) SUPERSEDED the stale-token premise the architect reasoned from. The correction REMOVES architectural scope (drops the new `--text-secondary` token and the contract §5 amendment) and introduces no new architectural decision, so no fresh architect pass was warranted. All contrast values re-verified locally against the design-source hexes.

**Divergence from upstream + prior plan**: the upstream research handoff AND the first (superseded) plan both assumed the muted-text ramp had a gap requiring a new `--text-secondary` token plus a contract §5 amendment. That premise was WRONG — the design source (`design/styles.css`) had already darkened the tokens for AA; the app's `tokens.css` never synced. This plan implements the corrected, smaller scope: a 3-value token sync + 2 genuine accent swaps.

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Layer map, design decisions, contrast values (original /plan run) | Authored the original plan tables; its `--text-secondary` proposal was superseded by the token-staleness correction | modified | own-reasoning; superseded by design/styles.css:19-20,62 |
| design-auditor | Contrast math / ramp ordering (requested at original run) | No response relayed; contrast re-derived + verified locally | no-response | own-reasoning |

## Summary

Sync three drifted design-token values in `src/renderer/styles/tokens.css` to `design/styles.css` (light `--text-muted` #6c6c75, light `--text-faint` #6e6e77, dark `--text-faint` #787881), and swap the two genuine accent-on-light color sites in `Tabs.css` (active-tab label + active-tab badge) to `var(--text)`. The token sync brings the inactive label, close icon, and dirty-dot to WCAG AA — and simultaneously fixes every other `--text-muted`/`--text-faint` text consumer app-wide — with no new token and no contract amendment.

**Why no new research**: no signals; approach is a verified value sync + two token-idiom swaps. Contrast is deterministic — all pairs re-computed from the design-source hexes.

## Technical Context

**Architecture**: Presentation only — renderer design tokens (`styles/tokens.css`) + one molecule stylesheet (`molecules/Tabs.css`). No main/preload/domain involvement (constitution §2.2).
**Error Handling**: N/A — static token/CSS change.
**State Management**: N/A — no state change; CSS resolves the tokens at render.

## Constitution Compliance

- §6.3 Search Before Building: compliant — syncs existing tokens and reuses the existing promote-to-`var(--text)` idiom; invents nothing.
- "Prefer design tokens over literals": compliant — the fix IS the token layer; component sites use `var()` refs.
- "Never use inline styles": compliant — edits are `.css`-only.
- §2.2 Renderer tier: compliant — tokens stay in `styles/tokens.css`; molecule CSS under `molecules/`.
- Design Fidelity: compliant and IMPROVED — the sync makes `tokens.css` match its declared source (`design/styles.css`), and `design-fidelity-contract §5` (which prescribes `--text-muted`/`--text-faint`) becomes correct without any hand-edit.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
| ------------ | ------------------------------ | ----------------------- |
| Presentation — design tokens | Sync 3 drifted values to the design source | src/renderer/styles/tokens.css (light `--text-muted`, light `--text-faint`, dark `--text-faint`) |
| Presentation — component styles | 2 accent-on-light swaps to `var(--text)` | src/renderer/src/components/molecules/Tabs.css (149 active label, 233 active badge) |
| Test (verification) | Re-baseline affected CT screenshots app-wide; add Tabs contrast assertions across light + dark | src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx (+ other components' CT baselines) |

*(No application/domain/data layer — static presentation-token change; single Electron-renderer package.)*

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
| ---------- | --------------- | ----------- | --------------------- |
| Fix mechanism for muted/faint sub-AA text | Sync `tokens.css` to `design/styles.css` (3 values) | The design source already declares AA-safe values (#6c6c75 / #6e6e77 / #787881); app tokens were stale. One edit fixes the inactive label (4.69:1), close icon (4.55/4.58:1), dirty-dot (4.55:1) AND every other muted/faint consumer app-wide. | New `--text-secondary` token + 5 swaps + contract amendment (the superseded stale-premise plan — solves a ramp gap that does not exist) |
| Active-tab label color (149) | `var(--accent)` → `var(--text)` | Accent-as-text is 2.29/2.54:1, sub-AA independent of the token sync; `var(--text)` is 15.98/17.72:1 and matches the contract selected-text idiom. `.tabbar` (480-481) inherits, so one edit covers both variants. | Keep `var(--accent)` (fails); recolor via a new token (unnecessary) |
| Active-tab badge text (233) | `var(--accent)` → `var(--text)` | Accent on `--accent-soft` fails as text; `var(--text)` clears AA; reuses the same idiom. | Keep `var(--accent)` (fails) |
| Inactive label / close icon / dirty-dot (97, 326, 388) | No per-site change — rely on the token sync | Post-sync `var(--text-muted)`=4.69:1 and `var(--text-faint)`=4.55:1 clear their thresholds; a per-site swap would duplicate the token-layer fix and diverge from the design source. | Swap 97→`--text-secondary`, 326/388→`--text-muted` (the superseded plan — redundant after the sync) |
| Contract §5 amendment | None | §5 prescribes `--text-muted`/`--text-faint`, which pass once the tokens sync; §5 derives from `design/styles.css`, so hand-editing it would desync it from its source. | Amend §5 (would desync the contract from its declared source) |
| New `--text-secondary` token | Do not add | The muted-text ramp gap that motivated it does not exist once the tokens are synced to the (already-darkened) design source. | Add `--text-secondary` (unnecessary; more surface, more risk) |

### File Impact

| File   | Action        | What Changes        |
| ------ | ------------- | ------------------- |
| src/renderer/styles/tokens.css | Modify | Sync 3 values to design/styles.css: light `--text-muted` #71717a→#6c6c75, light `--text-faint` #a1a1aa→#6e6e77, dark `--text-faint` #71717a→#787881 |
| src/renderer/src/components/molecules/Tabs.css | Modify | 2 swaps: line 149 `--accent`→`--text` (active label); line 233 `--accent`→`--text` (active badge). Lines 97/326/388 unchanged (fixed by the sync) |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | Add WCAG contrast assertions for the fixed sites across light + dark; re-baseline Tabs fidelity screenshots |
| (other components' CT baselines) | Modify | Re-baseline screenshots for every `--text-muted`/`--text-faint` consumer whose text darkens from the sync (see Risk R1) |

### Documentation Impact

No documentation changes — `design-fidelity-contract §5` already matches the synced tokens (it derives from `design/styles.css`); no `docs/<package>/` impact (internal token value change).

## Risk Assessment

| Risk   | Likelihood   | Impact       | Mitigation      |
| ------ | ------------ | ------------ | --------------- |
| R1: Token sync darkens muted/faint text across ~9 other components (Modal, Toast, Dropdown, RequestBar, TabBar, Titlebar, Statusbar, PrimitivesDemo); their CT screenshot baselines shift, not just Tabs | High | Med | Enumerate all `--text-muted`/`--text-faint` consumers; re-baseline every affected CT across light+dark. These are design-source-authoritative changes (intended), not regressions — /breakdown must plan the app-wide re-baseline, not a Tabs-only one |
| R2: CT single-variant baseline misses the dark theme | Med | Med | Cover BOTH themes; verify at runtime via design-auditor (CT/static miss what runtime catches — per MEMORY) |
| R3: `.tabbar` active-label inheritance assumption wrong | Low | Med | Confirmed: Tabs.css:480-481 sets only box-shadow+background; CT asserts the active-label color in both bare `.tabs` and `.tabbar` scopes |

## Dependencies

None — no packages, services, or environment variables. Pure renderer token/CSS change.

## Supporting Documents

- [Research](../../research/2026-07-01-bug-005-active-tab.md) — upstream research report. NOTE: its `--text-secondary` recommendation is SUPERSEDED — it reasoned from the stale `tokens.css` values, not the already-darkened `design/styles.css` source. Root-cause analysis for the active-label accent fix remains valid.
