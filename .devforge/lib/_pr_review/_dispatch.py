"""Brief assembler for pr_review_helper (PR-REVIEW Step 8).

`run(target, pr_number, devforge_dir)` is the Phase 6 entry point.

It reads state.json (populated by intake + detect-smells + compute-blast-radius
+ bundle-context + import-handoffs + check-scope-drift), assembles a fat
reviewer brief as Markdown, writes it atomically to
  <target>/<devforge_dir>/pr-reviews/<pr_number>/brief.md
and emits a summary JSON dict.

## Responsibility boundary

This helper ASSEMBLES the brief — it does NOT invoke cavecrew-reviewer or any
LLM / MCP tool. The LLM (orchestrator) is responsible for:
  1. Reading this module's JSON output (or brief.md) from stdout.
  2. Dispatching cavecrew-reviewer via the Task tool.
  3. Parsing findings from the reviewer's output.
  4. Appending findings to state.findings in state.json.

## Brief structure (canonical section order)

  # PR Review Brief — PR #N
  ## Metadata
  ## Ticket text
  ## Linked issues
  ## Diff
  ## Code-smell findings (Step 4)
  ## Blast-radius probe specs (Step 5)
  ## Scope-drift bullets (Step 7)
  ## Context bundle (Step 6)
  ## Reviewer instructions
  ## Notes

## Content caps (module constants)

  _DIFF_CAP            = 80_000   chars — excerpt: first 40K + marker + last 40K
  _CONSTITUTION_CAP    = 30_000   chars
  _CONCERN_CAP         =  5_000   chars per overview / architecture content
  _HANDOFF_CAP         =  2_000   chars per handoff excerpt
  _PLAN_INLINE_CAP     =    300   chars inline per plan file (brief bullet)
  _ADR_INLINE_CAP      =    200   chars inline per ADR (brief bullet)
  _BRIEF_TOTAL_TARGET  = 100_000  chars — not a hard cut; sections carry their
                                  own caps to stay within this budget

## Re-invocation semantics

Running dispatch-review is idempotent: it always regenerates brief.md from the
current state. An existing brief.md is overwritten atomically.

## TODO(Step 8+): _write_state is now 5 copies in the package:
  _intake.py, _blast.py, _bundle.py, _handoff_import.py, _scope_drift.py.
  Consolidate to _state.py.write_state when the next verb would create a 6th.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, Optional

from ._state import PRReviewState, state_path


# ---------------------------------------------------------------------------
# Content-cap constants.
# ---------------------------------------------------------------------------

_DIFF_CAP = 80_000
_CONSTITUTION_CAP = 30_000
_CONCERN_CAP = 5_000
_HANDOFF_CAP = 2_000
_PLAN_INLINE_CAP = 300
_ADR_INLINE_CAP = 200
_BRIEF_TOTAL_TARGET = 100_000

_TICKET_TEXT_CAP = 20_000
_DIFF_HALF = _DIFF_CAP // 2  # 40_000

_BRIEF_FILENAME = "brief.md"


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _truncate(text: str, cap: int, marker: str = "... [truncated]") -> str:
    """Return text unchanged if len <= cap, else text[:cap] + marker.

    Args:
        text:   Input string.
        cap:    Maximum character count (including marker).
        marker: Suffix to append when truncation occurs.

    Returns:
        Original string if len(text) <= cap, otherwise text[:cap] + marker.
    """
    if len(text) <= cap:
        return text
    return text[:cap] + marker


def _excerpt_diff(diff_text: str, cap: int = _DIFF_CAP) -> str:
    """Return diff_text, excerpting middle section if over cap.

    Excerpt strategy: first cap//2 chars + marker + last cap//2 chars.

    Args:
        diff_text: Raw unified diff string.
        cap:       Total character budget.

    Returns:
        diff_text unchanged if len <= cap; otherwise first half + marker + last half.
    """
    if len(diff_text) <= cap:
        return diff_text
    half = cap // 2
    return (
        diff_text[:half]
        + "\n... [truncated mid-diff] ...\n"
        + diff_text[-half:]
    )


# ---------------------------------------------------------------------------
# Section assemblers.
# ---------------------------------------------------------------------------


def _section_metadata(state: PRReviewState) -> str:
    """Render the ## Metadata section.

    Fields sourced from state (all available after intake):
      - repo       -> owner/repo
      - pr_number  -> used to derive PR URL from state.repo
      - pr_body    -> not used here (title not stored in state)
      - diff       -> count diff --git a/ lines as proxy for files changed

    PR title and URL are derived when derivable; otherwise "(not available)".
    Additions / deletions are not stored in state — shown as "(not available)".
    """
    repo = state.repo or "(not available)"
    pr_number = state.pr_number

    # Derive URL from repo + pr_number if both are available.
    if state.repo and state.pr_number:
        pr_url = "https://github.com/{repo}/pull/{num}".format(
            repo=state.repo, num=state.pr_number
        )
    else:
        pr_url = "(not available)"

    # Count files: parse "diff --git" header lines from diff.
    files_changed = state.diff.count("\ndiff --git ") + (
        1 if state.diff.startswith("diff --git ") else 0
    )
    files_changed_str = str(files_changed) if files_changed else "(not available)"

    lines = [
        "## Metadata",
        "",
        "- **Repo**: {0}".format(repo),
        "- **PR title**: (not available — not stored in state)",
        "- **PR URL**: {0}".format(pr_url),
        "- **Files changed**: {0}".format(files_changed_str),
        "- **Additions**: (not available) / **Deletions**: (not available)",
        "- **Reviewer**: cavecrew-reviewer (anti-slop + blast-aware + drift-aware mode)",
        "- **Author assumption**: time-constrained; possibly LLM-assisted;"
        " flag laziness + hallucination + scope drift",
        "",
    ]
    return "\n".join(lines)


def _section_ticket_text(state: PRReviewState) -> str:
    """Render the ## Ticket text section.

    Truncates at _TICKET_TEXT_CAP with a marker.
    Shows placeholder when ticket_text is empty.
    """
    lines = ["## Ticket text", ""]
    if state.ticket_text:
        text = _truncate(
            state.ticket_text,
            _TICKET_TEXT_CAP,
            marker="\n... [truncated at {cap} chars] ...".format(cap=_TICKET_TEXT_CAP),
        )
        lines.append(text)
    else:
        lines.append("_No ticket text provided._")
    lines.append("")
    return "\n".join(lines)


def _section_linked_issues(state: PRReviewState) -> str:
    """Render the ## Linked issues section.

    Each issue URL on its own bullet. Shows placeholder when list is empty.
    """
    lines = ["## Linked issues", ""]
    if state.linked_issues:
        for url in state.linked_issues:
            lines.append("- {0}".format(url))
    else:
        lines.append("_None._")
    lines.append("")
    return "\n".join(lines)


def _section_diff(state: PRReviewState, cap: int = _DIFF_CAP) -> str:
    """Render the ## Diff section.

    Applies excerpt strategy if diff exceeds cap.
    Shows placeholder when diff is empty.
    """
    lines = ["## Diff", ""]
    if state.diff:
        excerpted = _excerpt_diff(state.diff, cap=cap)
        lines.append(excerpted)
    else:
        lines.append("_No diff available._")
    lines.append("")
    return "\n".join(lines)


def _section_smells(state: PRReviewState) -> str:
    """Render the ## Code-smell findings (Step 4) section.

    Each smell formatted as: - **[severity]** `name` @ `location` — evidence
    Shows placeholder when smells list is empty.
    """
    lines = ["## Code-smell findings (Step 4)", ""]
    if not state.smells:
        lines.append("_No smells detected._")
    else:
        for smell in state.smells:
            severity = smell.get("severity", "low")
            name = smell.get("name", "(unknown)")
            location = smell.get("location", "*")
            evidence = smell.get("evidence", "")
            lines.append(
                "- **[{sev}]** `{name}` @ `{loc}` — {ev}".format(
                    sev=severity,
                    name=name,
                    loc=location,
                    ev=evidence,
                )
            )
    lines.append("")
    return "\n".join(lines)


def _section_blast(state: PRReviewState) -> str:
    """Render the ## Blast-radius probe specs (Step 5) section.

    Unfilled probes render as TODO for the reviewer LLM with CBM hints.
    Filled probes render as resolved data (callers, callees, data-flow, tests).
    Shows placeholder when blast list is empty.
    """
    lines = ["## Blast-radius probe specs (Step 5)", ""]
    if not state.blast:
        lines.append("_No blast-radius probe specs extracted._")
        lines.append("")
        return "\n".join(lines)

    for probe in state.blast:
        symbol = probe.get("symbol", "(unknown)")
        kind = probe.get("kind", "")
        language = probe.get("language", "")
        file_path = probe.get("file", "")
        filled = probe.get("filled", False)
        hints = probe.get("mcp_hints") or {}

        if not filled:
            # Render as TODO.
            header = "### `{sym}` ({kind}, {lang}) — `{file}`".format(
                sym=symbol, kind=kind, lang=language, file=file_path
            )
            lines.append(header)
            lines.append(
                "- `mcp_hints.trace_path_in = {sym}` → run"
                " `mcp__codebase-memory-mcp__trace_path`"
                " (mode=calls, direction=inbound)".format(sym=hints.get("trace_path_in", symbol))
            )
            lines.append(
                "- `mcp_hints.trace_path_out = {sym}` → trace_path"
                " (mode=calls, direction=outbound)".format(sym=hints.get("trace_path_out", symbol))
            )
            lines.append(
                "- `data_flow = {sym}` → trace_path (mode=data_flow)".format(
                    sym=hints.get("data_flow", symbol)
                )
            )
            lines.append(
                "- Surface callers/callees/data-flow targets;"
                " flag fan-out > N (suggest threshold from constitution if available)"
            )
        else:
            # Render as resolved.
            callers = probe.get("callers") or []
            callees = probe.get("callees") or []
            data_flow_targets = probe.get("data_flow_targets") or []
            tests_referencing = probe.get("tests_referencing") or []
            header = "### `{sym}` — `{file}` (resolved)".format(
                sym=symbol, file=file_path
            )
            lines.append(header)
            lines.append(
                "- Callers: {0}".format(", ".join(callers) if callers else "(none)")
            )
            lines.append(
                "- Callees: {0}".format(", ".join(callees) if callees else "(none)")
            )
            lines.append(
                "- Data-flow targets: {0}".format(
                    ", ".join(data_flow_targets) if data_flow_targets else "(none)"
                )
            )
            lines.append(
                "- Tests referencing: {0}".format(
                    ", ".join(tests_referencing) if tests_referencing else "(none)"
                )
            )
        lines.append("")

    return "\n".join(lines)


def _section_drift(state: PRReviewState) -> str:
    """Render the ## Scope-drift bullets (Step 7) section.

    Renders all bullets from state.drift["bullets"].
    If coverage_matrix is populated (drift["filled"] is True),
    renders coverage status per bullet after the bullet list.
    Appends separator + reviewer instructions for coverage fill.
    Shows placeholder when drift dict is empty or bullets list is empty.
    """
    lines = ["## Scope-drift bullets (Step 7)", ""]

    drift = state.drift or {}
    bullets = drift.get("bullets") or []

    if not bullets:
        lines.append("_No scope-drift bullets extracted._")
        lines.append("")
        return "\n".join(lines)

    for bullet in bullets:
        b_id = bullet.get("id", "?")
        extracted_via = bullet.get("extracted_via", "")
        source = bullet.get("source", "")
        text = bullet.get("text", "")
        lines.append(
            "- **{id}** (`{via}` from `{src}`) — {text}".format(
                id=b_id, via=extracted_via, src=source, text=text
            )
        )

    # Coverage matrix (filled only when drift["filled"] is True).
    filled = drift.get("filled", False)
    coverage_matrix = drift.get("coverage_matrix") or []

    if filled and coverage_matrix:
        lines.append("")
        lines.append("**Coverage status:**")
        lines.append("")
        for entry in coverage_matrix:
            bullet_id = entry.get("bullet_id", "?")
            status = entry.get("status", "unknown")
            evidence = entry.get("evidence", "")
            confidence = entry.get("confidence") or 0.0
            lines.append(
                "- **{id}**: {status} (confidence={conf:.1f}) — {ev}".format(
                    id=bullet_id,
                    status=status,
                    conf=float(confidence),
                    ev=evidence,
                )
            )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "> **Reviewer task**: for each bullet without a coverage entry, locate diff"
        " evidence and assess satisfied/partial/missing."
    )
    lines.append(
        "> Also list `scope_creep_files`: diff files NOT mapped to any bullet."
    )
    lines.append("")
    return "\n".join(lines)


def _section_bundle(
    state: PRReviewState,
    caps: Optional[Dict[str, int]] = None,
) -> str:
    """Render the ## Context bundle (Step 6) section.

    Sub-sections in order:
      1. Universal constitution
      2. Project constitute.json
      3. Concern docs
      4. ADRs (first 10)
      5. Repo-root PLAN files (first 5)
      6. Imported research handoffs

    caps: optional override dict for {
        'constitution': int,
        'concern': int,
        'handoff': int,
        'plan': int,
        'adr': int,
    }
    Falls back to module constants when key absent.
    """
    if caps is None:
        caps = {}

    c_constitution = caps.get("constitution", _CONSTITUTION_CAP)
    c_concern = caps.get("concern", _CONCERN_CAP)
    c_handoff = caps.get("handoff", _HANDOFF_CAP)
    c_plan = caps.get("plan", _PLAN_INLINE_CAP)
    c_adr = caps.get("adr", _ADR_INLINE_CAP)

    bundle = state.bundle or {}
    lines = ["## Context bundle (Step 6)", ""]

    # --- 1. Universal constitution ---
    lines.append("### Universal constitution")
    lines.append("")
    constitution_content = bundle.get("constitution_md_content") or ""
    constitution_path = bundle.get("constitution_md") or ""
    if constitution_content:
        truncated = _truncate(constitution_content, c_constitution)
        lines.append(truncated)
        if constitution_path:
            lines.append("")
            lines.append("_(Full path: {0})_".format(constitution_path))
    else:
        lines.append("_Not present._")
    lines.append("")

    # --- 2. Project constitute.json ---
    lines.append("### Project constitute.json")
    lines.append("")
    constitute_json = bundle.get("constitute_json")
    if constitute_json is not None:
        constitute_str = json.dumps(constitute_json, indent=2)
        truncated = _truncate(constitute_str, 5000)
        lines.append("```json")
        lines.append(truncated)
        lines.append("```")
    else:
        lines.append("_not present_")
    lines.append("")

    # --- 3. Concern docs ---
    lines.append("### Concern docs")
    lines.append("")
    concern_docs = bundle.get("concern_docs") or []
    if concern_docs:
        for doc in concern_docs:
            concern = doc.get("concern", "(unknown)")
            lines.append("#### `{0}`".format(concern))
            overview_path = doc.get("overview_path", "")
            overview_content = doc.get("overview_content", "")
            arch_path = doc.get("architecture_path", "")
            arch_content = doc.get("architecture_content", "")
            lines.append(
                "- overview.md (`{0}`):".format(overview_path)
            )
            if overview_content:
                lines.append("  " + _truncate(overview_content, c_concern).replace("\n", "\n  "))
            else:
                lines.append("  _(empty)_")
            lines.append(
                "- architecture.md (`{0}`):".format(arch_path)
            )
            if arch_content:
                lines.append("  " + _truncate(arch_content, c_concern).replace("\n", "\n  "))
            else:
                lines.append("  _(empty)_")
            lines.append("")
    else:
        lines.append("_None._")
        lines.append("")

    # --- 4. ADRs (first 10) ---
    lines.append("### ADRs")
    lines.append("")
    adrs = (bundle.get("adrs") or [])[:10]
    if adrs:
        for adr in adrs:
            filename = adr.get("filename", "(unknown)")
            path = adr.get("path", "")
            content = adr.get("content", "")
            lines.append("- **{0}** (`{1}`): {2}".format(
                filename, path, content[:c_adr].replace("\n", " ")
            ))
    else:
        lines.append("_None._")
    lines.append("")

    # --- 5. PLAN files (first 5) ---
    lines.append("### Repo-root PLAN files (in-flight intent)")
    lines.append("")
    plan_files = (bundle.get("plan_files") or [])[:5]
    if plan_files:
        for plan in plan_files:
            name = plan.get("name", "(unknown)")
            path = plan.get("path", "")
            content = plan.get("content", "")
            lines.append("- **{0}** (`{1}`): {2}".format(
                name, path, content[:c_plan].replace("\n", " ")
            ))
    else:
        lines.append("_None._")
    lines.append("")

    # --- 6. Research handoffs ---
    lines.append("### Imported research handoffs")
    lines.append("")
    research_handoffs = bundle.get("research_handoffs") or []
    if research_handoffs:
        for handoff in research_handoffs:
            slug = handoff.get("slug", "(unknown)")
            date = handoff.get("date", "")
            verdict = handoff.get("verdict", "")
            mode = handoff.get("mode", "")
            matched_via = handoff.get("matched_via", "")
            excerpt = handoff.get("content_excerpt", "")
            lines.append(
                "- **{slug}** ({date}) verdict={verdict}, mode={mode},"
                " matched_via={matched_via}".format(
                    slug=slug,
                    date=date,
                    verdict=verdict,
                    mode=mode,
                    matched_via=matched_via,
                )
            )
            if excerpt:
                truncated_excerpt = _truncate(excerpt, c_handoff)
                lines.append(
                    "  Excerpt (first {cap} chars): {text}".format(
                        cap=c_handoff,
                        text=truncated_excerpt.replace("\n", " "),
                    )
                )
            lines.append("")
    else:
        lines.append("_None._")
        lines.append("")

    return "\n".join(lines)


def _section_instructions(brief_size_chars: int) -> str:
    """Render the ## Reviewer instructions section.

    Embeds the brief size and finding schema. Includes VERBATIM copy instruction
    so the orchestrator LLM knows to copy this section into the cavecrew-reviewer
    dispatch (do not summarize or paraphrase).
    """
    lines = [
        "## Reviewer instructions",
        "",
        "You are reviewing a PR via the cavecrew-reviewer agent. Your job:",
        "",
        "1. **Compare diff against**:",
        "   - Universal constitution rules (SOLID/DRY/KISS, helper-owns-shape,"
        " no-escape-hatch, etc.)",
        "   - Project-specific overrides from constitute.json",
        "   - In-flight intent in PLAN files",
        "   - Prior research handoffs for same area",
        "",
        "2. **Use code-smell findings as PRE-FLAGGED risks** — every entry under"
        ' "Code-smell findings" already pre-extracted via deterministic heuristics.'
        " Confirm or refute each with reasoning + cite which heuristic.",
        "",
        "3. **Populate blast-radius probe specs** — for each probe spec with"
        " `filled=False`, dispatch CBM `trace_path`"
        " (via `mcp__codebase-memory-mcp__trace_path`) per hint;"
        " surface callers/callees; flag high fan-out + cross-concern reach.",
        "",
        "4. **Assess scope drift** — for each bullet in `state.drift.bullets`,"
        " locate diff evidence; assess `satisfied | partial | missing`."
        " Identify files in diff NOT mapped to any bullet (scope creep).",
        "",
        "5. **Findings format** (append each to `state.findings`):",
        "   ```python",
        "   {",
        '     "severity": "high|medium|low|nit",',
        '     "location": "file:line OR concern-name",',
        '     "category": "smell|blast|drift|convention|hallucination|missing-test",',
        '     "evidence": "<≤300 char verbatim quote from diff or prior heuristic>",',
        '     "fix_hint": "<≤200 char suggested fix>",',
        '     "source_heuristic": "<heuristic name if from smells / null otherwise>"',
        "   }",
        "   ```",
        "",
        "6. **Bias** — treat author as time-constrained. Flag laziness, hallucination,"
        " duplication, scope drift, missing tests. Skip nits unless they change meaning."
        " Be ruthless on substance.",
        "",
        "7. **Citation discipline** — every finding cites source layer: constitution /"
        " overlay / plan / ADR / smells-heuristic / blast-data.",
        "",
        "## Notes",
        "",
        "- This brief is ~{size} chars. cavecrew-reviewer must consume it in one read.".format(
            size=brief_size_chars
        ),
        "- If brief exceeds {target} chars, sections are truncated with"
        " `... [truncated]` markers — full data in state.json.".format(
            target=_BRIEF_TOTAL_TARGET
        ),
        "- After reviewing, append findings to state.findings"
        " (direct json.dump or via future `record-finding` verb).",
        "- Copy this brief VERBATIM into your next user-facing message as a fenced"
        " code block (do not summarize or paraphrase) when dispatching cavecrew-reviewer.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Atomic brief writer.
# ---------------------------------------------------------------------------


def _write_brief(brief_path: str, content: str) -> None:
    """Write brief Markdown to brief_path atomically.

    Uses tempfile.mkstemp in the same directory, then os.replace.

    Args:
        brief_path: Absolute path to the destination brief.md.
                    Parent directory must already exist.
        content:    Markdown string to write.

    Raises:
        OSError: if write or rename fails.
    """
    brief_dir = os.path.dirname(brief_path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="brief-", suffix=".tmp.md", dir=brief_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, brief_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(
    target: str,
    pr_number: int,
    devforge_dir: str = ".devforge",
) -> dict:
    """Assemble reviewer brief from state, write brief.md, return summary dict.

    Args:
        target:       Absolute (or relative) path to the reviewer's local repo root.
        pr_number:    PR number (positive int).
        devforge_dir: Name of the devforge directory under target (default ".devforge").

    Returns:
        dict with keys: status, state_path, brief_path, brief_size_chars,
        sections_included, smells_count, blast_probes_count, drift_bullets_count,
        bundle_sources_count, next_action.

    Raises:
        ValueError: if state.json does not exist or cannot be parsed.
        OSError:    if brief.md cannot be written.
    """
    abs_target = os.path.abspath(target)
    abs_devforge = os.path.join(abs_target, devforge_dir)
    sp = state_path(abs_devforge, pr_number)

    if not os.path.exists(sp):
        raise ValueError(
            "no state.json at {path}; run `intake` first".format(path=sp)
        )

    try:
        with open(sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            "cannot read state.json at {path}: {exc}".format(path=sp, exc=exc)
        ) from exc

    try:
        state = PRReviewState(**state_dict)
    except TypeError as exc:
        raise ValueError(
            "state schema error in {path}: {exc}".format(path=sp, exc=exc)
        ) from exc

    # Assemble sections.
    header = "# PR Review Brief — PR #{num}\n\n".format(num=pr_number)
    metadata = _section_metadata(state)
    ticket = _section_ticket_text(state)
    issues = _section_linked_issues(state)
    diff = _section_diff(state)
    smells = _section_smells(state)
    blast = _section_blast(state)
    drift = _section_drift(state)
    bundle = _section_bundle(state)

    # Compute instructions placeholder size before final assembly.
    # Use 0 initially; replace after final size is known.
    instructions_placeholder = _section_instructions(0)

    # Concatenate draft brief (without final instructions size).
    draft = (
        header
        + metadata + "\n"
        + ticket + "\n"
        + issues + "\n"
        + diff + "\n"
        + smells + "\n"
        + blast + "\n"
        + drift + "\n"
        + bundle + "\n"
        + instructions_placeholder
    )

    # Compute final size with accurate char count in instructions.
    instructions_final = _section_instructions(len(draft))
    brief_content = (
        header
        + metadata + "\n"
        + ticket + "\n"
        + issues + "\n"
        + diff + "\n"
        + smells + "\n"
        + blast + "\n"
        + drift + "\n"
        + bundle + "\n"
        + instructions_final
    )
    brief_size_chars = len(brief_content)

    # Determine brief output path.
    from ._state import _PR_REVIEWS_DIR
    pr_dir = os.path.join(abs_devforge, _PR_REVIEWS_DIR, str(pr_number))
    os.makedirs(pr_dir, exist_ok=True)
    brief_path = os.path.join(pr_dir, _BRIEF_FILENAME)

    _write_brief(brief_path, brief_content)

    # Build summary metrics.
    bundle_dict = state.bundle or {}
    bundle_sources_count = {
        "constitution_md": bool(bundle_dict.get("constitution_md_content")),
        "constitute_json": bundle_dict.get("constitute_json") is not None,
        "concern_docs": len(bundle_dict.get("concern_docs") or []),
        "adrs": len(bundle_dict.get("adrs") or []),
        "plan_files": len(bundle_dict.get("plan_files") or []),
        "research_handoffs": len(bundle_dict.get("research_handoffs") or []),
    }

    drift_dict = state.drift or {}
    drift_bullets_count = len(drift_dict.get("bullets") or [])

    return {
        "status": "ok",
        "state_path": sp,
        "brief_path": brief_path,
        "brief_size_chars": brief_size_chars,
        "sections_included": [
            "metadata",
            "ticket_text",
            "linked_issues",
            "diff",
            "smells",
            "blast",
            "drift",
            "bundle",
            "instructions",
            "notes",
        ],
        "smells_count": len(state.smells),
        "blast_probes_count": len(state.blast),
        "drift_bullets_count": drift_bullets_count,
        "bundle_sources_count": bundle_sources_count,
        "next_action": (
            "LLM: dispatch cavecrew-reviewer via Task tool with brief.md contents;"
            " parse findings; append to state.findings field in state.json"
        ),
    }
