# Project Constitution — {{PROJECT_NAME}}

Generated: {{DATE}}
Last updated: {{DATE}}

> Sections marked `[universal]` are pre-populated with rules that apply to ALL projects.
> Sections marked `[project-specific]` are populated by `constitute` based on your codebase or interview answers.
> Header fields in Section 1 are populated by the setup wizard from Phase 1 detection + Phase 2 answers. Per-stack details for multi-stack projects (Sections 3.2 / 3.4) follow the same paired-rendering rules as agent files — see `CLAUDE.md` `## Packages` section for the per-package breakdown.

---

## 1. Project Identity

**Name**: {{PROJECT_NAME}}
**Type**: {{PROJECT_TYPE}}
**Framework(s)**: {{FRAMEWORK}}
**Language(s)**: {{LANGUAGE}}
**Workspace Mode**: {{WORKSPACE_MODE}}
**Project Root**: {{PROJECT_ROOT}}

> For multi-package projects, per-package stack details (one row per package with language / framework / architecture / error-handling / API layer / testing) live in the `## Packages` section of `CLAUDE.md`, not duplicated here.

---

## 2. Architecture Rules [project-specific]

<!-- Populated by constitute — these depend on your chosen architecture -->

### 2.1 Layer Boundaries
_Run constitute to populate_

### 2.2 File Organization
_Run constitute to populate_

### 2.3 Dependency Rules
_Run constitute to populate_

---

## 3. Code Quality Standards

### 3.1 Type Safety [project-specific]
_Run constitute to populate with language-specific type rules_

### 3.2 Error Handling [project-specific]
- **Pattern**: {{ERROR_HANDLING}}

> For multi-stack projects, `{{ERROR_HANDLING}}` renders as paired bullets — one per stack (e.g., `"neverthrow Result<T,E> (TypeScript/Next.js), exceptions + returns.Result (Python/FastAPI)"`). `"TBD"` entries (user deferred in Q5) are omitted; `constitute` fills them in later.

_Run constitute to populate details_

### 3.3 Naming Conventions [project-specific]
_Run constitute to populate with project naming patterns_

### 3.4 Testing Requirements [project-specific]
- **Framework**: {{TESTING}}

> For multi-stack projects, `{{TESTING}}` renders as paired bullets — one per stack (e.g., `"vitest (TypeScript/Next.js), pytest (Python/FastAPI)"`). `"N/A"` stacks (no tests) are kept with the stack label so it's explicit; `"TBD"` entries are omitted.

_Run constitute to populate details_

### 3.5 Universal Code Quality [universal]

**No dead code.** Delete unused functions, variables, imports, and files. Do not comment them out "for later." Version control preserves history.

**No debug artifacts in committed code.** Remove all `console.log`, `print()`, `debugger`, `binding.pry`, `dd()`, and similar statements before marking a task complete. Logging that is part of the application's intentional logging system is fine.

**No magic values.** Use named constants for numbers and strings that carry meaning. `if (status === 3)` is wrong. `if (status === ORDER_COMPLETE)` is right.

**One function, one job.** If a function does two unrelated things, split it. If a function name has "and" in it, it probably does too much.

**Early returns over deep nesting.** Check error conditions first and return early. Do not nest happy-path logic inside multiple `if` blocks.

```
// Bad
function process(input) {
  if (input) {
    if (input.isValid) {
      // 20 lines of logic
    }
  }
}

// Good
function process(input) {
  if (!input) return;
  if (!input.isValid) return;
  // 20 lines of logic
}
```

**Keep functions short.** If a function exceeds ~40 lines, look for extraction opportunities. This is a guideline, not a hard rule — sometimes a long function is clearer than several small ones.

**Consistent style within a file.** If a file uses one pattern (arrow functions, single quotes, specific import style), follow that pattern. Do not introduce a different style.

*Backed by* `constitute_helper verify-magic-enum` when `forcing_functions.magic_enum_duplication.enabled = true` in `.devforge/constitute.json` — inline literals where a same-module enum-like declaration (TS `enum` / `as const` map / Python `Enum`) covers the same value surface as exit-2 findings when `constitute_helper verify-magic-enum` is run directly or via the optional `.devforge/templates/git-hooks/pre-commit-forcing-functions.sh` hook.

