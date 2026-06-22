# Task 001: set up renderer test stack and radix dependency

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 004, 005, 006, 007
**Spec criteria**: AC-20, AC-24, AC-16, AC-17
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File                 | Action | Description                                                                                                                                             |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| package.json         | Modify | Add `radix-ui` runtime dep; add `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, Playwright CT dev deps; add a `test` script |
| vitest.config.ts     | Create | Vitest + jsdom config for renderer interaction tests (resolve `@renderer` alias)                                                                        |
| playwright.config.ts | Create | Playwright component-test config                                                                                                                        |
| docs/architecture.md | Modify | Record the chosen renderer test stack under the Testing section                                                                                         |

## Description

Establish the gating test infrastructure (none exists) and install the Radix runtime dependency every overlay molecule needs. This is the first task because §9 risk 2 rates the missing test stack High/gating: every interaction AC is unverifiable without it, and `radix-ui` is a hard runtime prerequisite for tasks 005/006/007. Record the chosen stack in `docs/architecture.md` per constitution §3.4 / AC-24.

## Change Details

- In `package.json`:
  - Add dependency `radix-ui` (unified package).
  - Add devDependencies: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, and Playwright component testing (`@playwright/experimental-ct-react` or `@playwright/test`).
  - Add a `test` script (e.g. `vitest run`) and a Playwright CT script.
- In `vitest.config.ts`:
  - Configure the jsdom environment, React plugin, and the `@renderer` → `src/renderer/src` alias so tests resolve renderer imports.
- In `playwright.config.ts`:
  - Configure Playwright component testing for React.
- In `docs/architecture.md`:
  - Under the Testing section, record: renderer test stack = Vitest + @testing-library/react + user-event (jsdom) for interaction tests, plus Playwright component tests for focus/keyboard fidelity.

## Contracts

### Expects (checked before execution)

- `package.json` has no test runner and no `radix-ui` dependency.
- `zustand` and `react` 19 are already present in `package.json`.
- The `@renderer` alias is defined in `electron.vite.config.ts`.

### Produces (checked after execution)

- `package.json` lists `radix-ui` under dependencies and `vitest` + `@testing-library/react` + `@testing-library/user-event` + `jsdom` + a Playwright CT package under devDependencies, plus a `test` script.
- `vitest.config.ts` exists and configures the jsdom environment + the `@renderer` alias.
- `playwright.config.ts` exists configuring component testing.
- `docs/architecture.md` names the renderer test stack (Vitest + Testing Library + Playwright).

## Done When

- [x] `radix-ui` and the test-stack packages are in `package.json`; `npm install` resolves cleanly
- [x] A trivial smoke test runs green under `vitest run`
- [x] `docs/architecture.md` records the chosen test stack (AC-24)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-21T16:51:42Z
**Files changed**: package.json, package-lock.json, vitest.config.ts, playwright.config.ts, playwright/index.html, playwright/index.tsx, tsconfig.web.json, eslint.config.mjs, .gitignore, docs/architecture.md, src/renderer/src/**tests**/setup.ts, src/renderer/src/**tests**/smoke.test.tsx, src/renderer/src/**tests**/smoke.ct.tsx
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Added radix-ui + Vitest/RTL/user-event/jsdom + Playwright CT. Also (beyond declared files): excluded vendored .devforge/ and generated Playwright output from ESLint+gitignore; added vitest/globals to tsconfig.web.json. Vitest 3/3 + Playwright CT 2/2 (real Chromium) green.
