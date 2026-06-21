"""F.5 / 3a.5 — validate-doc helper (all tiers).

Walks a rendered doc and checks every Plan F density invariant: frontmatter
required keys present, section anchors present, no banned phrases, bullet
length within cap, structure annotations within their cap.

All tiers are implemented:
- ``concern`` (leaf): Purpose + Structure required (default path).
- ``concern --split`` (parent, Plan F 3a.5): Purpose + Sub-concerns required;
  Structure forbidden; each Sub-concerns bullet matches the locked shape
  ``- <name> — <summary> ([→](<doc_path>))`` + each `doc_path` resolves
  to a rendered child doc; summary capped at 200 chars per the spec.
- ``package-overview`` / ``package-architecture``.
- ``project-overview`` / ``project-architecture``.

Vue cite-back through-sourcemap validation is deferred — currently only
existence + line-range of cited paths is checked (concern-tier only).

Exit codes:
- 0 — every check passed
- 2 — at least one violation; stderr lists every error; orchestrator
       captures stderr as `previous_attempt_feedback` for the next
       compose retry

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from ._md_frontmatter import FrontmatterParseError, parse_frontmatter

_CONCERN_REQUIRED_KEYS = ("concern", "package", "files", "source_stamp", "last_indexed")
_CONCERN_REQUIRED_SECTIONS = ("## Purpose", "## Structure")

# Plan F 3a — split-parent concern doc (Purpose + Sub-concerns; NO Structure).
# Parent docs are aggregators over child concern docs; the structural detail
# lives inside each child. `files` is intentionally absent from required keys
# because the parent has no leaf file list — it's a list of sub_concerns.
_SPLIT_PARENT_REQUIRED_KEYS = ("concern", "package", "source_stamp", "last_indexed")
_SPLIT_PARENT_REQUIRED_SECTIONS = ("## Purpose", "## Sub-concerns")
_SPLIT_PARENT_FORBIDDEN_SECTIONS = ("## Structure",)

# Locked bullet shape from 3a.2 (`_render_subconcerns_bullets`):
#   - <name> — <purpose_summary> ([→](<doc_path>))
# Match-anchored to the entire bullet text after the `- ` prefix (which
# `_parse_bullets` strips). Path may contain forward slashes + dots; name
# is the first non-whitespace token.
_SUBCONCERN_BULLET_RE = re.compile(
    r"^(?P<name>\S+) — (?P<summary>.+?) \(\[→\]\((?P<path>[^)]+)\)\)$"
)
# Per the 3a.3 spec (Step 2.S.3) `purpose_summary = ≤200-char one-liner`;
# enforce here so verbose summaries surface as a validation error rather
# than slipping through under the broader 300-char whole-bullet cap.
_SUBCONCERN_SUMMARY_CAP = 200

_PACKAGE_OVERVIEW_REQUIRED_KEYS = ("package", "source_stamp", "last_indexed")
_PACKAGE_OVERVIEW_REQUIRED_SECTIONS = ("## Purpose", "## Concerns", "## Files")

_PACKAGE_ARCHITECTURE_REQUIRED_KEYS = ("package", "source_stamp", "last_indexed")
_PACKAGE_ARCHITECTURE_REQUIRED_SECTIONS = ("## Layers", "## Patterns")

_PROJECT_OVERVIEW_REQUIRED_KEYS = ("source_stamp", "last_indexed")
# Track 4 Phase 1: 5 mechanical sections added (Tech Stack, Project Structure,
# Key Commands, Cross-Module Dependencies, Test Files).
# Track 4 Phase 2: 4 mixed mechanical+LLM sections added (Entry Points,
# Module Map, Application Routes, Navigation Guards). Order in tuple does
# not affect validation, but mirrors skeleton emit order in
# `_doc_setters._build_project_overview_skeleton` for human readability.
_PROJECT_OVERVIEW_REQUIRED_SECTIONS = (
    "## Purpose",
    "## Tech Stack",
    "## Project Structure",
    "## Entry Points",
    "## Key Commands",
    "## Module Map",
    "## Cross-Module Dependencies",
    "## Application Routes",
    "## Navigation Guards",
    "## Test Files",
    "## Packages",
)

_PROJECT_ARCHITECTURE_REQUIRED_KEYS = ("source_stamp", "last_indexed")
# Track 4 Phase 3: 6 architecture sections added (Architecture Overview,
# Module / Package Structure, Patterns, Conventions, Dependency Direction
# Rules, Dependency Overview). Layers + Cross-Cuts retained as Phase 0
# anchors. Subsection-style sections (Patterns, Cross-Cuts, Conventions)
# don't trigger _BULLET_CAP false-positives because _parse_bullets only
# matches `- ` prefix lines (subsections use `### ` headings + prose +
# fenced blocks, no top-level `- ` bullets).
_PROJECT_ARCHITECTURE_REQUIRED_SECTIONS = (
    "## Architecture Overview",
    "## Module / Package Structure",
    "## Patterns",
    "## Conventions",
    "## Layers",
    "## Cross-Cuts",
    "## Dependency Direction Rules",
    "## Dependency Overview",
)

# Bullet length cap (Concerns/Layers/Patterns/Cross-Cuts).
# Bumped 200 → 300 (2026-05-08) after V5 smoke on pkg-cse-client surfaced
# Patterns bullets at 219-332 chars where the content was REAL (Vite dual-
# bundle build, AppSync subscription transport subclass override, etc.),
# not LLM rambling. 200 was Hazards-calibrated (smoke #5); Patterns/Layers
# are inherently more discursive — `<name> — <rule with explanation> —
# <cite>` plus deep monorepo paths eat 100+ chars on cite alone. 300 =
# 30 (name) + 150 (rule) + 100 (cite) with headroom.
_BULLET_CAP = 300

_BANNED_PHRASES_RE = re.compile(
    r"\b(this document|in this section|we will|various|several|many|some|other)\b",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^- ", re.MULTILINE)
_CITE_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./-]+):(?P<start>\d+)"
    r"(?:-(?P<end>\d+))?"
    r"(?:,(?P<extra>\d+))?"
)
_HAZARD_BULLET_CAP = 200
_ANNOTATION_CAP = 60
_HAZARD_COUNT_MIN = 3
_HAZARD_COUNT_MAX = 15


def _split_sections(body: str) -> Dict[str, str]:
    """Split body into {section_name: section_body} pairs.

    Section header pattern: a line starting with `## `. Body of a section
    is everything between its header and the next `## ` header (or EOF).
    """
    sections: Dict[str, str] = {}
    current_name: str = ""
    current_lines: List[str] = []
    for line in body.split("\n"):
        if line.startswith("## "):
            if current_name:
                sections[current_name] = "\n".join(current_lines).strip("\n")
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_name:
        sections[current_name] = "\n".join(current_lines).strip("\n")
    return sections


def _parse_bullets(section_text: str) -> List[str]:
    """Extract bullet entries from a `## ` section.

    A bullet entry begins with a line `- ` and continues until the next
    line that begins with `- ` or until end of section. Returns the joined
    text per bullet (whitespace-stripped).
    """
    if not section_text:
        return []
    lines = section_text.split("\n")
    bullets: List[str] = []
    current: List[str] = []
    for line in lines:
        if line.startswith("- "):
            if current:
                bullets.append(" ".join(s.strip() for s in current).strip())
            current = [line[2:]]
        elif current:
            stripped = line.strip()
            if stripped:
                current.append(stripped)
    if current:
        bullets.append(" ".join(s.strip() for s in current).strip())
    return bullets


def _resolve_cite_path(
    cite_path: str, target: str, project_root: Path
) -> Tuple[Path, str]:
    """Resolve a cite-back path string to an absolute file path.

    Plan F allows three cite-path forms (in priority order):

    1. Full project-relative path — `<pkg>/src/<concern>/.../<file>`.
       Tried first; resolves verbatim under project_root.
    2. In-concern basename — when the cited file lives in the doc's own
       concern subfolder, the agent may write only the basename. Source
       dir is `<pkg>/src/<concern>/` on disk; target convention is
       `<pkg>/<concern>` (no `src/`). This branch splits target into pkg
       + concern parts and probes `<project_root>/<pkg>/src/<concern>/<cite_path>`.
    3. Verbatim target append — fallback `<project_root>/<target>/<cite_path>`
       for callers passing a target that already includes `src/`.

    Returns (absolute_path, mode). Mode ∈ {"full", "basename", "verbatim",
    "miss"}. On miss the returned path is the full-form attempt (for
    diagnostic).
    """
    full_attempt = project_root / cite_path
    if full_attempt.is_file():
        return full_attempt, "full"

    target_parts = target.split("/")
    if len(target_parts) >= 2:
        pkg_part = "/".join(target_parts[:-1])
        concern_part = target_parts[-1]
        basename_attempt = project_root / pkg_part / "src" / concern_part / cite_path
        if basename_attempt.is_file():
            return basename_attempt, "basename"

    verbatim_attempt = project_root / target / cite_path
    if verbatim_attempt.is_file():
        return verbatim_attempt, "verbatim"

    return full_attempt, "miss"


def _validate_concern_doc(
    doc_path: Path, target: str, project_root: Path
) -> List[str]:
    """Apply concern-tier checks. Return list of error strings (empty = OK)."""
    errors: List[str] = []
    if not doc_path.is_file():
        return [f"doc not found: {doc_path}"]
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"doc unreadable: {exc}"]

    record: Dict[str, object] = {}
    body = text
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        errors.append(f"frontmatter parse: {exc}")

    missing_keys = [k for k in _CONCERN_REQUIRED_KEYS if k not in record]
    if missing_keys:
        errors.append(f"frontmatter missing keys: {missing_keys}")

    for anchor in _CONCERN_REQUIRED_SECTIONS:
        if anchor not in body:
            errors.append(f"missing required section: {anchor!r}")

    for match in _BANNED_PHRASES_RE.finditer(body):
        line_idx = body[: match.start()].count("\n") + 1
        errors.append(f"banned phrase {match.group(0)!r} at body line {line_idx}")

    sections = _split_sections(body)
    structure_text = sections.get("Structure", "")
    for line in structure_text.split("\n"):
        if " — " in line:
            annotation = line.split(" — ", 1)[1].strip()
            if len(annotation) > _ANNOTATION_CAP:
                errors.append(
                    f"structure annotation {annotation!r} length "
                    f"{len(annotation)} > {_ANNOTATION_CAP}"
                )

    return errors


def _validate_split_parent_doc(
    doc_path: Path, target: str, project_root: Path
) -> List[str]:
    """Plan F 3a.5 — validate a split-parent concern doc.

    Required: frontmatter has the split-parent keys, body has Purpose +
    Sub-concerns (and NOT Structure), each Sub-concerns bullet matches
    the locked shape, each child `doc_path` resolves to an existing file
    under `docs/<target>/`. Bullets capped at the standard 300-char limit.
    """
    errors: List[str] = []
    if not doc_path.is_file():
        return [f"doc not found: {doc_path}"]
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"doc unreadable: {exc}"]

    record: Dict[str, object] = {}
    body = text
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        errors.append(f"frontmatter parse: {exc}")

    missing_keys = [k for k in _SPLIT_PARENT_REQUIRED_KEYS if k not in record]
    if missing_keys:
        errors.append(f"frontmatter missing keys: {missing_keys}")

    for anchor in _SPLIT_PARENT_REQUIRED_SECTIONS:
        if anchor not in body:
            errors.append(f"missing required section: {anchor!r}")

    for anchor in _SPLIT_PARENT_FORBIDDEN_SECTIONS:
        if anchor in body:
            errors.append(
                f"forbidden section for split parent: {anchor!r} "
                f"(parent docs aggregate sub_concerns; structure lives in children)"
            )

    for match in _BANNED_PHRASES_RE.finditer(body):
        line_idx = body[: match.start()].count("\n") + 1
        errors.append(f"banned phrase {match.group(0)!r} at body line {line_idx}")

    sections = _split_sections(body)
    sub_section = sections.get("Sub-concerns", "")
    bullets = _parse_bullets(sub_section)
    if not bullets:
        errors.append("`## Sub-concerns` section has no bullets")
    parent_doc_dir = doc_path.parent
    for i, bullet in enumerate(bullets, start=1):
        if len(bullet) > _BULLET_CAP:
            errors.append(
                f"Sub-concerns bullet {i} length {len(bullet)} > {_BULLET_CAP} "
                f"(first 80 chars: {bullet[:80]!r})"
            )
        match = _SUBCONCERN_BULLET_RE.match(bullet)
        if not match:
            errors.append(
                f"Sub-concerns bullet {i} fails locked shape "
                f"`<name> — <summary> ([→](<doc_path>))`: {bullet!r}"
            )
            continue
        summary = match.group("summary")
        if len(summary) > _SUBCONCERN_SUMMARY_CAP:
            errors.append(
                f"Sub-concerns bullet {i} summary length {len(summary)} > "
                f"{_SUBCONCERN_SUMMARY_CAP}"
            )
        rel_path = match.group("path").strip()
        # `doc_path` in bullet is parent-relative (e.g., `accounts/index.md`).
        child_path = (parent_doc_dir / rel_path).resolve()
        if not child_path.is_file():
            errors.append(
                f"Sub-concerns bullet {i} doc_path does not resolve: {rel_path!r} "
                f"(expected file at {child_path})"
            )

    return errors


_TIER_DOC_FILENAMES = {
    "concern": "index.md",
    "package-overview": "overview.md",
    "package-architecture": "architecture.md",
    "project-overview": "overview.md",
    "project-architecture": "architecture.md",
}
_PROJECT_TIERS = ("project-overview", "project-architecture")


def _validate_package_doc(
    doc_path: Path,
    required_keys: Tuple[str, ...],
    required_sections: Tuple[str, ...],
) -> List[str]:
    """Validate a package-tier doc (overview or architecture).

    Checks: file exists, frontmatter parses + has required keys, all
    required section anchors present, no banned phrases, every bullet
    inside required sections is ≤200 chars.
    """
    errors: List[str] = []
    if not doc_path.is_file():
        return [f"doc not found: {doc_path}"]
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"doc unreadable: {exc}"]

    record: Dict[str, object] = {}
    body = text
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        errors.append(f"frontmatter parse: {exc}")

    missing_keys = [k for k in required_keys if k not in record]
    if missing_keys:
        errors.append(f"frontmatter missing keys: {missing_keys}")

    for anchor in required_sections:
        if anchor not in body:
            errors.append(f"missing required section: {anchor!r}")

    for match in _BANNED_PHRASES_RE.finditer(body):
        line_idx = body[: match.start()].count("\n") + 1
        errors.append(f"banned phrase {match.group(0)!r} at body line {line_idx}")

    sections = _split_sections(body)
    for anchor in required_sections:
        section_name = anchor[3:]  # strip "## "
        bullets = _parse_bullets(sections.get(section_name, ""))
        for i, b in enumerate(bullets, start=1):
            if len(b) > _BULLET_CAP:
                errors.append(
                    f"{section_name} bullet {i} length {len(b)} > {_BULLET_CAP} "
                    f"(first 80 chars: {b[:80]!r})"
                )

    return errors


def cmd_validate_doc(args: argparse.Namespace) -> int:
    """Handler for `validate-doc` subcommand. Returns CLI exit code."""
    tier = args.tier
    target = args.target
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()

    if tier not in _TIER_DOC_FILENAMES:
        print(
            f"unknown tier {tier!r} (supported: {tuple(_TIER_DOC_FILENAMES)})",
            file=sys.stderr,
        )
        return 2

    if getattr(args, "split", False) and tier != "concern":
        print(
            f"--split is only valid for tier=concern, got tier={tier!r}",
            file=sys.stderr,
        )
        return 2

    if tier in _PROJECT_TIERS:
        doc_path = project_root / "docs" / _TIER_DOC_FILENAMES[tier]
    else:
        doc_path = project_root / "docs" / target / _TIER_DOC_FILENAMES[tier]

    if tier == "concern":
        if getattr(args, "split", False):
            errors = _validate_split_parent_doc(doc_path, target, project_root)
        else:
            errors = _validate_concern_doc(doc_path, target, project_root)
    elif tier == "package-overview":
        errors = _validate_package_doc(
            doc_path,
            _PACKAGE_OVERVIEW_REQUIRED_KEYS,
            _PACKAGE_OVERVIEW_REQUIRED_SECTIONS,
        )
    elif tier == "package-architecture":
        errors = _validate_package_doc(
            doc_path,
            _PACKAGE_ARCHITECTURE_REQUIRED_KEYS,
            _PACKAGE_ARCHITECTURE_REQUIRED_SECTIONS,
        )
    elif tier == "project-overview":
        errors = _validate_package_doc(
            doc_path,
            _PROJECT_OVERVIEW_REQUIRED_KEYS,
            _PROJECT_OVERVIEW_REQUIRED_SECTIONS,
        )
    elif tier == "project-architecture":
        errors = _validate_package_doc(
            doc_path,
            _PROJECT_ARCHITECTURE_REQUIRED_KEYS,
            _PROJECT_ARCHITECTURE_REQUIRED_SECTIONS,
        )
    else:  # pragma: no cover — guarded above
        errors = [f"unhandled tier {tier!r}"]

    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 2
    return 0


def _build_validate_doc(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `validate-doc` subcommand."""
    p.add_argument(
        "--tier",
        required=True,
        choices=tuple(_TIER_DOC_FILENAMES),
    )
    p.add_argument(
        "--target",
        required=True,
        help="Tier target (concern: <package>/<concern>; package-*: <package>)",
    )
    p.add_argument("--devforge-dir", default=".devforge")
    p.add_argument(
        "--split",
        action="store_true",
        help=(
            "Plan F 3a — tier=concern only: validate the split-parent shape "
            "(Purpose + Sub-concerns; NO Structure) instead of the leaf-concern "
            "shape. Each Sub-concerns bullet must match the locked "
            "`- <name> — <summary> ([→](<doc_path>))` form + each doc_path must "
            "resolve to a rendered child doc."
        ),
    )
