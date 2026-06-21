"""Per-invocation trace logging for the generate_docs helper.

Every helper subcommand invocation appends ONE structured JSONL line to
`<DEVFORGE_DIR>/.generate-docs-trace.log`. The audit trail this produces
is the foundation for: (a) post-run cost analysis, (b) the upcoming
circuit breaker that will use the trace stream as its signal source,
(c) post-incident forensics — testForge20 (2026-05-01) was the
motivating incident: a 7-subagent dispatch silently dropped 3 concerns'
worth of work and triage took hours because there was no per-call audit
trail to bisect against.

Trace line shape (one JSON object per line, terminated by a newline):

    {"ts": "...", "subcommand": "...", "duration_ms": N,
     "exit_code": N, "args_summary": "..."}

Fields:

- `ts`        — ISO 8601 UTC timestamp with millisecond precision.
                Trailing `+00:00` is rewritten to `Z` for canonicalness.
- `subcommand`— argparse `args.subcommand`, or `<unknown>` when the
                user invoked help / a missing subcommand.
- `duration_ms` — int milliseconds from JUST-BEFORE handler dispatch
                to handler return (or exception). Computed in `_cli.py`
                via `time.perf_counter()`.
- `exit_code` — int return from the handler (0 success, 1 I/O, 2
                validation/CLI). On unexpected handler exception the
                CLI shim records 1 here.
- `args_summary` — short space-separated `key=value` rendering of the
                most-relevant args. NEVER a full argparse dump (long
                `--text` / `--code-snippet` values would bloat the
                log to the point of unusability and leak prose into
                what is meant to be a structured audit signal).

Append-only semantics
=====================

The file is opened in "a" mode, written, closed. One write per
invocation; helper invocations are separate processes and there is no
in-process buffering across calls. POSIX `O_APPEND` writes are atomic
for payloads under the kernel's PIPE_BUF threshold (4 KiB on Linux,
512 B on macOS — every line we emit is well under both limits), so
concurrent appends from multiple helper processes interleave at
line-granularity without corrupting individual lines. No flock is
needed for the trace file (state file is the lock-protected resource;
trace is a write-only journal).

Failure policy: trace-write failures (missing directory, permission
denied, full disk, read-only filesystem) MUST NOT cause the helper
invocation to fail. The trace is best-effort observability; the core
function is the state mutation, which has already happened by the
time we get to the trace step. `write_trace` swallows `OSError` and
the call site in `_cli.py` wraps the call in its own
`try / except OSError` for defense in depth.

Rotation policy: the trace file is APPEND-ONLY and never rotated
automatically. Long-running projects may produce a multi-MB trace
file over months of /generate-docs runs; users can
`rm .devforge/.generate-docs-trace.log` between major iterations
if they want a fresh slate. Future enhancement (deferred): rotation
on size threshold or by run-id, but not before empirical evidence
the size is a problem.

Platform: POSIX-only atomic-append guarantee. Windows is out of scope
for this helper (the broader project's `fcntl` usage in `_state.py`
also gates Windows support). On Windows the file would still be
written, but interleaving guarantees do not hold.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ._state import _state_file_path

TRACE_FILE_NAME = ".generate-docs-trace.log"


def _trace_file_path() -> Path:
    """Resolve the trace file path at call time (mirrors `_state_file_path`).

    Lives in the same directory as the state file. Honors `DEVFORGE_DIR`
    via `_state_file_path()` so tests can isolate per tmpdir.
    """
    return _state_file_path().parent / TRACE_FILE_NAME


def _utc_iso_ms() -> str:
    """Return current UTC time as ISO 8601 with ms precision and `Z` suffix.

    Example: `2026-05-01T18:30:42.123Z`. The `Z` form is more idiomatic
    than `+00:00` for log payloads and is what downstream tooling
    (jq queries, log aggregators) tends to expect.
    """
    raw = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    if raw.endswith("+00:00"):
        return raw[: -len("+00:00")] + "Z"
    return raw


def _summarize_args(subcommand: str, args: argparse.Namespace) -> str:
    """Build a short `key=value` summary of the traceworthy args.

    Defensive: every attr lookup uses `getattr(..., None)` — a missing
    attr (because argparse shape changed, or because `args` is a
    sentinel for help-mode) silently drops that key from the summary.
    Trace-writing must never crash on argparse-shape changes.

    Subcommands with no traceworthy args (`reset`, `status`) return
    the empty string. Long prose fields (`--text`, `--code-snippet`,
    `--description`, `--purpose`, `--signature`) are deliberately
    excluded: they would bloat the trace and leak prose into what is
    meant to be a structured audit signal.
    """
    parts = []  # type: list

    # All package-tier and concern-tier subcommands carry one of these
    # to identify the target package. Concern subcommands use --package;
    # package-tier setters use --path. Both surface as `package=...`
    # because semantically they identify the same entity.
    package = getattr(args, "package", None) or getattr(args, "path", None)
    if package:
        parts.append("package={0}".format(package))

    concern = getattr(args, "concern", None)
    if concern:
        parts.append("concern={0}".format(concern))

    # add-package-script / add-package-export / add-package-dep / add-concern-*
    # name; for add-package the name field is the package's display name
    # (already covered by package=...) but argparse namespace still has
    # `name` attr — we surface it for the dep / export tiers.
    # Heuristic: only include `name=` when the subcommand isn't `add-package`
    # (where `--name` is the display name) or `add-package-hazard`
    # (no --name). For the rest, `--name` is a record key worth tracing.
    name = getattr(args, "name", None)
    if name and subcommand not in ("add-package",):
        parts.append("name={0}".format(name))

    # add-package-script uses --script-name (note hyphen → script_name attr).
    script_name = getattr(args, "script_name", None)
    if script_name:
        parts.append("script={0}".format(script_name))

    # Hazard subcommands include category — small enum value, useful for
    # filtering trace by hazard kind.
    category = getattr(args, "category", None)
    if category:
        parts.append("category={0}".format(category))

    # Dep subcommands include kind (runtime/dev/peer/internal/...). Small
    # enum value, traceworthy.
    kind = getattr(args, "kind", None)
    if kind:
        parts.append("kind={0}".format(kind))

    # Cite subcommands: include cite location for line-range trace.
    cite_file = getattr(args, "cite_file", None)
    cite_start = getattr(args, "cite_start", None)
    cite_end = getattr(args, "cite_end", None)
    if cite_file and cite_start is not None and cite_end is not None:
        parts.append(
            "cite={0}:{1}-{2}".format(cite_file, cite_start, cite_end)
        )

    return " ".join(parts)


def write_trace(
    subcommand: str,
    duration_ms: int,
    exit_code: int,
    args: Optional[argparse.Namespace],
) -> None:
    """Append one JSONL trace line for an invocation. Best-effort.

    Swallows `OSError` (and only OSError) so an unwritable trace path
    does NOT fail the helper invocation. Programming errors
    (TypeError on bad payload, etc.) DO propagate — that would
    indicate a bug in the trace module itself worth surfacing.

    `args` may be None when the parser printed help and there is no
    namespace to summarize; the trace line still emits with an empty
    `args_summary`.
    """
    try:
        if args is not None:
            summary = _summarize_args(subcommand, args)
        else:
            summary = ""
        record = {
            "ts": _utc_iso_ms(),
            "subcommand": subcommand,
            "duration_ms": int(duration_ms),
            "exit_code": int(exit_code),
            "args_summary": summary,
        }
        # `sort_keys=True` keeps the on-disk shape stable regardless
        # of dict insertion order — easier downstream filtering.
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        path = _trace_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # "a" mode + O_APPEND: atomic per-line append on POSIX for
        # payloads under PIPE_BUF (we're well under). No flock needed.
        with open(str(path), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        # Best-effort: trace failure must never fail the invocation.
        # Other exception types (TypeError on bad payload, etc.)
        # propagate so genuine bugs in the trace module surface.
        pass
