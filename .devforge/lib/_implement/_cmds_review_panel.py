"""_cmds_review_panel -- merge-review-panel verb for implement_helper.

Aggregates the verdicts of the four per-task panel reviewers into a single
deterministic control-flow signal for /implement's PHASE 6 panel loop.

This module does the DETERMINISTIC part only: parse each reviewer's verdict
line from its markdown file, map it to clean/not-clean per that reviewer's
vocabulary, and aggregate across all four reviewers.  It does NOT parse,
merge, or conflict-detect FINDINGS -- that is semantic work the orchestrator
does by reading the reviewers' markdown directly.

Algorithm
---------
1. Parse --reviewer name:path pairs from the CLI.  Ordering is preserved.
2. For each reviewer: read the file; locate the ``### Verdict:`` heading line
   using the shared _VERDICT_RE pattern (imported from _cmds_review_loop so
   there is ONE source of truth for the anchor).
3. Extract + normalise the token after the colon (strip whitespace and
   trailing parentheticals; upper-case for comparison; reject slash-separated
   token groups as unfilled templates).
4. Validate the normalised token against that reviewer's allowed-token set.
   Unknown agent-name, missing verdict line, unfilled template, or wrong-vocab
   token all produce a parse error (exit 2, stderr names the reviewer).
5. Compute per_reviewer clean booleans; aggregate panel clean = all clean.
6. Compute escalate = (--iteration N >= REVIEW_LOOP_CAP), reusing the cap
   imported from _cmds_review_loop (ONE source of truth).
7. Emit JSON to stdout (exit 0):
     {
       "clean": <true iff ALL reviewers clean>,
       "escalate": <iteration >= REVIEW_LOOP_CAP>,
       "iteration": <int N>,
       "per_reviewer": [
           {"agent": "<name>", "verdict": "<TOKEN>", "clean": <bool>}, ...
       ]
     }
   Ordered as given on the CLI.

Exit codes
----------
  0 -- normal (JSON on stdout)
  2 -- parse error for any reviewer (stderr names which reviewer failed;
       no JSON on stdout); mirrors review-loop-step convention.

The cap and verdict-heading regex are imported from _cmds_review_loop to
keep a single authoritative source for both constants.

Stdlib only.  Python 3.8+.
"""

import json
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Imports from _cmds_review_loop (single source of truth)
# ---------------------------------------------------------------------------

from _implement._cmds_review_loop import (  # type: ignore[import]
    REVIEW_LOOP_CAP,
    _VERDICT_RE,  # ^###\s*verdict\s*: (re.IGNORECASE)
)

# ---------------------------------------------------------------------------
# Exit codes (mirrors _cmds_review_loop / _cmds_verify convention)
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_PARSE_ERROR = 2

# ---------------------------------------------------------------------------
# Per-reviewer vocabulary table
#
# Maps agent-name -> (clean_token, frozenset-of-all-valid-tokens).
# clean_token is the exact upper-cased string that means "this reviewer is
# satisfied".  All other valid tokens mean not-clean.
# ---------------------------------------------------------------------------

_REVIEWER_VOCAB = {
    "code-reviewer": (
        "APPROVE",
        frozenset(["APPROVE", "REQUEST CHANGES", "BLOCK"]),
    ),
    "qa-reviewer": (
        "ADEQUATE",
        frozenset(["ADEQUATE", "GAPS FOUND"]),
    ),
    "security-reviewer": (
        "PASS",
        frozenset(["PASS", "FAIL"]),
    ),
    "performance-analyst": (
        "MEETS TARGETS",
        frozenset(["MEETS TARGETS", "BOTTLENECKS FOUND"]),
    ),
}  # type: Dict[str, Tuple[str, Set[str]]]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _extract_token_after_colon(line):
    # type: (str) -> str
    """Return the text after the first ':' with surrounding whitespace stripped."""
    colon_pos = line.index(":")
    return line[colon_pos + 1:].strip()


def _normalise_for_vocab(raw_token, valid_tokens):
    # type: (str, Set[str]) -> Optional[str]
    """Normalise raw_token and match it against valid_tokens.

    Returns the matched valid token string on success, or None on failure.

    Rules (STRICTER than _cmds_review_loop._normalise_verdict):
    - Upper-case for comparison.
    - Reject any slash-separated text where a fragment matches a known
      valid token -- these are unfilled templates.
    - Match by prefix with a word-boundary guard: after the prefix match,
      the remainder must be absent (end-of-string) or start with a boundary
      character (space, tab, or punctuation from ".,:;!?()").  This rejects
      prefix collisions such as "BLOCKING" matching the "BLOCK" token, while
      still accepting trailing parentheticals like "APPROVE (with caveats)"
      (the space is a boundary character).  _cmds_review_loop._normalise_verdict
      uses a bare startswith() with no boundary guard and would accept "BLOCKING"
      as "BLOCK" -- this module's stricter behaviour is intentional and required
      for the multi-word, multi-vocab token sets the panel handles.
    """
    upper = raw_token.upper()

    # Detect slash-separated groups that look like unfilled templates.
    if "/" in upper:
        fragments = [f.strip() for f in upper.split("/")]
        if any(f in valid_tokens for f in fragments):
            return None

    # Longest-token-first prefix match to avoid SHORT prefix shadowing LONG
    # (e.g. "MEETS TARGETS" vs "MEETS" if a reviewer only used partial text).
    for token in sorted(valid_tokens, key=len, reverse=True):
        if upper.startswith(token):
            # Confirm word boundary: nothing after the prefix, OR a space /
            # punctuation follows.
            remainder = upper[len(token):]
            if not remainder or remainder[0] in " \t.,:;!?()":
                return token

    return None


