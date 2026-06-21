"""Helper-side circuit breaker for the generate_docs helper.

Reads the per-invocation trace log (`<DEVFORGE_DIR>/.generate-docs-trace.log`,
written by `_trace.py`) as its signal source and refuses to proceed when
one of two failure modes trips. Hook point: `_cli.main()`, AFTER
argparse and BEFORE handler dispatch. A tripped breaker aborts the
invocation entirely with exit code 3 and a clear stderr message.

The two breakers
================

1. **Doom loop**: same subcommand returning exit 2 for N consecutive
   trace entries with no successful invocation in between. Default
   N=3. Catches LLMs retrying the same broken command identically.
2. **Invocation budget**: total trace lines in the current run exceeds
   N. Default N=500. Catches runaway loops; a typical /generate-docs
   produces 100-200 helper calls, so 500 is a permissive ceiling.

"Current run" window
====================

The current run is the trailing portion of the trace file starting at
(inclusive) the most-recent `subcommand=reset` entry, OR the entire
trace file if no reset entry is present. `reset` clears state for a
fresh /generate-docs attempt; the breaker honors that boundary so a
failed prior run doesn't prevent a clean retry.

Configuration
=============

Defaults are module-level constants. Each can be overridden via
environment variable (parsed lazily at check time, so per-test env
isolation works):

- `DEVFORGE_CIRCUIT_DOOM_LOOP_THRESHOLD`        (default 3)
- `DEVFORGE_CIRCUIT_INVOCATION_BUDGET`          (default 500)

Master kill-switch:

- `DEVFORGE_DISABLE_CIRCUIT_BREAKER=1`  → all breakers skipped.

Fail-open policy
================

Every breaker is wrapped in try/except so one breaker's failure cannot
disable the others. Top-level `check_circuit_breakers` is wrapped too:
on ANY internal error (OSError reading trace, malformed JSON in trace
lines, unexpected exception in breaker logic), the function logs a
warning to stderr and returns None — the helper invocation proceeds.
Breakers are best-effort safety, not core function; they MUST NOT
block legitimate work due to their own bugs.

Performance
===========

The check reads the full trace file (split on newlines). In practice
trace files are bounded by the invocation budget (default 500 lines
per run); above that the budget breaker aborts the helper anyway, so
the read cost is bounded. Reading the full file is required for
invocation-budget to count run-scoped records accurately and for
`_scope_to_current_run` to find the most-recent reset anchor when it
falls outside any tail window.

Stdlib only. Targets Python 3.8+.
"""

import json
import os
import sys
from typing import List, Optional

from ._trace import _trace_file_path

# ---------------------------------------------------------------------------
# Defaults — overridable via env var per-call (read at check time, not
# import time, so per-test isolation works).
# ---------------------------------------------------------------------------

DOOM_LOOP_THRESHOLD = 3
# Bumped 500 → 5000 (2026-05-08) after V7 split-dispatch smoke hit the cap
# mid-run on testForge20 app/components: 23 sub_concerns × ~6 helper
# calls per child + parent chain + preflight chain ≈ 150 calls per BIG
# split concern alone. Full project run (63 concerns including ~15 split
# parents) easily clears 500. 5000 = 10× headroom against runaway loops
# while accommodating real-scale monorepos. Override per-run via
# DEVFORGE_CIRCUIT_INVOCATION_BUDGET env var.
INVOCATION_BUDGET = 5000

_ENV_DOOM = "DEVFORGE_CIRCUIT_DOOM_LOOP_THRESHOLD"
_ENV_INVOCATION = "DEVFORGE_CIRCUIT_INVOCATION_BUDGET"
_ENV_DISABLE = "DEVFORGE_DISABLE_CIRCUIT_BREAKER"


def _env_int(key: str, default: int) -> int:
    """Read an int env override; fall back to default on missing/malformed.

    Defensive: a malformed env value (non-int) silently falls back to
    the default rather than crashing. The breaker is best-effort; an
    operator who set the env var wrong should not break the helper.
    """
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _is_disabled() -> bool:
    """Master bypass: any non-empty, non-"0", non-"false" value disables."""
    raw = os.environ.get(_ENV_DISABLE, "")
    if not raw:
        return False
    return raw.lower() not in ("0", "false", "no", "off")


# ---------------------------------------------------------------------------
# Trace reading utilities.
# ---------------------------------------------------------------------------


def _read_trace_lines() -> List[str]:
    """Return all non-empty lines of the trace file, in order.

    Returns [] if the file does not exist or is empty. Trace files
    are bounded by the invocation budget (default 500 lines per run);
    once the budget is exceeded the breaker trips and the helper
    aborts, so the read size is bounded by design.

    Reading the full file (vs a tail slice) is required because the
    invocation-budget breaker counts records in the current run and
    `_scope_to_current_run` searches for the most-recent reset anchor
    — both can need records older than any fixed tail window.

    OSError propagates — the caller wraps it in fail-open handling.
    """
    path = _trace_file_path()
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if not text:
        return []
    return [ln for ln in text.split("\n") if ln.strip()]


