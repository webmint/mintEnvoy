"""Brief assembly for review_helper (Phase 3).

render_agent_brief  — assemble per-agent review instruction block

Assembly order (5 steps):
  1. Anti-relitigation preamble   (verbatim from references_dir)
  2. Emergent-issue checklist     (verbatim from references_dir — includes the
                                   full ## Finding N output contract at its end;
                                   do NOT duplicate a second contract block)
  3. Per-agent focus block        (_FOCUS_BLOCKS[agent])
  4. Scope block                  (from resolve-feature-scope, passed as a string)
  5. Closing instruction          (write findings to tmp_path via Bash)

The checklist already fully specifies the ## Finding N field shape and the
single Evidence: fenced block requirement.  The closing section appends the
Bash write instruction and reinforces the grounding rule; it does NOT re-emit
a separate output contract block that could drift from the checklist definition.

_shared._consume.parse_agent_tmp is the authoritative parser.  This module's
brief instructs agents to produce exactly the shape that parser reads.

Stdlib only.  Targets Python 3.8+.
"""

from __future__ import annotations

import os
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Per-agent focus blocks — emergent cross-task lens
# ---------------------------------------------------------------------------

_FOCUS_BLOCKS = {
    "code-reviewer": (
        "Your primary mission: EMERGENT CROSS-TASK REVIEW of the assembled "
        "feature diff. Focus on cross-task duplication and divergence — multiple "
        "tasks each open-coding a near-identical helper, type, or validation that "
        "should be unified; two tasks implementing the same rule with contradictory "
        "edge-case handling or thresholds. Also hunt cross-task layering violations "
        "visible only once the tasks are assembled: an import or call that crosses a "
        "layer boundary where neither task's diff alone crosses it. "
        "Tag duplication/divergence findings `Category: duplication`; layering "
        "violations `Category: system_design`; cross-task mislogic that spans two "
        "tasks' code paths `Category: mislogic`."
    ),
    "architect": (
        "Your primary mission: EMERGENT CROSS-TASK ARCHITECTURAL DRIFT. Find "
        "two tasks that each made a locally-reasonable choice that are GLOBALLY "
        "inconsistent once assembled — different error-handling patterns for the "
        "same concern, contradictory abstractions for the same domain concept, or "
        "one task introducing an abstraction that another task bypasses (task A adds "
        "a repository/service/wrapper as the intended single path; task B reaches "
        "around it to the underlying resource directly). Hunt dependency-direction "
        "violations that only cross a layer boundary when both tasks' changes are "
        "assembled. Tag architectural drift and layering violations "
        "`Category: system_design`; duplicated/diverged logic that should be shared "
        "`Category: duplication`."
    ),
    "qa-reviewer": (
        "Your primary mission: EMERGENT CROSS-TASK TEST GAPS at the seams between "
        "task-owned modules. Do NOT write tests — you are a read-only test-quality "
        "assessor. Hunt test coverage gaps that are invisible within one task's diff "
        "but appear once the tasks are assembled: an integration path that only "
        "exists once task A's code composes with task B's; a cross-task flow that "
        "task A's tests exercise in isolation but task B's code now short-circuits "
        "or bypasses; a contract between two tasks where the interface is tested on "
        "one side but not from the other. A gap within a single task's own module "
        "is out of scope — the per-task panel already owned it. "
        "Tag these findings `Category: blind_spot`."
    ),
    "security-reviewer": (
        "Your primary mission: EMERGENT CROSS-TASK SECURITY HOLES at feature scope. "
        "Hunt trust/auth boundary violations where task A establishes a guard and "
        "task B adds a code path that reaches the protected resource without going "
        "through it; validations that hold per-task but are skippable once the "
        "composed flow exists (task A validates on one entry, task B adds a second "
        "entry to the same downstream sink without the same validation); credential, "
        "scope, or permission interactions where one task narrows and another widens "
        "or re-exposes. Single-task security issues the per-task panel already owned "
        "are out of scope — the emergent cross-task surface is yours. "
        "Tag these findings `Category: security`."
    ),
    "performance-analyst": (
        "Your primary mission: EMERGENT ASSEMBLED-DATA-FLOW PERFORMANCE at feature "
        "scope. Hunt query/loop/fetch patterns that are fine WITHIN one task but "
        "become N+1, O(n²), or a redundant refetch once the tasks COMPOSE into the "
        "full data flow — task A adds a per-row fetch helper, task B calls it inside "
        "a loop over a collection task A populates; two tasks each fetching the same "
        "resource on the same request. A per-task idiom smell the task panel already "
        "owned is out of scope. "
        "Category rule: if the cost is an emergent property of how the tasks' layers "
        "or data flow are wired together (an N+1 born of one task looping over "
        "another's per-item call), tag `Category: system_design`. If, after assembly, "
        "the costly construct is a single local idiom that should have been "
        "memoized/derived/batched in one spot, tag `Category: best_practice`."
    ),
}  # type: Dict[str, str]

