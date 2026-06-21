"""_wip -- WIP marker I/O for /implement.

The .devforge/wip.md file is a lightweight crash-recovery marker written
before each task starts and cleared after the approved per-task WIP commit.

Public API:

  write_wip_marker(state)
      Write (or overwrite) <devforge_dir>/wip.md with fields derived from
      the given ImplementState.  The file always contains a
      "Command: /implement" field so a marker written by a different command is
      distinguishable at crash-recovery time.

  read_wip_marker(devforge_dir) -> Optional[dict]
      Parse wip.md and return a dict of its fields.
      Returns None when wip.md is absent (not an error).
      The returned dict contains a "Command" key only when the file has
      parseable **Key**: Value fields; a present-but-unparseable file yields
      {} (callers must use dict.get("Command"), never dict["Command"]).

  clear_wip_marker(devforge_dir)
      Remove wip.md.  Silent no-op when the file is absent.

File format (markdown, human-readable + machine-parseable):

  # WIP Marker — /implement
  **Command**: /implement
  **Feature**: <feature_dir>
  **Task**: <task_number>
  **Title**: <task_title>
  **Agent**: <agent_name>
  **Phase**: <phase>
  **Checkpoint**: <checkpoint_sha or "(none)">

The "Command: /implement" field is MANDATORY so the crash-recovery branch
can detect a mismatch (a marker from a different command) and refuse to proceed.

Atomic writes use tempfile.mkstemp + os.replace so concurrent invocations
and crash recovery are safe.

Stdlib only. No third-party dependencies. Python 3.8+.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Dict

# ---------------------------------------------------------------------------
# Internal field key constants (match the file format exactly).
# ---------------------------------------------------------------------------

_COMMAND_VALUE = "/implement"
_FIELD_PATTERN = re.compile(r"^\*\*([^*]+)\*\*:\s*(.*)$", re.MULTILINE)

# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _atomic_write(path, content):
    # type: (str, str) -> None
    """Write content to path atomically using tempfile.mkstemp + os.replace."""
    target = Path(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="wip-",
        suffix=".md.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_wip_marker(state):
    # type: (object) -> None
    """Write .devforge/wip.md from an ImplementState snapshot.

    The wip_marker_path on state determines the destination file.
    The parent directory must already exist (created by preflight).

    Parameters
    ----------
    state : ImplementState
        Current task execution state (from _implement._state).

    Raises
    ------
    OSError
        I/O failure during atomic write.
    """
    checkpoint_sha = state.checkpoint_sha if state.checkpoint_sha else "(none)"

    content = (
        "# WIP Marker — {cmd}\n"
        "\n"
        "**Command**: {cmd}\n"
        "**Feature**: {feature}\n"
        "**Task**: {task}\n"
        "**Title**: {title}\n"
        "**Agent**: {agent}\n"
        "**Phase**: {phase}\n"
        "**Checkpoint**: {checkpoint}\n"
    ).format(
        cmd=_COMMAND_VALUE,
        feature=str(state.feature_dir),
        task=state.task_number,
        title=state.task_title,
        agent=state.agent_name,
        phase=state.phase,
        checkpoint=checkpoint_sha,
    )

    _atomic_write(str(state.wip_marker_path), content)


def read_wip_marker(devforge_dir):
    # type: (object) -> Optional[Dict[str, str]]
    """Read and parse .devforge/wip.md.

    Parameters
    ----------
    devforge_dir : str or Path
        Path to the .devforge/ directory.

    Returns
    -------
    dict or None
        A dict mapping field names to their string values when wip.md
        exists and is parseable.  Returns None when wip.md is absent.

    Notes
    -----
    The dict contains a "Command" key when the wip.md was written by
    write_wip_marker (which always writes Command).  A present-but-unparseable
    file (no **Key**: Value lines) yields {} -- not None -- so callers must use
    dict.get("Command"), never dict["Command"].
    All field values are returned as stripped strings.
    Malformed lines (not matching the **Key**: Value pattern) are skipped.
    """
    wip_path = Path(devforge_dir) / "wip.md"
    if not wip_path.exists():
        return None

    try:
        text = wip_path.read_text(encoding="utf-8")
    except (OSError, IOError):
        return None

    fields = {}  # type: Dict[str, str]
    for m in _FIELD_PATTERN.finditer(text):
        key = m.group(1).strip()
        value = m.group(2).strip()
        fields[key] = value

    return fields if fields else {}


def clear_wip_marker(devforge_dir):
    # type: (object) -> None
    """Remove .devforge/wip.md.  Silent no-op when absent.

    Parameters
    ----------
    devforge_dir : str or Path
        Path to the .devforge/ directory.
    """
    wip_path = Path(devforge_dir) / "wip.md"
    try:
        wip_path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        # Re-raise unexpected OS errors (permission denied, etc.).
        raise
