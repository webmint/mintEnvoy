# Empirical bugs — preempt-from-day-one items

These five items shipped during the `/configure` Step 6 audit (2026-05-10). `/constitute` preempts each from day one — the spec text, helper validators, and install-side guards are all wired so the same failure modes do not recur.

## 1. Stop discipline (Phase 3 plain-prose echo)

**Symptom in `/configure`**: Phase 3 (bulk-confirmation echo) was originally written as a single fenced echo block followed by setter calls in the same assistant turn. The LLM auto-advanced through the bulk confirmation without waiting for user reply — the user's "yes" / overrides arrived after the setters had already fired with detected values.

**Why it matters for `/constitute`**: Phase 3 here is per-section — six echo turns (1-6) plus optional Section 7 (greenfield). Each section MUST end the assistant turn after its echo, awaiting the user's reply. Auto-advancing a single section is bad; auto-advancing six in a row corrupts every rule, table, and code example without user oversight.

**Mitigation in the spec**: each section's echo template in `main.md` § Phase 3 is preceded by an explicit "Stop discipline (mandatory)" directive that names the failure mode literally — "Do NOT echo the next section in the same turn. Do NOT call any `set-*` / `add-*` subcommand in the same turn. Do NOT call any tool after the echo." Plain-prose prompts have no harness-level "wait for user" affordance, so the LLM-level stop is the only mechanism.

**Mitigation in the helper**: none — this is a spec-discipline concern, not a code concern. The helper cannot enforce LLM turn boundaries.

## 2. JSON-array setter form (rule text + table cells with internal commas)

**Symptom in `/configure`**: a setter call like `set-error-handlings Either<DataError, T>, BLoC notifications` was parsed as TWO comma-separated values (`Either<DataError`, `T>, BLoC notifications`) because `_validate_string_array` split on `,` first. TypeScript generic syntax (`Either<DataError, T>`, `Result<Ok, Err>`, `Map<K, V>`) and prose with commas (`thrown exceptions, with global handler`) all hit this trap.

**Why it matters for `/constitute`**: rule text + table cells + code-example annotations frequently contain TS generics + multi-clause prose. `add-rule --text "errors propagate via Either<DataError, T>"` works fine because `--text` is a scalar (not split). But `add-table --columns "Layer, Path, Contains, Imports from"` would split on the `,` inside `"Imports from"` if that column happened to contain a comma; `add-table --rows-json '[["data", "src/data/", "Concrete impls, .graphql files", ...]]'` is the correct JSON-array form.

**Mitigation in the spec**: `main.md` § Phase 3 "Setter mapping per section" shows JSON-array form for `--columns` + `--rows-json` as the default in the example invocations. The Phase 3 echo template footer reminds the user explicitly: "For string-array fields whose values contain literal commas (e.g., TypeScript generic syntax `Either<DataError, T>`), supply the value as a JSON array — the helper's `_validate_string_array` accepts either form."

**Mitigation in the helper**: `_validate_string_array` accepts BOTH JSON-array and comma-separated forms. JSON-array is the safer default; comma-sep stays for backward compatibility with simple lists.

## 3. Case-insensitive enums (rule tag values)

**Symptom in `/configure`**: spec text said "use lowercase tag values only" and the LLM dutifully transcribed user input down-cased. But users typed mixed-case (`Extracted`, `Universal`) in their override lines, and the spec's transcription rule conflicted with the helper's actual behavior — `_validate_enum` was already case-insensitive, so the LLM's down-cast was redundant work that occasionally introduced typos.

**Why it matters for `/constitute`**: the `rule_tag` enum has four values (`extracted`, `enforced`, `universal`, `project-specific`); `code_label` has three uppercase values (`CORRECT`, `WRONG`, `EXAMPLE`). Users will type both casings depending on context. Spec text saying "use lowercase only" wastes LLM cycles and creates user-facing friction ("why did my `Extracted` get rewritten?").

**Mitigation in the spec**: `main.md` § Phase 3 "Parsing the user reply" notes "Tag values are case-insensitive (helper's `_validate_enum` normalizes mixed-case to canonical lowercase / uppercase per enum)." No instruction to down-cast in the LLM. The LLM passes through user input verbatim; the helper normalizes.

**Mitigation in the helper**: `_validate_enum` is case-insensitive — accepts `extracted` / `Extracted` / `EXTRACTED` and returns the canonical form (lowercase for `rule_tag`, uppercase for `code_label`).

## 4. install.sh stray-state-file guard

**Symptom in `/configure`**: early development churned the state file extension (yaml → json → yaml → json again). Stray `configure.yaml` files left behind in `src/devforge/` from old runs got picked up by the install rsync and shipped into target projects as data, breaking fresh installs that then loaded the stray data instead of writing fresh defaults.

**Why it matters for `/constitute`**: `/constitute` ships `.devforge/constitute.json` + `.devforge/constitute.json.lock`. If a developer runs `/constitute` against the forge repo itself (or a stray state file otherwise lands in `src/devforge/`), `install.sh` would carry it into target projects.

**Mitigation in the framework** (already shipped in CONSTITUTE-PLAN.md Step 0): `install.sh` includes a stray-state-file guard that errors out when `src/devforge/constitute.json` or `src/devforge/constitute.json.lock` is present. `.gitignore` complements with the same entries so accidental commits are blocked.

**Mitigation in the spec**: none — this is framework-side hygiene, not user-facing behavior. The spec does not need to mention it; the guard fires before `/constitute` is invoked.

## 5. Wrapper-mode path resolution

**Symptom in `/configure`**: in wrapper mode (`workspace_mode = wrapper`, `project_root = <inner-folder>`), early helper code wrote `project-config.json` inside `<inner-folder>/` instead of at install root. Downstream commands that loaded `project-config.json` via `Path("./.devforge/project-config.json")` got file-not-found errors because the helper had walked into the inner project root.

**Why it matters for `/constitute`**: `<install_root>/constitution.md` is the render artifact. In wrapper mode (`/Users/x/forge-wrapper/` is the install root, `/Users/x/forge-wrapper/client-project/` is the project root), `constitution.md` MUST land at `/Users/x/forge-wrapper/constitution.md`, NOT inside `client-project/`. All framework artifacts (`docs/`, `specs/`, `constitution.md`) live at install root regardless of wrapper mode.

**Mitigation in the spec**: `main.md` § Outputs and § Phase 5 both name `<install_root>/constitution.md` explicitly. The placement-rule sentence ("Lives at install root in both standalone and wrapper modes (parallels `docs/`); never inside `project_root`.") is preserved verbatim.

**Mitigation in the helper**: `constitute_helper`'s `--install-root` argument defaults to the parent of `--devforge-dir` (resolved as an absolute path), so the helper writes to the correct location regardless of CWD at invocation time. `cmd_render` uses `Path(args.install_root) / "constitution.md"` — never `project_root`-prefixed.