# Default write path shown in the closing when no tmp_path is supplied.
_DEFAULT_TMP_PATH = "specs/.tmp-{agent-name}.md"

_CLOSING_REMINDER = """\
REMEMBER: EMERGENT CROSS-TASK REVIEW MODE is in effect. Every finding MUST span \
at least two tasks — if you can state the finding from a single task's diff alone, \
it is out of scope. The `Evidence:` block quotes ONLY the ANCHOR file named in \
`File:` (the defect site — the bypass, the unvalidated entry, the diverged copy). \
The PARTNER file (the boundary bypassed, the first validated entry, the original \
copy) is named by path and line in `Why it's wrong:` prose — do NOT quote the \
partner file's code inside `Evidence:` and do NOT use `// from <file>` separators. \
A finding without a verbatim Evidence block, or whose Evidence block contains code \
not present in the anchor file, will be discarded by the anti-hallucination validator. \
The Confidence tier keeps cross-task judgments honest: `Certain` only for defects \
provable from the quoted code alone; `Likely` or `Speculative` for opinion/preference.

When you have finished writing your findings, run this Bash command to write them \
to the output file:

```bash
cat > {tmp_path} << 'REVIEW_FINDINGS_EOF'
# Agent: {agent}
# Status: complete
# Finding count: <N>

<paste your ## Finding 1 ... ## Finding N blocks here>

## Top 5 Priorities (this agent only)
1. Finding #N — <one-line description>
2. ...
REVIEW_FINDINGS_EOF
```

If you find nothing, write `# Finding count: 0` and omit the Finding blocks. \
If you fail partway, write `# Status: failed` and `# Reason: <message>` so the \
pipeline can detect the failure.\
"""


# ---------------------------------------------------------------------------
# render_agent_brief
# ---------------------------------------------------------------------------


def render_agent_brief(agent, references_dir, scope_block, tmp_path=None):
    # type: (str, str, str, Optional[str]) -> str
    """Assemble the per-agent review instruction block.

    Assembly order (5 steps):
      1. Anti-relitigation preamble (verbatim from anti-relitigation-preamble.md)
      2. Emergent-issue checklist   (verbatim from emergent-issue-checklist.md;
                                     contains the full ## Finding N output contract)
      3. Per-agent focus block      (_FOCUS_BLOCKS[agent])
      4. Scope block                (pre-rendered string from resolve-feature-scope)
      5. Closing instruction        (Bash write command + grounding reminder)

    The emergent-issue-checklist.md already specifies the ## Finding N field
    shape and single Evidence: block requirement verbatim.  The closing section
    adds the Bash write command; it does NOT re-emit a second contract block
    that could diverge from the checklist definition.

    Args:
        agent:          One of the five review agents (key in _FOCUS_BLOCKS).
        references_dir: Directory containing anti-relitigation-preamble.md and
                        emergent-issue-checklist.md.
        scope_block:    Pre-rendered scope summary string (from resolve-feature-scope
                        scope_block field or _render_scope_block output).
        tmp_path:       Agent findings write-path emitted in the closing instruction.
                        When None, defaults to _DEFAULT_TMP_PATH (backward-compatible).

    Returns:
        Multi-line string forming the agent instruction block.

    Raises:
        ValueError: if agent is not in _FOCUS_BLOCKS, or if a reference file
                    is missing or unreadable.
    """
    if agent not in _FOCUS_BLOCKS:
        raise ValueError(
            "unknown agent {0!r}; must be one of {1}".format(
                agent, sorted(_FOCUS_BLOCKS.keys())
            )
        )

    preamble_path = os.path.join(references_dir, "anti-relitigation-preamble.md")
    checklist_path = os.path.join(references_dir, "emergent-issue-checklist.md")

    try:
        with open(preamble_path, "r", encoding="utf-8") as fh:
            preamble = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read anti-relitigation-preamble.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    try:
        with open(checklist_path, "r", encoding="utf-8") as fh:
            checklist = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read emergent-issue-checklist.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    focus = _FOCUS_BLOCKS[agent]

    effective_tmp = tmp_path if tmp_path is not None else _DEFAULT_TMP_PATH
    closing = _CLOSING_REMINDER.replace("{tmp_path}", effective_tmp).replace(
        "{agent}", agent
    )

    parts = [
        preamble,
        checklist,
        focus,
        scope_block,
        closing,
    ]

    return "\n\n".join(parts)
