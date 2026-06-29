# Research: RequestBar (009) visual drift from design/reference.html filled state — pure styling pass, zero behaviour change


**Date**: 2026-06-28
**Topic**: RequestBar (009) visual drift from design/reference.html filled state — pure styling pass, zero behaviour change
**Mode**: Enhancement
**Verdict**: Feasible

## Summary

RequestBar's visual drift from design/reference.html's filled state is token-APPLICATION local to RequestBar.css, NOT a token gap or a logic defect. The component was built to a uniform 24px / --radius-sm geometry with no focus ring, no primary-button shadow, a soft-chip method treatment and icon-only actions; the reference is 32px / --radius (7px) with an accent focus ring, a weight-600 inset-shadow primary Send, a bordered .method-select with bold plain-coloured method text, labelled ghost actions and a ⌘↵ kbd keycap. Every value the reference needs already exists as a token in tokens.css — so the fix is a localised RequestBar.css rewrite plus small presentational markup edits (⌘↵ keycap, optional action labels), with the per-method colour kept on the existing .method/{METHOD} class path (never a data-mstyle write, AC-6). The suspected token-gap (the migration dropped the un-gated .method.GET..OPTIONS{color} defaults that styles.css has) is real but secondary: Shell writes data-mstyle='soft' by default so the in-app pill IS coloured; the gap only bites in no-data-mstyle isolation (CT/stories) and is an optional design-system follow-up.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Against design/reference.html's FILLED state, RequestBar drifts visually: bar too cramped (height/padding/internal spacing undersized); URL input border-radius + focus border wrong; method pill missing per-method colour; Send active (non-empty URL) not solid-primary + ⌘↵ affordance; Save/Share are bare undersized icons not laid-out labelled actions. Empty-state Send greying is EXCLUDED (correct canSend guard). |
| Affected area | RequestBar organism (src/renderer/src/components/organisms/RequestBar.tsx + co-located RequestBar.css) is definitely affected. tokens.css / design/tokens.json presumed correct but unverified — investigation must confirm whether the needed spacing/radius/method-colour custom-properties exist there or are a gap. |
| Repro / Current | Mount RequestBar in the app request pane (or its story/CT harness) and render it. Most drift (cramped height/padding/spacing, wrong URL-input radius, greyscale method pill, bare undersized Save/Share) is visible immediately at render WITHOUT typing. Only the Send active solid-primary + ⌘↵ affordance and the focus border require a non-empty URL / focus to observe. Compare against design/reference.html FILLED state. |
| Desired | RequestBar visually matches design/reference.html in BOTH states (empty/not-filled AND filled): correct bar height/padding/internal spacing, matching URL-input border-radius + focus border, per-method coloured pill via the 005 .method/.{METHOD} class convention (NOT a data-mstyle write), Send active = solid-primary + ⌘↵ affordance, Save/Share laid-out + labelled. The ONE exclusion: Send greyed-disabled on an empty URL is correct canSend-guard behaviour, not a drift to fix. Fidelity rebuilt with semantic classes bound to tokens.css (values from design/tokens.json) — NOT by importing design-export markup/cruft (data-om-*, __OmT, tweaks-panel). Zero behaviour change; all unit + CT tests green. |
| Scope | feature-wide |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| Root bar geometry — cramped | src/renderer/src/components/organisms/RequestBar.css:52 | padding 5px 8px / gap 6px vs reference .reqbar padding 12px 16px / gap 8px (design/styles.css:773-774). Wrong literal values; no token missing — --space scale not used, but --radius/--fs tokens exist. Pure application. | primary |
| URL input radius + focus ring | src/renderer/src/components/organisms/RequestBar.css:131 | border-radius var(--radius-sm) (5px) + height 24px; focus (:158) sets border-color only. Reference .url-bar uses --radius (7px), height 32px, focus ring box-shadow 0 0 0 3px accent14% (design/styles.css:801-816). Both tokens exist; wrong binding + missing ring rule. Application. | primary |
| Send button treatment + missing ⌘↵ kbd | src/renderer/src/components/organisms/RequestBar.css:222 | Send uses base 24px height / --radius-sm / weight 500 / no shadow; reference .btn-primary is 32px / --radius / weight 600 / inset highlight shadow (design/styles.css:851-860) inside .send-split with a .kbd ⌘↵ keycap (design/styles.css:245,861-868). Component never renders a ⌘↵ element. Geometry = application; kbd = presentational markup add (RequestBar.tsx). | primary |
| Action buttons base undersized / icon-only | src/renderer/src/components/organisms/RequestBar.css:206 | Shared base height 24px / padding 0 8px; Save+Share render icon-only. Reference action buttons are .btn-ghost bordered, 32px, padding 0 14px, laid-out (design/styles.css:838-849). Geometry = application; any visible label = presentational markup add. | primary |
| Method pill renders soft data-mstyle chip not method-select | src/renderer/src/components/organisms/RequestBar.tsx:256 | Trigger uses cx('request-bar__method','method',method) → inherits [data-mstyle='soft'] .method chip (faint 16% tint, 9.5px, 42px min). Reference request-bar method is .method-select: bordered 88px box (border/bg-elev/--radius) with plain bold 11.5px coloured method text via un-gated .method.GET{color} (design/styles.css:490-516,785-799). Treatment mismatch — fix is a local RequestBar.css override of the soft chip, NO data-mstyle write (AC-6 safe). Application. | primary |
| tokens.css un-gated method-colour default GAP | src/renderer/styles/tokens.css:109 | tokens.css keeps only bare .method{font-family} + un-gated .method.HEAD{color}; the un-gated .method.GET..OPTIONS{color:var(--m-*)} rules present in design/styles.css:500-516 were dropped in migration (005 restored only font-family+HEAD). Per-method colour therefore absent in any no-data-mstyle context. Design-system-wide if restored. RUNNER-UP token-gap evidence. | runner-up |
| Canonical per-method colour convention (reusable) | src/renderer/src/components/molecules/Tabs.tsx:117 | canonical pattern — reusable: methodChipClassName = cx('method', method) is the 005 .method/{METHOD} convention, consumed by TabBar and already by RequestBar.tsx:256. RequestBar's class path is already canonical-correct; reuse it, do not invent a new method-colour mechanism. | primary |
| Canonical input focus-ring — NONE in components | (none) | no canonical pattern found project-wide for an input focus-ring box-shadow; design/styles.css:814 .url-bar:focus-within ring (box-shadow 0 0 0 3px accent14%) was never migrated to any renderer component CSS (only tokens.css:241 dot-decoration uses 0 0 0). New rule in RequestBar.css is justified — but it is a localised rule, not a token addition (--accent already exists). | primary |
| Shell sole-writer of data-mstyle (unchanged-behaviour anchor) | src/renderer/src/components/organisms/shell/Shell.tsx:237 | Effect 1 unconditionally writes documentElement.dataset.mstyle = mstyle (default 'soft', settingsStore.ts:65). Confirms AC-6: RequestBar must NOT write data-mstyle; the method-pill fix must stay class-based, never attribute-writing. | primary |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Drift is token-APPLICATION local to RequestBar.css: undersized 24px geometry vs reference 32px, --radius-sm vs --radius binding, omitted focus-ring + primary-button shadow, soft-chip method treatment instead of the bordered .method-select, icon-only actions, and a missing ⌘↵ kbd. Every needed token already exists in tokens.css, so the core fix is localised to RequestBar.css plus small presentational markup edits in RequestBar.tsx (⌘↵ keycap, optional action labels). The tokens.css un-gated .method default-colour gap is real but secondary — it only affects no-data-mstyle contexts (CT/stories) and is an OPTIONAL design-system patch, not required for the in-app drift.

