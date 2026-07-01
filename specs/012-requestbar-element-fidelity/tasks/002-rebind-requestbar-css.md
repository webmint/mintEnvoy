# Task 002: rebind requestbar css fidelity

**Feature**: 012-requestbar-element-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 004
**Spec criteria**: AC-9, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File                                                 | Action | Description                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/organisms/RequestBar.css | Modify | Add `.url-bar` container treatment + `:focus-within` accent ring; method-select treatment with the extra `justify-content:center` removed and `color` still unset; Save `.request-bar__save` rest+hover bound to reference tokens; keep the seven `[data-mstyle='chip']` counter-rules in lockstep with `METHODS`; all rules scoped under `.request-bar`. |

## Description

Rebind the RequestBar CSS to `design/styles.css` resolved values via EXISTING `tokens.css` custom-properties — no new tokens, no logic. Three edits: (1) style the new `.url-bar` flex container (from task 001) to the reference `.url-bar` treatment plus a `:focus-within` accent border + 3px accent ring, keeping the inner input mono; (2) remove the extra `justify-content:center` from the method-trigger rule while KEEPING `color` unset (the documented cascade hazard — adding `color` kills all seven per-method colours with no compile error), and keep the reference `.method-select` treatment; (3) bind the Save `.request-bar__save` rest + hover to the reference `.btn-ghost` treatment. The seven `(0,5,0)` `[data-mstyle='chip']` per-method counter-rules MUST stay in lockstep with `METHODS` in `httpMethods.ts` (removing/drifting reintroduces the white-on-white chip regression). All rules stay scoped under `.request-bar`.

## Change Details

- In `src/renderer/src/components/organisms/RequestBar.css`:
  - Add a `.request-bar .url-bar` container rule bound to the reference `.url-bar` (design/styles.css:772-795): `display:flex; align-items:center; gap:6px; border:1px solid var(--border); background:var(--bg-elev); border-radius:var(--radius); height:32px; padding:0 12px; font-family:var(--font-mono); flex:1 1 0; min-width:0`, and a `.request-bar .url-bar:focus-within` rule with an accent border (`border-color:var(--accent)`) + `box-shadow:0 0 0 3px var(--accent-soft)` ring (design/styles.css:785-788). The inner `.request-bar__url` input keeps its mono font at 12.5px; move the border/background/height/padding that previously lived on `.request-bar__url` onto the `.url-bar` container so the container owns the box (input becomes borderless/transparent, `flex:1`, `min-width:0`), preserving no-reflow (AC-12).
  - In `.request-bar .request-bar__method.method`, REMOVE the `justify-content: center;` declaration; keep every other declaration (font-family `--font-mono`, weight 700, font-size 11.5px, letter-spacing 0.04em, padding `7px 10px 7px 12px`, min-width 88px, border `1px var(--border)`, background `var(--bg-elev)`, border-radius `var(--radius)`), and keep NO `color` declaration on this rule (AC-13, the cascade hazard).
  - Confirm `.request-bar__save` rest is `color:var(--text-muted); border:1px solid var(--border); background:var(--bg-elev)` and `.request-bar__save:hover` is `color:var(--text); border-color:var(--border-strong)` — adjust to these exact reference `.btn-ghost` values if drifted (AC-9). Leave the `--dirty` variant untouched.
  - Keep the seven `[data-mstyle='chip'] .request-bar .request-bar__method.method.{METHOD}` counter-rules exactly (one per method: GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD) — do not add, drop, or reorder.
  - Update the file's header/inline comments to document the `.url-bar` container structure and reaffirm the method-trigger no-`color` / no-`justify-content` rule (AC-14).

## Contracts

### Expects (checked before execution)

- `RequestBar.tsx` renders a `className="url-bar"` container wrapping the `.request-bar__url` input (produced by task 001).
- `RequestBar.css` `.request-bar .request-bar__method.method` currently declares `justify-content: center;` and no `color`.
- `tokens.css` defines `--border`, `--border-strong`, `--bg-elev`, `--radius`, `--accent`, `--accent-soft`, `--font-mono`, `--text`, `--text-muted`.
- `METHODS` in `src/renderer/src/lib/httpMethods.ts` lists exactly 7 methods (GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD).

### Produces (checked after execution)

- `RequestBar.css` contains a `.url-bar` rule bound to `var(--border)` / `var(--bg-elev)` / `var(--radius)` / `var(--font-mono)` with `gap:6px`, `height:32px`, `padding:0 12px`, and a `.url-bar:focus-within` rule with `var(--accent)` border + `box-shadow: 0 0 0 3px var(--accent-soft)`.
- `.request-bar .request-bar__method.method` contains NO `justify-content` declaration and NO `color` declaration.
- `.request-bar__save` rest declares `color: var(--text-muted)` and `.request-bar__save:hover` declares `color: var(--text)` + `border-color: var(--border-strong)`.
- Exactly seven `[data-mstyle='chip'] … .method.{METHOD}` counter-rules remain, one per `METHODS` entry.
- No hardcoded colour literals and no `var(--x, <literal>)` fallbacks introduced in the new/edited `.request-bar` rules.

## Done When

- [x] `.url-bar` container styled to the reference treatment + `:focus-within` accent ring; box model owns border/bg/height/padding (AC-12)
- [x] `justify-content:center` removed from the method-trigger rule; `color` still unset (AC-13)
- [x] Save rest (`--text-muted`/`--border`/`--bg-elev`) + hover (`--text`/`--border-strong`) bound to reference tokens (AC-9)
- [x] Seven `[data-mstyle='chip']` counter-rules retained in lockstep with `METHODS` (no white-on-white regression)
- [x] All new/edited rules scoped under `.request-bar`; comments document the changes (AC-14)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (`npm run typecheck:web`)
- [x] Linter passes on changed files (`npm run lint`)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-01T08:40:23Z
**Files changed**: src/renderer/src/components/organisms/RequestBar.css
**Contract**: Expects 4/4 | Produces 5/5
**Notes**: CSS-only rebind. Panel repair leg: added height:100% to input to eliminate dead click-zones (input was natural text-height in 32px container). Save rest/hover already at reference tokens (no change). typecheck+lint+build pass; CSS fidelity CT deferred to task 004.
