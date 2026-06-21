"""Banned phrases for annotation labels.

Words that signal archetype substitution rather than evidence-based labeling.
Sourced verbatim from the Obsidian note referenced by VALIDATOR-LOOP-PLAN.md.
Step A.2 ships this list as the complete v0 set; ecosystem-specific extensions
are out of scope for Part A.

Match is case-insensitive, whole-word boundary (Python `\\b`). Hyphens count
as word boundaries (e.g. `validates-input` triggers `validates`). A label is
rejected if ANY listed phrase appears as a token in the label text.
"""

from typing import Tuple

BANNED_PHRASES: Tuple[str, ...] = (
    "handles",
    "manages",
    "processes",
    "validates",
    "various",
    "etc",
    "responsible for",
)