**Confidence**: Confirmed

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Drift is a tokens.css / global-CSS token GAP, not RequestBar.css application: the styles.css→tokens.css migration dropped the un-gated default .method.GET..OPTIONS {color: var(--m-*)} rules (design/styles.css:500-516); only .method.HEAD survived (tokens.css:109). So per-method colour is absent in any context where Shell has NOT written data-mstyle, and restoring it ripples design-system-wide (TabBar + every .method consumer) and re-incurs the 005 CSS load-order fragility. |
| Falsifier | If the running app (Shell mounted, default data-mstyle='soft') renders a genuinely COLOURLESS method pill, the cause is the missing tokens.css default, not local RequestBar.css application. Counter-evidence found: Shell Effect 1 unconditionally writes dataset.mstyle='soft' (default in settingsStore.ts:65), so [data-mstyle='soft'] .method.GET tints the pill at runtime — per-method colour IS present in-app, just as a faint 9.5px soft chip vs the reference's bold 11.5px method-select. The in-app drift is geometry/treatment APPLICATION, not absent colour → runner-up falsified for the in-app case; the token gap only bites in no-data-mstyle isolation (CT/stories). |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| PRIMARY: drift is token-APPLICATION local to RequestBar.css — classes set undersized geometry (uniform 24px vs reference 32px), bind --radius-sm where reference uses --radius (7px), omit the focus-ring box-shadow and the primary-button inset shadow/weight-600, inherit the soft data-mstyle chip instead of presenting the bordered .method-select treatment, and render icon-only actions; plus a missing ⌘↵ kbd element. Every needed token already exists in tokens.css. | Find a reference target value (radius/spacing/colour/shadow) that maps to NO existing custom-property in tokens.css — that would push the fix into a token addition (runner-up), not pure application. | no |
| RUNNER-UP: drift is a tokens.css/global-CSS GAP — the migration dropped the un-gated .method.GET..OPTIONS{color:var(--m-*)} defaults (design/styles.css:500-516; only .method.HEAD survived at tokens.css:109), so per-method colour is absent wherever Shell has not written data-mstyle; restoring it is design-system-wide and re-incurs 005 load-order fragility. | If the running app (Shell mounted, default data-mstyle='soft') already colours the pill, the colour is NOT absent at runtime → gap is not the in-app cause. CONFIRMED disproved for in-app: Shell Effect 1 writes dataset.mstyle='soft' unconditionally (settingsStore.ts:65 default), soft variant tints the pill. Gap only bites in no-data-mstyle isolation (CT/stories). | no |
| METHOD-PILL TREATMENT: the pill shows the soft chip (faint 9.5px tint) where the reference request bar uses a bordered .method-select box with plain bold 11.5px coloured method text; fidelity needs a LOCAL RequestBar.css override of the soft chip — never a data-mstyle write (AC-6). | If the reference's request-bar method selector is actually a soft chip (not the .method-select box), this treatment mismatch is moot. design/styles.css:785-799 .method-select shows it is a bordered box → mismatch is real. | no |

