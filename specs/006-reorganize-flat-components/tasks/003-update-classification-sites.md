# Task 003: Update constitution and architecture-doc classification sites to the new layout

**Feature**: 006-reorganize-flat-components
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-8, AC-9, AC-10, AC-14
**Review checkpoint**: No
**Context docs**: docs/architecture.md

## Files

| File                 | Action | Description                                                                                                                                   |
| -------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| constitution.md      | Modify | Add the labelled domain-placement rule inside §2.2; update the §2.2 EXAMPLE membership tree and the §5.1 UI-primitives list to the new layout |
| docs/architecture.md | Modify | Update all five moved-path citation sites to the new layout                                                                                   |

## Description

Update the three classification sites that enumerate the renderer component layout so they reflect the post-move structure, in lockstep with the code moves from tasks 001–002. Docs-only task — no source code, no import graph, no runtime impact.

1. **Constitution §2.2 — add the domain-placement rule.** Record a single labelled rule inside §2.2 that EXTENDS (does not replace) the existing §2.2:56 layering canon. Use this exact wording for the rule's substance (compose nothing new):

   > Shared + domain-agnostic components belong in `molecules/`; single-domain-bound components belong in `organisms/<domain>/`; create an `organisms/<domain>/` subfolder only when a domain reaches ≥2 components (no empty future domain folders); no barrel/index files.

2. **Constitution §2.2 EXAMPLE membership tree** (the `**EXAMPLE** — renderer module structure` fenced tree, ~l.70): update the `molecules/` and `organisms/` lines so `molecules/` lists `Divider` and `organisms/` shows the `shell/` group (Shell, Titlebar, Statusbar, PaneSplit) plus the flat `Sidebar`, `TabBar` singletons.

3. **Constitution §5.1 UI-primitives list** (~l.198): reclassify `Divider` as a molecule and group the shell organisms, matching the membership tree in lockstep.

4. **docs/architecture.md — all five moved-path citation sites:**
   - UI-Primitives Layer table row (~l.30): move `Divider` to the molecules row, group Shell/Titlebar/Statusbar/PaneSplit under `organisms/shell/`.
   - Prose tier description (~l.68): same reclassification in the narrative.
   - Module-structure tree (~l.83): reflect `molecules/ … Divider` and `organisms/shell/ …`.
   - The two code-comment path markers: `<!-- … organisms/Shell.tsx:250 -->` → `organisms/shell/Shell.tsx:250`, and `<!-- … organisms/Divider.tsx:250 -->` → `molecules/Divider.tsx:250`.
   - Mermaid Dependency Overview (~l.310): the `organisms[…]` and `molecules[…]` nodes reflect the new grouping (Divider under molecules; shell group under organisms/shell).

Do not change any other content. Line numbers above are guides — locate each site by its surrounding text, not by line number (earlier edits shift lines).

## Change Details

- In `constitution.md` §2.2:
  - Add the labelled domain-placement rule (wording above) as a new bullet/labelled line extending the existing layering-canon bullets.
  - In the EXAMPLE module-structure tree: change the `molecules/` comment to include `Divider`, and change the `organisms/` comment to show the `shell/` group (Shell, Titlebar, Statusbar, PaneSplit) plus flat `Sidebar`, `TabBar`.
- In `constitution.md` §5.1 (UI primitives line):
  - Move `Divider` from the organisms enumeration to the molecules enumeration; group the shell organisms.
- In `docs/architecture.md`:
  - Update the UI-Primitives Layer table, prose tier description, module-structure tree, the two `Shell.tsx`/`Divider.tsx` path-comment markers, and the mermaid Dependency Overview nodes, all to the new layout.

## Contracts

### Expects (checked before execution)

- (from tasks 001–002) `Divider` lives under `components/molecules/`; `Shell`/`Titlebar`/`Statusbar`/`PaneSplit` live under `components/organisms/shell/`.
- `constitution.md` contains a §2.2 section with the EXAMPLE membership tree and a §5.1 UI-primitives list.
- `docs/architecture.md` contains the UI-Primitives Layer table, the module-structure tree, the `Shell.tsx`/`Divider.tsx` path-comment markers, and the mermaid Dependency Overview.

### Produces (checked after execution)

- `constitution.md` §2.2 contains a single labelled domain-placement rule (the `molecules/` vs `organisms/<domain>/` wording).
- `constitution.md` §2.2 membership tree lists `Divider` under `molecules/` and shows the `organisms/shell/` group; §5.1 list classifies `Divider` as a molecule — both in lockstep.
- `docs/architecture.md` UI-Primitives table, prose, module tree, both path-comment markers, and mermaid all reflect the new layout.
- No occurrence of `organisms/(Divider|Shell|Titlebar|Statusbar|PaneSplit)` as a path in `constitution.md` or `docs/architecture.md`.

## Done When

- [x] §2.2 carries the labelled domain-placement rule (extends the existing canon, does not replace it)
- [x] §2.2 membership tree and §5.1 UI-primitives list both reflect the new layout (Divider→molecule, shell group)
- [x] docs/architecture.md table, prose, module tree, both path markers, and mermaid all reflect the new layout
- [x] `grep -nE 'organisms/(Divider|Shell|Titlebar|Statusbar|PaneSplit)' constitution.md docs/architecture.md` returns nothing
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (no .ts/.tsx touched — no-op)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T22:09:06Z
**Files changed**: constitution.md, docs/architecture.md
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Updated 3 classification sites to new layout: constitution §2.2 (added Domain-placement rule + tree), §5.1 list; docs/architecture.md table/prose/tree/2 path-markers/mermaid. Lockstep verified; old-path grep clean. eslint/build green.
