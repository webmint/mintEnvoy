"""_state -- frozen dataclass capturing per-task execution state for /implement.

ImplementState is a lightweight snapshot of the current task execution context.
It is created at preflight time and threaded through the per-task loop phases.
It is NOT persisted to disk -- the .devforge/wip.md marker and the git checkpoint
commit are the durable crash-recovery artefacts.

Design notes:

- Frozen dataclass: immutable after construction; phase transitions produce a new
  instance (dataclasses.replace). This prevents accidental mutation across phases.

- phase is a string Literal constrained to exactly the seven loop phases.
  Validated by __post_init__ against _VALID_PHASES rather than relying on the
  type-checker at runtime.

- checkpoint_sha is Optional[str]: None at construction (before the empty
  checkpoint commit is created) and non-None after preflight writes it.

- touched_files is a mutable snapshot -- it starts empty and is populated by
  capture-touched-files after the agent runs. The frozen nature of the dataclass
  means a new ImplementState is produced each time the list grows.

- Type-hint convention: typing.Optional / typing.List (Python 3.8+). No PEP 604
  (X | None) or PEP 585 (list[str]) syntax. from __future__ import annotations
  intentionally NOT used so __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Allowed phase values (the loop stages in execution order).
# ---------------------------------------------------------------------------

_VALID_PHASES = frozenset([
    "preflight",
    "agent",
    "verify",
    "review",
    "forcing_functions",
    "gate",
    "commit",
    "complete",
])

# ---------------------------------------------------------------------------
# Validation helpers.
# (Intentionally self-contained -- no import of _breakdown or any sibling.)
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    # type: (object, str) -> None
    """Raise ValueError if value is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            "{0} must be a string, got {1}".format(field_name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError("{0} must be a non-empty string".format(field_name))


# ---------------------------------------------------------------------------
# ImplementState
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImplementState:
    """Frozen snapshot of the current task execution state for /implement.

    Fields:
      feature_dir         Path to the feature directory (e.g. specs/001-slug/).
      task_number         Zero-padded task number string (e.g. "001").
      task_title          Human-readable task title string.
      agent_name          Name of the assigned agent (e.g. "backend-engineer").
      touched_files       List of file paths touched by the agent during this task.
      phase               Current loop phase (one of _VALID_PHASES).
      wip_marker_path     Path where the wip.md marker will be written.
      checkpoint_sha      Git SHA of the pre-task empty checkpoint commit, or None
                          before the checkpoint has been created.
    """

    feature_dir: Path
    task_number: str
    task_title: str
    agent_name: str
    touched_files: List[str]
    phase: str
    wip_marker_path: Path
    checkpoint_sha: Optional[str]

    def __post_init__(self):
        # type: () -> None

        # feature_dir must be a Path.
        if not isinstance(self.feature_dir, Path):
            raise ValueError(
                "ImplementState.feature_dir must be a pathlib.Path, "
                "got {0}".format(type(self.feature_dir).__name__)
            )

        # task_number must be non-empty string.
        _require_nonempty(self.task_number, "ImplementState.task_number")

        # task_title must be non-empty string.
        _require_nonempty(self.task_title, "ImplementState.task_title")

        # agent_name must be non-empty string.
        _require_nonempty(self.agent_name, "ImplementState.agent_name")

        # touched_files must be a list.
        if not isinstance(self.touched_files, list):
            raise ValueError(
                "ImplementState.touched_files must be a list, "
                "got {0}".format(type(self.touched_files).__name__)
            )

        # phase must be one of the valid phase strings.
        if self.phase not in _VALID_PHASES:
            raise ValueError(
                "ImplementState.phase must be one of {0!r}, "
                "got {1!r}".format(sorted(_VALID_PHASES), self.phase)
            )

        # wip_marker_path must be a Path.
        if not isinstance(self.wip_marker_path, Path):
            raise ValueError(
                "ImplementState.wip_marker_path must be a pathlib.Path, "
                "got {0}".format(type(self.wip_marker_path).__name__)
            )

        # checkpoint_sha must be None or a non-empty string.
        if self.checkpoint_sha is not None:
            if not isinstance(self.checkpoint_sha, str):
                raise ValueError(
                    "ImplementState.checkpoint_sha must be a string or None, "
                    "got {0}".format(type(self.checkpoint_sha).__name__)
                )
            if self.checkpoint_sha.strip() == "":
                raise ValueError(
                    "ImplementState.checkpoint_sha must be non-empty when set"
                )
