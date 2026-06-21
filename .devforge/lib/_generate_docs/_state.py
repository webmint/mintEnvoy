"""Persists the generate_docs helper's JSON state file with atomic writes.

State path is `<DEVFORGE_DIR>/.generate-docs-state.json`, resolved at
call time so tests can override via `DEVFORGE_DIR`. The file IS the
source of truth: each setter does a read-modify-write cycle. Atomicity
of the write step is guaranteed via `tempfile.mkstemp` + `os.replace`
in the target directory; on any write failure the temp file is unlinked
and the exception re-raised (anti-pattern #4 — fixed-name temp files
are NOT used).

Concurrency: the read-modify-write cycle as a whole is serialized
across processes via `_state_transaction()`, an exclusive POSIX file
lock on a sidecar `<state>.lock` file. Without this, two concurrent
setters can both load state BEFORE either writes; the second writer
silently overwrites the first one's mutation. This was observed in
practice: an LLM-driven `add-package-script` loop lost ~20% of
script entries when multiple invocations ran in parallel. Setters MUST
go through `_state_transaction()` rather than calling `_load_state()`
+ `_write_state()` directly.

This module also exposes the small `_die` / `_info` stderr printers
used by every other submodule to report state-related success and
failure to the CLI. They live here because they are inseparable from
the state-error flow (a failed `_load_state` immediately routes through
`_die`); centralizing them avoids duplicating a 2-line printer in five
modules. No other module-level concerns belong here — argparse wiring,
field validation, manifest detection, and rendering all live elsewhere.

Stdlib only. Targets Python 3.8+.
"""

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

try:
    import fcntl  # POSIX-only; Windows builds fall through to no-op locking.
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - Windows fallback
    _HAVE_FCNTL = False


STATE_FILE_NAME = ".generate-docs-state.json"
STATE_VERSION = 1