def _parse_trace_line(line: str) -> Optional[dict]:
    """Parse one trace line; return None on malformed JSON.

    The trace file is append-only across processes and a partial-write
    crash could in principle leave a corrupt tail. We treat any
    malformed line as "absent" rather than crashing the breaker.
    """
    try:
        rec = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(rec, dict):
        return None
    return rec


def _scope_to_current_run(records: List[dict]) -> List[dict]:
    """Trim `records` to the current run (most-recent reset onward).

    Scans backwards. The reset entry itself is included as the first
    record of the run (it's the run-start anchor). If no reset is
    found, returns the input unchanged.
    """
    for i in range(len(records) - 1, -1, -1):
        if records[i].get("subcommand") == "reset":
            return records[i:]
    return records


# ---------------------------------------------------------------------------
# Individual breakers. Each takes the current-run records list and the
# current subcommand; returns Optional[str] (None = clean, str = trip
# message). Each is wrapped in its own try/except by the top-level
# orchestrator so one breaker's bug cannot disable the others.
# ---------------------------------------------------------------------------


def _check_doom_loop(records: List[dict], current_subcommand: str) -> Optional[str]:
    """Trip if the last N records are all (same subcommand, exit 2).

    "Same subcommand" matches across all N records (not "matches the
    current invocation's subcommand") — what we're detecting is a
    same-call-repeating-itself pattern in history. The current
    invocation hasn't traced yet, so it's not part of the count.
    """
    threshold = _env_int(_ENV_DOOM, DOOM_LOOP_THRESHOLD)
    if threshold <= 0 or len(records) < threshold:
        return None
    tail = records[-threshold:]
    first_sub = tail[0].get("subcommand")
    if not first_sub:
        return None
    for rec in tail:
        if rec.get("subcommand") != first_sub:
            return None
        if rec.get("exit_code") != 2:
            return None
    return (
        "circuit-breaker: doom loop detected — '{0}' has returned exit 2 "
        "{1} times consecutively. Aborting before retry. Inspect trace "
        "log at {2} and resolve the underlying error."
    ).format(first_sub, threshold, _trace_file_path())


def _check_invocation_budget(records: List[dict], current_subcommand: str) -> Optional[str]:
    """Trip if the current run has more than INVOCATION_BUDGET records."""
    budget = _env_int(_ENV_INVOCATION, INVOCATION_BUDGET)
    if budget <= 0:
        return None
    count = len(records)
    if count <= budget:
        return None
    return (
        "circuit-breaker: invocation budget exceeded — current run has "
        "reached {0} helper invocations (limit: {1}). Aborting. Run "
        "/generate-docs again with reset if you want a fresh attempt, "
        "or investigate why so many calls were needed."
    ).format(count, budget)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


_BREAKERS = (
    ("doom_loop", _check_doom_loop),
    ("invocation_budget", _check_invocation_budget),
)


def _emit_warning(message: str) -> None:
    """Best-effort stderr warning; swallows any further failure."""
    try:
        sys.stderr.write("circuit-breaker: skipped due to internal error: " + message + "\n")
    except Exception:
        pass


def check_circuit_breakers(current_subcommand: str) -> Optional[str]:
    """Evaluate all breakers against the trace log scoped to current run.

    Returns None if no breaker tripped. Returns a stderr-ready string
    describing the trip if one tripped.

    Defensive: any internal error logs a warning and returns None
    (fail-open). Honors `DEVFORGE_DISABLE_CIRCUIT_BREAKER` env var as
    master kill-switch.

    A tripped breaker does NOT itself produce a trace line — the
    invocation is aborted before the trace-write step runs. This is
    intentional: the trip message on stderr is the audit trail, and
    re-running the helper to re-evaluate would either trip again
    (still in doom-loop / over budget) or have been bypassed.
    """
    if _is_disabled():
        return None
    try:
        # Read the full trace file and scope to the current run
        # (most-recent `reset` onward, or the whole file if no reset
        # is present). Invocation-budget needs the run-scoped count;
        # doom-loop reads only the last N records of `scoped` but
        # must see them after run-scoping. Both work equally on a
        # full-file list.
        all_lines = _read_trace_lines()
        if not all_lines:
            return None
        records = []  # type: List[dict]
        for ln in all_lines:
            rec = _parse_trace_line(ln)
            if rec is not None:
                records.append(rec)
        if not records:
            return None
        scoped = _scope_to_current_run(records)
    except OSError as err:
        _emit_warning("trace read failed: {0}".format(err))
        return None
    except Exception as err:  # pragma: no cover - defensive fail-open
        _emit_warning("scope-to-run failed: {0}".format(err))
        return None

    # Evaluate each breaker independently. A bug in one MUST NOT
    # disable the others.
    for name, fn in _BREAKERS:
        try:
            trip = fn(scoped, current_subcommand)
        except Exception as err:  # pragma: no cover - defensive fail-open
            _emit_warning("breaker '{0}' raised: {1}".format(name, err))
            continue
        if trip is not None:
            return trip
    return None
