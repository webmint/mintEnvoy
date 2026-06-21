"""Topic slug derivation + Phase 0 conflict / coverage logic."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from ._state import RUBRIC_DIMENSIONS, RUBRIC_STATE_DEFAULT, _empty_dimension


# ---------------------------------------------------------------------------
# Topic slug derivation.
# ---------------------------------------------------------------------------

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_MAX_CHARS = 60


def derive_topic_slug(topic: str) -> str:
    """Lowercase + kebab-case + truncate at last `-` boundary before max 60 chars.

    Empty input or no-alnum-chars → "topic" as fallback. Used for
    discover-scope filename slug + memo.topic_slug / report.topic_slug.
    """
    lowered = topic.lower().strip()
    cleaned = _SLUG_NON_ALNUM.sub("-", lowered).strip("-")
    if not cleaned:
        return "topic"
    if len(cleaned) <= _SLUG_MAX_CHARS:
        return cleaned
    # Truncate at last `-` boundary before max_chars to avoid mid-word cuts.
    head = cleaned[:_SLUG_MAX_CHARS]
    boundary = head.rsplit("-", 1)[0]
    truncated = (boundary or head).rstrip("-")
    if not truncated:
        return "topic"
    return truncated


# ---------------------------------------------------------------------------
# Token-overlap conflict detection (Phase 0, deterministic, no LLM).
# ---------------------------------------------------------------------------

# Stopwords excluded from token-overlap matching.
_CONFLICT_STOPWORDS = frozenset({
    "a", "an", "the", "or", "and", "to", "of", "for",
    "with", "in", "on", "at", "by", "is", "as", "but", "not", "no",
})

# Minimum token length (characters) for overlap matching.
_CONFLICT_MIN_TOKEN_LEN = 4

# Dimension pairs checked by check-conflicts. non_goals is the anchor;
# the second dimension is the target. Locked order.
_CONFLICT_CHECK_PAIRS = (
    ("non_goals", "integration_points"),
    ("non_goals", "functional_scope"),
    ("non_goals", "success_criteria"),
    ("non_goals", "edge_cases"),
)


def _tokenize_for_conflict(text: str) -> List[str]:
    """Split text into lowercase tokens, drop stopwords + short tokens.

    Splits on whitespace and punctuation (any non-alphanumeric character).
    Returns tokens of length >= _CONFLICT_MIN_TOKEN_LEN not in stopwords.
    """
    raw_tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [
        t for t in raw_tokens
        if len(t) >= _CONFLICT_MIN_TOKEN_LEN and t not in _CONFLICT_STOPWORDS
    ]


def _detect_scope_conflicts(memo: dict) -> List[dict]:
    """Scan memo dimensions for direct contradictions via token overlap.

    For each pair in _CONFLICT_CHECK_PAIRS, checks whether any
    significant token from dim_a also appears in dim_b. Returns a list
    of conflict dicts (type=direct, resolution=None). Read-only.
    """
    dims = memo.get("dimensions", {})
    conflicts = []  # type: List[dict]

    def _val(name: str) -> str:
        rec = dims.get(name, {})
        if not isinstance(rec, dict):
            return ""
        v = rec.get("value")
        return v if isinstance(v, str) else ""

    for dim_a, dim_b in _CONFLICT_CHECK_PAIRS:
        val_a = _val(dim_a)
        val_b = _val(dim_b)
        if not val_a or not val_b:
            continue
        tokens_a = set(_tokenize_for_conflict(val_a))
        tokens_b = set(_tokenize_for_conflict(val_b))
        overlap = tokens_a & tokens_b
        if overlap:
            # Pick the lexicographically first token for deterministic output.
            token = min(overlap)
            conflicts.append({
                "type": "direct",
                "dimensions": [dim_a, dim_b],
                "description": "'{0}' appears in both {1} and {2}".format(
                    token, dim_a, dim_b
                ),
                "resolution": None,
            })
    return conflicts


# ---------------------------------------------------------------------------
# Coverage helper (used by scope-coverage + scope-finalize).
# ---------------------------------------------------------------------------


def _compute_scope_coverage(
    memo: dict,
) -> Tuple[Dict[str, str], int, int, int]:
    """Return (per-dim state map, clear_count, partial_count, missing_count)."""
    dims = memo.get("dimensions", {})
    state_map = {}  # type: Dict[str, str]
    clear = partial = missing = 0
    for d in RUBRIC_DIMENSIONS:
        rec = dims.get(d, _empty_dimension())
        st = rec.get("state", RUBRIC_STATE_DEFAULT)
        state_map[d] = st
        if st == "Clear":
            clear += 1
        elif st == "Partial":
            partial += 1
        else:
            missing += 1
    return state_map, clear, partial, missing