def _state_file_path() -> Path:
    """Resolve the state file path at call time (not import time).

    Honors `DEVFORGE_DIR` when set; otherwise falls back to the helper's
    own location's parent (`<install>/.devforge/`) following the same
    convention as `init_helper`.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / STATE_FILE_NAME
    # `Path(__file__).resolve().parent` -> `_generate_docs/`
    # `.parent` -> `lib/`
    # `.parent` -> `devforge/`
    # The state lives at `<devforge>/.generate-docs-state.json` (one
    # level above `lib/`), matching the prior monolith's layout.
    return Path(__file__).resolve().parent.parent.parent / STATE_FILE_NAME


def default_state() -> Dict[str, Any]:
    """Return a fresh defaults dict for a brand-new state file."""
    return {"version": STATE_VERSION, "packages": {}}


def default_package_record(name: str, path: str) -> Dict[str, Any]:
    """Return the per-package skeleton dict — every field initialized.

    The `concerns` dict (Phase 3.1+) is keyed by `concern_name` for O(1)
    lookup. Existing pre-3.1 state files lack the key — `_load_state`
    backfills it on read so older state files load without modification.
    """
    return {
        "name": name,
        "path": path,
        "overview": None,
        "directory_tree": None,
        "primary_language": None,
        "framework": None,
        "build_tool": None,
        "scripts": {},
        "exports": [],
        "dependencies": [],
        "hazards": [],
        "usage_example": None,
        "consumer_pattern": None,
        "concerns": {},
    }


def default_concern_record(concern_name: str) -> Dict[str, Any]:
    """Return the per-concern skeleton dict — every field initialized.

    Mirrors `default_package_record` for the ConcernDoc tier (schema:
    `generate_docs_schema.ConcernDoc`). NOTE: there is no
    `consumer_pattern` field at the concern level (that's package-tier
    only); keep the two factories distinct rather than parameterizing.
    """
    return {
        "concern_name": concern_name,
        "overview": None,
        "directory_tree": None,
        "public_surface": [],
        "types": [],
        "dependencies": [],
        "hazards": [],
        "usage_example": None,
    }


class StateLoadError(Exception):
    """Raised when the on-disk state file is unreadable or malformed."""


def _load_state() -> Dict[str, Any]:
    """Read JSON state from disk if present; otherwise return defaults.

    A missing file is normal (first invocation). A present-but-corrupt
    file is surfaced as `StateLoadError` so the CLI can exit non-zero
    with a clear message rather than silently resetting.

    Wrong-type top-level keys (`packages` not a dict, etc.) are also
    surfaced — silently coercing them would hide data loss. Missing
    keys, by contrast, are backfilled from defaults (legitimate
    forward-compat for older state shapes).
    """
    path = _state_file_path()
    if not path.exists():
        return default_state()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise StateLoadError(
            "cannot read state file {0}: {1}".format(path, err)
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise StateLoadError(
            "state file {0} is corrupt: {1}".format(path, err)
        )
    if not isinstance(data, dict):
        raise StateLoadError(
            "state file {0} root must be an object".format(path)
        )
    # Defensive backfill — preserve forward compat with older state
    # shapes if/when version migrations happen.
    if "version" not in data:
        data["version"] = STATE_VERSION
    if "packages" not in data:
        data["packages"] = {}
    elif not isinstance(data["packages"], dict):
        # Wrong-type — surfaced rather than silently reset, so a
        # corrupt file does NOT cause silent data loss. (Reviewer
        # finding #1.)
        raise StateLoadError(
            "state file {0}: 'packages' must be an object, got {1}".format(
                path, type(data["packages"]).__name__
            )
        )
    # Phase 3.1 migration: backfill the `concerns` dict on any package
    # record that predates the concern-tier addition. Pre-3.1 state
    # files lack the key entirely; we treat missing-or-None as `{}` so
    # status / validate-package keep working on legacy state. Wrong-type
    # values (`concerns` present but not a dict) are raised as a load
    # error — same policy as `packages` itself, so corrupt fields don't
    # cause silent data loss.
    for pkg_path, pkg_record in data["packages"].items():
        if not isinstance(pkg_record, dict):
            continue
        if "concerns" not in pkg_record or pkg_record["concerns"] is None:
            pkg_record["concerns"] = {}
        elif not isinstance(pkg_record["concerns"], dict):
            raise StateLoadError(
                "state file {0}: packages[{1!r}].concerns must be an "
                "object, got {2}".format(
                    path, pkg_path, type(pkg_record["concerns"]).__name__
                )
            )
    return data


def _write_state(state: Dict[str, Any]) -> None:
    """Atomically write `state` to the state file path.

    Uses `tempfile.mkstemp` in the target directory + `os.replace` to
    guarantee atomicity. Cleans up the temp file on any failure.
    """
    target = _state_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".generate-docs-state-",
        suffix=".json",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _lock_file_path() -> Path:
    """Sidecar lock path next to the state file.

    Kept distinct from the state file itself so the state JSON is
    never opened in r+ / w+ mode — the lock is purely metadata. The
    file is created on first use and intentionally never deleted; an
    empty .lock file alongside the state file is the steady state.
    """
    return _state_file_path().with_suffix(".json.lock")


class _AbortTransaction(Exception):
    """Sentinel raised inside `_state_transaction()` to skip the write step.

    Setters use this to bail out of the transaction WITHOUT persisting
    their (unchanged) in-memory state — e.g., a "package not registered"
    or "duplicate entry" check that fails after the lock is acquired
    but before any mutation. The exception itself carries the int return
    code the caller should propagate to the CLI dispatcher.
    """

    def __init__(self, code: int) -> None:
        super().__init__("aborted")
        self.code = code


@contextlib.contextmanager
def _state_transaction() -> Iterator[Dict[str, Any]]:
    """Read-modify-write the state under an exclusive process lock.

    Setters call this in place of separate `_load_state()` / `_write_state()`
    invocations:

        with _state_transaction() as state:
            pkg = state["packages"][path]
            pkg["scripts"][name] = command

    The lock is held from BEFORE the read until AFTER the write so two
    concurrent setters cannot both load stale state and clobber each
    other's mutation. Lock implementation is `fcntl.flock(LOCK_EX)` on
    POSIX. On Windows (no fcntl) the context manager degrades to a
    no-op — that platform is out of scope for the helper today, but
    the degradation is silent rather than a hard import error.

    Mid-transaction abort: if the body raises `_AbortTransaction`, the
    write is SKIPPED and the lock released cleanly. Other exceptions
    propagate (also without writing) — the state writer sits at the
    end of the body, after both the user mutation and any abort check.
    """
    state_path = _state_file_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_file_path()
    # `os.open` with O_CREAT keeps the lock-file presence sticky across
    # invocations. The fd itself is what fcntl locks against.
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = _load_state()
            # Write only on clean body exit. _AbortTransaction (and any
            # other exception) skips the write, propagates out of the
            # context manager, and is caught by the setter's outer
            # try/except.
            yield state
            _write_state(state)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _die(message: str, code: int = 2) -> int:
    """Print `message` to stderr and return `code` for the CLI dispatcher."""
    sys.stderr.write("generate_docs_helper: {0}\n".format(message))
    return code


def _info(message: str) -> None:
    """Print a success message to stderr (stdout is reserved for data)."""
    sys.stderr.write("generate_docs_helper: {0}\n".format(message))


def _require_package(state: Dict[str, Any], path: str) -> Optional[Dict[str, Any]]:
    """Return the package record for `path` or None if absent.

    The caller is responsible for surfacing the "package not registered"
    error — this helper just looks it up so the call site stays linear.
    """
    return state["packages"].get(path)


def _require_concern(
    state: Dict[str, Any], path: str, concern_name: str,
) -> Optional[Dict[str, Any]]:
    """Return the concern record under `path`/`concern_name` or None.

    Two-step lookup: the package must exist AND have a registered
    concern by that name. Returning a single Optional keeps callers
    flat — the caller surfaces the appropriate "package not registered"
    vs "concern not registered" error after a None check.
    """
    pkg = state["packages"].get(path)
    if pkg is None:
        return None
    concerns = pkg.get("concerns") or {}
    return concerns.get(concern_name)
