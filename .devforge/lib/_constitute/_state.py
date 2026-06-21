"""State shape helpers + JSON IO + transactions + section lookup."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Iterator, Union

from ._schema import FIELD_SCHEMA, OUTPUT_FILE_NAME, _PATTERNS_BUCKETS

try:
    import fcntl  # POSIX-only.
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback path
    _HAVE_FCNTL = False


def _empty_section() -> dict:
    """Return a fresh section record with all subfields at defaults."""
    return {
        "number": None,
        "title": None,
        "tag": None,
        "description": None,
        "rules": [],
        "tables": [],
        "code_examples": [],
    }


def _empty_patterns_section() -> dict:
    """Return the patterns_and_antipatterns 6-bucket default."""
    return {bucket: [] for bucket in _PATTERNS_BUCKETS}


def _empty_scaffolding_guide() -> dict:
    """Return a fresh scaffolding_guide record (when non-null)."""
    return {
        "starter_directories": [],
        "sample_files": [],
    }


def default_state() -> dict:
    """Return a fresh defaults state dict matching FIELD_SCHEMA.

    All scalars default to None; section_arrays default to []; the
    patterns_section defaults to its 6-bucket structure with empty lists;
    project_identity and scaffolding_guide default to None (nullable).
    """
    state = {}  # type: Dict[str, object]
    for name, kind in FIELD_SCHEMA:
        if kind in ("scalar", "date_scalar", "enum_scalar", "nullable_record",
                    "optional_dict"):
            state[name] = None
        elif kind == "section_array":
            state[name] = []
        elif kind == "patterns_section":
            state[name] = _empty_patterns_section()
        else:
            raise AssertionError("unknown field kind: {0}".format(kind))
    return state


def _output_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the canonical state file path for the given devforge dir."""
    return Path(devforge_dir) / OUTPUT_FILE_NAME


def _write_state(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write `state` to the output JSON path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. flush + fsync before
    os.replace adds a durability barrier. On any failure, attempts to
    remove the temp file and re-raises.
    """
    target = _output_file_path(devforge_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="constitute-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=False)
            f.write("\n")
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
    """Load constitute.json into a state dict.

    If the file is missing, returns default_state() — normal on first run.
    Malformed JSON propagates json.JSONDecodeError so the caller can exit
    non-zero with a clear message rather than silently resetting.
    """
    path = _output_file_path(devforge_dir)
    if not path.exists():
        return default_state()
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _dump(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Write state dict to constitute.json atomically.

    Thin wrapper around _write_state so setters can call paired
    _load/_dump without depending on _write_state's signature directly.
    """
    _write_state(state, devforge_dir)


def _lock_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the sidecar lock path for constitute.json in devforge_dir."""
    return _output_file_path(devforge_dir).parent / (OUTPUT_FILE_NAME + ".lock")


@contextlib.contextmanager
def _state_transaction(devforge_dir: Union[str, "os.PathLike[str]"]) -> Iterator[dict]:
    """Read-modify-write constitute.json under an exclusive process lock.

    Usage:
        with _state_transaction(args.devforge_dir) as state:
            state["project_name"] = "my-project"
        # state written to disk on context exit; NOT written if body raises

    Lock: fcntl.flock(LOCK_EX) on POSIX. On Windows (no fcntl) the
    manager degrades to no-op locking — that platform is out of scope.

    If the body raises ANY exception, the write is skipped and the lock
    is released cleanly. The exception propagates to the caller.
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


def _find_section(state: dict, number: str):
    """Return (bucket_list, section_dict) for the section with given number.

    Searches in this order: architecture_rules, code_quality_standards,
    domain_rules, workflow_rules. Numbers are strings ("2.1", "3.5", etc.).
    Returns (None, None) if not found.

    First-match policy: if the same number exists in two buckets (e.g.,
    "1.1" in both architecture_rules and workflow_rules), the architecture
    bucket wins — add-rule / add-table / add-code-example would always
    route to the architecture copy and silently miss the workflow copy.
    The Phase 5 spec convention numbers each bucket non-overlappingly
    (2.x = architecture, 3.x = code-quality, 5.x = domain, 6.x = workflow,
    matching wrapper/constitution.md), so cross-bucket
    duplicates are a caller bug to avoid, not a helper bug to enforce.
    """
    for bucket_key in ("architecture_rules", "code_quality_standards",
                       "domain_rules", "workflow_rules"):
        bucket = state.get(bucket_key, [])
        for section in bucket:
            if section.get("number") == number:
                return bucket, section
    return None, None
