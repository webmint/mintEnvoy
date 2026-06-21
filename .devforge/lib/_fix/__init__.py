"""Internal package for fix_helper (the /fix command's mechanical work).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `fix_helper` or `fix_helper.main`.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Verbs (Phase 1):
  preflight         — 4-command setup-chain gate + feature resolution +
                      source_root/wrapper_mode (reads .devforge/ paths only;
                      does NOT read .claude/ — plan-22 finding F avoided).
  read-findings     — parse specs/[feature]/review.md + verification.md
                      NEEDS-WORK issues into one working list.
                      OQ-1 decision: PERSISTED — reads on-disk artifacts so
                      /fix works in a fresh session after /review//verify ran
                      earlier and the parser can round-trip real producer output.
  resolve-scope     — map the working list to the narrow file set for
                      implement_helper verify-touched --files.
                      OQ-2 decision: NARROW (finding-targeted) — /fix
                      remediates a finding set, not the whole assembled diff;
                      does NOT pull in _shared/feature_scope.py.
  in-fix-window     — return whether the active feature is in the
                      post-/implement, pre-/summarize window (D2 condition
                      3c — the case-3 conversational offer gate).
                      OQ-4 decision: helper verb — so the always-on rule stays
                      short (plan-08 discipline) and the detection is
                      deterministic rather than model-judged.

_state.py decision: NOT built.
  Rationale: /fix's back-half (verify-touched loop, review panel,
  forcing-functions gate, hard gate, wip-commit) is owned entirely by the
  installed implement_helper binary.  /fix itself has no multi-phase
  back-half state of its own — it reads findings (read-findings), scopes
  (resolve-scope), confirms the window (in-fix-window), and then the
  orchestrator calls implement_helper verbs sequentially.  Adding a
  fix-state.json would be dead surface (no verb would write phase
  transitions, and no verb would read prior phase data).  If /fix ever
  grows its own multi-phase loop, add _state.py at that point.
"""

from ._cli import main

__all__ = ["main"]
