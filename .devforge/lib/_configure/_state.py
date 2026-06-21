"""State IO: defaults + atomic write + load + transaction."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Iterator, Union

from ._schema import FIELD_SCHEMA, OUTPUT_FILE_NAME
from ._yaml import emit_yaml, parse_yaml

try:
    import fcntl  # POSIX-only.
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback path
    # AIDevTeamForge targets POSIX (macOS, Linux, WSL) only — see
    # CLAUDE.md. The graceful-degradation flag exists to avoid an import
    # crash if the helper is somehow invoked on Windows native, but the
    # no-op locking path is NOT a supported configuration: concurrent
    # add-package-stack invocations on Windows would silently lose
    # writes. If Windows support ever lands, replace this with a real
    # lock (msvcrt.locking) — DO NOT rely on the no-op fallback.
    _HAVE_FCNTL = False


def _output_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the output file path for the given devforge directory.

    Joins OUTPUT_FILE_NAME to devforge_dir. The devforge_dir is supplied
    explicitly by callers (threaded from CLI args or from the DEVFORGE_DIR
    env var via main()) — not resolved from the environment at call time.
    This makes the path explicit at every call site.
    """
    return Path(devforge_dir) / OUTPUT_FILE_NAME


def default_state() -> dict:
    """Return a fresh defaults dict matching FIELD_SCHEMA shape.

    Walks FIELD_SCHEMA and returns all 29 keys with type-appropriate
    defaults: scalars → None, string_array → [], package_stack_array → [].
    """
    state = {}
    for name, kind in FIELD_SCHEMA:
        if kind == "scalar":
            state[name] = None
        else:
            state[name] = []
    return state


def _write_state(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write `state` to the output yaml path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. flush + fsync before
    os.replace adds a durability barrier. On any failure, attempts to
    remove the temp file and re-raises.
    """
    target = _output_file_path(devforge_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="configure-",
        suffix=".yaml.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(emit_yaml(state))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load configure.yaml into a state dict.

    If the file is missing, returns default_state() — normal on first run.
    Malformed file propagates YamlParseError so the caller can exit non-zero
    with a clear message rather than silently resetting.
    """
    path = _output_file_path(devforge_dir)
    if not path.exists():
        return default_state()
    text = path.read_text(encoding="utf-8")
    return parse_yaml(text)


def _dump(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Write state dict to configure.yaml atomically.

    Thin wrapper around _write_state so setters can call paired
    _load/_dump without depending on _write_state's signature directly.
    """
    _write_state(state, devforge_dir)


def _lock_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the sidecar lock path for the configure.yaml in devforge_dir.

    Kept distinct from the yaml itself so the yaml is never opened in r+/w+
    mode — the lock is purely metadata. The file is created on first use and
    intentionally never deleted.
    """
    return _output_file_path(devforge_dir).parent / (OUTPUT_FILE_NAME + ".lock")


@contextlib.contextmanager
def _state_transaction(devforge_dir: Union[str, "os.PathLike[str]"]) -> Iterator[dict]:
    """Read-modify-write configure.yaml under an exclusive process lock.

    Usage:
        with _state_transaction(args.devforge_dir) as state:
            state["project_name"] = "my-project"
        # state written to disk on context exit; NOT written if body raises

    The lock is held from before the read until after the write so two
    concurrent processes cannot both load stale state and clobber each
    other's mutation. Lock: fcntl.flock(LOCK_EX) on POSIX. On Windows
    (no fcntl) the manager degrades to no-op locking — that platform is
    out of scope for the helper.

    If the body raises ANY exception, the write is skipped and the lock
    released cleanly. The exception propagates to the caller (setter).
    """
    devforge_path = Path(devforge_dir)
    devforge_path.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_file_path(devforge_dir)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = _load(devforge_dir)
            yield state
            _dump(state, devforge_dir)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
