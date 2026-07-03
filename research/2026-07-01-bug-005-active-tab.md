# Research: Bug 005: active-tab label color fails WCAG contrast and diverges from design contract


**Date**: 2026-07-01
**Topic**: Bug 005: active-tab label color fails WCAG contrast and diverges from design contract
**Mode**: Bug
**Verdict**: Root cause confirmed

## Summary

Bug 005 is confirmed: the active-tab label uses the decorative --accent token as text color (Tabs.css:149), measuring 2.29:1 on --bg-sunken and 2.54:1 on the #fff active wrapper — both fail WCAG 2.1 AA SC 1.4.3 and diverge from the contract idiom of promoting selected text to var(--text). A standalone probe reproduced every reported ratio and validated the fix (var(--text) = 15.98/17.72:1). The root cause is partly systemic: the palette has no AA-safe muted text step, so --text-muted (4.36:1) and --text-faint (~2.3:1) are used as text/icon across ~9 components (siblings 006/007 are the Tabs instances), and contract §5 itself prescribes these sub-AA tokens. Recommended fix is scoped: point the active label at var(--text) (contract-aligned), add an additive --text-secondary token for the inactive label (006), and promote the close icon to --text-muted (007) — deferring the project-wide token-ramp remediation and the required contract §5 amendment to a follow-up.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Active-tab label renders var(--accent)#10b981 = 2.29:1 on --bg-sunken and 2.54:1 on #fff active wrapper; both fail WCAG 2.1 AA SC 1.4.3 (4.5:1 for 12.5px). Also diverges from design-fidelity-contract §5 which prescribes active-tab color: var(--text) #18181b. |
| Affected area | src/renderer/src/components/molecules/Tabs.css — .tabs__tab--active / [aria-selected='true'] color rule (line 149). Molecules/Tabs component; consumed by organisms/TabBar. |
| Repro / Current | Current: open app, view a tab strip; active tab label is emerald (--accent), low contrast. Surfaced by design-auditor during feature 011-tab-width-cap review. Pre-existing, not introduced by 011. |
| Desired | 005 (this ticket): active-tab label color var(--accent)#10b981 -> var(--text)#18181b, meets WCAG AA 1.4.3 (~14:1) and design-contract §5. Combined-pass siblings: 007 close-icon var(--text-faint)#a1a1aa -> var(--text-muted)#71717a (clears 3:1 non-text 1.4.11); 006 inactive label var(--text-muted)#71717a -> needs >=4.5:1 but no existing token sits between --text-muted and --text, so likely a new mid token (~#52525b) to keep active/inactive distinction. |
| Scope | one place (evidence: src/renderer/src/components/molecules/Tabs.css:149) |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| Token def: --text-muted (systemic ramp gap) | src/renderer/styles/tokens.css:28 | --text-muted #71717a = 4.36:1 on --bg-sunken, below WCAG AA 4.5:1; no token exists between --text-muted and --text, so no AA-safe muted text step in the ramp | primary |
| 005 symptom: active-tab label color | src/renderer/src/components/molecules/Tabs.css:149 | active label color:var(--accent)#10b981 = 2.29:1 / 2.54:1, fails 1.4.3; .tabbar override (480-481) sets only box-shadow+bg so inherits this color -> one fix covers both variants | primary |
| 006 sibling: inactive-tab label color | src/renderer/src/components/molecules/Tabs.css:97 | inactive label color:var(--text-muted) = 4.36:1, marginally fails 1.4.3; contract §5 line 130 prescribes this same sub-AA token | primary |
| 007 sibling: close-button icon color | src/renderer/src/components/molecules/Tabs.css:326 | close icon color:var(--text-faint) = 2.31/2.56:1, fails 1.4.11 (3:1 non-text); contract §5 line 133 prescribes this same sub-AA token | primary |
| Token def: --text-faint | src/renderer/styles/tokens.css:29 | --text-faint #a1a1aa ~2.31:1; used as text/icon in ~7 sites; only clears 3:1 when promoted, never 4.5:1 text | primary |
| Canonical AA-safe idiom: promote interactive text to --text | src/renderer/src/components/molecules/Tabs.css:120 | canonical pattern — reusable: existing hover rule promotes tab text to color:var(--text)#18181b (AA-safe ~14:1); 005 active label should reuse this token idiom rather than inventing a value | primary |
| Runner-up falsifier (REFUTED): project-wide muted-as-text | src/renderer/src/components/molecules/Modal.css:117 | refutes component-local framing: --text-muted used as text color in ~18 sites across 9 components (Modal, Toast, Dropdown, TabBar, RequestBar, Statusbar, Titlebar, PrimitivesDemo, Tabs) — the sub-AA failure is systemic, not Tabs-local | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Active-tab label sets color:var(--accent) (Tabs.css:149), a decorative green token that is not an AA-safe text color (2.29:1 / 2.54:1). Systemically, the token palette has no AA-verified muted text step: --text-muted (4.36:1) and --text-faint (~2.3:1) are below AA for text yet used as text/icon color across ~9 components, and design-contract §5 itself prescribes these sub-AA tokens.

