# Feature Verification — 001-ui-primitives — 2026-06-22

**Feature**: specs/001-ui-primitives
**Date**: 2026-06-22
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | `src/renderer/src/components/atoms/icons.ts:14-157` — `ICONS` const map with 40+ named icon entries, `IconName = keyof typeof ICONS` type union exported at line 157. |
| AC-20 | PASS (code) | `package.json:38-60` — devDeps include `vitest@^3.2.4`, `@testing-library/react@^16.3.0`, `@testing-library/user-event@^14.5.2`, `@testing-library/jest-dom@^6.6.3`, `@playwright/experimental-ct-react@^1.50.1`. Scripts: `"test": "vitest run"`, `"test:ct": "playwright test -c playwright.config.ts"`. `vitest.config.ts` and `playwright.config.ts` both present and configured. |
| AC-21 | PASS (code) | Atoms: `src/renderer/src/components/atoms/Icon.tsx`, `icons.ts`, `Icon.css`. Molecules: `src/renderer/src/components/molecules/Dropdown.tsx`, `Modal.tsx`, `Toast.tsx` (with `.css` counterparts). All confirmed present by direct file reads. |
| AC-2 | PASS (code) | `Dropdown.tsx:247-253` — `DropdownMenu.Content` with `avoidCollisions={true}` delegates keyboard navigation to Radix (Arrow/Home/End/typeahead). `Dropdown.ct.tsx:33-161` — full CT suite covering ArrowDown, ArrowUp, Home, End keys in real Chromium. |
| AC-3 | PASS (code) | `Dropdown.tsx:233` — `DropdownMenu.Trigger asChild` enables Radix focus-return; `Modal.tsx:168` — `Dialog.Trigger asChild`; both comment AC-3. CT: `Dropdown.ct.tsx:208-261`, `Modal.ct.tsx:87-116` assert focus on trigger after close in real Chromium. |
| AC-4 | PASS (code) | `Dropdown.tsx:246-253` — Radix `DropdownMenu.Content` handles Escape via DismissableLayer and click-outside via its own pointer event wiring (both dispatch `onOpenChange(false)`). `Dropdown.test.tsx:148-162` and `Dropdown.ct.tsx:168-201` cover both paths. |
| AC-5 | PASS (code) | `Dropdown.tsx:248-253` — `avoidCollisions={true}`, `collisionPadding={8}`, `sideOffset={4}` set on `DropdownMenu.Content`. `Dropdown.ct.tsx:332-403` — two CT tests (bottom-right and top-left trigger positions) assert bounding box lies within the viewport. |
| AC-6 | PASS (code) | `Modal.tsx:178` — `Dialog.Overlay className="modal-overlay"` (Radix mounts RemoveScroll for scroll lock); `Modal.tsx:184` — `Dialog.Content` (Radix mounts FocusScope for focus trap). `Modal.test.tsx:128-177` — scroll-lock `data-scroll-locked` assertion. `Modal.ct.tsx:151-225` — Tab/Shift+Tab focus-trap CT. |
| AC-7 | PASS (code) | `Modal.tsx:143-148` — doc comment "Escape close (DismissableLayer): pressing Escape fires `onOpenChange(false)`"; `Modal.test.tsx:183-197` — unit test asserts `onOpenChange` called with `false` on Escape. Focus-return on close delegated to Radix FocusScope (AC-3). |
| AC-8 | PASS (code) | `toastStore.ts:80-87` — `scheduleTimer` registers a `setTimeout` that calls `dismiss(id)` after `ms`. `toastStore.test.ts:79-103` — fake-timer tests assert toast removed at exactly the duration elapsed; `Toast.test.tsx:288-313` — DOM removal integration test. |
| AC-9 | PASS (code) | `toastStore.ts:174-201` — `pauseTimer` records `remaining` and clears the timer; `resumeTimer` restarts from `remaining`. `Toast.tsx:101-106` — `onPause`/`onResume` props wire Radix's pointer/focus events to store methods. `toastStore.test.ts:109-224` and `Toast.test.tsx:170-280` cover pause/resume. |
| AC-10 | PASS (code) | `toastStore.ts:163-172` — `dismiss(id)` filters array to remove only the matching id, no-ops for unknown id. `toastStore.test.ts:231-258` and `Toast.test.tsx:113-163` assert one toast removed, others remain. |
| AC-11 | PASS (code) | `Dropdown.tsx:117-130` — `open: boolean` / `onOpenChange: (open: boolean) => void` props; `Modal.tsx:75-87` — same pattern. `Dropdown.test.tsx:93-142` and `Modal.test.tsx:95-122` assert menu/dialog presence reflects `open` prop and `onOpenChange` fires correctly. |
| AC-12 | PASS (code) | `nested-overlays.ct.tsx:26-68` — CT test: open Modal + nested Dropdown, first Escape closes only dropdown (menu gone, modal visible), second Escape closes modal. Focus-return chain also tested at `nested-overlays.ct.tsx:75-113`. Radix DismissableLayer stacks overlays internally. |
| AC-13 | PASS (code) | `icons-glue.ts:35-38, 64-72` — `FALLBACK_ENTRY` (diamond path), `resolveIcon` returns fallback for any non-existent name (never throws). `Icon.tsx:84-88` — additional runtime guard `safeMarkup = typeof markup === 'string' ? markup : ''`. `icons-glue.test.ts:7-61` + `Icon.test.tsx:82-108` cover all unknown-name paths. |
| AC-14 | PASS (code) | `Icon.css:47-51` — `@media (prefers-reduced-motion: reduce) { .icon--spin { animation: none } }`. `Dropdown.css:229-234` — `@media` rule disables `.dropdown-content` animation. `Modal.css:187-194` — overlay and content animations suppressed. `Toast.css:197-201` — toast slide-in suppressed. All four have real-browser CT: `Icon.ct.tsx`, `Dropdown.ct.tsx:410-447`, `Modal.ct.tsx:28-81`, `nested-overlays.ct.tsx:152-223`. |
| AC-22 | PASS (code) | `toastStore.ts:230-248` — `export function toast(message, opts)` calls `toastStore.getState().enqueue(message, opts)` and returns the id. Shorthand variants `toast.info`, `toast.success`, `toast.warning`, `toast.error` also exported. `toastStore.test.ts:284-324` — imperative API fully tested. |
| AC-23 | PASS (code) | `Icon.tsx:83-119` — renders `<svg viewBox="0 0 16 16" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={1.5}>` with inner geometry from `resolveIcon(name).markup`. Default `size=16`. `Icon.test.tsx:20-79` — asserts viewBox, stroke-width, width/height=16, fill, stroke on `<svg>`. |
| AC-15 | PASS (code) | All public interfaces and components have JSDoc: `IconProps` (Icon.tsx:28-66), `Icon` function (Icon.tsx:70-82), `DropdownProps` (Dropdown.tsx:117-189), `DropdownItemDescriptor` (Dropdown.tsx:89-114), `DropdownItem`/`DropdownSeparator`/`DropdownLabel` (Dropdown.tsx:310+, 352+, 362+), `ModalProps` (Modal.tsx:74-129), `Modal` (Modal.tsx:136-152), `ToastProviderProps` (Toast.tsx:177-180), `ToastProvider`/`ToastViewport` (Toast.tsx:201+, 226+). |
| AC-24 | PASS (code) | `docs/architecture.md:27-34` — "### Renderer Test Stack" section documents: Vitest + @testing-library/react + user-event (jsdom) for interaction tests; Playwright component tests (`@playwright/experimental-ct-react`) for real-browser focus/keyboard fidelity; configuration files and test file glob patterns listed. |
| AC-16 | PASS (code) | `tsconfig.web.json` extends `@electron-toolkit/tsconfig/tsconfig.web.json` (which enables strict mode per electron-toolkit). grep for `: any` in renderer source files returned zero results. No `@ts-ignore` or `as any` casts found in the primitive source files. |
| AC-17 | PASS (code) | `eslint.config.mjs` — configures `@electron-toolkit/eslint-config-ts` (strict TS rules), `eslint-plugin-react`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, and Prettier. No `eslint-disable` comments found in the primitive source files. |
| AC-18 | PASS (code) | Shell grep for `style={{` across all five primitive component files (Icon.tsx, Dropdown.tsx, Modal.tsx, Toast.tsx, PrimitivesDemo.tsx) returned zero matches. Size is set via `width`/`height` SVG attributes in Icon.tsx:98-99, not inline style. |
| AC-19 | PASS (code) | Shell grep for `from 'electron'`, `from 'node:'`, and `require('electron')` across all renderer component and lib files returned zero matches. `toastStore.ts:9` and `icons-glue.ts:9` both explicitly document "NO node/electron imports". |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/001-ui-primitives/review.md
**Scope creep**: 147 changed file(s) outside the planned scope: "design/mintenvoy \342\200\224 a friendly API client.html", .claude/agents/ac-verifier.md, .claude/agents/api-designer.md, .claude/agents/architect.md, .claude/agents/code-reviewer.md (+ 142 more)
**Leftover artifacts**: 337 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

