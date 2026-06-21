"""Scope resolution and agent-brief assembly for audit_helper (Phase 2).

resolve_scope  — resolve the actual file list + metadata from a mode_result dict
render_scope_block  — human-readable summary of a scope result
render_agent_brief  — assemble per-agent audit instruction block

Module constants (_FOCUS_BLOCKS, _OUTPUT_CONTRACT, _CLOSING_REMINDER) are
copied VERBATIM from the draft audit.md Phase 3 sections 3.1, 3.2, 3.3.

Stdlib only.  Targets Python 3.8+.
"""

from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional

from ._hotspot import enumerate_candidates


# ---------------------------------------------------------------------------
# Module constants — VERBATIM from draft §3.1 / §3.2 / §3.3
# ---------------------------------------------------------------------------

_FOCUS_BLOCKS = {
    "code-reviewer": (
        "Your primary mission in ADVERSARIAL MODE: find naming-vs-behavior "
        "mismatches, lying comments, dead branches, off-by-one errors, inverted "
        "conditions, copy-paste bugs, and scope-creep residue. Constitution "
        "violations remain Critical and are never downgraded. "
        "You also own language/framework best-practice violations and "
        "type-safety suppression — tag those findings `Category: best_practice`, "
        "and mislogic findings `Category: mislogic`."
    ),
    "architect": (
        "Your primary mission in ADVERSARIAL MODE: find cross-module "
        "contradictions, layering drift, SOLID violations that compound across "
        "files, contradictory domain rules in different files, and dependency "
        "direction violations. You are looking for the \"two files that can't "
        "both be right\" situations. "
        "Tag layering/SOLID/god-component findings `Category: system_design` "
        "and copy-paste/diverged-code findings `Category: duplication`."
    ),
    "qa-reviewer": (
        "Your primary mission in ADVERSARIAL MODE: treat untested branches as "
        "**logic blind spots** where mislogic hides. Do **NOT** write tests — "
        "you are a read-only test-quality assessor. "
        "Report each significant untested branch as an audit finding with "
        "severity based on how much domain logic is uncovered.\n"
        "\n"
        "**Branch scope (strict)**: only consider untested **public functions "
        "and methods in business-logic modules** (services, controllers, use "
        "cases, domain logic). Do NOT report: private helpers, pure utility "
        "functions, type-only files, configuration files, generated code, or "
        "files matching `*.test.*` / `*.spec.*`.\n"
        "\n"
        "If the project has zero tests, return a single High finding: "
        "`\"No tests found — entire codebase is a logic blind spot\"` and stop. "
        "Tag these findings `Category: blind_spot`."
    ),
    "security-reviewer": (
        "Your primary mission in ADVERSARIAL MODE: scan for security regressions "
        "and drift in code that has **NOT** been touched in recent features. You "
        "are the second line of defense after per-feature `/review`. Assume "
        "nothing is safe just because it is old. "
        "Tag these findings `Category: security`."
    ),
}  # type: Dict[str, str]