**Confidence**: Confirmed

### Structured root cause

| Field | Value |
|---|---|
| trigger | Active-tab rule Tabs.css:149 assigns color:var(--accent) (green decorative token) to 12.5px label text. |
| root_cause | Design-token palette provides no AA-verified muted text ramp: --text-muted #71717a (4.36:1) and --text-faint #a1a1aa (~2.3:1) are both below AA for text but used as text/icon across ~9 components; the contract §5 prescribes these sub-AA tokens, so there is no AA-safe intermediate token for muted label text. |
| contributing_factors | 1. Design-fidelity-contract §5 prescribes the failing tokens (base tab --text-muted, close --text-faint), so the implementation faithfully reproduced a sub-AA design. 2. No automated WCAG-contrast gate in CT/design-fidelity tests; the violations surfaced only via design-auditor during feature 011 review. 3. No token exists between --text-muted and --text, so there was no obvious AA-safe token for muted label text (006). |

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Component-local mis-token: only Tabs.css picks wrong color tokens; fix is a purely local 3-rule swap in Tabs.css with no token-file change. |
| Falsifier | Other components also use --text-muted/--text-faint in text roles (color:) — if they do, the sub-AA failure is project-wide/systemic, not Tabs-local. |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| Systemic: active-tab label assigns the decorative --accent token to text (Tabs.css:149), and the palette provides no AA-safe muted text step — --text-muted (4.36:1) and --text-faint (~2.3:1) are both defined below AA yet used as text across ~9 components. | If --accent #10b981 measured >=4.5:1 on --bg-sunken/#fff, or if --text-muted/--text-faint were used only decoratively (never color:), there would be no text-contrast violation. | no |
| Component-local: only Tabs.css picked wrong tokens; an isolated 3-rule swap in Tabs.css fully resolves it with no token-file change. | Other components using --text-muted/--text-faint as color: (text) — a project-wide grep shows ~18 muted + ~7 faint text sites, refuting Tabs-locality. | no |

## Approaches (HOW to change)

