"""Brief assembly for grill_helper (Phase 2).

render_agent_brief  -- assemble the single devils-advocate dispatch brief

/grill dispatches ONE adversary (the ``devils-advocate`` agent), not a
5-finder ensemble.  This module owns:

  * The three-ring blast-radius traversal instruction (the helper cannot call
    the CBM graph; the agent performs the traversal itself).
  * The _OUTPUT_CONTRACT constant (same field shape as /audit and /review;
    File is polymorphic -- plan.md / spec.md / a source path; Evidence for an
    external-claim/web attack is a re-fetchable citation + quoted doc passage).
  * Assembly of the per-brief text from references_dir files + manifest paths
    + traversal instruction + output contract.

Assembly order (6 steps):
  1. Anti-relitigation preamble    (verbatim from references_dir)
  2. Design-level attack checklist (verbatim from references_dir)
  3. Scope / read-context block    (derived from GrillScopeManifest paths)
  4. Three-ring traversal instruction (parameterized by ring1_cap)
  5. Output Contract               (_OUTPUT_CONTRACT, __FINDING_CAP__ replaced)
  6. Closing instruction           (_CLOSING_REMINDER, write-path + grounding)

The output contract fully specifies the ## Finding N field shape.  The closing
section appends the Bash write command; it does NOT re-emit a second contract
block that could diverge from step 5.

_shared._consume.parse_agent_tmp is the authoritative parser.  This module
instructs the agent to produce exactly the shape that parser reads.

Stdlib only.  Targets Python 3.8+.  No from __future__ import annotations.
"""

import os
from typing import Optional

from ._scope import GrillScopeManifest


# ---------------------------------------------------------------------------
# Agent identity constant
# ---------------------------------------------------------------------------

GRILL_AGENT = "devils-advocate"

# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

_OUTPUT_CONTRACT = """\
Each agent writes its findings to `{tmp-path}` using this **fixed parseable \
format**. The parent command will regex-parse these headings, so deviation \
breaks the pipeline.

````
# Agent: {agent-name}
# Status: complete
# Finding count: N

## Finding 1
Severity: Critical | High | Medium | Info
File: path/to/plan.md  (or spec.md, or a source path, or a URL for web claims)
Line: 42  (use -1 when the file has no lines, e.g. for a URL citation)
Pattern: <one-line pattern name, e.g. "Scope creep" or "Unvalidated assumption">
Category: mislogic | system_design | best_practice | duplication | security | blind_spot
Confidence: Certain | Likely | Speculative
Evidence:
```
<verbatim quoted text, copy-pasted from the file or the cited doc passage, no edits>
```
Why it's wrong: <one paragraph>
Remediation: <one paragraph>

## Finding 2
[same fields]

...

## Top 5 Priorities (this agent only)
1. Finding #N — <one-line description>
2. ...
````

Category glossary: `mislogic` — logic contradictions, lying names/comments, \
control-flow bugs, dead branches; `system_design` — layering/dependency-direction \
violations, SOLID-at-scale, god components, business/data logic in presentation; \
`best_practice` — language/framework idiom and type-safety violations; \
`duplication` — copy-pasted or diverged logic that should be shared; \
`security` — security regressions / drift; `blind_spot` — untested or \
unvalidated business-logic branch (logic blind spot).

**Hard rules for the agent**:
- **Every finding MUST declare exactly one `Category:`** from the list above. \
If unsure, use `mislogic`.
- **Enumerate every real, grounded instance — do NOT collapse a recurring \
pattern to one example.** If a problem appears in N places, report all N as \
separate findings, each with its own verbatim quote. Cap: __FINDING_CAP__ \
findings total — only if you genuinely exceed it, drop the lowest-confidence.
- **Every finding MUST have a verbatim Evidence block.** No quote = no \
finding. The parent will validate this and discard ungrounded findings.
- **The Evidence block must be a literal copy from the cited file or doc.** \
Do not paraphrase, do not abbreviate, do not insert `...`. If the relevant \
text is more than 20 lines, cite the most important 5-10 lines. If you cannot \
locate and copy the EXACT text from the source, DROP the finding.
- **For external-claim / web attacks:** File is the URL, Line is -1, and \
Evidence is a re-fetchable citation (URL + section/heading) followed by a \
verbatim quoted passage from that document.
- **The Line field must point to the first line of the Evidence block in the \
actual file.** Use -1 for URL citations.
- If the agent fails partway, it must still write a temp file with \
`# Status: failed` and a `# Reason: <message>` line.
- If the agent finds nothing, write a temp file with `# Status: complete` and \
`# Finding count: 0`. Empty file != failure."""

