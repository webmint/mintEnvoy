"""package-input helper.

Walks `<project_root>/<package>/` and the package's already-rendered
concern docs, emits batch JSON consumed by the /generate-docs
orchestrator's package-tier compose step (Phase 3).

Output shape:
    {
      "package": "<pkg-path>",
      "concern_seeds": [
        {"concern": "<name>", "frontmatter": {...},
         "purpose_text": "<verbatim content under ## Purpose>"},
        ...
      ],
      "package_root_files": [
        {"path": "<pkg>/<file>", "comment_rich_span": "..."},
        ...
      ],
      "source_stamp": "<sha256-prefix-16>"
    }

`concern_seeds` is the list the orchestrator uses to compose the
package overview's `## Concerns` section (each entry's role-line is
sourced from the concern doc's `## Purpose` paragraph) AND the
package architecture's `## Layers` / `## Patterns` sections (concern
groupings inform layer derivation).

`package_root_files` carries top-of-tree files (README, CHANGELOG,
package.json, etc.) — same comment-rich-span shape as F.2 — so the
composer can extract narrative cues without re-reading the source
itself.

`source_stamp` is a SHA-256 prefix over sorted (concern_stamp_pairs +
package_root_file_hashes); F.0/F.4 use it for incremental skip.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._concern_input import _extract_comment_rich_span
from ._md_frontmatter import FrontmatterParseError, parse_frontmatter

_PER_FILE_SPAN_CAP = 6 * 1024
_BATCH_SPAN_CAP = 60 * 1024
_PACKAGE_ROOT_FILES = (
    "README.md",
    "README.txt",
    "README",
    "CHANGELOG.md",
    "CHANGELOG.txt",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "build.gradle",
    "pom.xml",
)
_ROOT_FILE_BATCH_CAP = 60 * 1024
_CONCERN_DOCS_RELATIVE = "docs"


def _enumerate_concerns(project_root: Path, pkg: str) -> List[str]:
    """List direct subdirs of `<project_root>/<pkg>/src/`. Sorted alphabetical."""
    src_dir = (project_root / pkg / "src").resolve()
    if not src_dir.is_dir():
        return []
    out: List[str] = []
    try:
        for entry in sorted(src_dir.iterdir()):
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith(".") or name in ("node_modules", "dist", "build", "target"):
                continue
            out.append(name)
    except OSError:
        return []
    return out


def _read_concern_seed(
    project_root: Path, pkg: str, concern: str
) -> Optional[Dict[str, Any]]:
    """Read frontmatter + Purpose section from the rendered concern doc.

    Returns None when the doc is missing, frontmatter is unparseable, or
    the doc has no `## Purpose` anchor.
    """
    doc_path = project_root / _CONCERN_DOCS_RELATIVE / pkg / concern / "index.md"
    if not doc_path.is_file():
        return None
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError:
        return None
    purpose_text = ""
    lines = body.split("\n")
    in_purpose = False
    purpose_lines: List[str] = []
    for line in lines:
        if line.startswith("## Purpose"):
            in_purpose = True
            continue
        if in_purpose and line.startswith("## "):
            break
        if in_purpose:
            purpose_lines.append(line)
    purpose_text = "\n".join(purpose_lines).strip()
    return {
        "concern": concern,
        "frontmatter": record,
        "purpose_text": purpose_text,
    }


def _collect_package_root_files(
    project_root: Path, pkg: str
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
    """Read package-root files (README, CHANGELOG, package.json, etc.).

    Returns (records, hash_pairs) where records carry comment_rich_span
    extractions and hash_pairs feed the source_stamp computation.
    """
    project_root = project_root.resolve()
    pkg_dir = (project_root / pkg).resolve()
    records: List[Dict[str, str]] = []
    hash_pairs: List[Tuple[str, str]] = []
    if not pkg_dir.is_dir():
        return records, hash_pairs
    total_span_bytes = 0
    for filename in _PACKAGE_ROOT_FILES:
        candidate = pkg_dir / filename
        if not candidate.is_file():
            continue
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = candidate.resolve().relative_to(project_root).as_posix()
        except ValueError:
            rel = candidate.as_posix()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        hash_pairs.append((rel, content_hash))
        if total_span_bytes >= _BATCH_SPAN_CAP:
            records.append({"path": rel, "comment_rich_span": "<...batch cap reached, span omitted...>"})
            continue
        span = _extract_comment_rich_span(content, _PER_FILE_SPAN_CAP)
        total_span_bytes += len(span.encode("utf-8"))
        records.append({"path": rel, "comment_rich_span": span})
    return records, hash_pairs


def _collect_src_root_files(
    project_root: Path, pkg: str
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
    """Walk `<project_root>/<pkg>/src/` for direct files (non-dir).

    Returns (records, hash_pairs). Each record has `path` (project-relative),
    `basename`, and `comment_rich_span` extracted via F.2's helper.
    """
    project_root = project_root.resolve()
    src_dir = (project_root / pkg / "src").resolve()
    records: List[Dict[str, str]] = []
    hash_pairs: List[Tuple[str, str]] = []
    if not src_dir.is_dir():
        return records, hash_pairs
    total_span_bytes = 0
    try:
        entries = sorted(src_dir.iterdir())
    except OSError:
        return records, hash_pairs
    for entry in entries:
        if not entry.is_file():
            continue
        try:
            content = entry.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = entry.resolve().relative_to(project_root).as_posix()
        except ValueError:
            rel = entry.as_posix()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        hash_pairs.append((rel, content_hash))
        if total_span_bytes >= _ROOT_FILE_BATCH_CAP:
            records.append(
                {
                    "path": rel,
                    "basename": entry.name,
                    "comment_rich_span": "<...batch cap reached, span omitted...>",
                }
            )
            continue
        span = _extract_comment_rich_span(content, _PER_FILE_SPAN_CAP)
        total_span_bytes += len(span.encode("utf-8"))
        records.append(
            {"path": rel, "basename": entry.name, "comment_rich_span": span}
        )
    return records, hash_pairs


def _compute_source_stamp(
    concern_seeds: List[Dict[str, Any]],
    package_root_hashes: List[Tuple[str, str]],
    src_root_hashes: List[Tuple[str, str]] = (),
) -> str:
    """Aggregate stamp over concern source_stamps + package-root file hashes
    + src-root file hashes."""
    parts: List[str] = []
    for seed in concern_seeds:
        fm = seed.get("frontmatter") or {}
        c = seed.get("concern", "")
        s = fm.get("source_stamp", "")
        parts.append(f"concern\t{c}\t{s}")
    for path, h in package_root_hashes:
        parts.append(f"root\t{path}\t{h}")
    for path, h in src_root_hashes:
        parts.append(f"src-root\t{path}\t{h}")
    parts.sort()
    blob = "\n".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cmd_package_input(args: argparse.Namespace) -> int:
    """Handler for `package-input` subcommand. Returns CLI exit code."""
    devforge_dir = Path(args.devforge_dir)
    pkg = args.package
    project_root = devforge_dir.parent.resolve()

    concern_names = _enumerate_concerns(project_root, pkg)
    if not concern_names:
        print(
            f"package {pkg!r} has no `src/<concern>/` subdirs at "
            f"{project_root / pkg / 'src'} — verify the package path",
            file=sys.stderr,
        )
        return 2

    concern_seeds: List[Dict[str, Any]] = []
    missing: List[str] = []
    for c in concern_names:
        seed = _read_concern_seed(project_root, pkg, c)
        if seed is None:
            missing.append(c)
            continue
        concern_seeds.append(seed)

    if not concern_seeds:
        print(
            f"no concern docs found under docs/{pkg}/ — run /generate-docs "
            f"on this package's concerns before package-input",
            file=sys.stderr,
        )
        return 2

    root_records, root_hashes = _collect_package_root_files(project_root, pkg)
    src_root_records, src_root_hashes = _collect_src_root_files(project_root, pkg)
    source_stamp = _compute_source_stamp(
        concern_seeds, root_hashes, src_root_hashes
    )

    output: Dict[str, Any] = {
        "package": pkg,
        "concern_seeds": concern_seeds,
        "package_root_files": root_records,
        "src_root_files": src_root_records,
        "source_stamp": source_stamp,
    }
    if missing:
        output["missing_concern_docs"] = missing
    print(json.dumps(output, indent=2))
    return 0


def _build_package_input(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `package-input` subcommand."""
    p.add_argument("--package", required=True)
    p.add_argument("--devforge-dir", default=".devforge")
