# Handoff — finish feature 010-request-bar-fidelity (HEAD chip-mode fix)

**Branch**: `spec/010-request-bar-fidelity` · **Date written**: 2026-06-29

## TL;DR — one `/fix` left, then close the feature

The feature is functionally done and fidelity-matched. The **only** open item is a confirmed **2× High** defect from the latest `/review`: the chip-mode method-select fix covered 6 of 7 HTTP methods — **HEAD is missing** — so a HEAD tab in `data-mstyle='chip'` renders white-on-light (unreadable), and the chip CT only tests GET+POST so it's uncaught.

Resume with: **`/fix`** → **`/review`** → **`/verify`** → **`/summarize`** → **`/finalize`**.

## The exact defect (confirmed by /review refutation, 2 High findings)

`specs/010-request-bar-fidelity/review.md` (latest) holds both:

1. **`RequestBar.css:368`** — chip counter-rules enumerate only GET/POST/PUT/PATCH/DELETE/OPTIONS. `METHODS` (`src/renderer/src/lib/httpMethods.ts:29`) = `['GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD']` — **HEAD** is the 7th. `RequestBar.tsx:269` emits `cx('request-bar__method','method',method)` → a HEAD tab gets the `.HEAD` class. With no HEAD chip rule, HEAD falls to the `(0,3,0)` `background: var(--bg-elev)` override (white) + `#fff` text from `[data-mstyle='chip'] .method` (tokens.css) → white-on-light.
2. **`RequestBar.ct.tsx:1067`** (chip describe block, lines 1078–1196) — asserts only GET + POST backgrounds; no HEAD test.

## The fix (verified facts)

- Token EXISTS: `--m-head` in `src/renderer/styles/tokens.css` (light `#ec4899` line 53, dark `#f472b6` line 103). No token addition needed.
- Current chip rules: `RequestBar.css:363–368` (GET..OPTIONS), inside a `stylelint-disable no-descending-specificity` block.

**CSS** (`RequestBar.css`): add the 7th rule after line 368, same form/specificity (0,5,0):

```css
[data-mstyle='chip'] .request-bar .request-bar__method.method.HEAD {
  background: var(--m-head);
  border: none;
}
```

**Consider a more robust form** than enumeration (the enumeration is exactly what let this reopen): e.g. drive the per-method chip background off a single CSS custom property the method class sets, so a future `METHODS` addition can't silently break chip again. If that's not clean, at minimum the enumeration must stay in lockstep with `METHODS` (7 rules) — add a comment tying it to `METHODS`.

**CT** (`RequestBar.ct.tsx` chip-mode describe block ~line 1078): add a HEAD assertion (probe-resolved `var(--m-head)` background). **Better**: loop over all 7 `METHODS` so the test can't drift from the CSS again. Reuse the existing probe-element + `data-mstyle='chip'` inner-beforeEach pattern already in that block. Seed/switch to a HEAD tab (the two-tab fixture supports method switching).

## How to run it

`/fix` (auto-resolves this feature, reads the 2 High findings from `review.md`). It's a defect repair — no `/specify` bounce. Scope will be `RequestBar.css` + `RequestBar.ct.tsx`. Brief the implementing agents to (a) add the HEAD chip rule, (b) extend chip CT to cover HEAD/all-7. The CSS change does NOT alter soft-mode render, so the screenshot baseline should not need regen (confirm: CT screenshot test stays green; if it reports a diff, investigate rather than blindly updating).

## ⚠️ Critical process caveats (do NOT skip)

1. **`/fix` → `/review` → `/verify` order — never `/fix` then cold `/verify`.** `review.md` currently lists the 2 HEAD findings as confirmed. After `/fix`, they're stale-but-present; a cold `/verify` folds them → false NEEDS WORK. Re-run `/review` after `/fix` to refresh `review.md` to clean, THEN `/verify`. (Memory: `fix-then-rereview-before-verify`.)
2. **`consume-tmp` parser bug — filed as `bugs/004-review-consume-tmp-parser.md`.** During `/review`, qa-reviewer and design-auditor findings silently parse to **0** when they use `- Field:` (dash), `**Field**:` (bold), or backtick-wrapped `File:` paths. Watch for `parsed[... 0]` when an agent clearly reported findings — if seen, normalize the tmp file (strip `- `, `**…**`, backticks) before re-running `consume-tmp`/`validate-findings`. This bug will be fixed in the framework repo, not here. (Memories: `review-finder-dash-prefix-parse`, `review-qa-quote-mismatch-drops-findings`.) Brief finders to write PLAIN field labels (no dash, no bold, unquoted File paths).
3. **Runtime fidelity NEVER machine-verified** — Chrome MCP was down every run; all design checks were static CSS-vs-`design/styles.css` diffs. If `ac_verification_mode` is runtime-assisted and Chrome MCP is back, `/verify` can finally do the real check.
4. **`design-manifest.json` has empty `elements`** — no MATCH/DEVIATE disposition table, which is why design-auditor kept surfacing reference mismatches the spec intentionally diverges from (e.g. AC-11 mandates visible Save/Share TEXT; the reference is icon-only). Those nits were all refuter-dismissed as not-AC-scoped. Populating the manifest (a `/breakdown` PHASE-2.5 task) would stop the noise — optional, not blocking the feature.
5. **Subagent infra was flaky** (watchdog stalls + a classifier hiccup) at the time of writing — re-dispatch any stalled finder/reviewer; keep agent prompts concise to reduce stalls.

## Pipeline state

- All 3 tasks Complete (`tasks/README.md`). Spec NOT yet flipped to Complete (that happens on `/verify` APPROVED).
- WIP commits on branch (squashed later by `/finalize`), newest first:
  - `9c6f9b5` review · `6374ea1` fix(chip) · `ff5d0e9` review · `5e5af06` fix(fidelity) · `346ddce` review · `b471a66` fix(fidelity) · `2990c99` review · `7656dde` fix(AC-20) · `e821ca3` task003 · `b3cac77` task002 · `c6b78fb` task001 (+ checkpoints + spec/plan/breakdown/research WIP).
- Base/merge-base for the assembled diff: `0eb938d7a8d855f9b9615de79a20a64e8c903541`.
- Working tree: `review.md` + `review-state.json` already committed (`9c6f9b5`). Pre-existing dirty: forge planning artifacts (`.devforge/*`, etc.) — expected, harmless (precise-staging protects per-task commits).

## What's already solid (don't re-litigate)

- Markup (visible Save/Share labels, canSend-gated aria-hidden ⌘↵ keycap), AC-20 test isolation, all design-fidelity values (border tokens, font-mono URL, paddings, hovers, method (0,3,0) no-color override) — fixed + locked by 26 CT computed-style assertions.
- chip-mode regression fixed for 6/7 methods + chip CT for GET/POST. Only HEAD remains.

## Relevant memories (auto-loaded)

`method-mstyle-background-override-chip` (the chip root cause + why CT pinning one mstyle hid it), `fix-then-rereview-before-verify`, `review-finder-dash-prefix-parse`, `ct-fidelity-fixture-scoping`, `ct-layout-baseline-keycap-confound`.
