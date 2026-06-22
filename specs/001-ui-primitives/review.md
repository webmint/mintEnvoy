# Feature Review — specs/001-ui-primitives — 2026-06-22

**Feature**: specs/001-ui-primitives
**Scope**: assembled feature diff (all tasks together) — 160 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst
**Refuters invoked**: code-reviewer, architect
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
1. [Medium] src/renderer/src/components/molecules/Toast.tsx:125 — An abstraction one task introduced (cx) that another task bypassed — Toast open-codes className composition instead of routing through the shared helper the sibling molecules adopted [Likely]
2. [Medium] src/renderer/src/components/molecules/__tests__/Dropdown.test.tsx:349 — Cross-task icon-rendering path gap — the items-array `icon` prop route through Dropdown (Task 7) to Icon (Task 3) is untested; only the children-API `DropdownItem icon` path is exercised [Certain]
3. [Low] src/renderer/src/components/molecules/Toast.css:76 — Two tasks that each made a locally-reasonable choice now globally inconsistent — the defensive var() fallback-literal convention the sibling molecule stylesheets establish is dropped by Toast's variant rules [Likely]

## Confirmed Findings

### src/renderer/src/components/molecules/Toast.css

#### System Design
- [F-002] [Low] :76 — Two tasks that each made a locally-reasonable choice now globally inconsistent — the defensive var() fallback-literal convention the sibling molecule stylesheets establish is dropped by Toast's variant rules  [Likely]
  Severity: Low
  File: src/renderer/src/components/molecules/Toast.css
  Line: 76
  Pattern: Two tasks that each made a locally-reasonable choice now globally inconsistent — the defensive var() fallback-literal convention the sibling molecule stylesheets establish is dropped by Toast's variant rules
  Confidence: Likely
  Category: system_design
  Evidence:
  ```
  .toast--info {
    border-left: 3px solid var(--accent);
  }
  ```
  Why it's wrong: Dropdown.css and Modal.css establish a uniform convention that every `var()` carries a defensive fallback literal so the rule stays legible if the sheet loads before tokens.css in an isolated test environment — Dropdown.css documents it explicitly in its header ("Every var() call includes a defensive fallback literal") and applies it everywhere (e.g. `var(--accent, #10b981)` at `src/renderer/src/components/molecules/Dropdown.css:60`); Modal.css does the same (`var(--accent, #10b981)` at `src/renderer/src/components/molecules/Modal.css:87`). Toast.css follows that convention in its base/text rules (`var(--accent, #10b981)`-style fallbacks at lines 59-63, 132-137) but drops it precisely in the variant block — `var(--accent)`, `var(--status-2xx)`, `var(--status-4xx)`, `var(--status-5xx)` at lines 76, 80, 84, 88, plus the icon-tint and focus rules (lines 106-118, 177). The assembled three-molecule CSS surface therefore carries two contradictory answers for the same concern, and Toast.css is even internally inconsistent against its own header claim. Theme-switching still works (the tokens resolve at runtime from tokens.css), so this is drift, not breakage.
  Remediation: Add the same fallback literals to Toast.css's variant/icon/focus rules (e.g. `var(--accent, #10b981)`, `var(--status-2xx, #16a34a)`, `var(--status-4xx, #f59e0b)`, `var(--status-5xx, #ef4444)`) so the fallback convention is uniform across Dropdown.css, Modal.css, and Toast.css — or, if the team decides fallbacks are unnecessary, drop them everywhere and remove the "defensive fallback" claims from the file headers. Either way, pick one answer across the molecule stylesheets.


### src/renderer/src/components/molecules/Toast.tsx

#### System Design
- [F-001] [Medium] :125 — An abstraction one task introduced (cx) that another task bypassed — Toast open-codes className composition instead of routing through the shared helper the sibling molecules adopted  [Likely]
  Severity: Medium
  File: src/renderer/src/components/molecules/Toast.tsx
  Line: 125
  Pattern: An abstraction one task introduced (cx) that another task bypassed — Toast open-codes className composition instead of routing through the shared helper the sibling molecules adopted
  Confidence: Likely
  Category: system_design
  Evidence:
  ```
  className={`toast toast--${variant}`}
  ```
  Why it's wrong: The remediation introduced `cx()` at `src/renderer/src/lib/cx.ts` as the single intended path for className composition, and its own docstring (lines 4-7) states it "Replaces the open-coded `[...].filter(Boolean).join(' ')` idiom used across Icon, Dropdown, and Modal." Icon (`src/renderer/src/components/atoms/Icon.tsx:93`), Dropdown (`src/renderer/src/components/molecules/Dropdown.tsx:248`, `259`, `331`), and Modal (`src/renderer/src/components/molecules/Modal.tsx:184`, `189`) all compose classes through `cx()`. Toast is the one molecule that reaches around the shared abstraction and builds its class string with a raw template literal, so the assembled feature has no single answer for "how does a component build its className." The bypass is benign at runtime here (a fixed base class plus a guaranteed-present variant token, no falsy branch), which is why this is a consistency/architectural-drift defect rather than a behavioral bug — but it leaves the cx() adoption incomplete across the four components it was meant to unify.
  Remediation: Compose the Toast root class via `cx('toast', `toast--${variant}`)` so all four components (Icon, Dropdown, Modal, Toast) route className composition through the single shared helper, completing the cx() adoption the remediation intended.