*Backed by* `constitute_helper verify-any-leak` when `forcing_functions.any_with_generated_available.enabled = true` — `any` annotations (TypeScript) / `Any` (Python) in files importing from declared generated-types dirs surface as exit-2 findings when `constitute_helper verify-any-leak` is run directly or via the pre-commit hook.

### 3.6 Design Principles [universal]

**SOLID:**
- **Single Responsibility** — a class/module/function has one reason to change. If you can't describe what it does without "and," split it.
- **Open/Closed** — extend behavior through composition or new implementations, not by modifying existing working code.
- **Liskov Substitution** — subtypes must be usable wherever their parent type is expected without breaking behavior.
- **Interface Segregation** — don't force consumers to depend on methods they don't use. Prefer small, focused interfaces over large ones.
- **Dependency Inversion** — depend on abstractions (interfaces, types), not concrete implementations. High-level modules should not import from low-level modules directly.

**DRY (Don't Repeat Yourself):**
- If the same logic appears in 3+ places, extract it into a shared function or utility.
- 2 occurrences are fine — don't abstract prematurely. Wait for the third.
- DRY applies to logic, not to code that looks similar but serves different purposes. Two functions that happen to look alike but handle different domain concepts should stay separate.

**KISS (Keep It Simple, Stupid):**
- Choose the simplest solution that works correctly.
- Don't add abstractions, patterns, or layers "in case we need them later."
- If a junior developer can't understand the code in 30 seconds, it's too complex.

*Backed by* `constitute_helper verify-cross-layer-imports` when `forcing_functions.cross_layer_imports.enabled = true` in `.devforge/constitute.json` — import edges that cross declared layer boundaries (per the user-supplied DAG + per-layer dir mapping in the rule config) surface as exit-2 findings when `constitute_helper verify-cross-layer-imports` is run directly or via the optional `.devforge/templates/git-hooks/pre-commit-forcing-functions.sh` hook.

### 3.7 Check Before You Build [universal]

**Before writing anything generic or reusable, search first.** The codebase may already have:
- A utility function that does what you need
- A helper, composable, or hook that covers your use case
- A shared component that handles this UI pattern
- A type or interface that models this data

Search for it using Grep and Glob before creating a new one. Duplicating existing functionality is worse than not having it — it creates confusion about which version to use and doubles the maintenance burden.

---

## 4. Patterns & Anti-Patterns

### 4.1 ALWAYS Do [universal]

- **Read before write.** Always read a file before modifying it. Understand what exists before changing it.
- **Handle both paths.** Every operation that can fail must handle the success case AND the error case. No unhandled promise rejections. No ignored return values from fallible operations.
- **Validate at boundaries.** Validate all external input: user input, API responses, file content, environment variables. Trust internal code. Do not validate data that your own code just created.
- **Name what things ARE, not what they DO temporarily.** Variable names describe the data. Function names describe the action. `userData` not `tempVar`. `calculateTotal` not `doStuff`.
- **Test your assumptions.** If a change depends on "X should already be Y," verify it. Read the code. Don't assume.

### 4.1.1 ALWAYS Do [project-specific]
_Run constitute to populate with concrete examples from your codebase_

### 4.2 NEVER Do [universal]

- **Never swallow errors silently.** Empty `catch` blocks are forbidden. If you catch an error, you must either: (a) handle it meaningfully, (b) re-throw it, or (c) log it and explain why you're suppressing it.

```
// Forbidden
try { doThing(); } catch (e) {}

// Forbidden
try { doThing(); } catch (e) { /* ignore */ }

// Acceptable
try { doThing(); } catch (e) {
  logger.warn('Non-critical: doThing failed, using fallback', e);
  return fallbackValue;
}
```

- **Never commit secrets.** No API keys, passwords, tokens, private keys, or credentials in code. Not in variables, not in comments, not in test files, not "temporarily." Use environment variables or secret management.
- **Never leave a TODO without context.** `// TODO` alone is useless. Always include: what needs to be done, why it can't be done now, and a reference (ticket number, feature name). Example: `// TODO(FEAT-123): Add pagination after backend supports cursor-based queries`
- **Never modify code outside your task scope.** Do not "fix" unrelated code you happen to see. Do not refactor surrounding code. Do not add type annotations to functions you didn't change. If you see a real problem, note it — don't fix it unless asked.
- **Never guess at behavior.** If you are unsure how existing code works, read it. If you are unsure what the user wants, ask. Guessing leads to wrong implementations that waste time.

### 4.2.1 NEVER Do [project-specific]
_Run constitute to populate with project-specific anti-patterns_

### 4.3 PREFER [universal]

- **Explicit over implicit.** Named parameters over positional. Explicit types over inferred when the inference is non-obvious. Explicit imports over wildcards.
- **Composition over inheritance.** Build behavior by combining small pieces, not by extending base classes. Deep inheritance hierarchies are fragile.
- **Flat over nested.** Flat directory structures over deeply nested ones. Flat conditionals (early returns) over nested if/else chains. Flat data over deeply nested objects when possible.
- **Boring over clever.** Readable, obvious code over clever one-liners. The person reading your code (including future you and other AI agents) should understand it without pausing.
- **Existing patterns over new ones.** When the codebase already has a pattern for something, use it. Do not introduce a second way to do the same thing unless the existing way is clearly broken.
- **Small PRs over large ones.** One concern per change. If a task touches more than 5-7 files, consider whether it can be split.

### 4.3.1 PREFER [project-specific]
_Run constitute to populate with project-specific preferences_

---

## 5. Domain Rules [project-specific]

_Run constitute to populate with business domain terms, rules, and constraints_

---

## 6. Workflow Rules

### 6.1 Minimal Changes [universal]
Every code change MUST impact as little code as possible. Do not refactor, improve, or "clean up" code outside the scope of the current task. A bug fix changes the bug. A feature adds the feature. Nothing more.

### 6.2 Semantic Understanding [universal]
Before renaming or replacing any identifier, VERIFY:
1. What the identifier semantically means
2. All callers and consumers of the identifier
3. That the new name correctly represents the concept
4. That no external contracts (APIs, database columns, config keys) depend on the old name

### 6.3 Read-First Principle [universal]
Before writing ANY code:
1. Read the files you plan to modify
2. Read the files that import/use the code you plan to modify
3. Check the constitution for relevant rules
4. Check memory for past lessons about this area

Skipping this step is the #1 cause of wrong implementations.

### 6.4 Documentation [universal]
- **Read docs before starting**: Before any task, read relevant docs in `docs/` for context about the area you're changing
- **Write docs after completing**: After every task, the tech-writer agent updates `docs/` with changes. This is mandatory — not optional
- All new public functions must have a brief inline description (JSDoc/docstring)
- All new types/interfaces must have a brief inline description
- Do NOT add documentation to code you didn't write or change
- Update existing documentation when you change the behavior it describes
- `docs/` is the source of truth for project documentation — organized by topic, not by task

### 6.5 Deprecation Handling [project-specific]
_Run constitute to populate_

### 6.6 Project-Specific Workflow [project-specific]
_Run constitute to populate_

---

## 7. Scaffolding Guide [greenfield-only]

_This section is populated by `constitute` when run on a greenfield project._
_It contains the recommended directory structure, initial file setup, and bootstrapping steps._

---

## Rule Tags

Rules use these tags to indicate their origin:
- `[universal]` — Applies to all projects. Pre-populated in template.
- `[convention]` — Team convention discovered or decided during `constitute`.
- `[extracted]` — Pattern extracted from existing codebase during `constitute`.
- `[enforced]` — Hard rule with automated checking (linting, type checking, hooks).
- `[recommended]` — Best practice suggestion. Can be overridden with good reason.
- `[greenfield-only]` — Only applies during initial project scaffolding.
- `[project-specific]` — Populated by `constitute` based on your project.