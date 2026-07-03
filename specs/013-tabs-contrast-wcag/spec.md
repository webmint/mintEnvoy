# Spec: tabs-contrast-wcag

**Date**: 2026-07-02
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

The working-tabs strip renders two accent-colored roles below WCAG 2.1 AA, and separately the app's design tokens are STALE relative to design/styles.css (their declared source of truth): the muted and faint text tokens were already darkened for AA at the source but never synced into src/renderer/styles/tokens.css. This spec (1) syncs the three drifted token values to design/styles.css — which brings every --text-muted / --text-faint text consumer app-wide to AA in one edit — and (2) swaps the two genuine accent-on-light sites in Tabs.css to var(--text). No new token and no contract amendment are needed.

## 2. Current State

The app tokens in src/renderer/styles/tokens.css have drifted from design/styles.css (the design source of truth): light --text-muted is #71717a but the source declares #6c6c75; light --text-faint is #a1a1aa but the source declares #6e6e77; dark --text-faint is #71717a but the source declares #787881 (dark --text-muted #a1a1aa already matches). This staleness is why the inactive-tab label (Tabs.css:97, var(--text-muted)) measures 4.36:1 and the close-button icon (Tabs.css:326, var(--text-faint)) measures 2.31:1 — both sub-AA. Two failures are independent of the token drift: the active-tab label (Tabs.css:149, color:var(--accent) #10b981) at 2.29:1 / 2.54:1 and the active-tab badge text (Tabs.css:233, color:var(--accent) on var(--accent-soft)); accent fails as text regardless of the muted/faint values. The dirty-dot indicator (Tabs.css:388, background:var(--text-faint)) also rides on the faint token. The .tabbar active override (Tabs.css:480-481) sets only box-shadow + background, so it inherits the active-label color from line 149. design-fidelity-contract §5 (lines 130, 133) prescribes var(--text-muted) / var(--text-faint) — already correct once the tokens sync. Pre-existing; surfaced by design-auditor during feature 011 review.

## 3. Desired Behavior

Sync the three drifted token values in src/renderer/styles/tokens.css to design/styles.css: light --text-muted -> #6c6c75, light --text-faint -> #6e6e77, dark --text-faint -> #787881 (dark --text-muted stays #a1a1aa). Post-sync, the inactive-tab label reads 4.69:1, the close-button icon 4.55:1 light / 4.58:1 dark, and the dirty-dot 4.55:1 — all clearing their WCAG AA thresholds in both themes, and every other --text-muted / --text-faint text consumer app-wide is simultaneously brought to AA. Separately, swap the two accent-on-light sites in Tabs.css to var(--text): active-tab label (149) and active-tab badge text (233); the .tabbar variant inherits line 149. No new token is introduced (no --text-secondary), the existing token names and semantics are preserved, and design-fidelity-contract §5 is NOT hand-edited — it already matches the synced tokens, and editing it would desync it from design/styles.css.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Design tokens | src/renderer/styles/tokens.css | Sync 3 drifted values to design/styles.css: light --text-muted->#6c6c75, light --text-faint->#6e6e77, dark --text-faint->#787881 |
| Tabs molecule styles | src/renderer/src/components/molecules/Tabs.css | Two accent-on-light swaps: active-tab label (149) and active-tab badge text (233) var(--accent)->var(--text); .tabbar inherits 149. Lines 97/326/388 unchanged (fixed by token sync) |
| App-wide muted/faint text consumers (tests) | src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Token darkening shifts every --text-muted/--text-faint consumer visually (Modal, Toast, Dropdown, RequestBar, TabBar, Titlebar, Statusbar, PrimitivesDemo) — affected CT screenshot baselines re-based across light+dark; Tabs CT gains contrast assertions |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The design-token stylesheet shall define the muted and faint text tokens at the darkened values from the design source.
  > Verification: grep -q -- '--text-muted: #6c6c75' src/renderer/styles/tokens.css && grep -q -- '--text-faint: #6e6e77' src/renderer/styles/tokens.css && grep -q -- '--text-faint: #787881' src/renderer/styles/tokens.css

