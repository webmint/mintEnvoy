# Feature Summary: 001-ui-primitives

**Reusable UI primitives layer** — Dropdown, Modal, Toast, and a project-owned SVG Icon for the mintEnvoy renderer.

## What was built

A presentation-only primitives layer the app's feature components build on: an anchored **Dropdown/popover** (keyboard nav, focus return, click-outside + Escape dismiss, edge-aware positioning), a **Modal** dialog (focus trap, scrim, Escape close, body scroll lock), a transient stacked **Toast** (auto + manual dismiss, hover/focus pause), and an inline **Icon** driven by a project-owned 40-icon set. The three overlays wrap Radix primitives and are styled via semantic classes bound to `tokens.css` design tokens (theme-switchable). A dev-only gallery route exercises every primitive in its states for manual QA. All behavior is verified by jsdom interaction tests plus real-browser Playwright component tests.

## Changes

- **Test stack + Radix** — added `radix-ui`, Vitest + Testing Library + user-event (jsdom), and Playwright component tests.
- **Icon set + lookup** — 40 icons extracted to a typed `IconName` union; `resolveIcon` resolves by name with a safe, non-throwing fallback.
- **Icon component** — inline SVG, attribute-driven sizing (no inline styles), a11y modes, reduced-motion.
- **toastStore** — single zustand store + imperative `toast()` API (`.info/.success/.warning/.error`); auto-dismiss timers, hover/focus pause preserving remaining time.
- **Toast** — renders the store queue over Radix Toast (store owns timing); per-item `React.memo` so one hover re-renders only that toast.
- **Modal** — Radix Dialog wrapper (controlled; focus-trap/scrim/scroll-lock/Escape/focus-return); `title` required for a11y.
- **Dropdown** — Radix DropdownMenu wrapper; edge-aware flip/shift, keyboard nav + activation, dismiss + focus-return.
- **App-root substrate** — single ToastProvider + ToastViewport mounted once; nested overlays compose (Escape closes topmost only, focus nests, toast renders above scrim).
- **Dev demo route** — DEV-gated dynamic import so the gallery JS + CSS are absent from the production bundle.
- **Shared `cx()` helper** — className-merge utility unifying Icon/Dropdown/Modal/Toast.
- **App shell cleanup** — removed the electron-vite starter boilerplate (logo, marketing text, IPC demo link, version badge, wavy-lines background).

## Files changed

Feature code under `src/renderer/` (41 files): `components/atoms/` (Icon, icons set, Icon.css), `components/molecules/` (Dropdown, Modal, Toast + CSS + `__tests__/`), `lib/` (toastStore, icons-glue, cx), `components/PrimitivesDemo`, `App.tsx`, `main.tsx`, `styles/tokens.css`, plus test/build config (`package.json`, `vitest.config.ts`, `playwright.config.ts`, `tsconfig.web.json`, `eslint.config.mjs`).

(The branch's full `main..HEAD` diff is 160 files / +36,212 / −11,828 — the bulk is non-feature: a repo-wide formatter pass over framework files plus pipeline artifacts under `.claude/`, `.devforge/`, `specs/`, `docs/`. The feature itself is the 41 `src/` files above.)

## Key decisions

- **Headless library**: the unified `radix-ui` package (mature Dialog/DropdownMenu/Popover/Toast, official React 19, unstyled + className styling) over hand-rolling.
- **Thin `lib/`**: only `toastStore` + `toast()` + minimal Icon glue; Radix owns focus-trap/positioning (constitution §6.3/§7 "keep lib/ thin").
- **Toast queue in zustand**: the store owns the stack; Radix Toast is the render/a11y primitive, not the queue (constitution §4).
- **Project-owned Icon**: a typed `IconName` string-literal union over the 40-icon set + safe fallback — no icon dependency, no `any`.
- **Token styling**: semantic class names bound to `tokens.css` custom properties; Radix parts take `className` directly (AC-18).
- **Test stack**: Vitest + Testing Library (jsdom) for interactions; Playwright CT covers the jsdom focus/keyboard fidelity gaps.

## Deviations from plan

- **Task 001**: also excluded vendored `.devforge/` + generated Playwright output from ESLint/gitignore and added `vitest/globals` to `tsconfig.web.json` (beyond declared files).
- **Task 003**: the review panel caught and fixed a `title → dangerouslySetInnerHTML` XSS — `title` now renders as an escaped JSX child; only static geometry is injected.
- **Task 006**: cross-cutting — `tokens.css` was never imported anywhere; added the import to `main.tsx` so all token styling resolves, and added a `--scrim` token.
- **Task 009**: fixed a user-reported no-scroll bug in the demo via a `position: fixed` scroll container (without touching the global `body` rule).
- **Post-implement** (`/review` → `/fix`, two rounds): unified Toast onto `tokens.css` (theme-switch fix), added `React.memo` to the toast item (re-render fix), extracted the shared `cx()` helper, added Toast CT variant coverage + a composed reduced-motion CT + an items-array icon test, and tokenized Toast.css fallbacks.

## Acceptance criteria

Status from `verification.md` (`ac_verification_mode: tests`, code-read) — **24/24 PASS**:

- AC-1, AC-20, AC-21 (tooling/artifacts) — PASS
- AC-2…AC-14, AC-22, AC-23 (behavior: keyboard nav, focus trap/return, dismiss, edge-aware, scrim/scroll-lock, toast lifecycle, nested-overlay Escape, reduced-motion, icon fallback, imperative API) — PASS
- AC-15, AC-24 (documentation) — PASS
- AC-16…AC-19 (hygiene: strict types, lint, no inline styles, no node/electron import in renderer) — PASS

**Referenced `/verify` verdict: NEEDS WORK** — driven entirely by non-code artifacts, not feature defects: a stale `review.md` (its findings were remediated by `/fix` after the report was written) and hygiene scope noise (147 scope-creep from framework/pipeline files outside the breakdown baseline + 337 leftover flags that are `//`-comment false positives). The feature's own AC (24/24), mechanical checks (typecheck/lint/build/120 tests), and two review+remediation rounds are clean; the spec was flipped to Complete on that basis.
