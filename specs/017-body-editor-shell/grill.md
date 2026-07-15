# Plan Grill -- specs/017-body-editor-shell -- 2026-07-10

**Feature**: specs/017-body-editor-shell
**Scope**: plan.md + referenced specs -- 2 files
**Finders invoked**: devils-advocate
**Refuters invoked**: code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React

## Disposition

**Verdict**: REVISE-PLAN

**Rationale**:

Cycle-3 verification re-grill. F-001 (cycle-1) and F1/F2/F4 (cycle-2) all VERIFIED CLOSED. But the cycle-2 F3 fix itself introduced a confirmed Medium regression: the plan debounces the ENTIRE <pre> snapshot, yet in the chosen transparent-textarea technique the <pre> is the SOLE visible text layer (textarea is color:transparent), so during a typing burst the trailing-100ms debounce freezes the visible text — typed characters are invisible until the user pauses. §7 c3 sanctions debouncing the expensive tokenise pass, NOT the plain-text render; the fix conflated the two. Correctable against the same spec (REVISE-PLAN): render the <pre> plain TEXT live from body.raw.text, debounce ONLY the JSON/var coloring pass (D6 already has the plain-degrade path). A second CONFIRMED Info finding: the §3.1 'both-props unrepresentable / XOR' claim is overstated — a bare object-type union without ?:never companions permits both-props under TS excess-property rules (non-functional; callers pass one shape and 'rows' in props narrows correctly — a wording/typing correction, not a bug). One finding dismissed (AC-23 gutter/pre both derive from the same snapshot, so counts match by construction — the refuter read 'rendered line count' as the pre's count per the spec's verbatim wording).

> The defects are real but correctable at the plan level. Revise `plan.md` to address the confirmed findings, then re-run `/plan` (or hand-patch `plan.md`), and optionally re-run `/grill` before proceeding to `/breakdown`.

## Confirmed -- Top Priorities
Force-ranked across the confirmed findings. Fix these first.
1. [Medium] specs/017-body-editor-shell/plan.md:77 -- F3 fix regression — debounced <pre> snapshot lags the SOLE visible text layer (typed text invisible up to ~100ms) [Likely]
2. [Info] specs/017-body-editor-shell/plan.md:47 -- F4 verification — bare object-type union does not enforce XOR under strict TS ("unrepresentable" claim overstated) [Likely]

## Confirmed Findings

### specs/017-body-editor-shell/plan.md

#### System Design
- [F-001] [Medium] :77 -- F3 fix regression — debounced <pre> snapshot lags the SOLE visible text layer (typed text invisible up to ~100ms)  [Likely]
  Severity: Medium
  File: specs/017-body-editor-shell/plan.md
  Line: 77
  Pattern: F3 fix regression — debounced <pre> snapshot lags the SOLE visible text layer (typed text invisible up to ~100ms)
  Confidence: Likely
  Category: system_design
  Evidence:
  ```
  code area = real `<textarea>` bound to `body.raw.text` (editable, native caret/IME, per-keystroke store write) + aria-hidden `<pre>` rendering `compose(debouncedText, lang, validVars)` where `debouncedText` = trailing-debounced (`BODY_HIGHLIGHT_DEBOUNCE_MS`, default 100ms) snapshot of `body.raw.text` (F3)
  ```
  Why it's wrong: The F3 fix debounces the ENTIRE `<pre>` snapshot, not just the expensive tokenise pass — and in the react-simple-code-editor technique the plan itself adopts, the `<pre>` is the ONLY visible text layer. Plan Summary (plan.md:35) quotes the chosen technique as "the canonical react-simple-code-editor technique — transparent textarea, CSS-Grid alignment, single scroll source", and the design mockup confirms it: `design/styles.css:1115-1118` gives `.code-editor pre { color: var(--text) }` and the `.tk-*` colored spans live in the pre — there is no visible textarea text (it must be transparent, else doubled text). Because the overlay `<pre>` is debounced with a TRAILING 100ms debounce, during any continuous typing burst the trailing edge never fires until the user pauses ≥100ms, so the pre stays frozen at the pre-burst snapshot and every character typed in the burst is INVISIBLE until the user stops. That is a perceptible input-lag / invisible-typing regression for a code editor, introduced by the F3 fix. The spec sanctions "debounce/off-keystroke" for the TOKENISE (§7 c3b) and AC-9 permits highlight convergence within one interval — but neither sanctions the visible TEXT itself lagging; debouncing the whole snapshot conflates the cheap text render with the expensive coloring.
  Remediation: Split the two: render the `<pre>` TEXT from the LIVE `body.raw.text` (plain, uncolored `var(--text)` — the same degrade path D6 already defines for the >50k ceiling) so characters appear immediately, and debounce ONLY the JSON structural tokenise/coloring pass (plain-immediate → colored on the trailing edge). This honours §7 c3b (no synchronous full-body tokenise per keystroke) without freezing the sole visible text layer, and keeps native-caret immediacy.

