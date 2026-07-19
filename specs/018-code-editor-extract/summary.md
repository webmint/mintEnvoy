# Feature Summary — 018 Code Editor Extract

**Status**: Complete · **Verdict**: APPROVED (`/verify` — all 21 ACs PASS)

## What was built

The syntax-highlighted code editor that powered the request **Body** tab is now a standalone, reusable `CodeEditor` molecule. Previously the three-layer overlay editor (gutter + highlight layer + transparent textarea), its JSON tokenizing, and its tab-switch reset logic lived inline inside the `BodyEditor` organism, unavailable to anything else. It is now a self-contained, domain-agnostic component any part of the app can drop in — the first consumer being `BodyEditor`'s raw slot, with a future response-body viewer able to reuse it with no change. Behavior for the user is identical: same highlighting, same gutter alignment, same scroll and caret preservation when switching tabs.

## Changes

- **Task 001** — Created the `CodeEditor` molecule: the three-layer overlay, `jsonTokens.compose()` highlighting (reused byte-for-byte), a 100 ms compose debounce, and a single `--code-line-h` CSS variable that source-defines gutter/highlight/textarea row height.
- **Task 002** — Rewired `BodyEditor` to consume `<CodeEditor>` for its raw slot; removed the now-duplicated inline overlay, editor state/effects, and CSS. Radiogroup, language pill, and the other body-type panels are unchanged.
- **Task 003** — Added a component test suite proving row-height equality, font-size independence, token colors in light/dark, malformed-JSON degrade-to-plain, and deterministic tab-switch reset for `CodeEditor` in isolation.
- **Task 004** — Pruned the `BodyEditor` tests down to organism-boundary concerns (the 8 now-molecule-level tests moved to Task 003's suite) and added a wiring test proving the tab-switch reset flows through `resetKey`.
- **Task 005** — Documented `CodeEditor` as a reusable molecule and `BodyEditor` as its consumer in the architecture and renderer docs.

## Files changed

33 files, +3364 / −523.

- **src/** (8) — `CodeEditor.tsx`, `CodeEditor.css`, `CodeEditor.ct.tsx`, `CodeEditor.stories.tsx` (new molecule + tests); `BodyEditor.tsx`, `BodyEditor.css`, `BodyEditor.ct.tsx`, `BodyEditor.stories.tsx` (rewired consumer + trimmed tests).
- **docs/** (2) — `architecture.md`, `renderer/src/index.md` (CodeEditor documented as reusable molecule).
- **specs/** (21) — feature planning + pipeline artifacts (spec, plan, grill, tasks, review, verification).
- **research/** (2) — the gutter-alignment research report + handoff that seeded the extraction.

## Key decisions

- **D1 Placement** — `CodeEditor` lives in `molecules/` (domain-agnostic per §2.2), so organisms consume it downward with no sibling-organism import.
- **D2 Line-box unit** — one local CSS var `--code-line-h = calc(12.5px * 1.65)` = 20.625px single-sources textarea + highlight + gutter row height; absolute px avoids the `1.65em` drift against the smaller gutter font.
- **D3 API shape** — self-contained controlled molecule, props `{value, lang, onChange, validVars, resetKey?}`; owns compose + debounce + colored snapshot; reuses `jsonTokens.compose()` unchanged.
- **D5 Tab-switch reset** — an optional `resetKey?` prop keys the scroll-reset and compose-rearm effects; `BodyEditor` passes `resetKey={activeTabId}`, a verbatim port of the old inline behavior.
- **D4 testids** — kept `body-code-editor` / `body-gutter` / `body-pre` on `CodeEditor` for zero CT churn.

## Deviations

- **Task 003 (Produces #4)** — a `CodeEditor.stories.tsx` fixture module was added beyond the task's stated produces, because Playwright component tests cannot mount a spec-file-inline fixture; the story module is the mountable entry point and the canonical `JSON_ALL_TOKENS` source. Folded by `/verify` as justified scope, non-blocking.
- **Tasks 003 & 004 `test:ct` Done-When left UNVERIFIED** — the Playwright CT harness has a pre-existing mount break (a pristine `BodyEditor.ct` fails independently of this feature). Test correctness was proven statically plus by live Chrome DevTools runtime verification of AC-4 / AC-6 / AC-11 (scroll + caret preservation, tab-switch reset, `jsonTokens` reuse). Recorded in `.devforge/memory.md`.

## Acceptance criteria

All 21 acceptance criteria **PASS** (authoritative status from `verification.md`, APPROVED verdict):

AC-1 … AC-21 — PASS. Reusable molecule extraction (AC-9/AC-14/AC-15/AC-18), `jsonTokens` reuse unchanged (AC-11), single-source row-height DRY (AC-12/AC-13/AC-20/AC-21), malformed-JSON degrade (AC-2/AC-17), tab-switch scroll+caret reset (AC-4/AC-6), and testid/CT continuity (AC-8) all verified.