# Default write-path placeholder used in the output contract and closing reminder.
# This token is replaced at render time with the actual tmp_path.
_DEFAULT_TMP_PATH_TOKEN = "specs/.tmp-devils-advocate.md"

_CLOSING_REMINDER = """\
REMEMBER: ADVERSARIAL DEVILS-ADVOCATE MODE is in effect. Challenge every \
assumption, every scope decision, every design choice in the plan and spec. \
Report only defects you can demonstrate from verbatim quotes of the actual \
plan/spec/source text or from a re-fetchable external citation — a real quote \
of correct text is not a finding; do not assume a problem exists. Fabrications \
are forbidden. Enumerate every real instance you can quote exactly, up to \
__FINDING_CAP__ — do not stop at one example of a recurring problem, and drop \
any finding whose quote you cannot copy verbatim. \
Every finding needs a verbatim Evidence block and a Confidence tier. \
Do not soften. Critical of plans and designs, not people.

When you have finished writing your findings, run this Bash command to write \
them to the output file:

```bash
cat > {tmp_path} << 'GRILL_FINDINGS_EOF'
# Agent: devils-advocate
# Status: complete
# Finding count: <N>

<paste your ## Finding 1 ... ## Finding N blocks here>

## Top 5 Priorities (this agent only)
1. Finding #N — <one-line description>
2. ...
GRILL_FINDINGS_EOF
```

If you find nothing, write `# Finding count: 0` and omit the Finding blocks. \
If you fail partway, write `# Status: failed` and `# Reason: <message>` so \
the pipeline can detect the failure.\
"""

# ---------------------------------------------------------------------------
# Three-ring traversal instruction
# ---------------------------------------------------------------------------

_TRAVERSAL_INTRO = """\
## Three-Ring Blast-Radius Traversal

You hold the codebase-memory MCP tools.  Perform the following traversal \
yourself — the helper cannot call the graph.

**Ring 0 — File-Impact files (mandatory):** Read every source file listed in \
the plan's File Impact section and any test files that directly exercise them. \
These are your primary evidence sources.

**Ring 1 — One-hop callers/callees (capped at __RING1_CAP__ entries):** Using \
`trace_path` and `search_graph`, identify the direct callers and callees of \
the Ring 0 files. Read up to __RING1_CAP__ of the highest-relevance entries \
(by call frequency or coupling weight). Do NOT recurse further into Ring 1 \
results.

**Ring 2 — Query-only (no new reads):** Use `query_graph` and `search_graph` \
for structural queries (dependency direction, ownership, cross-layer paths) \
but do NOT read additional source files beyond Ring 0 and Ring 1.

This traversal is your evidence base for implementation-level findings. \
Findings about source files MUST be grounded in text you observed in Ring 0 \
or Ring 1.\
"""

# Placeholder for ring1_cap substitution (same __TOKEN__ pattern as __FINDING_CAP__).
_RING1_CAP_TOKEN = "__RING1_CAP__"

# ---------------------------------------------------------------------------
# render_agent_brief
# ---------------------------------------------------------------------------

DEFAULT_RING1_CAP = 15
DEFAULT_FINDING_CAP = 30


