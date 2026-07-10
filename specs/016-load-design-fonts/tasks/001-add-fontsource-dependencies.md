# Task 001: Add @fontsource dependencies

**Feature**: 016-load-design-fonts
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002
**Spec criteria**: AC-2
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| package.json | Modify | Add `@fontsource/inter` + `@fontsource/jetbrains-mono` to dependencies |

## Description

Install the self-hosted webfont packages that supply the woff2 files the app will bundle. `@fontsource/inter` and `@fontsource/jetbrains-mono` each ship per-weight latin woff2 under `node_modules/<pkg>/files/`. This task only adds + installs the dependencies; the `@font-face` rules that reference the woff2 are authored in task 002.

## Change Details

- In `package.json`:
  - Add `@fontsource/inter` and `@fontsource/jetbrains-mono` under `dependencies` (they are bundled into the renderer build, so runtime deps, not devDeps).
- Run the install so `node_modules/@fontsource/{inter,jetbrains-mono}/files/*.woff2` exist for task 002's `url()` to resolve against.

## Contracts

### Expects (checked before execution)
- `package.json` has a `dependencies` object.

### Produces (checked after execution)
- `package.json` `dependencies` contains `@fontsource/inter` and `@fontsource/jetbrains-mono`.
- `node_modules/@fontsource/inter/files/` and `node_modules/@fontsource/jetbrains-mono/files/` exist and contain latin `*-normal.woff2` files.

## Done When

- [x] `@fontsource/inter` and `@fontsource/jetbrains-mono` appear in `package.json` dependencies and are installed
- [x] `node_modules/@fontsource/inter/files/` and `node_modules/@fontsource/jetbrains-mono/files/` contain latin woff2 files
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-09T18:31:54Z
**Files changed**: package.json, package-lock.json
**Contract**: Expects 1/1 | Produces 2/2
**Notes**: Installed @fontsource/inter + @fontsource/jetbrains-mono ^5.2.8; latin woff2 confirmed present (inter-latin-{400,500,600,700}-normal.woff2, jetbrains-mono-latin-{400,700}-normal.woff2). npm install run in main thread (subagent watchdog-stall avoidance).