7 confirmed | 0 contested | 2 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 2 High, 5 Medium, 0 Info

## Issues Found

### High

- [High] src/renderer/src/components/molecules/Toast.css:60 — Cross-task architectural drift — diverged token surface for surface/text colors across molecule tasks
- [High] src/renderer/src/components/molecules/__tests__/Toast.stories.tsx:33 — Cross-task CT fixture exercises only one variant of the Icon→Toast composed path, leaving three variant/icon pairings untested in a real browser

### Medium

- [Medium] src/renderer/src/components/molecules/Dropdown.tsx:247 — Cross-task duplication — `[...].filter(Boolean).join(' ')` className-merge pattern open-coded independently across three task outputs with no shared utility
- [Medium] src/renderer/src/components/molecules/Toast.css:62 — Cross-task architectural drift — two sibling molecule stylesheets styling the same concern (surface bg/text/border/radius) bind to two different design-token namespaces; one molecule diverges from the feature's design-system token source
- [Medium] src/renderer/src/components/molecules/Toast.css:59 — Cross-task divergence — hardcoded design-token values in Toast where Dropdown and Modal consume the tokens by reference
- [Medium] src/renderer/src/components/molecules/Toast.tsx:155 — Assembled-data-flow performance — full-list re-render on every pause/resume event due to whole-array replacement in store + full-array selector in subscriber
- [Medium] src/renderer/src/components/molecules/__tests__/nested-overlays.ct.tsx:26 — AC-14 reduced-motion coverage is present for all four individual components (tasks 003/005/006/007) but absent in the assembled nested-overlay CT suite (task mix of 005+006+007), leaving the composed animation-suppression path untested in a real browser

## Verdict

**NEEDS WORK**

**Reasons**:

- Critical/High review findings: [High] Cross-task architectural drift — diverged token surface for , [High] Cross-task CT fixture exercises only one variant of the Icon.
- Hygiene issues: 147 scope-creep file(s), 337 leftover artifact(s).

**Next step**: address the issues above, then re-run `/verify`. Run `/implement` for code fixes.