## Approaches (HOW to change)

### Localised RequestBar.css fidelity pass
- **Description**: Rewrite RequestBar.css geometry + treatment to the reference values using existing tokens (32px heights, --radius, accent focus ring, weight-600 + inset-shadow Send, bordered .method-select override of the soft chip, labelled ghost actions), and add the ⌘↵ kbd keycap + any visible action label as presentational markup/className edits in RequestBar.tsx. No tokens.css change, no data-mstyle write.
- **Addresses hypothesis**: A, C
- **Does NOT cover**: B
- **Pros**: Localised — no design-system ripple, no 005 load-order fragility re-incurred; Zero AC-6 risk: method colour stays on the .method/{METHOD} class path, RequestBar never writes data-mstyle; All needed tokens already exist; no generated-file (tokens.css) hand-edit; Behaviour untouched (RequestSpec r/w, onSend, ⌘Enter/⌘S, canSend, dirty/markClean, per-tab isolation) — unit+CT stay green
- **Cons**: Per-method pill colour stays absent in no-data-mstyle isolation (CT/stories) — hypothesis B unaddressed; CT fidelity tests must reproduce the data-mstyle=soft context (known 005 CT-fixture-scoping constraint); Adds presentational JSX (kbd/labels) — slightly more than pure className edits
- **Complexity**: Med

### Localised pass + restore un-gated tokens.css .method defaults
- **Description**: Approach 1 PLUS restore the un-gated .method.GET..OPTIONS{color:var(--m-*)} default rules in tokens.css (and tokens.json source) so the pill colours even when data-mstyle is absent.
- **Addresses hypothesis**: A, B, C
- **Does NOT cover**: (none)
- **Pros**: Per-method colour present in ALL contexts incl. CT/stories isolation; Closes the styles.css→tokens.css migration gap design-system-wide; Simpler CT fidelity — no data-mstyle fixture scaffolding needed
- **Cons**: Design-system ripple: changes every .method consumer (TabBar chips) — broader regression surface; Re-incurs the known 005 CSS load-order fragility; tokens.css is generated-from-tokens.json (header: do not hand-edit) — must add the default at the source layer, more moving parts; Larger blast radius for a feature scoped to RequestBar fidelity
- **Complexity**: High

