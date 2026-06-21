"""State dataclass + path helpers for pr_review_helper.

Owns the PRReviewState schema and the per-PR storage path convention.
Transactional read/write ships with Step 3 (intake), when the first
verb needs to write state.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


_PR_REVIEWS_DIR = "pr-reviews"
_STATE_FILENAME = "state.json"


@dataclass
class PRReviewState:
    """Per-PR review state stored at <devforge_dir>/pr-reviews/<pr>/state.json.

    Fields are populated by successive verb invocations (Steps 3-9).
    Defaults represent the empty/unset sentinel for each field type:
    0 for int, "" for str, [] for lists, {} for dicts.
    """

    # Step 3 (intake) populates.
    pr_number: int = 0
    repo: str = ""
    pr_title: str = ""
    # Runtime-injected by _cli (cmd_detect_smells); written to state.json but
    # always overwritten from --target args at run time — do not rely on the
    # persisted value across machines (it is machine-local). Declared here
    # rather than via dynamic-attribute injection so heuristics can access
    # state.target without a getattr defensive fallback.
    target: str = ""
    diff: str = ""
    pr_body: str = ""
    linked_issues: List[str] = field(default_factory=list)
    ticket_text: str = ""
    commit_subjects: List[str] = field(default_factory=list)

    # Step 2 (detect-forge-state) populates.
    forge_tier: str = "none"  # one of: full / partial / none

    # Step 6 (bundle-context) populates.
    bundle: Dict = field(default_factory=dict)

    # Step 4 (detect-smells) populates.
    smells: List = field(default_factory=list)

    # Step 5 (compute-blast-radius) populates.
    blast: List = field(default_factory=list)

    # Step 7 (check-scope-drift) populates.
    drift: Dict = field(default_factory=dict)

    # Step 8 (dispatch-review) populates.
    findings: List = field(default_factory=list)


def state_path(devforge_dir: str, pr_number: int) -> str:
    """Return the absolute path to the per-PR state JSON file.

    Path structure: <devforge_dir>/_PR_REVIEWS_DIR/<pr_number>/_STATE_FILENAME

    devforge_dir may be relative or absolute; the result is always
    converted to an absolute path using os.path.abspath so callers
    can rely on it without knowing the caller's cwd.
    """
    abs_devforge = os.path.abspath(devforge_dir)
    return os.path.join(abs_devforge, _PR_REVIEWS_DIR, str(pr_number), _STATE_FILENAME)
