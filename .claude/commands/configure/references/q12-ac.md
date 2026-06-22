# Q12 — AC verification mode

`/configure` Phase 4 asks one AskUserQuestion to pick the acceptance-criteria verification mode, then conditionally asks three follow-up questions (Q12.1 / Q12.2 / Q12.3) when the user selects `runtime-assisted`. Persist each answer via its setter before issuing the next question.

## Q12 — Mode selection

Use AskUserQuestion: "How should /verify check acceptance criteria?"

- `code-only` (Recommended) — read code; no test execution; no runtime probing
- `tests` — run tests; no runtime probing
- `runtime-assisted` — run app + probe via Chrome DevTools MCP / API calls
- `off` — skip behavioral AC verification; code-reading floor only (advisory, non-blocking)

Save via `.devforge/lib/configure_helper set-ac-verification-mode <choice>`.

### Mode taxonomy

- **`code-only`** — `/verify` reads task output files, source code, and the spec to check that acceptance criteria are mechanically satisfied. No subprocess execution, no runtime probing. Default for projects without a stable test suite or running app.
- **`tests`** — `/verify` runs the project's test suite (per-package, scope-aware) and checks that tests pass alongside reading code. Suitable for projects with reliable test coverage.
- **`runtime-assisted`** — `/verify` boots the app (or assumes it is already running) and probes via Chrome DevTools MCP and/or API calls to validate user-facing behavior. Suitable for web apps with a stable dev server.
- **`off`** — `/verify` skips behavioral AC verification (no browser/API probing, no test execution) but still applies a code-reading floor: it reads the changed files and produces per-AC code-only statuses, noted as code-verified in the verdict (advisory, not blocking). Pick this when the project has no running app and no test suite, or when behavioral AC verification is owned by an external pipeline.

If the user picks `code-only`, `tests`, or `off`, Phase 4 advances directly to Phase 5 — Q12.1 / Q12.2 / Q12.3 are NOT asked.

If the user picks `runtime-assisted`, proceed to the conditional follow-up triple below.

## Q12.1 — Runtime URL (only when mode == `runtime-assisted`)

Phase 2 detection populated `AC_RUNTIME_URL` from matched config files (e.g., `vite.config.*` `server.host` + `server.port`). Pre-fill the prompt with that detected value.

If detection produced a non-empty value, use AskUserQuestion (substitute `<value>` with the Phase 2 composed URL): "Detected runtime URL: `<value>`. Confirm or override?"

- `Confirm` — use the detected URL
- `Override` — let me type a different URL

If the user picks `Confirm`, save via `.devforge/lib/configure_helper set-ac-runtime-url <value>` using the Phase 2 composed value. If the user picks `Override`, follow up with a plain free-text prompt: "What's the runtime URL?", then save via `.devforge/lib/configure_helper set-ac-runtime-url <answer>`.

If detection produced an empty value, skip the AskUserQuestion and ask plainly: "What's the runtime URL? (e.g., `http://localhost:5173`)", then save via `.devforge/lib/configure_helper set-ac-runtime-url <answer>`.

## Q12.2 — API base (only when mode == `runtime-assisted`)

Phase 2 detection populated `AC_RUNTIME_API_BASE` from matched `.env*` files (e.g., `VITE_API_URL`).

If detection produced a non-empty value, use AskUserQuestion (substitute `<value>` with the Phase 2 composed URL): "Detected API base: `<value>`. Confirm or override?"

- `Confirm` — use the detected API base
- `Override` — let me type a different URL

If the user picks `Confirm`, save via `.devforge/lib/configure_helper set-ac-runtime-api-base <value>` using the Phase 2 composed value. If the user picks `Override`, follow up with a plain free-text prompt: "What's the API base URL?", then save via `.devforge/lib/configure_helper set-ac-runtime-api-base <answer>`.

If detection produced an empty value, skip the AskUserQuestion and ask plainly: "What's the API base URL? (e.g., `http://localhost:3000/api`)", then save via `.devforge/lib/configure_helper set-ac-runtime-api-base <answer>`.

## Q12.3 — CLI command (only when mode == `runtime-assisted`)

Phase 2 detection populated `AC_RUNTIME_CLI_COMMAND` from manifest `scripts.dev` or `scripts.start`.

If detection produced a non-empty value, use AskUserQuestion (substitute `<value>` with the Phase 2 composed command): "Detected runtime CLI command: `<value>`. Confirm or override?"

- `Confirm` — use the detected command
- `Override` — let me type a different command

If the user picks `Confirm`, save via `.devforge/lib/configure_helper set-ac-runtime-cli-command <value>` using the Phase 2 composed value. If the user picks `Override`, follow up with a plain free-text prompt: "What command starts the dev server?", then save via `.devforge/lib/configure_helper set-ac-runtime-cli-command <answer>`.

If detection produced an empty value, skip the AskUserQuestion and ask plainly: "What command starts the dev server? (e.g., `npm run dev`)", then save via `.devforge/lib/configure_helper set-ac-runtime-cli-command <answer>`.
