# Research: code-editor-toggle

**Date**: 2026-07-19
**Signals detected**: architectural decision with multiple valid approaches — (1) caret-at-click placement mechanism (AC-12/AC-13, spec Q-1); (2) scroll retention across an edit↔preview toggle (spec Q-2). No external-library / new-service / new-stack signals: the change uses only the native `textarea`, standard DOM APIs, and the already-present `jsonTokens.compose()` lib.

## Questions Investigated

1. **Caret-at-click: native focus vs coordinate→offset mapping (Q-1)?** → In this design the click target is the highlighted **`pre`** (the textarea is NOT mounted at click time — it mounts only on entering edit), so native `textarea.focus()` cannot land the caret at the clicked character. A coordinate→offset mapping IS required. `document.caretPositionFromPoint(x, y)` (the standard API, now in Chromium) returns a `CaretPosition {offsetNode, offset}`; `document.caretRangeFromPoint(x, y)` (older Blink/WebKit API) is the fallback. Both are available in Electron's Chromium renderer. The known "textarea offset is wrong" caveat does NOT apply here because the hit target is the `pre` (normal text nodes / token spans), not a textarea. To convert the hit `(node, offset)` to an absolute string offset across multiple token spans, build a `Range` from the pre's start to the caret point and take `range.toString().length`. Then `textarea.setSelectionRange(offset, offset)` after mount+focus. **Decision**: coordinate→offset mapping via `caretPositionFromPoint` with `caretRangeFromPoint` fallback, absolute offset via Range length, clamp for AC-13.

2. **Out-of-bounds click clamp (AC-13)?** → A click past end-of-line or below the text yields a `caretPositionFromPoint` hit on the nearest text node / the pre container. `Range.toString().length` from pre-start to that hit naturally lands at the nearest character / end-of-text, satisfying "clamp to nearest character." Additionally clamp the computed offset to `[0, value.length]` defensively (a null hit → fall back to `value.length`). **Decision**: clamp computed offset to `[0, value.length]`; a null/failed hit falls back to end-of-text.

3. **Scroll retention across an edit↔preview toggle (Q-2)?** → Conditional-mount unmounts the hidden layer, so its `scrollTop`/`scrollLeft` is lost on every toggle (the MEMORY "mount-all hidden scroll preservation" lesson: `display:none`/unmount loses scrollTop and `focus()` can re-clobber it). Both layers bind the same `--code-line-h` (20.625px) and identical padding, so a captured offset maps 1:1 between them. **Decision**: preserve within-tab scroll across a toggle — stash `{scrollTop, scrollLeft}` in a ref at switch time, restore it in a layout-effect after the new layer mounts, and use `focus({preventScroll: true})` on the textarea so focus does not re-clobber the restored offset. AC-6's tab-switch reset (resetKey) still zeroes scroll on tab change — that path is unchanged and takes precedence.

## Alternatives Compared

### Caret-at-click placement (AC-12 / AC-13)
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Coordinate→offset mapping (`caretPositionFromPoint` on the pre → Range-length → `setSelectionRange`) | Lands caret at the actual clicked char (AC-12); Range-length handles multi-span pre; natural clamp (AC-13) | ~20 lines of new code (no repo canonical exists) | **Chosen** |
| Native `textarea.focus()` only | Zero new code | Cannot place caret at the pre-click position — textarea isn't mounted at click time; fails AC-12 | Rejected |

**Decision**: Coordinate→offset mapping — the only option that satisfies AC-12 (caret at clicked character), since the click lands on the pre while the textarea is unmounted.

### Scroll retention across toggle (Q-2)
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Reset scroll on every toggle | Simplest; no capture ref, no restore effect, no cross-component effect-ordering surface | User loses scroll place on each edit↔preview flip on long JSON | **Chosen (revised)** |
| Capture-at-switch ref + layout-effect restore + `focus({preventScroll})` | Preserves scroll on long bodies | A capture ref + a restore `useLayoutEffect` whose correctness depends on a same-commit editing-reset precondition across BodyEditor↔CodeEditor — three `/grill` cycles surfaced adjacent effect-ordering edge cases (inert passive-clear; unpinned same-commit precondition; CT gap) | Rejected (descoped) |

**Decision (revised after 3 `/grill` cycles)**: Reset the code-area scroll to (0,0) on EVERY edit↔preview toggle. The capture/restore approach (originally chosen) generated three consecutive REVISE-PLAN cycles of effect-ordering edge cases, all in this optional-nicety family (spec Q-2, which the spec deliberately left open). Descoping scroll-retention removes the entire capture-ref + restore-`useLayoutEffect` + effect-ordering surface, yielding a strictly simpler design. AC-6's tab-switch reset is unchanged; the per-toggle reset is a superset of it.

## References
- [MDN — Document.caretPositionFromPoint()](https://developer.mozilla.org/en-US/docs/Web/API/Document/caretPositionFromPoint) — standard API, returns `CaretPosition {offsetNode, offset}`; textarea-offset caveat does not apply to a `pre` hit target
- [MDN — Document.caretRangeFromPoint()](https://developer.mozilla.org/en-US/docs/Web/API/Document/caretRangeFromPoint) — non-standard Blink/WebKit fallback available in Chromium/Electron
- MEMORY: `mount-all-hidden-scroll-preservation` — capture-at-switch + layout-effect restore + `focus({preventScroll:true})`
- research/2026-07-19-change-the-raw-mode.md — recommended approach + the two open uncertainties this file resolves
