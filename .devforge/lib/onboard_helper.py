#!/usr/bin/env python3
"""Onboard Helper for the /onboard command.

The onboard LLM (and its dispatched tech-writer subagents) calls this tool
to register documentation artifacts: per-package docs, per-concern docs,
the workspace architecture doc, and memory findings. The helper is the
*only* sanctioned path to write under docs/. Bulk-script-write is
unrepresentable in the API surface — this is the forcing function for
per-unit dispatch + per-concern decomposition.

Verbs:
  set                   Set a top-level scalar (e.g. mode = overwrite|merge|fresh)
  add-package-doc       Register one package's index.md content
  add-concern-doc       Register one concern doc inside a package
  add-architecture-doc  Register the workspace architecture.md (single call)
  add-memory-finding    Register one memory observation (multiple calls)
  status                Print machine-readable progress
  compose-onboard       Validate + atomically write all registered docs

Step 2.7 adds: cross-link existence + sigil hygiene. Final pair of
gates. Cross-link checks that markdown link targets resolve to docs
being written or existing files. Sigil hygiene rejects /<cmd> or
$<cmd> workflow command prefixes in docs (cross-runtime artifact rule).

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional


# ─── Paths ───────────────────────────────────────────────────────────────────
# The onboard command invokes this tool from the target project root.
# `.devforge/` is created by install.sh; we mkdir defensively for ad-hoc / test
# use (in load_state / save_state).

DEVFORGE_DIR = Path(".devforge")
STATE_FILE = DEVFORGE_DIR / ".onboard-state.json"
PROJECT_CONFIG = DEVFORGE_DIR / "project-config.json"
DOCS_DIR = Path("docs")
BASELINE_DIR = DEVFORGE_DIR / "baseline" / "docs"


# ─── Schema ──────────────────────────────────────────────────────────────────
# State persisted between invocations. Each invocation reads → mutates →
# writes back. compose-onboard consumes the final state and clears it.


@dataclass
class DocEntry:
    """Common shape for package / concern / architecture doc registrations."""
    content: str = ""
    block_count: int = 0
    ref_count: int = 0


@dataclass
class PackageDoc(DocEntry):
    """A package-level index.md registration."""
    unit: str = ""
    path: str = ""  # Source path relative to SOURCE_ROOT.


@dataclass
class ConcernDoc(DocEntry):
    """A concern-level doc registration nested within a package."""
    unit: str = ""
    concern: str = ""


@dataclass
class MemoryFinding:
    """One observation for .devforge/memory.md."""
    category: str = ""  # module-boundaries | dependency-warnings | complexity | inconsistencies
    unit: str = ""  # or 'workspace' for cross-cutting
    observation: str = ""


@dataclass
class OnboardState:
    """All registered onboard artifacts. Persisted as .devforge/.onboard-state.json."""
    mode: Optional[str] = None  # overwrite | merge | fresh
    package_docs: dict[str, PackageDoc] = field(default_factory=dict)  # keyed by unit name
    concern_docs: list[ConcernDoc] = field(default_factory=list)
    architecture_doc: Optional[DocEntry] = None
    memory_findings: list[MemoryFinding] = field(default_factory=list)


# ─── State R/W (atomic) ──────────────────────────────────────────────────────


def load_state() -> OnboardState:
    """Read state from STATE_FILE; return empty OnboardState if missing."""
    if not STATE_FILE.exists():
        return OnboardState()
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"onboard_helper: corrupt state file {STATE_FILE}: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    return _state_from_dict(raw)


def save_state(state: OnboardState) -> None:
    """Atomically write state to STATE_FILE via temp file + os.replace."""
    DEVFORGE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(state), indent=2, sort_keys=False)
    # Write to a sibling temp file in the same directory for atomic rename.
    fd, tmp_path = tempfile.mkstemp(
        prefix=".onboard-state-", suffix=".json", dir=str(DEVFORGE_DIR)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        # Clean up the temp file if rename failed.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def clear_state() -> None:
    """Remove the state file. Called by compose-onboard on success."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _state_from_dict(raw: dict[str, Any]) -> OnboardState:
    """Reconstruct OnboardState from the JSON-loaded dict.

    Hand-written rather than asdict-inverse because dataclass nesting needs
    explicit reconstruction for list[X] / dict[str, X] fields.
    """
    state = OnboardState(mode=raw.get("mode"))

    pkg_docs_raw = raw.get("package_docs") or {}
    for unit, doc_raw in pkg_docs_raw.items():
        state.package_docs[unit] = PackageDoc(**doc_raw)

    for c_raw in raw.get("concern_docs") or []:
        state.concern_docs.append(ConcernDoc(**c_raw))

    arch_raw = raw.get("architecture_doc")
    if arch_raw is not None:
        state.architecture_doc = DocEntry(**arch_raw)

    for m_raw in raw.get("memory_findings") or []:
        state.memory_findings.append(MemoryFinding(**m_raw))

    return state


