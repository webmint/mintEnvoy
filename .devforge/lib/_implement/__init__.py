"""_implement — internal package for implement_helper submodules.

Domains owned by this package:

- Task resolution: scan breakdown-handoff.json to find the next runnable task
  (lowest-numbered feature, lowest dependency-ready task).
- WIP marker: write/read/clear the .devforge/wip.md interrupted-session marker
  (Command: /implement field distinguishes from a marker written by a different command).
- Scope-aware verification: match touched files against PACKAGE_STACKS config,
  run the appropriate type_check_command + lint_command per package, cap
  self-repair at 3 iterations.
- Forcing-functions gate: after verify + code-review loop, invoke
  constitute_helper verify-<rule> for each enabled forcing_functions rule and
  aggregate results (exit 2 if any fail).
- Per-task WIP commit: stage touched_files + task file only (never git add -A),
  compose the commit message per wrapper/non-wrapper convention, honor
  COMMIT_ATTRIBUTION from project-config.json.

Public surface: _state, _handoff_reader, _wip, _cmds_resolve,
_cmds_preflight, _cli.
All submodules are implementation-private (underscore prefix).
"""
