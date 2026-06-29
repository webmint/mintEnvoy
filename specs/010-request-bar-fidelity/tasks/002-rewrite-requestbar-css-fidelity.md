# Task 002: rewrite-requestbar-css-fidelity

**Feature**: 010-request-bar-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003
**Spec criteria**: AC-3, AC-5, AC-6, AC-8, AC-9, AC-11, AC-12, AC-14, AC-15, AC-16, AC-17
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/RequestBar.css | Modify | Rewrite geometry + treatment to the reference values using existing tokens; add the ancestor-scoped `(0,3,0)` method-select background override; all new rules scoped under `.request-bar` |

## Description

Rewrite `RequestBar.css` so the bar matches `design/reference.html`'s request bar (reference target values in `design/styles.css`) using ONLY custom-properties that already exist in `tokens.css` — no token additions, no `tokens.css` change. The single Med-risk decision is the method-select treatment: the in-app pill inherits the soft chip (tint background + colour) from `[data-mstyle='soft'] .method.{METHOD}` at specificity `(0,3,0)`, while the existing 009 override `.request-bar__method.method` is only `(0,2,0)` and cannot beat it. Add an ancestor-scoped rule `.request-bar .request-bar__method.method` (specificity `(0,3,0)`) that sets `background`/`border`/`border-radius` (the flat elevated method-select box) and declares **NO `color`**, so per-method text colour falls through to the `.method.{METHOD}` cascade. The override wins the `(0,3,0)` tie by source order (RequestBar.css imports after tokens.css). RequestBar must NEVER write `data-mstyle`. Every new rule is anchored under `.request-bar` so no other `.method` consumer (TabBar) regresses.

## Change Details

- In `src/renderer/src/components/organisms/RequestBar.css`:
  - `.request-bar`: padding `12px 16px`, gap `8px` (reference `.reqbar`).
  - URL input (`.request-bar__url`): height `32px`; `border-radius: var(--radius)`; `:focus` → `outline: none`, `border-color: var(--accent)`, `box-shadow: 0 0 0 3px var(--accent-soft)`.
  - Send (`.request-bar__send`): height `32px`; `border-radius: var(--radius)`; `background: var(--accent)`; `color: var(--text-inverse)`; `font-weight: 600`; `box-shadow: 0 1px 0 rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.15)`; keep the `:disabled` muted state (009 — empty-URL greying preserved).
  - Keycap (`.request-bar__kbd`): `font-size: 11px`, `color: var(--text-faint)`, `background: var(--bg-elev)`, `border: 1px solid var(--border)`, `border-radius: 3px`, `padding: 1px 5px` (reference `.kbd`).
  - Save/Share (`.request-bar__save`, `.request-bar__share`): bordered ghost treatment — height `32px`, `border-radius: var(--radius)`, `border: 1px solid var(--border)`, `background: var(--bg-elev)`, `color: var(--text-muted)`; gap between icon and label; Share stays muted/non-interactive.
  - Method-select override: `.request-bar .request-bar__method.method` → `background: var(--bg-elev)`, `border: 1px solid var(--border)`, `border-radius: var(--radius)`, sizing (`min-width: 88px`, padding ~`7px 10px 7px 12px`, mono `font-weight: 700`, `font-size: 11.5px`), and **no `color` declaration**.
  - Update the file header JSDoc to document the `.request-bar`-scoped fidelity treatment, the `(0,3,0)` ancestor override (correcting the prior non-standard specificity note), and the keycap.
  - All new/changed rules anchored under `.request-bar`.

## Contracts

### Expects (checked before execution)
- Task 001 landed: `RequestBar.tsx` renders a `request-bar__kbd` element inside Send and visible Save/Share labels.
- The method trigger still carries `cx('request-bar__method', 'method', method)`; `tokens.css` defines `--radius`, `--accent`, `--accent-soft`, `--bg-elev`, `--text-faint`, `--text-muted`, `--text-inverse`, `--border`, `--font-mono`.
- `tokens.css` defines `[data-mstyle='soft'] .method.{METHOD}` colour rules.

### Produces (checked after execution)
- `.request-bar` uses `padding: 12px 16px` and `gap: 8px`; URL input, Send, method-select and ghost actions bind `border-radius: var(--radius)` at a `32px` control height.
- `.request-bar__url:focus` declares both `border-color: var(--accent)` and `box-shadow: 0 0 0 3px var(--accent-soft)`.
- `.request-bar__send` declares `font-weight: 600` and an inset-highlight `box-shadow`.
- `.request-bar__kbd` is styled per the reference keycap (border, `--bg-elev`, `border-radius: 3px`).
- A `.request-bar .request-bar__method.method` rule sets `background`/`border`/`border-radius` and declares NO `color`.
- No `data-mstyle` write anywhere in RequestBar; every new rule selector begins with `.request-bar`.

## Done When

- [x] Bar geometry + control height + `--radius` binding match the reference values
- [x] URL focus ring (accent border + `0 0 0 3px var(--accent-soft)`) renders
- [x] Send solid-primary weight-600 + inset shadow; `.kbd` styled
- [x] Method-select `(0,3,0)` override sets bg/border/radius only (no color); per-method text colour still resolves
- [x] Every new rule scoped under `.request-bar`; no `data-mstyle` write
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (npm run typecheck:web)
- [x] Linter passes on changed files (npm run lint)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-29T08:01:15Z
**Files changed**: src/renderer/src/components/organisms/RequestBar.css
**Contract**: Expects 3/3 | Produces 6/6
**Notes**: CSS-only fidelity rewrite to design reference using existing tokens. Method-select (0,3,0) ancestor override (bg/border/radius, no color) wins source-order tie; per-method [data-mstyle] color falls through. New .request-bar__kbd keycap; ghost-bordered Save/Share; Send weight-600 + inset shadow. All selectors .request-bar-scoped; no data-mstyle write. Panel clean R0. Deviation: removed var() fallback literals (token-only bind per spec; CT imports tokens.css globally). No test_command configured — fidelity verified by Task 003 CT.