#### Best Practices
- [F-002] [Info] :47 -- F4 verification — bare object-type union does not enforce XOR under strict TS ("unrepresentable" claim overstated)  [Likely]
  Severity: Info
  File: specs/017-body-editor-shell/plan.md
  Line: 47
  Pattern: F4 verification — bare object-type union does not enforce XOR under strict TS ("unrepresentable" claim overstated)
  Confidence: Likely
  Category: best_practice
  Evidence:
  ```
  The KVTable prop union intersects the shared optional `validVars?` onto both arms (`(… | …) & { validVars? }`, F4) — `validVars?` is present-optional, NOT a discriminant, so `{field}` XOR `{rows,onRowsChange}` mutual-exclusion + narrowing are preserved.
  ```
  Why it's wrong: The F4 fix itself is sound on the part that mattered — intersecting `validVars?` distributes to `({field} & {validVars?}) | ({rows,onRowsChange} & {validVars?})`, so `validVars?` survives on both arms and `'rows' in props` still narrows cleanly; that claim holds and the missing-highlight CT keeps type-checking. But the repeated §3.1 justification that the union enforces "`{field}` XOR `{rows,onRowsChange}` mutual-exclusion" (also stated in D3 as "makes both-props/neither-props unrepresentable") is only half true under strict TS. Neither-props IS unrepresentable (a bare `{validVars}` is assignable to no arm). Both-props is NOT: `{field:'params', rows, onRowsChange}` passes JSX excess-property checking (each property exists in at least one union member, so none is "excess") and is structurally assignable to the `{field}` arm — a classic non-discriminated-union gotcha. True mutual exclusion needs `?: never` guards on each arm (`{field; rows?: never; onRowsChange?: never} | {field?: never; rows; onRowsChange}`), which the plan's type does not use. This is non-functional in practice (BodyEditor/App each pass exactly one shape, and `writeRows`' `'rows' in props` narrows deterministically even if both were passed), so it is Info-level — but the plan's stated §3.1 "unrepresentable" guarantee is inaccurate and should not be relied on as the correctness argument.
  Remediation: Either add the `?: never` companions to each arm to make both-props genuinely unrepresentable (matching the "XOR / unrepresentable" claim), or soften the D3/§3.1 wording to "narrows via `'rows' in props`; callers pass exactly one shape" and drop the "both-props unrepresentable" guarantee. No functional change is required for the current call sites.


## Summary
- Critical: 0 | High: 0 | Medium: 1 | Info: 1
- Confirmed: 2 | Contested: 0 | Dismissed: 1 | Uncertain: 0
- Disposition: REVISE-PLAN
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable plan-level defect; uncertain findings could not be resolved from the plan alone. A reviewer may want to glance at them before accepting the verdict.

### Dismissed
- [D-001] [Medium] specs/017-body-editor-shell/data-model.md:90 -- F3 fix regression — gutter/scroll derived from debounced snapshot diverges from the LIVE textarea for up to 100ms (AC-23 transient)

## Methodology
Findings are grounded -- every finding carries a verbatim quote from the
actual plan/spec/research artefacts. A refutation stage cross-examines each
grounded finding before it reaches the report: a finding earns the headline
only by surviving an adversary who default-dismisses anything not
demonstrable as a real plan-level defect. Confirmed findings reach the
headline; dismissed and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; high-stakes [CONTESTED] findings
(security / [CONSTITUTION-VIOLATION] / [DATA-LOSS] / [IRREVERSIBLE] the
refuter could not confirm) are surfaced in the headline, flagged
[CONTESTED], never buried.
