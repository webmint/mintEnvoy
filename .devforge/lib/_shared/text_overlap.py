"""Shared token-overlap utilities.

tokenize_for_overlap is the single authoritative tokenizer for token-overlap
matching across devforge subpackages. It splits on non-alphanumeric boundaries,
lowercases, and drops tokens shorter than min_len and any stopword.

Technique mirrors _discover/_topic.py:_tokenize_for_conflict and the prior
_research/_cmds_render_verify.py:_tokenize_hypothesis. Those copies are NOT
migrated in this round (tracked as a follow-up); new callers must import from
here rather than adding a fourth divergent copy.

The stopword set is the union of the two prior sets, expanded to cover common
English function words that add no discriminating signal for vocabulary-overlap
detection:
  - _discover/_topic.py set: short connective words (a, an, the, or, and, etc.)
  - _research/_cmds_render_verify.py set: auxiliary verbs + determiners
    (that, this, from, are, was, has, have, had, its, their, into, when,
     will, been, also, such, more, they)
  - Codebase-specific boilerplate: "scope", "shall", "system" — these are
    universal in spec/EARS prose ("The system shall…", "…— out of scope") and
    carry zero discriminating signal for overlap detection. Without them, every
    EARS-formatted AC shares "system" and "shall" with every OOS entry that
    contains those words, producing universal false positives.

The check catches IDENTIFIER/VOCABULARY reuse, not semantic paraphrase.
Pure-paraphrase approaches that encode the same mechanism with different
vocabulary pass this check — that gap is intentional and is caught by the
Step-5 intake echo-back human gate, not by this mechanical backstop.
"""

from __future__ import annotations

import re
from typing import List

# Union of stopwords from _discover/_topic.py and _research/_cmds_render_verify.py.
# These are high-frequency English function words that add no discriminating
# signal for identifier/vocabulary-overlap detection.
_OVERLAP_STOPWORDS = frozenset({
    # Short connectives (from _discover)
    "a", "an", "the", "or", "and", "to", "of", "for",
    "with", "in", "on", "at", "by", "is", "as", "but", "not", "no",
    # Auxiliary verbs + determiners (from _research)
    "that", "this", "from", "are", "was", "has", "have", "had",
    "its", "their", "into", "when", "will", "been", "also",
    "such", "more", "they",
    # Codebase-specific boilerplate: universal in spec/EARS prose, zero
    # discriminating signal — "The system shall…" / "…— out of scope" appear
    # in almost every EARS AC and OOS entry respectively.
    "scope", "shall", "system",
})

# Minimum token length. Tokens shorter than this are typically prepositions
# or articles and add noise to overlap matching.
_OVERLAP_MIN_TOKEN_LEN = 4


def tokenize_for_overlap(text, min_len=_OVERLAP_MIN_TOKEN_LEN):
    # type: (str, int) -> List[str]
    """Split text into lowercase tokens for overlap matching.

    Splits on any non-alphanumeric character sequence, lowercases, then
    drops tokens shorter than min_len and stopwords.

    This is a literal-vocabulary check: two texts share a token when they
    use the SAME identifier or word, not when they describe the same concept
    in different words (paraphrase is not detected).

    Args:
        text: Input string to tokenize.
        min_len: Minimum token length to keep (default 4). Tokens shorter
                 than this are dropped regardless of stopword list.

    Returns:
        List of lowercase tokens passing the length and stopword filters.
        Order is preserved; duplicates are retained (caller dedupes via set()
        if set-intersection is needed).
    """
    raw = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [
        t for t in raw
        if len(t) >= min_len and t not in _OVERLAP_STOPWORDS
    ]