**Recommended approach**: Localised RequestBar.css fidelity pass — Recommended because the target values each map to a custom-property the project exposes today; the running app therefore avoids any shared-stylesheet edit — the work fits inside this one component's stylesheet plus a few presentational markup additions. Reuse the shared verb-class helper methodChipClassName (src/renderer/src/components/molecules/Tabs.tsx:117), which this component consumes at RequestBar.tsx:256, rather than building a new path — this REUSES the canonical pattern instead of reinventing it. The document-level marker attribute stays managed by its sole owner alone upstream; this approach leaves it to the owning organism and touches it from nowhere here, honouring the spec invariant. The wider question is split into an Open Uncertainty to keep scope small. Respects unchanged_behaviour: stylesheet and presentational markup additions, with RequestSpec read/write, onSend, the ⌘Enter/⌘S handlers, canSend, dirty/markClean and per-tab isolation all untouched.

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Only Shell.tsx writes documentElement data-mstyle (AC-6 / §4 Never) | Method-pill colour fix MUST stay class-based on .method/{METHOD}; RequestBar must never write document.documentElement.dataset.mstyle. Enforces the local-CSS-override approach over any attribute write. |
| Never use inline styles — class-based styling via cx() (§4 Never) | All geometry/treatment changes land in RequestBar.css + className edits; no inline style additions in RequestBar.tsx. |
| Prefer design tokens over literal style values (§4 Prefer) | Bind radius/colour/shadow to existing tokens (--radius, --accent, --border, --bg-elev, --fs-*); raw px is acceptable only for spacing where no --space token exists (reference 12px/16px/8px), matching the existing RequestBar.css pattern. |
| Search before building | Reuse the canonical .method/{METHOD} per-method colour convention at src/renderer/src/components/molecules/Tabs.tsx:117 (already used by RequestBar.tsx:256); do not invent a new method-colour mechanism. |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Med | One CSS file fully rewritten (RequestBar.css ~323 lines) + a handful of className/markup edits in RequestBar.tsx (⌘↵ kbd, optional labels). No token/store/logic files touched. |
| Risk | Low | Behaviour paths untouched (onSend, ⌘Enter/⌘S, canSend, dirty/markClean, per-tab isolation, data-mstyle invariant). Main risk is CT fidelity tests needing the data-mstyle=soft context (005 fixture-scoping) and visual-snapshot churn. |
| Verify cost | Med | Runtime fidelity check via design-auditor (Chrome DevTools MCP) computed-style + screenshot diff vs design/reference.html filled state; plus existing unit+CT suites must stay green. |

## Open Uncertainties

- [NEEDS CLARIFICATION: desired — Confirm the exact reference geometry/treatment target values via a runtime design-auditor screenshot + computed-style diff against design/reference.html (filled state) before locking RequestBar.css values — diagnosis is code-confirmed but not yet runtime-verified.]
- [NEEDS CLARIFICATION: desired — Decide separately whether the shared stylesheet should expose un-prefixed per-verb default rules for contexts the shell has not initialised (CT/stories) — design-system-scope question, deferred from this localised pass.]

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Against design/reference.html's FILLED state, RequestBar drifts visually: bar too cramped (height/padding/internal spacing undersized); URL input border-radius + focus border wrong; method pill missing per-method colour; Send active (non-empty URL) not solid-primary + ⌘↵ affordance; Save/Share are bare undersized icons not laid-out labelled actions. Empty-state Send greying is EXCLUDED (correct canSend guard). — RequestBar visually matches design/reference.html in BOTH states (empty/not-filled AND filled): correct bar height/padding/internal spacing, matching URL-input border-radius + focus border, per-method coloured pill via the 005 .method/.{METHOD} class convention (NOT a data-mstyle write), Send active = solid-primary + ⌘↵ affordance, Save/Share laid-out + labelled. The ONE exclusion: Send greyed-disabled on an empty URL is correct canSend-guard behaviour, not a drift to fix. Fidelity rebuilt with semantic classes bound to tokens.css (values from design/tokens.json) — NOT by importing design-export markup/cruft (data-om-*, __OmT, tweaks-panel). Zero behaviour change; all unit + CT tests green."

Research reference: research/2026-06-28-requestbar-009-visual-drift.md
Key facts:
- Mode: Enhancement
- Symptom: Against design/reference.html's FILLED state, RequestBar drifts visually: bar too cramped (height/padding/internal spacing undersized); URL input border-radius + focus border wrong; method pill missing per-method colour; Send active (non-empty URL) not solid-primary + ⌘↵ affordance; Save/Share are bare undersized icons not laid-out labelled actions. Empty-state Send greying is EXCLUDED (correct canSend guard).
- Desired: RequestBar visually matches design/reference.html in BOTH states (empty/not-filled AND filled): correct bar height/padding/internal spacing, matching URL-input border-radius + focus border, per-method coloured pill via the 005 .method/.{METHOD} class convention (NOT a data-mstyle write), Send active = solid-primary + ⌘↵ affordance, Save/Share laid-out + labelled. The ONE exclusion: Send greyed-disabled on an empty URL is correct canSend-guard behaviour, not a drift to fix. Fidelity rebuilt with semantic classes bound to tokens.css (values from design/tokens.json) — NOT by importing design-export markup/cruft (data-om-*, __OmT, tweaks-panel). Zero behaviour change; all unit + CT tests green.
- Recommended approach: Localised RequestBar.css fidelity pass
- Hypothesis addressed: A, C
- Hypotheses NOT covered: B
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
