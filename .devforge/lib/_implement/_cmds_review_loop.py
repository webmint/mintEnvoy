"""_cmds_review_loop -- review-loop-step verb for implement_helper.

Parses the code-reviewer agent's markdown output and emits a JSON
control-flow signal so the orchestrator knows whether to continue the
autonomous review loop, accept, or escalate to the hard gate.

Algorithm
---------
1. Read the code-reviewer's markdown from --verdict-file <path> or stdin.
2. Locate the ``### Verdict:`` heading line (case-insensitive).
3. Extract the single verdict token that follows the colon:
     APPROVE             → clean=true
     REQUEST CHANGES     → clean=false
     BLOCK               → clean=false
   If the line contains all three slash-separated tokens (the unfilled
   template), treat it as a parse error → exit 2 (no JSON).
   If no ``### Verdict:`` line is found → exit 2 (no JSON).
4. Compute escalate: true when --iteration N >= REVIEW_LOOP_CAP (3).
   The helper owns this cap; the orchestrator cannot bypass it.
5. Emit JSON to stdout:
     {clean: bool, escalate: bool, iteration: int, verdict: str}
   Exit 0.

Exit codes
----------
  0 -- normal (JSON on stdout)
  2 -- parse error (no/unparseable verdict line); stderr message

The helper intentionally owns the cap constant so the orchestrator
cannot silently extend the loop beyond the policy limit.  This mirrors
the self-repair cap in _cmds_verify.py (SELF_REPAIR_CAP = 3).

Stdlib only.  Python 3.8+.
"""

import json
import re
import sys
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Constants (helper-owned; the orchestrator cannot override these)
# ---------------------------------------------------------------------------

# Maximum review-loop iterations before escalating to the hard gate.
# Mirrors the self-repair cap (SELF_REPAIR_CAP) in _cmds_verify.py.
REVIEW_LOOP_CAP = 3  # default 3 rounds; code-commented per plan spec

# Exit codes (mirrors _cmds_verify.py convention)
EXIT_OK = 0
EXIT_ERR = 1
EXIT_FINDINGS = 2  # used to signal parse error (no valid verdict)

# Known clean verdict token (upper-cased for comparison).
_TOKEN_APPROVE = "APPROVE"
# Known dirty verdict tokens.
_TOKEN_REQUEST_CHANGES = "REQUEST CHANGES"
_TOKEN_BLOCK = "BLOCK"

# The unfilled-template sentinel: all three tokens separated by slashes.
# When the reviewer emits the template without filling it, it looks like:
#   ### Verdict: APPROVE / REQUEST CHANGES / BLOCK
# This is NOT a verdict — it's a parse error.
_TEMPLATE_TOKENS = frozenset(["APPROVE", "REQUEST CHANGES", "BLOCK"])