# ─── Subcommand handlers ─────────────────────────────────────────────────────


def _not_implemented(name: str) -> int:
    print(f"onboard_helper: '{name}' not implemented yet (current step skeleton).", file=sys.stderr)
    return 2


def cmd_set(args: argparse.Namespace) -> int:
    """Update a top-level scalar on the state."""
    state = load_state()
    field_name = args.field
    if field_name == "mode":
        state.mode = args.value
    else:
        # No validation gate yet (lands in Phase 2). Accept any field name and
        # set it as a generic attribute. Currently only `mode` is recognized;
        # unknown fields print a warning but do not fail.
        print(
            f"onboard_helper: warning — unknown top-level field '{field_name}'. "
            f"Currently only 'mode' is recognized. Stored anyway for forward compat.",
            file=sys.stderr,
        )
        # Use setattr for forward-compat with future top-level fields.
        setattr(state, field_name, args.value)
    save_state(state)
    print(f"set {field_name} = {args.value}")
    return 0


def _check_block_ref_equality(label: str, block_count: int, ref_count: int) -> Optional[int]:
    """Register-time gate: block_count must equal ref_count.

    Returns exit code (2) if rejection, or None to continue.
    """
    if block_count != ref_count:
        print(
            f"onboard_helper: register-time validation failed for {label}: "
            f"block_count={block_count} != ref_count={ref_count}. "
            f"Per spec, every fenced code block must have a corresponding "
            f"<!-- path/file.ext:line-range --> reference comment. "
            f"Recount and resubmit.",
            file=sys.stderr,
        )
        return 2
    return None


def cmd_add_package_doc(args: argparse.Namespace) -> int:
    """Register one package-level index.md."""
    rc = _check_block_ref_equality(f"package '{args.unit}'", args.block_count, args.ref_count)
    if rc is not None:
        return rc
    state = load_state()
    state.package_docs[args.unit] = PackageDoc(
        unit=args.unit,
        path=args.path,
        content=args.content,
        block_count=args.block_count,
        ref_count=args.ref_count,
    )
    save_state(state)
    print(f"add-package-doc {args.unit} (path={args.path}, blocks={args.block_count}, refs={args.ref_count})")
    return 0


def cmd_add_concern_doc(args: argparse.Namespace) -> int:
    """Register one concern doc within a package."""
    rc = _check_block_ref_equality(f"concern '{args.unit}/{args.concern}'", args.block_count, args.ref_count)
    if rc is not None:
        return rc
    state = load_state()
    state.concern_docs.append(ConcernDoc(
        unit=args.unit,
        concern=args.concern,
        content=args.content,
        block_count=args.block_count,
        ref_count=args.ref_count,
    ))
    save_state(state)
    print(f"add-concern-doc {args.unit}/{args.concern} (blocks={args.block_count}, refs={args.ref_count})")
    return 0


def cmd_add_architecture_doc(args: argparse.Namespace) -> int:
    """Register the workspace architecture.md (overwrites if called twice)."""
    rc = _check_block_ref_equality("architecture", args.block_count, args.ref_count)
    if rc is not None:
        return rc
    state = load_state()
    state.architecture_doc = DocEntry(
        content=args.content,
        block_count=args.block_count,
        ref_count=args.ref_count,
    )
    save_state(state)
    print(f"add-architecture-doc (blocks={args.block_count}, refs={args.ref_count})")
    return 0