_OUTPUT_CONTRACT = """\
Each agent writes its findings to `audits/.tmp-{agent-name}.md` using this **fixed parseable format**. The parent command will regex-parse these headings, so deviation breaks the pipeline.

````
# Agent: {agent-name}
# Status: complete
# Finding count: N

## Finding 1
Severity: Critical | High | Medium | Info
File: path/to/file.ext
Line: 42
Pattern: <one-line pattern name, e.g. "Naming lie">
Category: mislogic | system_design | best_practice | duplication | security | blind_spot
Confidence: Certain | Likely | Speculative
Evidence:
```
<verbatim quoted code or comment, copy-pasted from the file, no edits>
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

Category glossary: `mislogic` — logic contradictions, lying names/comments, control-flow bugs, dead branches; `system_design` — layering/dependency-direction violations, SOLID-at-scale, god components, business/data logic in presentation; `best_practice` — language/framework idiom & type-safety violations (casts that launder a real type gap, untyped boundaries, framework reactivity/lifecycle misuse, perf-idiom smells); `duplication` — copy-pasted or diverged logic that should be shared; `security` — security regressions / drift; `blind_spot` — untested business-logic branch (logic blind spot).

**Hard rules for the agent**:
- **Every finding MUST declare exactly one `Category:`** from the list above. If unsure, use `mislogic`.
- **Enumerate every real, grounded instance — do NOT collapse a recurring pattern to one example.** If a pattern (untyped prop, `as any`/cast laundering, watcher-that-should-be-computed, a duplicated/diverged block, a swallowed error) appears in N places, report all N as separate findings, each with its own verbatim quote. A missed instance is a missed bug; recall matters more than brevity. Cap: __FINDING_CAP__ findings total — only if you genuinely exceed it, drop the lowest-confidence.
- **Every finding MUST have a verbatim Evidence block.** No quote = no finding. The parent will validate this and discard ungrounded findings (see Phase 4).
- **The Evidence block must be a literal copy from the file.** Do not paraphrase, do not abbreviate, do not insert `...`. If the relevant code is more than 20 lines, cite the most important 5–10 lines. If you cannot locate and copy the EXACT bytes from the file, DROP the finding — an approximate or remembered quote fails Phase-4 validation and wastes a finding slot.
- **The Line field must point to the first line of the Evidence block in the actual file.**
- If the agent fails partway, it must still write a temp file with `# Status: failed` and a `# Reason: <message>` line, so Phase 4 can detect failure.
- If the agent finds nothing, write a temp file with `# Status: complete` and `# Finding count: 0`. Empty file ≠ failure."""

_CLOSING_REMINDER = (
    "REMEMBER: ADVERSARIAL AUDIT MODE is in effect. Report only defects you can "
    "demonstrate from verbatim quotes of the actual code — a real quote of correct "
    "code is not a finding; do not assume a bug exists. Fabrications are "
    "forbidden. Enumerate every real instance you can quote exactly, up to "
    "__FINDING_CAP__ — do not stop at one example of a recurring pattern, and drop "
    "any finding whose quote you cannot copy verbatim from the file. "
    "Every finding needs a verbatim Evidence quote and a Confidence tier. Do not "
    "soften. Critical of code, not people."
)

# Dirs skipped by the non-git filesystem fallback walker.
_IGNORE_DIRS = frozenset((
    "node_modules", "dist", "build", "__pycache__",
    ".venv", ".git", "vendor",
))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_ls_files_stdout(stdout):
    # type: (str) -> List[str]
    """Parse stdout from git ls-files into a sorted list of non-empty paths."""
    result = []
    for line in stdout.splitlines():
        fp = line.strip()
        if fp:
            result.append(fp)
    result.sort()
    return result