# Heading prefix (case-insensitive search).
_VERDICT_RE = re.compile(r"^###\s*verdict\s*:", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _extract_verdict_token(line):
    # type: (str) -> str
    """Return the text after '### Verdict:' with leading/trailing whitespace stripped.

    Assumes the caller has already confirmed the line matches _VERDICT_RE.
    """
    colon_pos = line.index(":")
    # The regex matched "### Verdict:" so there is always a colon.
    return line[colon_pos + 1:].strip()


def _normalise_verdict(raw_token):
    # type: (str) -> Optional[str]
    """Map the raw post-colon text to a normalised verdict token.

    Returns one of 'APPROVE', 'REQUEST CHANGES', 'BLOCK', or None when
    the token does not match any known verdict (including the unfilled
    template).

    Rules
    -----
    - Strip trailing punctuation (periods, exclamation marks, parenthetical
      notes like "APPROVE (with warnings)").  The clean signal comes from
      the leading token.
    - Upper-case for comparison.
    - If the text contains all three slash-separated tokens, the template
      is unfilled → return None (caller signals parse error).
    """
    upper = raw_token.upper()

    # Detect any slash-separated mix of known tokens — these are malformed /
    # unfilled templates regardless of how many tokens appear.  A single slash
    # in the verdict text with any fragment matching a known token is enough to
    # reject: e.g. "APPROVE / REQUEST CHANGES" (2-token) and the full
    # "APPROVE / REQUEST CHANGES / BLOCK" (3-token) both parse as errors.
    if "/" in upper:
        fragments = [f.strip() for f in upper.split("/")]
        if any(f in _TEMPLATE_TOKENS for f in fragments):
            return None

    # Match known tokens.  We only need to test the start of the string
    # (a reviewer may append parenthetical notes like "(with warnings)").
    if upper.startswith(_TOKEN_REQUEST_CHANGES):
        return _TOKEN_REQUEST_CHANGES
    if upper.startswith(_TOKEN_BLOCK):
        return _TOKEN_BLOCK
    if upper.startswith(_TOKEN_APPROVE):
        return _TOKEN_APPROVE

    # Unknown token.
    return None


def parse_verdict(markdown_text):
    # type: (str) -> Tuple[Optional[str], Optional[str]]
    """Parse the code-reviewer markdown and return (verdict_token, error_msg).

    Parameters
    ----------
    markdown_text : Full markdown string from the code-reviewer agent.

    Returns
    -------
    (verdict_token, None) on success:
        verdict_token is one of 'APPROVE', 'REQUEST CHANGES', 'BLOCK'.
    (None, error_msg) on failure:
        error_msg describes why parsing failed.
    """
    for line in markdown_text.splitlines():
        if not _VERDICT_RE.match(line):
            continue
        raw = _extract_verdict_token(line)
        token = _normalise_verdict(raw)
        if token is None:
            # Matched the heading but the token is unrecognised or the
            # unfilled template.
            if not raw:
                return None, (
                    "review-loop-step: ### Verdict: line found but "
                    "no token after the colon"
                )
            return None, (
                "review-loop-step: ### Verdict: line is the unfilled "
                "template or contains an unrecognised token: {raw!r}".format(
                    raw=raw
                )
            )
        return token, None

    return None, "review-loop-step: no '### Verdict:' line found in reviewer output"


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_review_loop_step(args):
    # type: (object) -> int
    """Handler for the ``review-loop-step`` subcommand.

    Reads the code-reviewer markdown, parses the verdict, and emits JSON
    controlling the autonomous review loop.
    """
    # --- Read markdown input ---
    verdict_file = getattr(args, "verdict_file", None)
    if verdict_file:
        try:
            with open(verdict_file, "r", encoding="utf-8") as fh:
                markdown_text = fh.read()
        except OSError as exc:
            sys.stderr.write(
                "review-loop-step: cannot read --verdict-file {path}: {err}\n".format(
                    path=verdict_file, err=exc
                )
            )
            return EXIT_FINDINGS
    else:
        markdown_text = sys.stdin.read()

    # --- Parse iteration ---
    iteration = getattr(args, "iteration", 0) or 0
    if not isinstance(iteration, int) or iteration < 0:
        sys.stderr.write(
            "review-loop-step: --iteration must be a non-negative integer\n"
        )
        return EXIT_FINDINGS

    # --- Parse verdict ---
    verdict_token, error_msg = parse_verdict(markdown_text)
    if verdict_token is None:
        sys.stderr.write("{0}\n".format(error_msg))
        return EXIT_FINDINGS

    # --- Compute clean and escalate ---
    clean = verdict_token == _TOKEN_APPROVE
    escalate = iteration >= REVIEW_LOOP_CAP

    # --- Emit JSON ---
    payload = {
        "clean": clean,
        "escalate": escalate,
        "iteration": iteration,
        "verdict": verdict_token,
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argparse registration (called from _cli.py)
# ---------------------------------------------------------------------------


def add_args_review_loop_step(parser):
    # type: (object) -> None
    """Add arguments for review-loop-step to the subparser."""
    parser.add_argument(
        "--verdict-file",
        dest="verdict_file",
        metavar="PATH",
        default=None,
        help=(
            "Path to the code-reviewer agent's returned markdown file. "
            "If omitted, markdown is read from stdin."
        ),
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Current review-loop iteration count (0-based). "
            "When N >= REVIEW_LOOP_CAP ({cap}), escalate=true is emitted "
            "regardless of the verdict.  Default: 0.".format(cap=REVIEW_LOOP_CAP)
        ),
    )