### Scoped Tabs fix + additive --text-secondary token
- **Description**: Point the active-label color at var(--text) (Tabs.css:149, contract-aligned). For 007, promote the close icon to var(--text-muted) (Tabs.css:326), which clears the 3:1 non-text bar (4.36/4.83:1). For 006, add a NEW additive token --text-secondary (light #52525b ~6.97:1, dark parity) in tokens.css and use it for the inactive label (Tabs.css:97); being additive it touches no existing consumer. The .tabbar variant inherits Tabs.css:149 so no extra site is needed.
- **Addresses hypothesis**: A
- **Does NOT cover**: B
- **Pros**: 005 is contract-aligned and self-contained; new token is additive: zero regression to the ~17 other --text-muted consumers; reuses the existing promote-to-var(--text) idiom (Tabs.css:120); keeps active vs inactive distinction (--text vs --text-secondary)
- **Cons**: 006/007 diverge from contract §5 which prescribes the sub-AA tokens -> needs a contract amendment; leaves the project-wide sub-AA --text-muted/--text-faint text usage unfixed; introduces a new token that must be documented + dark-theme tuned
- **Complexity**: Low

### Global token-ramp remediation in tokens.css
- **Description**: Redefine --text-muted from #71717a to an AA-safe value (~#52525b) plus dark parity, fixing all ~18 text consumers at once, and stop using --text-faint as text. Single source of truth for the muted text step.
- **Addresses hypothesis**: A
- **Does NOT cover**: (none)
- **Pros**: fixes the systemic root, every component benefits; single source of truth for the text ramp
- **Cons**: changes visual weight across 9 components; needs full design review + CT screenshot re-baseline; scope explosion far beyond ticket 005; risks regressing the intended muted hierarchy; still requires contract §5 amendment
- **Complexity**: High

**Recommended approach**: Scoped Tabs fix + additive --text-secondary token — This is the confirmed 005 fix and stays contract-aligned: give the active label an AA-safe foreground (var(--text)), matching the contract idiom for selected text, and reuse the existing promote-to-foreground hover pattern rather than inventing a value — satisfying Search Before Building. An additive secondary-foreground variable fixes 006 with zero impact on the ~17 other muted-text consumers, honoring unchanged_behavior: the active versus inactive distinction is preserved (var(--text) beside var(--text-secondary)) and dark-theme parity is kept. Project-wide ramp remediation and the §5 amendment for 006/007 are deferred to a follow-up so this ticket stays within its endorsed scope.

**Single-layer justification:**
The symptom and its fix are genuinely local to the renderer styling layer: the color values live in tokens.css and are consumed by component CSS rules; there is no application/domain layer to cross for a static presentation-token defect. The single Electron-renderer package (src/renderer) holds both the definitions and the consumers.

**Cites:**
- Tabs.css .tabs__tab--active color rule

**Proposed call shape:**
```
var(--text)
```

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| §6.3 Search Before Building | Reuse the existing AA-safe idiom at Tabs.css:120 (promote interactive text to var(--text)) for the 005 active-label fix instead of inventing a color; no new helper needed for 005. |
| Design Fidelity (contract §5) | 005 fix aligns with contract §5's active-text-promotes-to-var(--text) idiom. 006/007 fixes DIVERGE from §5 (which prescribes --text-muted/--text-faint) and therefore require a contract §5 amendment before implementation. |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Low | 3 CSS declarations in Tabs.css + 1 additive token (light+dark) in tokens.css; ~5 lines |
| Risk | Med | must preserve active/inactive distinction (avoid 006 collapsing to --text) and verify dark-theme parity; 006/007 need contract §5 amendment first |
| Verify cost | Low | executable contrast probe already validates all pairs; CT/design-fidelity screenshot re-baseline for Tabs |

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Active-tab label renders var(--accent)#10b981 = 2.29:1 on --bg-sunken and 2.54:1 on #fff active wrapper; both fail WCAG 2.1 AA SC 1.4.3 (4.5:1 for 12.5px). Also diverges from design-fidelity-contract §5 which prescribes active-tab color: var(--text) #18181b. — 005 (this ticket): active-tab label color var(--accent)#10b981 -> var(--text)#18181b, meets WCAG AA 1.4.3 (~14:1) and design-contract §5. Combined-pass siblings: 007 close-icon var(--text-faint)#a1a1aa -> var(--text-muted)#71717a (clears 3:1 non-text 1.4.11); 006 inactive label var(--text-muted)#71717a -> needs >=4.5:1 but no existing token sits between --text-muted and --text, so likely a new mid token (~#52525b) to keep active/inactive distinction."

Research reference: research/2026-07-01-bug-005-active-tab.md
Key facts:
- Mode: Bug
- Symptom: Active-tab label renders var(--accent)#10b981 = 2.29:1 on --bg-sunken and 2.54:1 on #fff active wrapper; both fail WCAG 2.1 AA SC 1.4.3 (4.5:1 for 12.5px). Also diverges from design-fidelity-contract §5 which prescribes active-tab color: var(--text) #18181b.
- Desired: 005 (this ticket): active-tab label color var(--accent)#10b981 -> var(--text)#18181b, meets WCAG AA 1.4.3 (~14:1) and design-contract §5. Combined-pass siblings: 007 close-icon var(--text-faint)#a1a1aa -> var(--text-muted)#71717a (clears 3:1 non-text 1.4.11); 006 inactive label var(--text-muted)#71717a -> needs >=4.5:1 but no existing token sits between --text-muted and --text, so likely a new mid token (~#52525b) to keep active/inactive distinction.
- Recommended approach: Scoped Tabs fix + additive --text-secondary token
- Hypothesis addressed: A
- Hypotheses NOT covered: B
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