def _git_ls_files_dir(repo_root, subdir, timeout=60):
    # type: (str, str, int) -> Optional[List[str]]
    """Run git ls-files for a subdir under repo_root.

    Returns a sorted list of workspace-relative paths, or None if git fails
    or is not on PATH.  Empty list (zero files resolved) is distinct from None
    (git unavailable/error).

    When the plain ``git ls-files`` call returns an empty list (rc 0, zero
    files), the directory may contain or be contained in a nested independent
    git repository (its own ``.git`` dir or gitlink file) that the superproject
    does not track.  In that case nested-repo resolution is attempted:

    1. Walk the ancestors of ``subdir`` from just-under ``repo_root`` downward
       toward ``subdir`` (inclusive), checking whether each candidate dir ``A``
       has a ``.git`` entry (directory OR gitlink file — covers both independent
       repos and registered submodules).  The FIRST such ``A`` is the nested-repo
       root ``R``.
    2. If found, run ``git -C <repo_root/R> ls-files`` with the path of
       ``subdir`` relative to ``R``, parse the output with the same
       ``_parse_ls_files_stdout`` helper, then prefix each result with the
       workspace-relative path of ``R`` so callers receive workspace-relative
       paths.
    3. If no nested ``.git`` is found, or the nested ``git -C`` call fails for
       any reason (non-zero exit, FileNotFoundError, TimeoutExpired), the
       original empty list is returned — callers still see ``[]``, not ``None``.

    This handles independent nested repos — directories that own their own
    ``.git`` but are NOT registered as submodules of the workspace.
    Registered submodules are NOT handled here: plain ``git ls-files`` returns
    a non-empty gitlink entry for them (the submodule name, not its files), so
    the empty-result path is not reached for registered submodules.
    """
    cmd = ["git", "-C", repo_root, "ls-files", "--", subdir]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if proc.returncode != 0:
        return None

    plain_result = _parse_ls_files_stdout(proc.stdout)

    # Non-empty result: normal directory tracked by the superproject.
    if plain_result:
        return plain_result

    # Plain call returned [] — attempt nested-repo resolution.
    # Walk ancestors of subdir (relative to repo_root) from top downward,
    # looking for the first directory that owns its own .git entry.
    #
    # Build the list of candidate ancestor components.  For example, if
    # subdir is "a/b/c" the candidates are ["a", "a/b", "a/b/c"].
    parts = []
    current = subdir
    while True:
        head, tail = os.path.split(current)
        if tail:
            parts.append(current)
        if not tail or not head or head == current:
            break
        current = head
    # parts is innermost-first; reverse to walk outermost-first.
    parts.reverse()

    nested_root_rel = None  # workspace-relative path of the nested repo root
    for candidate_rel in parts:
        git_entry = os.path.join(repo_root, candidate_rel, ".git")
        if os.path.exists(git_entry):
            nested_root_rel = candidate_rel
            break

    if nested_root_rel is None:
        return plain_result  # no nested repo found → []

    nested_repo_abs = os.path.join(repo_root, nested_root_rel)
    # Compute the path of subdir relative to the nested repo root.
    # os.path.relpath handles the case where subdir == nested_root_rel
    # (returns "."), and deeper cases.
    sub_rel = os.path.relpath(
        os.path.join(repo_root, subdir),
        nested_repo_abs,
    )
    # Build the nested git -C command.  When sub_rel is "." (subdir IS the
    # nested root), pass no pathspec so ls-files lists all tracked files.
    if sub_rel == ".":
        nested_cmd = ["git", "-C", nested_repo_abs, "ls-files"]
    else:
        nested_cmd = ["git", "-C", nested_repo_abs, "ls-files", "--", sub_rel]

    try:
        nested_proc = subprocess.run(
            nested_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return plain_result  # [] — not None

    if nested_proc.returncode != 0:
        return plain_result  # [] — not None

    nested_files = _parse_ls_files_stdout(nested_proc.stdout)
    if not nested_files:
        return plain_result  # nested repo also empty → []

    # Prefix each path with the workspace-relative nested-root path so callers
    # receive workspace-relative paths (e.g. "nested/a.py", not "a.py").
    prefix = nested_root_rel.replace(os.sep, "/")
    result = sorted(
        prefix + "/" + fp.replace(os.sep, "/")
        for fp in nested_files
    )
    return result


def _walk_dir_fallback(dirpath):
    # type: (str) -> List[str]
    """Filesystem walk under dirpath, skipping dot-dirs and _IGNORE_DIRS.

    Returns sorted absolute paths to all non-directory files.  This is the
    degenerate path when git ls-files yields nothing (non-git dir or git error).
    """
    collected = []
    for root, dirs, files in os.walk(dirpath):
        # Prune ignored dirs in-place so os.walk skips them.
        dirs[:] = [
            d for d in dirs
            if d not in _IGNORE_DIRS and not d.startswith(".")
        ]
        for fname in files:
            collected.append(os.path.join(root, fname))
    collected.sort()
    return collected


def _git_uncommitted_files(repo_root, timeout=30):
    # type: (str, int) -> Optional[List[str]]
    """Return sorted, deduped workspace-relative paths of uncommitted changes.

    Combines ``git diff --name-only`` (unstaged) and
    ``git diff --cached --name-only`` (staged).  Returns None on git error.
    """
    paths = set()  # type: set
    for cached_flag in ([], ["--cached"]):
        cmd = ["git", "-C", repo_root, "diff", "--name-only"] + cached_flag
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        if proc.returncode != 0:
            return None

        for line in proc.stdout.splitlines():
            fp = line.strip()
            if fp:
                paths.add(fp)

    return sorted(paths)


# ---------------------------------------------------------------------------
# resolve_scope
# ---------------------------------------------------------------------------


def resolve_scope(mode_result, repo_root, hotspot_files=None):
    # type: (dict, str, Optional[List[str]]) -> dict
    """Resolve the actual file list and metadata from a mode_result dict.

    Args:
        mode_result:    Dict from resolve_mode (keys: mode, scope_arg,
                        uncommitted, top_n, scope_limit, line_range, ...).
        repo_root:      Absolute path to the git repo root.
        hotspot_files:  For mode=="hotspot": caller-supplied top-N file list.
                        Ignored for other modes.  None treated as empty list.

    Returns:
        dict with stable keys:
          scope_kind     — "broad" | "hotspot" | "file" | "directory" |
                           "uncommitted" | "error"
          pipeline       — "simplified" | "full"
          files          — sorted list of paths
          file_count     — int
          scope_limit    — int (from mode_result)
          scope_oversize — bool (Decision 11)
          line_range     — str | None
          error          — str | None
    """
    scope_limit = int(mode_result.get("scope_limit") or 200)
    line_range = mode_result.get("line_range")

    def _ok(scope_kind, pipeline, files):
        # type: (str, str, List[str]) -> dict
        sorted_files = sorted(files)
        count = len(sorted_files)
        oversize = (
            scope_kind in {"directory", "uncommitted"}
            and count > scope_limit
        )
        return {
            "scope_kind": scope_kind,
            "pipeline": pipeline,
            "files": sorted_files,
            "file_count": count,
            "scope_limit": scope_limit,
            "scope_oversize": oversize,
            "line_range": line_range,
            "error": None,
        }

    def _err(message):
        # type: (str) -> dict
        return {
            "scope_kind": "error",
            "pipeline": "full",
            "files": [],
            "file_count": 0,
            "scope_limit": scope_limit,
            "scope_oversize": False,
            "line_range": line_range,
            "error": message,
        }

    mode = mode_result.get("mode")

    # ---- broad ---------------------------------------------------------------
    if mode == "broad":
        try:
            files = enumerate_candidates(repo_root)
        except (FileNotFoundError, ValueError) as exc:
            return _err("enumerate_candidates failed: {0}".format(exc))
        return _ok("broad", "full", files)

    # ---- hotspot -------------------------------------------------------------
    if mode == "hotspot":
        files = list(hotspot_files) if hotspot_files else []
        return _ok("hotspot", "full", files)

    # ---- narrow --------------------------------------------------------------
    if mode == "narrow":
        uncommitted = bool(mode_result.get("uncommitted"))
        scope_arg = mode_result.get("scope_arg")

        if uncommitted:
            changed = _git_uncommitted_files(repo_root)
            if changed is None:
                return _err(
                    "git diff failed or git is not available; "
                    "cannot resolve uncommitted changes"
                )
            return _ok("uncommitted", "full", changed)

        if not scope_arg:
            return _err(
                "narrow mode requires scope_arg or uncommitted=True"
            )

        # Resolve scope_arg relative to repo_root if not absolute.
        if os.path.isabs(scope_arg):
            abs_path = scope_arg
        else:
            abs_path = os.path.join(repo_root, scope_arg)

        if os.path.isfile(abs_path):
            # Single file — simplified pipeline (Decision 10).
            rel = os.path.relpath(abs_path, repo_root)
            return _ok("file", "simplified", [rel])

        if os.path.isdir(abs_path):
            # Directory — Decision 9: git ls-files (tracked + non-gitignored).
            # git_files is None ONLY when git failed / is absent — in that case
            # fall back to a filesystem walk. An EMPTY list means git found no
            # files in this subtree (including after nested-repo resolution for
            # independent or submodule dirs); honor that as an empty result
            # rather than walking (which would pull in untracked / gitignored
            # junk and violate Decision 9's "tracked files only").
            rel_dir = os.path.relpath(abs_path, repo_root)
            git_files = _git_ls_files_dir(repo_root, rel_dir)
            if git_files is not None:
                return _ok("directory", "full", git_files)
            # Non-git fallback: walk filesystem (degenerate path).
            walked = _walk_dir_fallback(abs_path)
            # Return absolute paths converted to relative.
            rel_files = [os.path.relpath(p, repo_root) for p in walked]
            return _ok("directory", "full", rel_files)

        # scope_arg doesn't exist on disk.
        return _err(
            "scope_arg does not exist on disk: {0!r}".format(scope_arg)
        )

    # Unknown / None mode.
    return _err("unknown mode: {0!r}".format(mode))


# ---------------------------------------------------------------------------
# render_scope_block
# ---------------------------------------------------------------------------


def render_scope_block(scope_result, source_root):
    # type: (dict, str) -> str
    """Human-readable summary of a scope result.

    Includes scope kind, pipeline depth, file count, source root, and the
    file list (or a "(N files)" note when > 25).

    Args:
        scope_result: dict from resolve_scope.
        source_root:  repo / workspace root shown to the agent.

    Returns:
        Multi-line string describing the audit scope.
    """
    lines = []
    lines.append("=== Audit Scope ===")
    lines.append("Scope kind : {0}".format(scope_result.get("scope_kind", "?")))
    lines.append("Pipeline   : {0}".format(scope_result.get("pipeline", "?")))
    lines.append("File count : {0}".format(scope_result.get("file_count", 0)))
    lines.append("Source root: {0}".format(source_root))

    line_range = scope_result.get("line_range")
    if line_range:
        lines.append("Line range : {0}".format(line_range))

    oversize = scope_result.get("scope_oversize", False)
    if oversize:
        scope_limit = scope_result.get("scope_limit", 200)
        lines.append(
            "WARNING: scope exceeds limit ({0} files > {1} limit). "
            "Consider narrowing the scope.".format(
                scope_result.get("file_count", 0), scope_limit
            )
        )

    error = scope_result.get("error")
    if error:
        lines.append("ERROR: {0}".format(error))
        return "\n".join(lines)

    files = scope_result.get("files", [])
    lines.append("")
    if len(files) <= 25:
        lines.append("Files:")
        for f in files:
            lines.append("  {0}".format(f))
    else:
        lines.append("Files: ({0} files — list omitted; see scope JSON)".format(len(files)))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# render_agent_brief
# ---------------------------------------------------------------------------


def render_agent_brief(agent, references_dir, scope_block, source_root, extra_context="", finding_cap=30, tmp_path=None):
    # type: (str, str, str, str, str, int, Optional[str]) -> str
    """Assemble the per-agent audit instruction block.

    Assembly order (7 steps):
      1. Adversarial Preamble        (read verbatim from references_dir)
      2. Mislogic Checklist          (read verbatim from references_dir)
      3. Best-Practices Checklist    (read verbatim from references_dir)
      4. Per-agent focus block       (_FOCUS_BLOCKS[agent])
      5. Scope + source-root note + extra_context
      6. Output Contract             (_OUTPUT_CONTRACT)
      7. Closing mode reminder       (_CLOSING_REMINDER)  — MUST be last

    After assembling the parts, the ``__FINDING_CAP__`` token present in
    ``_OUTPUT_CONTRACT`` and ``_CLOSING_REMINDER`` is replaced with
    ``str(finding_cap)`` so the rendered brief contains the numeric cap value
    and the token never leaks to the agent.

    Args:
        agent:          One of the four audit agents (key in _FOCUS_BLOCKS).
        references_dir: Directory containing adversarial-preamble.md,
                        mislogic-checklist.md, and best-practices-checklist.md.
        scope_block:    Pre-rendered scope summary string (from render_scope_block).
        source_root:    Workspace / repo root label shown in the scope section.
        extra_context:  Optional orchestrator-supplied context (constitution /
                        MEMORY.md excerpts, recurring issues, etc.).
        finding_cap:    Maximum findings the agent should report (default: 30).
                        Substituted for the ``__FINDING_CAP__`` token in the brief.
                        Non-positive values fall back to 30.
        tmp_path:       Optional override for the agent findings write-path.
                        When None (default), the output contract uses the default
                        ``audits/.tmp-{agent-name}.md`` path (backward-compatible).
                        When provided, that literal string replaces every
                        occurrence of the default path in the output contract,
                        including the main write-path sentence and the
                        failure/empty-file instructions.  The value is emitted
                        verbatim — no normalization is applied.

    Returns:
        Multi-line string forming the agent instruction block.

    Raises:
        ValueError: if agent is not in _FOCUS_BLOCKS, or if a reference file
                    is missing or unreadable.
    """
    # Defensive: a bad cap value (0, negative, or wrong type) falls back to 30.
    if not isinstance(finding_cap, int) or finding_cap <= 0:
        finding_cap = 30
    if agent not in _FOCUS_BLOCKS:
        raise ValueError(
            "unknown agent {0!r}; must be one of {1}".format(
                agent, sorted(_FOCUS_BLOCKS.keys())
            )
        )

    preamble_path = os.path.join(references_dir, "adversarial-preamble.md")
    checklist_path = os.path.join(references_dir, "mislogic-checklist.md")

    try:
        with open(preamble_path, "r", encoding="utf-8") as fh:
            preamble = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read adversarial-preamble.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    try:
        with open(checklist_path, "r", encoding="utf-8") as fh:
            mislogic_checklist = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read mislogic-checklist.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    best_practices_path = os.path.join(references_dir, "best-practices-checklist.md")

    try:
        with open(best_practices_path, "r", encoding="utf-8") as fh:
            best_practices_checklist = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read best-practices-checklist.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    focus = _FOCUS_BLOCKS[agent]

    # scope_block (from render_scope_block) already carries the "Source root:"
    # line, so do NOT re-emit source_root here — it would duplicate the label.
    # The source_root parameter is retained for call-site symmetry and possible
    # future use, but is intentionally not appended to avoid the double line.
    scope_section_parts = [scope_block]
    if extra_context:
        scope_section_parts.append(extra_context)
    scope_section = "\n".join(scope_section_parts)

    # Build the output contract, optionally substituting the write-path.
    # When tmp_path is None, _OUTPUT_CONTRACT is used verbatim (default behavior,
    # backward-compatible: path reads `audits/.tmp-{agent-name}.md`).
    # When tmp_path is provided, replace every occurrence of the default
    # write-path token AND update the failure/empty-file instructions so all
    # path references in the contract point to the single provided path.
    if tmp_path is None:
        output_contract = _OUTPUT_CONTRACT
    else:
        output_contract = _OUTPUT_CONTRACT.replace(
            "audits/.tmp-{agent-name}.md",
            tmp_path,
        )
        output_contract = output_contract.replace(
            "write a temp file with",
            "write `{0}` with".format(tmp_path),
        )

    parts = [
        preamble,
        mislogic_checklist,
        best_practices_checklist,
        focus,
        scope_section,
        output_contract,
        _CLOSING_REMINDER,
    ]

    brief = "\n\n".join(parts)
    brief = brief.replace("__FINDING_CAP__", str(finding_cap))
    return brief