def _parse_reviewer_verdict(agent_name, file_path):
    # type: (str, str) -> Tuple[Optional[str], Optional[str], Optional[str]]
    """Parse one reviewer's markdown file and return (token, clean_token, error_msg).

    Returns
    -------
    (token, clean_token, None) on success:
        token is the normalised verdict string (one of the reviewer's valid tokens).
        clean_token is this reviewer's designated clean token.
    (None, None, error_msg) on failure.
    """
    # --- Validate agent-name against VOCAB table ---
    if agent_name not in _REVIEWER_VOCAB:
        return None, None, (
            "merge-review-panel: unknown agent '{name}'; "
            "valid agents: {agents}".format(
                name=agent_name,
                agents=", ".join(sorted(_REVIEWER_VOCAB.keys())),
            )
        )

    clean_token, valid_tokens = _REVIEWER_VOCAB[agent_name]

    # --- Read file ---
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            markdown_text = fh.read()
    except OSError as exc:
        return None, None, (
            "merge-review-panel: cannot read file for '{name}' at {path}: {err}".format(
                name=agent_name, path=file_path, err=exc
            )
        )

    # --- Locate ### Verdict: line (shared pattern from _cmds_review_loop) ---
    verdict_line = None
    for line in markdown_text.splitlines():
        if _VERDICT_RE.match(line):
            verdict_line = line
            break

    if verdict_line is None:
        return None, None, (
            "merge-review-panel: no '### Verdict:' line found "
            "in '{name}' output at {path}".format(name=agent_name, path=file_path)
        )

    # --- Extract + normalise token ---
    raw = _extract_token_after_colon(verdict_line)
    if not raw:
        return None, None, (
            "merge-review-panel: '{name}' ### Verdict: line found "
            "but no token after the colon in {path}".format(
                name=agent_name, path=file_path
            )
        )

    normalised = _normalise_for_vocab(raw, valid_tokens)
    if normalised is None:
        return None, None, (
            "merge-review-panel: '{name}' ### Verdict: token {raw!r} is "
            "not in the reviewer's valid vocabulary {vocab} "
            "(or is an unfilled template) in {path}".format(
                name=agent_name,
                raw=raw,
                vocab=sorted(valid_tokens),
                path=file_path,
            )
        )

    return normalised, clean_token, None


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_merge_review_panel(args):
    # type: (object) -> int
    """Handler for the ``merge-review-panel`` subcommand.

    Reads each reviewer's markdown, parses the verdict, aggregates clean +
    escalate, and emits JSON controlling the panel review loop.
    """
    # --- Parse --iteration ---
    iteration = getattr(args, "iteration", 0) or 0
    if not isinstance(iteration, int) or iteration < 0:
        sys.stderr.write(
            "merge-review-panel: --iteration must be a non-negative integer\n"
        )
        return EXIT_PARSE_ERROR

    # --- Parse --reviewer name:path pairs ---
    reviewer_specs = getattr(args, "reviewer", None) or []
    if not reviewer_specs:
        sys.stderr.write(
            "merge-review-panel: at least one --reviewer name:path argument required\n"
        )
        return EXIT_PARSE_ERROR

    parsed_specs = []  # type: List[Tuple[str, str]]
    for spec in reviewer_specs:
        # Split on the first ':' only so paths on Windows or absolute POSIX
        # paths (/tmp/...) work correctly.
        colon_idx = spec.find(":")
        if colon_idx <= 0:
            sys.stderr.write(
                "merge-review-panel: malformed --reviewer argument {spec!r}; "
                "expected 'agent-name:/path/to/file'\n".format(spec=spec)
            )
            return EXIT_PARSE_ERROR
        agent_name = spec[:colon_idx]
        file_path = spec[colon_idx + 1:]
        parsed_specs.append((agent_name, file_path))

    # --- Parse each reviewer ---
    per_reviewer = []  # type: List[Dict]
    for agent_name, file_path in parsed_specs:
        token, clean_token, error_msg = _parse_reviewer_verdict(agent_name, file_path)
        if token is None:
            sys.stderr.write("{0}\n".format(error_msg))
            return EXIT_PARSE_ERROR
        is_clean = token == clean_token
        per_reviewer.append({
            "agent": agent_name,
            "verdict": token,
            "clean": is_clean,
        })

    # --- Aggregate ---
    panel_clean = all(r["clean"] for r in per_reviewer)
    escalate = iteration >= REVIEW_LOOP_CAP

    # --- Emit JSON ---
    payload = {
        "clean": panel_clean,
        "escalate": escalate,
        "iteration": iteration,
        "per_reviewer": per_reviewer,
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argparse registration (called from _cli.py)
# ---------------------------------------------------------------------------


def add_args_merge_review_panel(parser):
    # type: (object) -> None
    """Add arguments for merge-review-panel to the subparser."""
    parser.add_argument(
        "--reviewer",
        action="append",
        metavar="AGENT:PATH",
        default=None,
        dest="reviewer",
        help=(
            "Reviewer agent name and path to its returned markdown, "
            "in the form 'agent-name:/path/to/file.md'. "
            "Repeat for each reviewer (e.g. "
            "--reviewer code-reviewer:/tmp/cr.md "
            "--reviewer qa-reviewer:/tmp/qa.md). "
            "Valid agent names: {agents}.".format(
                agents=", ".join(sorted(_REVIEWER_VOCAB.keys()))
            )
        ),
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Current panel-review iteration count (0-based). "
            "When N >= REVIEW_LOOP_CAP ({cap}), escalate=true is emitted "
            "regardless of verdicts.  Default: 0.".format(cap=REVIEW_LOOP_CAP)
        ),
    )