### 5.2 Behavior preservation

- [x] **AC-2**: The system shall preserve the existing token names and semantics, introducing no new color token.
- [x] **AC-3**: WHILE either theme is active, the Tabs strip shall keep the active-tab and inactive-tab labels visually distinct.

### 5.3 Behavior change

- [x] **AC-4**: The system shall bring every muted and faint text role to the WCAG AA contrast minimum by syncing the token values to the design source.
- [x] **AC-5**: WHILE either theme is active, the active-tab label shall meet the WCAG AA contrast minimum for normal text by using var(--text), which the tabbar variant inherits.
- [x] **AC-6**: WHILE a tab is active, the active-tab badge text shall meet the WCAG AA contrast minimum for normal text on the accent-soft background by using var(--text).
- [x] **AC-7**: WHILE either theme is active, the inactive-tab label shall meet the WCAG AA contrast minimum for normal text via the synced var(--text-muted).
- [x] **AC-8**: WHILE either theme is active, the close-button icon shall meet the WCAG AA non-text contrast minimum via the synced var(--text-faint).
- [x] **AC-9**: WHILE a tab is marked dirty, the dirty-state indicator shall meet the WCAG AA non-text contrast minimum via the synced var(--text-faint).

### 5.4 CI / pipeline

N/A — No CI or pipeline change; renderer token/CSS fix verified by existing lint/type-check/CT.

### 5.5 Hooks / gates

N/A — No git hooks or quality gates added or changed.

### 5.6 Documentation

N/A — design-fidelity-contract §5 already matches the synced tokens (its source is design/styles.css); no doc edit — hand-editing §5 would desync it from its source.

### 5.7 Hygiene

- [x] **AC-10**: The system shall pass lint and type-check on all changed files.
  > Verification: npm run lint && npm run typecheck

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Disabled-tab label color (Tabs.css:174/183, var(--text-faint)) — WCAG exempts disabled UI from the contrast minimum; left as-is (rides the synced faint anyway).
- NOT included: Any token drift beyond the three contrast-relevant values (e.g. the app-only dark --m-head token absent from design/styles.css) — not reconciled here. — F-tokens-3
- NOT included: Hand-editing design-fidelity-contract §5 — the contract derives from design/styles.css and is already correct post-sync; editing it would desync it from its source. — F-design-fidelity-contract-2

## 7. Technical Constraints

- Must follow: Must follow WCAG 2.1 AA — SC 1.4.3 (normal text) and SC 1.4.11 (non-text UI), in both light and dark themes.
- Must follow: Prefer design tokens over literal style values; never use inline styles — changes are token values plus var() references only.
- Must follow: tokens.css must mirror design/styles.css (the design source of truth); token values are synced from it, not hand-picked, and derived docs (contract §5) are not hand-edited.
- Must not break: The active-tab badge and Tabs WAI-ARIA engine must remain intact; the fix is color/token-only.
- Must follow constitution §3.6: Search for an existing utility/token before building — sync the existing muted/faint tokens rather than inventing a new one.
- Must follow constitution §2.2: Renderer tier: design tokens live in styles/tokens.css; molecule CSS under molecules/.

## 8. Open Questions

- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Token sync darkens muted/faint text across ~9 other components (Modal, Toast, Dropdown, RequestBar, TabBar, Titlebar, Statusbar, PrimitivesDemo); their CT screenshot baselines shift, not just Tabs. | High | Med | Enumerate all --text-muted/--text-faint consumers; re-baseline every affected CT across light+dark. These are design-source-authoritative changes (intended), not regressions. |
| CT single-variant baseline misses the dark theme; a color-only shortcut could leave other drift. | Med | Med | Cover BOTH themes in CT; verify at runtime via design-auditor, not just static/CT. |
| .tabbar active-label inheritance assumption wrong (line 149 not inherited by the tabbar variant). | Low | Med | Confirmed: Tabs.css:480-481 sets only box-shadow+background; CT must assert the active-label color in both bare .tabs and .tabbar scopes. |
