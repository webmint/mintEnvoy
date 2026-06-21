"""Topic slug derivation + mode detection + direct-conflict detection.

derive_topic_slug builds the YYYY-MM-DD-<slug>.md filename component
from a topic string. detect_mode_from_symptom uses bug/enhancement
token overlap. detect_direct_conflicts scans memo dimensions against
antagonist regex pairs. _compute_coverage returns per-dim state + counts.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ._constants import RUBRIC_DIMENSIONS, RUBRIC_STATE_DEFAULT
from ._state import _empty_dimension


# ---------------------------------------------------------------------------
# Topic slug derivation (used for filename + state record).
# ---------------------------------------------------------------------------


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def derive_topic_slug(topic: str, max_words: int = 4) -> str:
    """Lowercase + kebab-case + truncate to N words.

    Empty input or no-alnum-chars → "topic" as fallback. Used for
    research/YYYY-MM-DD-<slug>.md filename + memo.topic_slug field.
    """
    lowered = topic.lower().strip()
    cleaned = _SLUG_NON_ALNUM.sub("-", lowered).strip("-")
    if not cleaned:
        return "topic"
    parts = [p for p in cleaned.split("-") if p]
    if not parts:
        return "topic"
    return "-".join(parts[:max_words])


# ---------------------------------------------------------------------------
# Mode detection (token-overlap; deterministic, no LLM).
# ---------------------------------------------------------------------------


# Mode detection tokens. Case-insensitive substring match against the
# symptom field. Mixed-signal (both sets hit) → returns None and
# orchestrator asks user to disambiguate.
_BUG_TOKENS = (
    "fail", "broken", "wrong", "missing", "error",
    "crash", "bug", "regress", "doesn't work", "not working",
    "freezes", "hangs", "stuck",
)
_ENHANCEMENT_TOKENS = (
    "slow", "faster", "optimize", "support", "add",
    "integrate", "should", "enhance", "improve", "expand",
    "extend",
)


def detect_mode_from_symptom(symptom_text: str) -> Optional[str]:
    """Return "bug" / "enhancement" / None based on token presence.

    "bug" if at least one bug token and no enhancement tokens.
    "enhancement" if at least one enhancement token and no bug tokens.
    None if both sets hit (mixed-signal — orchestrator asks user) OR
    neither set hits (no signal — orchestrator asks user).
    """
    if not symptom_text:
        return None
    lower = symptom_text.lower()
    bug_hit = any(tok in lower for tok in _BUG_TOKENS)
    enh_hit = any(tok in lower for tok in _ENHANCEMENT_TOKENS)
    if bug_hit and not enh_hit:
        return "bug"
    if enh_hit and not bug_hit:
        return "enhancement"
    return None


# ---------------------------------------------------------------------------
# Conflict detection (token-overlap rules; deterministic).
# ---------------------------------------------------------------------------

# Antagonist regex pairs. Each entry: (dim_a, regex_a, dim_b, regex_b,
# description). Detector reports a conflict when BOTH regexes match
# their respective dimensions' values. Patterns are case-insensitive.
# Intentionally short list — covers the most common contradictions for
# UI/data symptoms. Extend as empirical data surfaces new pairs.
_CONFLICT_PATTERNS: Tuple[Tuple[str, str, str, str, str], ...] = (
    # alphabetical sort vs numeric/insertion order regression scope
    (
        "desired", r"\b(alphabetical|alpha\s*sort|name[- ]?sort|a[-→ ]+z)\b",
        "unchanged_behavior", r"\b(numeric|insert(ion)?|current|original)\s+order\b",
        "alphabetical sort would replace numeric/insertion order listed as unchanged",
    ),
    # ascending vs descending
    (
        "desired", r"\bascending\b",
        "unchanged_behavior", r"\bdescending\b",
        "ascending sort contradicts descending order required in unchanged behavior",
    ),
    (
        "desired", r"\bdescending\b",
        "unchanged_behavior", r"\bascending\b",
        "descending sort contradicts ascending order required in unchanged behavior",
    ),
    # async migration vs sync requirement
    (
        "desired", r"\basync(hronous)?\b",
        "unchanged_behavior", r"\bsync(hronous)?\b",
        "async transition contradicts synchronous requirement in unchanged behavior",
    ),
    # speed increase vs latency budget
    (
        "desired", r"\b(under|less than|<)\s*\d+\s*(ms|s|sec|second)",
        "unchanged_behavior", r"\b(under|less than|<)\s*\d+\s*(ms|s|sec|second)",
        "two conflicting latency budgets between desired and unchanged",
    ),
)


def detect_direct_conflicts(memo: dict) -> List[dict]:
    """Scan memo dimensions for direct contradictions; return conflict records.

    Each returned dict matches Conflict schema (type=direct). Used by
    `check-conflicts` setter to surface hard-block items to the
    orchestrator. Refinement / drift / mode-flip live in LLM-side logic;
    the helper only catches deterministic value-on-value contradictions.
    """
    conflicts = []  # type: List[dict]
    dims = memo.get("dimensions", {})

    def _val(name: str) -> str:
        rec = dims.get(name, {})
        if not isinstance(rec, dict):
            return ""
        v = rec.get("value")
        return v if isinstance(v, str) else ""

    for dim_a, rx_a, dim_b, rx_b, desc in _CONFLICT_PATTERNS:
        val_a = _val(dim_a)
        val_b = _val(dim_b)
        if not val_a or not val_b:
            continue
        if re.search(rx_a, val_a, re.IGNORECASE) and re.search(rx_b, val_b, re.IGNORECASE):
            conflicts.append(
                {
                    "type": "direct",
                    "dimensions": [dim_a, dim_b],
                    "description": desc,
                    "resolution": "blocked-pending-user",
                }
            )
    return conflicts


# ---------------------------------------------------------------------------
# Coverage helper (used by symptom-coverage + symptom-finalize).
# ---------------------------------------------------------------------------


def _compute_coverage(memo: dict) -> Tuple[Dict[str, str], int, int, int]:
    """Return (per-dim state map, clear_count, partial_count, missing_count).

    State per dim: derived from the stored {state, turns, value} record.
    Missing → no value yet. Partial → has value but turns >= cap with no
    explicit Clear marker, OR explicitly set to Partial. Clear → set to Clear.
    """
    dims = memo.get("dimensions", {})
    state_map = {}
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