def render_agent_brief(
    manifest,         # type: GrillScopeManifest
    references_dir,   # type: str
    ring1_cap=DEFAULT_RING1_CAP,  # type: int
    finding_cap=DEFAULT_FINDING_CAP,  # type: int
    tmp_path=None,    # type: Optional[str]
):
    # type: (...) -> str
    """Assemble the single devils-advocate dispatch brief for /grill.

    Assembly order (6 steps):
      1. Anti-relitigation preamble    (verbatim from references_dir/
                                        anti-relitigation-preamble.md)
      2. Design-level attack checklist (verbatim from references_dir/
                                        design-attack-checklist.md)
      3. Scope / read-context block    (paths from GrillScopeManifest)
      4. Three-ring traversal instruction (ring1_cap substituted in)
      5. Output Contract               (_OUTPUT_CONTRACT, __FINDING_CAP__
                                        and tmp-path token replaced)
      6. Closing instruction           (_CLOSING_REMINDER, same substitutions)

    Args:
        manifest:       GrillScopeManifest from build_scope_manifest (carries
                        plan_path, spec_path, handoff_path, constitution_path,
                        claude_md_path).
        references_dir: Directory containing anti-relitigation-preamble.md and
                        design-attack-checklist.md.
        ring1_cap:      Maximum Ring-1 CBM entries the agent should follow.
                        Substituted for __RING1_CAP__ in the traversal block.
                        Non-positive values fall back to DEFAULT_RING1_CAP.
        finding_cap:    Maximum findings the agent should report.
                        Substituted for __FINDING_CAP__ in the output contract
                        and closing reminder.
                        Non-positive values fall back to DEFAULT_FINDING_CAP.
        tmp_path:       Agent findings write-path emitted in the output contract
                        and closing instruction.  When None, defaults to
                        _DEFAULT_TMP_PATH_TOKEN (backward-compatible).

    Returns:
        Multi-line string forming the agent instruction block.

    Raises:
        ValueError: if a required reference file is missing or unreadable.
    """
    # Defensive: bad cap values fall back to defaults.
    # bool is a subclass of int, so isinstance(True, int) is True; reject bools
    # explicitly to avoid ring1_cap=True silently being treated as 1.
    if isinstance(ring1_cap, bool) or not isinstance(ring1_cap, int) or ring1_cap <= 0:
        ring1_cap = DEFAULT_RING1_CAP
    if isinstance(finding_cap, bool) or not isinstance(finding_cap, int) or finding_cap <= 0:
        finding_cap = DEFAULT_FINDING_CAP

    # --- Step 1: read anti-relitigation preamble ---
    preamble_path = os.path.join(references_dir, "anti-relitigation-preamble.md")
    try:
        with open(preamble_path, "r", encoding="utf-8") as fh:
            preamble = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read anti-relitigation-preamble.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    # --- Step 2: read design-level attack checklist ---
    checklist_path = os.path.join(references_dir, "design-attack-checklist.md")
    try:
        with open(checklist_path, "r", encoding="utf-8") as fh:
            checklist = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read design-attack-checklist.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    # --- Step 3: scope / read-context block ---
    scope_block = _render_scope_block(manifest)

    # --- Step 4: three-ring traversal instruction (ring1_cap substituted) ---
    traversal = _TRAVERSAL_INTRO.replace(_RING1_CAP_TOKEN, str(ring1_cap))

    # --- Step 5 + 6: output contract + closing (tmp_path + finding_cap) ---
    effective_tmp = tmp_path if tmp_path is not None else _DEFAULT_TMP_PATH_TOKEN

    output_contract = _OUTPUT_CONTRACT.replace(
        "{tmp-path}", effective_tmp
    )
    output_contract = output_contract.replace("__FINDING_CAP__", str(finding_cap))

    closing = _CLOSING_REMINDER.replace("{tmp_path}", effective_tmp)
    closing = closing.replace("__FINDING_CAP__", str(finding_cap))

    parts = [
        preamble,
        checklist,
        scope_block,
        traversal,
        output_contract,
        closing,
    ]

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Internal: scope block renderer
# ---------------------------------------------------------------------------


def _render_scope_block(manifest):
    # type: (GrillScopeManifest) -> str
    """Render a human-readable read-context block from a GrillScopeManifest.

    Lists all paths the agent should read, marking optional ones that were not
    found.  The agent reads all files directly — this block tells it what to
    read, not what the files contain.
    """
    lines = [
        "## Read Context (your source material)",
        "",
        "Read these files before generating findings:",
        "",
        "  plan.md:           {0}".format(manifest.plan_path),
        "  spec.md:           {0}".format(manifest.spec_path),
    ]

    if manifest.handoff_path is not None:
        lines.append(
            "  handoff.json:      {0}".format(manifest.handoff_path)
        )
    else:
        lines.append(
            "  handoff.json:      (not present — upstream handoff not available)"
        )

    lines += [
        "  constitution.md:   {0}".format(manifest.constitution_path),
        "  CLAUDE.md:         {0}".format(manifest.claude_md_path),
        "",
        "Feature: {0}".format(manifest.feature_id),
    ]

    return "\n".join(lines)