### src/renderer/src/components/molecules/__tests__/Dropdown.test.tsx

#### Mislogic
- [F-003] [Medium] :349 — Cross-task icon-rendering path gap — the items-array `icon` prop route through Dropdown (Task 7) to Icon (Task 3) is untested; only the children-API `DropdownItem icon` path is exercised  [Certain]
  Severity: Medium
  File: src/renderer/src/components/molecules/__tests__/Dropdown.test.tsx
  Line: 349
  Pattern: Cross-task icon-rendering path gap — the items-array `icon` prop route through Dropdown (Task 7) to Icon (Task 3) is untested; only the children-API `DropdownItem icon` path is exercised
  Confidence: Certain
  Category: blind_spot
  Evidence:
  ```
  describe('DropdownItem icon', () => {
    it('renders an svg icon when the icon prop is supplied', () => {
      render(
        <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
          <DropdownItem onSelect={vi.fn()} icon="copy">
            Copy URL
          </DropdownItem>
        </Dropdown>
      )
  ```
  Why it's wrong: The Dropdown component (Task 7) exposes two rendering paths for icons: (a) the children API via `DropdownItem` with an `icon` prop (lines 322–347 of Dropdown.tsx), and (b) the items-array API where `items[].icon` is rendered inline inside the `items.map()` branch at `src/renderer/src/components/molecules/Dropdown.tsx:266–270`. Both paths render the same `<Icon>` atom from Task 3, but path (b) is never exercised in any test or CT fixture: `Dropdown.test.tsx` only tests path (a) via `<DropdownItem icon="copy">`, and neither `Dropdown.stories.tsx` nor `Dropdown.ct.tsx` include any fixture item with an `icon` field. The gap is cross-task because the items-array branch was introduced by Task 7 (Dropdown) and depends on the Icon rendering contract established by Task 3 (Icon), while the Icon tests (Task 3) exercise the atom in isolation but never through the Dropdown items-array route. A regression in how Dropdown.tsx passes the `icon` name to `<Icon>` in the items-array branch would go undetected by any existing test.
  Remediation: Add a test case to Dropdown.test.tsx (or its CT counterpart) that exercises the items-array API with an `icon` field — e.g., `items={[{ id: 'x', label: 'Copy', icon: 'copy', onSelect: vi.fn() }]}` — and asserts that an `<svg>` element is rendered inside the item, mirroring the existing DropdownItem icon test at line 350 but using the items-array route.


## Summary
- Critical: 0 | High: 0 | Medium: 2 | Info: 0
- Confirmed: 3 | Contested: 0 | Dismissed: 3 | Uncertain: 0
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable emergent defect at feature scope; uncertain findings could not be resolved from the code alone. A reviewer may want to glance at them before closing the review.

### Dismissed
- [D-001] [Medium] src/renderer/src/components/molecules/Toast.css:76 — Cross-task divergence — Toast.css omits var() fallback literals on variant-specific tokens while Dropdown.css and Modal.css always include them
- [D-002] [Info] src/renderer/src/components/molecules/Toast.tsx:125 — Cross-task divergence — Toast.tsx open-codes className assembly with a template literal; every other atom and molecule uses the shared cx() helper
- [D-003] [Medium] src/renderer/src/components/__tests__/PrimitivesDemo.test.tsx:29 — Cross-task shared-store leakage — PrimitivesDemo test renders toastStore consumers (Task 9) without resetting the module-level store owned by Task 4, while Toast.test.tsx (Task 5) does reset it

## Methodology
Findings are grounded — every finding carries a verbatim quote from the actual
cross-task code, and validation discards ungrounded ones. A refutation stage
then cross-examines each grounded finding before it reaches the report: a
finding earns the headline only by surviving an adversary who default-dismisses
anything not demonstrable as emergent at feature scope. Confirmed findings reach
the headline; dismissed findings and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; contested findings (a high-stakes `security`
/ `[CONSTITUTION-VIOLATION]` finding the refuter could not confirm, or a
`[CONSTITUTION-VIOLATION]` finding the refuter dismissed) are surfaced in the
headline, flagged `[CONTESTED]`, never buried. This report is findings only —
the verdict is `/verify`'s.