def cmd_add_memory_finding(args: argparse.Namespace) -> int:
    """Register one memory observation."""
    state = load_state()
    state.memory_findings.append(MemoryFinding(
        category=args.category,
        unit=args.unit,
        observation=args.observation,
    ))
    save_state(state)
    print(f"add-memory-finding [{args.category}] {args.unit}: {args.observation[:60]}...")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print machine-readable progress.

    Format: one field per line, `field: value`. Consumable by the LLM
    orchestrator to decide whether more registrations are needed before
    compose-onboard.
    """
    state = load_state()
    print(f"mode: {state.mode if state.mode else 'UNSET'}")
    print(f"package_docs: {len(state.package_docs)}")
    print(f"concern_docs: {len(state.concern_docs)}")
    print(f"architecture_doc: {'SET' if state.architecture_doc else 'UNSET'}")
    print(f"memory_findings: {len(state.memory_findings)}")
    # Per-package concern-doc counts (helps the orchestrator see which units
    # have decomposition coverage).
    if state.concern_docs:
        per_unit_concerns: dict[str, int] = {}
        for c in state.concern_docs:
            per_unit_concerns[c.unit] = per_unit_concerns.get(c.unit, 0) + 1
        print("concern_docs_by_unit:")
        for unit, count in sorted(per_unit_concerns.items()):
            print(f"  {unit}: {count}")
    return 0


def cmd_compose_onboard(args: argparse.Namespace) -> int:
    """Validate state and atomically write all registered docs.

    Validation gates run before any write. If validation fails, errors are
    printed and the helper exits 2 with state preserved (so the LLM can
    register missing items and re-invoke compose).
    """
    state = load_state()

    # ── Validation gates ────────────────────────────────────────────────
    errors = _validate_compose(state)
    if errors:
        print("compose-onboard: validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            f"\n{len(errors)} validation error(s). State preserved; "
            "register missing items and re-invoke compose-onboard.",
            file=sys.stderr,
        )
        return 2

    written: list[Path] = []

    # 1. Package docs.
    for unit, pkg in state.package_docs.items():
        target = DOCS_DIR / pkg.path / "index.md"
        _write_doc_atomically(target, pkg.content)
        written.append(target)

    # 2. Concern docs (resolved against parent package's path).
    skipped_concerns: list[str] = []
    for concern in state.concern_docs:
        parent = state.package_docs.get(concern.unit)
        if parent is None:
            skipped_concerns.append(f"{concern.unit}/{concern.concern}")
            continue
        target = DOCS_DIR / parent.path / f"{concern.concern}.md"
        _write_doc_atomically(target, concern.content)
        written.append(target)

    # 3. Architecture doc.
    if state.architecture_doc is not None:
        target = DOCS_DIR / "architecture.md"
        _write_doc_atomically(target, state.architecture_doc.content)
        written.append(target)

    # 4. Memory findings.
    memory_appended = _append_memory_findings(state.memory_findings)

    # 5. Drop baselines.
    for target in written:
        rel = target.relative_to(DOCS_DIR)
        baseline_path = BASELINE_DIR / rel
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, baseline_path)

    # 6. Clear state on success.
    clear_state()

    # 7. Report.
    print(
        f"compose-onboard: wrote {len(written)} doc files; "
        f"baselines dropped at {BASELINE_DIR}; "
        f"memory findings appended: {memory_appended}"
    )
    if skipped_concerns:
        print(
            f"  warning: {len(skipped_concerns)} concern doc(s) skipped (no parent package): "
            f"{', '.join(skipped_concerns)}",
            file=sys.stderr,
        )
    return 0


# ─── compose-onboard internals ───────────────────────────────────────────────


def _validate_compose(state: OnboardState) -> list[str]:
    """Run all validation gates. Returns list of error strings (empty = pass)."""
    errors: list[str] = []
    errors.extend(_gate_per_package_coverage(state))
    errors.extend(_gate_per_concern_decomposition(state))
    errors.extend(_gate_block_ref_count_accuracy(state))
    errors.extend(_gate_boilerplate_overview(state))
    errors.extend(_gate_principal_type_presence(state))
    errors.extend(_gate_type_dedup(state))
    errors.extend(_gate_cross_link_existence(state))
    errors.extend(_gate_sigil_hygiene(state))
    return errors


# Markdown link pattern: [text](path-or-url).
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Sigil-prefixed workflow command pattern. Negative lookbehind excludes
# URL-y characters (slash/dot/word) so "https://example.com/onboard" or
# "./packages/onboard/" don't trigger. Standalone /onboard or $onboard
# does trigger.
_WORKFLOW_COMMANDS = (
    "onboard", "setup-wizard", "constitute", "specify",
    "plan", "breakdown", "implement", "verify",
)
_SIGIL_RE = re.compile(
    r"(?<![\w/.])([/$])(" + "|".join(_WORKFLOW_COMMANDS) + r")\b"
)


def _will_write_targets(state: OnboardState) -> set[Path]:
    """Compute the set of doc paths that compose-onboard will write."""
    targets: set[Path] = set()
    for pkg in state.package_docs.values():
        targets.add(DOCS_DIR / pkg.path / "index.md")
    for c in state.concern_docs:
        parent = state.package_docs.get(c.unit)
        if parent is None:
            continue  # per-concern decomp gate already errors on this case
        targets.add(DOCS_DIR / parent.path / f"{c.concern}.md")
    if state.architecture_doc is not None:
        targets.add(DOCS_DIR / "architecture.md")
    return targets


def _gate_cross_link_existence(state: OnboardState) -> list[str]:
    """Step 2.7a: every relative markdown link must resolve.

    Resolves each link relative to its doc's intended location, then
    checks: target is in WILL-write set OR exists on disk OR is an
    external URL/anchor. Else error.
    """
    errors: list[str] = []
    will_write = {p.resolve() for p in _will_write_targets(state)}

    def check(label: str, content: str, doc_dir: Path) -> None:
        for match in _MD_LINK_RE.finditer(content):
            target = match.group(2).strip()
            # Skip external links + anchor-only + mailto.
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip in-page anchors.
            target_no_anchor = target.split("#", 1)[0]
            if not target_no_anchor:
                continue
            # Resolve relative to the doc's directory.
            try:
                resolved = (doc_dir / target_no_anchor).resolve()
            except OSError:
                continue
            if resolved in will_write:
                continue
            if resolved.exists():
                continue
            errors.append(
                f"cross-link: {label} links to '{target}' which doesn't resolve "
                f"to a doc being written or an existing file. Verify the path."
            )

    for unit, pkg in state.package_docs.items():
        check(f"package '{unit}'", pkg.content, DOCS_DIR / pkg.path)
    for c in state.concern_docs:
        parent = state.package_docs.get(c.unit)
        if parent is None:
            continue
        check(f"concern '{c.unit}/{c.concern}'", c.content, DOCS_DIR / parent.path)
    if state.architecture_doc is not None:
        check("architecture", state.architecture_doc.content, DOCS_DIR)

    return errors


def _gate_sigil_hygiene(state: OnboardState) -> list[str]:
    """Step 2.7b: reject /<cmd> or $<cmd> workflow-command sigils in doc content.

    docs/ is cross-runtime; sigil-prefixed forms break for the other
    runtime. Bare command names ('onboard', 'constitute') are required.
    """
    errors: list[str] = []

    def check(label: str, content: str) -> None:
        matches = _SIGIL_RE.findall(content)
        if not matches:
            return
        # matches is a list of (sigil, command) tuples.
        offenders = sorted({f"{sigil}{cmd}" for sigil, cmd in matches})
        errors.append(
            f"sigil hygiene: {label} contains workflow-command sigils: "
            f"{', '.join(offenders)}. docs/ is cross-runtime; use bare command "
            f"names (e.g., 'onboard') not sigil-prefixed forms."
        )

    for unit, pkg in state.package_docs.items():
        check(f"package '{unit}'", pkg.content)
    for c in state.concern_docs:
        check(f"concern '{c.unit}/{c.concern}'", c.content)
    if state.architecture_doc is not None:
        check("architecture", state.architecture_doc.content)

    return errors


# Source-reference HTML comment pattern: <!-- path/file.ext:N --> or
# <!-- path/file.ext:N-M -->. Requires file extension before colon and
# digits after, which catches real refs while excluding generic comments.
_SRC_REF_RE = re.compile(r"<!--\s*\S+\.\w+:\d+(?:-\d+)?\s*-->")


def _count_fenced_blocks_requiring_refs(content: str) -> int:
    """Count fenced code blocks that require a source reference.

    State-machine walk over lines. Mermaid-tagged blocks are exempt — they
    are LLM-synthesized diagrams, not lifted code.
    """
    in_block = False
    is_mermaid = False
    count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_block:
                lang = stripped[3:].strip().lower()
                in_block = True
                is_mermaid = (lang == "mermaid")
            else:
                if not is_mermaid:
                    count += 1
                in_block = False
                is_mermaid = False
    return count


def _count_source_refs(content: str) -> int:
    """Count <!-- path/file.ext:line-range --> reference comments in content."""
    return len(_SRC_REF_RE.findall(content))


# Exported type/interface/class/enum declaration patterns. Multi-language:
# - TypeScript: `export (abstract )?(interface|type|class|enum) XName`
# - Python: `class XName:` or `class XName(`
# - Rust: `pub struct|enum|trait XName`
# - Go: `type XName struct|interface|...`
_EXPORT_TYPE_PATTERNS = [
    re.compile(r"^\s*export\s+(?:abstract\s+|default\s+)?(?:interface|type|class|enum)\s+(\w+)", re.MULTILINE),
    re.compile(r"^\s*pub\s+(?:struct|enum|trait|fn)\s+(\w+)", re.MULTILINE),
    re.compile(r"^\s*type\s+(\w+)\s+(?:struct|interface)", re.MULTILINE),  # Go
    re.compile(r"^\s*class\s+(\w+)\s*[\(:]", re.MULTILINE),  # Python (and some TS-like)
]


def _gate_type_dedup(state: OnboardState) -> list[str]:
    """Step 2.6: each exported type name should appear at most once per doc.

    an LLM emitted FooterChargeLine twice (line ranges 20-28 and 24-28)
    and CalcOptions three times (3-11, 4-11, 5-11) because its parser
    walked overlapping line ranges and didn't dedup at emit time. The
    structural defect: same name declared multiple times in the same doc.
    """
    errors: list[str] = []

    def check(label: str, content: str) -> None:
        seen: dict[str, int] = {}
        for pattern in _EXPORT_TYPE_PATTERNS:
            for m in pattern.findall(content):
                seen[m] = seen.get(m, 0) + 1
        duplicates = {name: count for name, count in seen.items() if count > 1}
        for name, count in sorted(duplicates.items()):
            errors.append(
                f"type dedup: {label} declares '{name}' {count} times in the same doc. "
                f"Each exported type should appear once. Remove the duplicate code "
                f"block(s)."
            )

    for unit, pkg in state.package_docs.items():
        check(f"package '{unit}'", pkg.content)
    for c in state.concern_docs:
        check(f"concern '{c.unit}/{c.concern}'", c.content)
    if state.architecture_doc is not None:
        check("architecture", state.architecture_doc.content)

    return errors


# BLoC base classes — names not to count as ownership signals.
_BLOC_BASE_CLASSES = {"BLoC", "BLoCAlt", "BLoCAltSecond"}

# Pattern: `class XBLoC` (TypeScript class declaration).
_BLOC_CLASS_DECL_RE = re.compile(r"\bclass\s+(\w+BLoC)\b")

# Pattern: `provideXBLoC` (Clean Architecture factory naming).
_BLOC_FACTORY_RE = re.compile(r"\b(provide\w+BLoC)\b")


def _detect_owned_blocs(content: str) -> set[str]:
    """Detect BLoCs this doc *owns* (vs. just mentions/consumes).

    Ownership signals:
    - `class XBLoC` declaration in a code block.
    - `provideXBLoC` factory mention (the doc owning the BLoC owns its
      factory; consumers don't typically write the factory name).

    Excludes base classes (BLoC, BLoCAlt, BLoCAltSecond).
    """
    owned: set[str] = set()
    for m in _BLOC_CLASS_DECL_RE.finditer(content):
        owned.add(m.group(1))
    for m in _BLOC_FACTORY_RE.finditer(content):
        name = m.group(1)[len("provide"):]  # strip "provide" prefix
        if name:
            owned.add(name)
    return owned - _BLOC_BASE_CLASSES


def _gate_principal_type_presence(state: OnboardState) -> list[str]:
    """Step 2.5: docs owning a BLoC must include the corresponding State type.

    For each registered doc, detect owned BLoCs (via class decl or provide
    factory). For each owned BLoC, expect the matching `XState` type name
    somewhere in the same doc. If missing, error.

    Catches the QuoteOwnersState miss pattern: the parser surfaced helper
    types instead of the principal state type. Forcing State-presence per
    BLoC is the structural fix.
    """
    errors: list[str] = []

    def check(label: str, content: str) -> None:
        owned_blocs = _detect_owned_blocs(content)
        for bloc in owned_blocs:
            expected_state = bloc.replace("BLoC", "State")
            # Substring search; case-sensitive (TS type names are case-sensitive).
            if expected_state not in content:
                errors.append(
                    f"principal-type presence: {label} declares ownership of '{bloc}' "
                    f"but does not include the corresponding state type '{expected_state}' "
                    f"in this doc. Add '{expected_state}' to the Types section with its "
                    f"inline definition (interface or type alias)."
                )

    for unit, pkg in state.package_docs.items():
        check(f"package '{unit}'", pkg.content)
    for c in state.concern_docs:
        check(f"concern '{c.unit}/{c.concern}'", c.content)
    # Architecture is workspace-level; no BLoC-ownership expected.

    return errors


# Boilerplate overview phrases observed in LLM output. Adding to
# this list closes more template-shape failure modes. Phrases are matched
# case-insensitively against the Overview section text.
_BOILERPLATE_PHRASES = [
    "is a documentation unit",
    "feature boundaries, presentation adapters",
    "and supporting domain contracts",
    "presentation adapters, and supporting domain contracts",
    "this documentation unit",
    "this is a documentation unit",
]


def _extract_overview_section(content: str) -> str:
    """Return the text under '## Overview' until the next '## ' heading.

    Returns empty string if no Overview section. Comparison is
    case-insensitive on the heading.
    """
    in_overview = False
    captured: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not in_overview:
            if stripped.lower().startswith("## overview"):
                in_overview = True
            continue
        if stripped.startswith("## "):  # next H2 ends the section
            break
        captured.append(line)
    return "\n".join(captured)


def _gate_boilerplate_overview(state: OnboardState) -> list[str]:
    """Step 2.4: reject docs whose Overview contains template-shape phrases.

    Catches the "X is a documentation unit inside CSE UI" pattern
    where the generator emits a template-shaped overview that describes how
    the doc is organized rather than what the package does.
    """
    errors: list[str] = []

    def check(label: str, content: str) -> None:
        overview = _extract_overview_section(content)
        if not overview:
            return  # Per-doc structural-completeness gate covers missing Overview.
        overview_lower = overview.lower()
        for phrase in _BOILERPLATE_PHRASES:
            if phrase.lower() in overview_lower:
                errors.append(
                    f"boilerplate overview: {label} Overview contains template phrase "
                    f"'{phrase}'. Rewrite the Overview to be project-specific — "
                    f"what does this unit actually provide, who consumes it, what "
                    f"are the principal responsibilities."
                )
                return  # One error per doc is enough

    for unit, pkg in state.package_docs.items():
        check(f"package '{unit}'", pkg.content)
    for c in state.concern_docs:
        check(f"concern '{c.unit}/{c.concern}'", c.content)
    if state.architecture_doc is not None:
        check("architecture", state.architecture_doc.content)

    return errors


def _gate_block_ref_count_accuracy(state: OnboardState) -> list[str]:
    """Step 2.3: declared block_count and ref_count must match content reality.

    For each registered doc:
    - Recount fenced code blocks (excluding Mermaid).
    - Recount source-ref HTML comments matching path/file.ext:line pattern.
    - Compare against declared block_count and ref_count.

    Register-time gate already enforces declared block_count == ref_count.
    This compose-time gate catches lies about the declared values.
    """
    errors: list[str] = []

    def check(label: str, content: str, declared_blocks: int, declared_refs: int) -> None:
        actual_blocks = _count_fenced_blocks_requiring_refs(content)
        actual_refs = _count_source_refs(content)
        if actual_blocks != declared_blocks:
            errors.append(
                f"block-count accuracy: {label} declared block_count={declared_blocks} "
                f"but content has {actual_blocks} fenced code blocks (excluding mermaid). "
                f"Recount and resubmit."
            )
        if actual_refs != declared_refs:
            errors.append(
                f"ref-count accuracy: {label} declared ref_count={declared_refs} "
                f"but content has {actual_refs} <!-- path:line --> reference comments. "
                f"Recount and resubmit."
            )
        if actual_blocks != actual_refs:
            errors.append(
                f"block-vs-ref equality: {label} content has {actual_blocks} fenced blocks "
                f"but {actual_refs} reference comments. Each block needs a "
                f"<!-- path/file.ext:line-range --> comment immediately above it."
            )

    for unit, pkg in state.package_docs.items():
        check(f"package '{unit}'", pkg.content, pkg.block_count, pkg.ref_count)
    for c in state.concern_docs:
        check(f"concern '{c.unit}/{c.concern}'", c.content, c.block_count, c.ref_count)
    if state.architecture_doc is not None:
        check(
            "architecture",
            state.architecture_doc.content,
            state.architecture_doc.block_count,
            state.architecture_doc.ref_count,
        )

    return errors


def _load_detected_packages() -> list[dict[str, Any]]:
    """Load PACKAGES_DETECTED from .devforge/project-config.json.

    Returns empty list if file missing (tests / ad-hoc use). The
    per-package coverage gate handles "no detected packages" as a no-op
    pass — the LLM can register packages without wizard pre-detection.
    """
    if not PROJECT_CONFIG.exists():
        return []
    try:
        cfg = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        # Fail loud — this is a setup-wizard contract violation.
        print(
            f"onboard_helper: corrupt {PROJECT_CONFIG}: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    return cfg.get("PACKAGES_DETECTED") or []


def _gate_per_package_coverage(state: OnboardState) -> list[str]:
    """Step 2.1: every detected package must have an add-package-doc registration.

    Match by path (state.package_docs[unit].path == detected[].path). If a
    detected package has no matching registration, that's a coverage failure.
    """
    detected = _load_detected_packages()
    if not detected:
        return []  # No detection report → no coverage requirement.

    registered_paths = {pkg.path for pkg in state.package_docs.values()}
    errors: list[str] = []
    for entry in detected:
        path = entry.get("path")
        if not path:
            continue
        if path not in registered_paths:
            errors.append(
                f"per-package coverage: no add-package-doc registration for detected package "
                f"path='{path}' (manifest={entry.get('manifest', '?')})"
            )
    return errors


# Concern-name heuristic: subfolders matching these names are always
# considered substantive regardless of file count. Lowercase set for
# case-insensitive comparison.
_CONCERN_NAMES = {
    "components", "services", "routing", "router", "handlers", "daos",
    "models", "views", "pages", "stores", "composables", "hooks", "plugins",
    "controllers", "presenter", "presentation", "domain", "data",
    "infrastructure", "repositories", "entities", "helpers", "utils",
    "adapters", "middleware", "actions", "reducers", "selectors", "queries",
    "mutations", "subscriptions", "guards", "interceptors", "filters",
}

# Subfolders never counted as substantive (build/cache/dependency artifacts).
_IGNORE_SUBDIRS = {
    "node_modules", "target", "build", "dist", ".next", ".nuxt", "vendor",
    "__pycache__", ".venv", "venv", ".tox", "coverage", ".cache", "tmp",
    "bin", "obj", "Pods", ".bundle", ".dart_tool", ".gradle", ".cargo",
    ".mypy_cache", ".ruff_cache", "test", "tests", "__tests__", "__test__",
    "spec", "specs",
}

# File-count threshold for "substantive" when the subfolder name doesn't
# match the concern heuristic. Tunable.
_SUBSTANTIVE_FILE_THRESHOLD = 4


def _detect_substantive_subfolders(pkg_path: str) -> list[str]:
    """Identify substantive source subfolders within a package.

    Tries common source roots in order (src, lib, then unit root for Go-style
    layouts). For each immediate child directory of the source root:
    - Skip ignore set + dot-prefixed dirs.
    - Mark substantive if the lowercased name is in _CONCERN_NAMES.
    - Mark substantive if it contains _SUBSTANTIVE_FILE_THRESHOLD+ files
      (recursive count, ignoring nested ignore-set dirs).

    Returns the substantive subfolder names sorted alphabetically. Empty list
    if the package directory doesn't exist or has no substantive children.
    """
    pkg_root = Path(pkg_path)
    if not pkg_root.is_dir():
        return []

    source_root: Optional[Path] = None
    for candidate in ("src", "lib"):
        cand = pkg_root / candidate
        if cand.is_dir():
            source_root = cand
            break
    if source_root is None:
        source_root = pkg_root

    substantive: list[str] = []
    try:
        children = list(source_root.iterdir())
    except (OSError, PermissionError):
        return []

    for child in children:
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        if child.name in _IGNORE_SUBDIRS:
            continue
        # Concern-name heuristic.
        if child.name.lower() in _CONCERN_NAMES:
            substantive.append(child.name)
            continue
        # File-count heuristic.
        try:
            file_count = 0
            for entry in child.rglob("*"):
                # Skip files inside ignored nested dirs.
                if any(part in _IGNORE_SUBDIRS for part in entry.parts):
                    continue
                if entry.is_file():
                    file_count += 1
                    if file_count >= _SUBSTANTIVE_FILE_THRESHOLD:
                        break
        except (OSError, PermissionError):
            file_count = 0
        if file_count >= _SUBSTANTIVE_FILE_THRESHOLD:
            substantive.append(child.name)

    return sorted(substantive)


def _gate_per_concern_decomposition(state: OnboardState) -> list[str]:
    """Step 2.2: every substantive source subfolder must have a concern doc.

    For each registered package, detect substantive subfolders. For each,
    require a matching add-concern-doc registration (unit + concern name).
    Missing concern docs = error, with explicit miss list.

    Closes the "concern mentioned inside index.md" monolith collapse:
    the LLM cannot satisfy this gate by adding more text to index.md; it
    must call add-concern-doc for each substantive subfolder.
    """
    errors: list[str] = []
    for unit, pkg in state.package_docs.items():
        substantive = _detect_substantive_subfolders(pkg.path)
        if not substantive:
            continue
        registered_concerns = {
            c.concern for c in state.concern_docs if c.unit == unit
        }
        missing = [s for s in substantive if s not in registered_concerns]
        for sub in missing:
            errors.append(
                f"per-concern decomposition: package '{unit}' (path={pkg.path}) "
                f"has substantive subfolder '{sub}' but no add-concern-doc "
                f"registration. Call: onboard_helper add-concern-doc "
                f"--unit {unit} --concern {sub} ..."
            )
    return errors


def _write_doc_atomically(target: Path, content: str) -> None:
    """Write content to target via temp file in same dir + os.replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".onboard-doc-", suffix=".md", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# Memory category → (parent section heading, subsection-heading-format).
# Subsection heading is dated so re-runs append rather than collide.
_MEMORY_SECTION_MAP = {
    "module-boundaries": ("## Architecture Decisions", "### Module boundaries (from onboard {date})"),
    "dependency-warnings": ("## Known Pitfalls", "### Dependency warnings (from onboard {date})"),
    "complexity": ("## Known Pitfalls", "### Areas of complexity (from onboard {date})"),
    "inconsistencies": ("## Known Pitfalls", "### Inconsistencies (from onboard {date})"),
}


def _append_memory_findings(findings: list[MemoryFinding]) -> int:
    """Insert findings into .devforge/memory.md under scaffold sections.

    Returns count of findings appended. If memory.md doesn't exist, prints a
    warning and returns 0.
    """
    if not findings:
        return 0

    memory_file = DEVFORGE_DIR / "memory.md"
    if not memory_file.exists():
        print(
            f"warning: {memory_file} not found; memory findings not persisted",
            file=sys.stderr,
        )
        return 0

    today = date.today().isoformat()

    # Group findings by category.
    by_category: dict[str, list[MemoryFinding]] = {}
    for f in findings:
        by_category.setdefault(f.category, []).append(f)

    existing = memory_file.read_text(encoding="utf-8")
    updated = existing
    appended = 0

    for category, items in by_category.items():
        if category not in _MEMORY_SECTION_MAP:
            continue
        parent_heading, sub_heading_fmt = _MEMORY_SECTION_MAP[category]
        sub_heading = sub_heading_fmt.format(date=today)
        bullets = "\n".join(f"- `{f.unit}`: {f.observation}" for f in items)
        block = f"\n{sub_heading}\n{bullets}\n"

        # Insert immediately after the parent heading line if it exists;
        # otherwise append at end with parent heading prepended.
        if parent_heading in updated:
            idx = updated.index(parent_heading) + len(parent_heading)
            line_end = updated.index("\n", idx)
            updated = updated[: line_end + 1] + block + updated[line_end + 1 :]
        else:
            updated += f"\n{parent_heading}\n{block}"

        appended += len(items)

    memory_file.write_text(updated, encoding="utf-8")
    return appended


# ─── Argparse setup ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onboard_helper",
        description=(
            "Register onboard documentation artifacts (per-package, per-concern, "
            "architecture, memory) and atomically compose them into docs/. "
            "Bulk-script-write is unsupported by design."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser(
        "set",
        help="Set a top-level scalar (e.g. mode).",
    )
    p_set.add_argument("field", help="Field name (e.g. mode).")
    p_set.add_argument("--value", required=True, help="Value to set.")
    p_set.set_defaults(func=cmd_set)

    p_pkg = sub.add_parser(
        "add-package-doc",
        help="Register one package's index.md content.",
    )
    p_pkg.add_argument("--unit", required=True, help="Package/unit name.")
    p_pkg.add_argument("--path", required=True, help="Package's source path relative to SOURCE_ROOT (e.g. packages/pkg-foo).")
    p_pkg.add_argument("--content", required=True, help="Full markdown content for docs/<path>/index.md.")
    p_pkg.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_pkg.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_pkg.set_defaults(func=cmd_add_package_doc)

    p_concern = sub.add_parser(
        "add-concern-doc",
        help="Register one concern doc inside a package.",
    )
    p_concern.add_argument("--unit", required=True, help="Parent package/unit name (must be already registered via add-package-doc).")
    p_concern.add_argument("--concern", required=True, help="Concern name (subfolder name, e.g. components, services, routing).")
    p_concern.add_argument("--content", required=True, help="Full markdown content for docs/<unit-path>/<concern>.md.")
    p_concern.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_concern.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_concern.set_defaults(func=cmd_add_concern_doc)

    p_arch = sub.add_parser(
        "add-architecture-doc",
        help="Register the workspace architecture.md (single call). Distinct prompt template — NOT the per-package template.",
    )
    p_arch.add_argument("--content", required=True, help="Full markdown content for docs/architecture.md.")
    p_arch.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_arch.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_arch.set_defaults(func=cmd_add_architecture_doc)

    p_mem = sub.add_parser(
        "add-memory-finding",
        help="Register one memory observation. Multiple calls. Findings collected during a separate source-reading pass, NOT summarized from generated docs.",
    )
    p_mem.add_argument(
        "--category",
        required=True,
        choices=["module-boundaries", "dependency-warnings", "complexity", "inconsistencies"],
        help="Memory category (maps to scaffold subsection).",
    )
    p_mem.add_argument("--unit", required=True, help="Unit/package this finding applies to (or 'workspace' for cross-cutting).")
    p_mem.add_argument("--observation", required=True, help="The finding itself (one line).")
    p_mem.set_defaults(func=cmd_add_memory_finding)

    p_status = sub.add_parser(
        "status",
        help="Show machine-readable progress (registrations per category, missing required, validator state).",
    )
    p_status.set_defaults(func=cmd_status)

    p_compose = sub.add_parser(
        "compose-onboard",
        help="Validate state and atomically write all registered docs to docs/. Drop baselines on success. Clears state on success.",
    )
    p_compose.set_defaults(func=cmd_compose_onboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
