# Task 001: restructure requestbar markup

**Feature**: 012-requestbar-element-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 004
**Spec criteria**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-12, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                                                | Action | Description                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| src/renderer/src/components/organisms/RequestBar.tsx                | Modify | Wrap URL input in a `.url-bar` flex container with a leading aria-hidden `<Icon name="link">`; set placeholder to the exact reference string; drop the Share visible text node (icon-only) + add `aria-label="Share"`; keep Save label. Presentational only — no logic change. |
| src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx | Modify | Extend unit asserts: exact placeholder string, Share icon-only accessible name (`getByRole('button', { name: 'Share' })`), Save visible label retained.                                                                                                                        |

## Description

Presentational markup restructure of the RequestBar organism to close three of the five fidelity gaps that need markup changes: (1) the URL field becomes a `.url-bar` flex container holding a leading decorative link icon plus the existing input; (2) the placeholder string is corrected; (3) the Share button becomes icon-only while retaining its accessible name via `aria-label`. Save keeps its visible label. ZERO behaviour change: the input stays bound to `RequestSpec.url` via `updateActiveSpec`, the `canSend` trim guard reads the same value, Shell stays the sole writer of `data-mstyle`, Share stays a disabled no-op stub, and all keyboard/Send/Save paths are untouched. The `link` Icon already exists in `atoms/icons.ts` — reuse it, add nothing to the icon set. Unit tests in the sibling `.test.tsx` are extended to lock the new markup semantics.

## Change Details

- In `src/renderer/src/components/organisms/RequestBar.tsx`:
  - Replace the bare `<input className="request-bar__url" …>` block with a `<div className="url-bar">` container wrapping a leading `<Icon name="link" size={13} aria-hidden />` (decorative) followed by the existing `<input className="request-bar__url" …>`. Keep the input's `value={url}`, `onChange={(e) => updateActiveSpec({ url: e.target.value })}`, and `aria-label="Request URL"` exactly as-is.
  - Change the input `placeholder` from `"Enter URL"` to exactly `Enter URL or paste cURL command…` (literal text only — no cURL parsing, no other behaviour).
  - In the Share button, remove the visible `Share` text node so it renders icon-only (`<Icon name="share" size={13} />` only) and add `aria-label="Share"`; keep `disabled aria-disabled="true"` and its final-slot position. Update the adjacent comment to state the accessible name now comes from `aria-label` (was: visible text).
  - Leave the Save button, Send button + keycap, method Dropdown, store bindings, `canSend`, handlers, and the keydown effect unchanged.
  - Update the JSDoc/inline comments to document the `.url-bar` restructure and the icon-only Share with restored `aria-label` (AC-14).
- In `src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx`:
  - Add/adjust asserts: placeholder is exactly `Enter URL or paste cURL command…`; the Share button is resolvable by `getByRole('button', { name: 'Share' })` and contains no visible "Share" text node; the Save button still exposes its visible "Save" label. Keep all existing behaviour asserts green.

## Contracts

### Expects (checked before execution)

- `RequestBar.tsx` renders the URL as a bare `<input className="request-bar__url">` with `placeholder="Enter URL"` and the Share button carries a visible `Share` text node.
- `link` is exported in the icon map in `src/renderer/src/components/atoms/icons.ts` (`link:` key present).
- `updateActiveSpec` and the `canSend` (`url.trim() !== ''`) predicate exist in `RequestBar.tsx`.

### Produces (checked after execution)

- `RequestBar.tsx` contains a `className="url-bar"` container element wrapping an `<Icon name="link"` (aria-hidden) and the `className="request-bar__url"` input.
- The URL input `placeholder` attribute is exactly the string `Enter URL or paste cURL command…`.
- The Share `<button>` has `aria-label="Share"`, remains `disabled`, and contains no visible "Share" text node.
- The Save `<button>` retains its visible `Save` text label.
- `RequestBar.tsx` contains no `data-om-`, `__OmT`, or `tweaks-panel` markers and no `style={{` inline-style attribute (outside comments).
- `RequestBar.test.tsx` asserts the exact placeholder, the Share `getByRole` name of "Share", and the retained Save label.

## Done When

- [x] `.url-bar` container wraps a leading aria-hidden link `<Icon>` + the existing URL input in `RequestBar.tsx`
- [x] URL input placeholder is exactly `Enter URL or paste cURL command…`
- [x] Share renders icon-only with `aria-label="Share"`, still `disabled`, in its final slot
- [x] Save keeps its visible label; store bindings / `canSend` / keydown effect unchanged (no logic change)
- [x] `! grep -REn 'data-om-|__OmT|tweaks-panel' src/renderer/src/components/organisms/RequestBar.tsx` passes (AC-1)
- [x] No inline `style={{` in `RequestBar.tsx` outside comments (AC-18)
- [x] `npx vitest run src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx` passes with the new placeholder / Share-name / Save-label asserts (AC-19)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (`npm run typecheck:web`)
- [x] Linter passes on changed files (`npm run lint`)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-01T08:09:48Z
**Files changed**: src/renderer/src/components/organisms/RequestBar.tsx, src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx
**Contract**: Expects 3/3 | Produces 6/6
**Notes**: Markup-only restructure; .url-bar CSS lands in task 002 (intermediate unstyled visual state expected). Tests 34/34 (raw vitest); typecheck+lint+build clean.
