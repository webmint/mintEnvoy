"""concern-input helper.

Walks the concern's source subfolder on disk, emits batch JSON consumed
by the /generate-docs orchestrator's concern-tier compose step.

Why filesystem and not index.json: /init-forge's index.json caps file lists
at 500 entries per package (`files_truncated: true` flag). On real
monorepos (testForge20 app hits the cap), the helpers/ subfolder falls
past the cap and would be invisible to a fully indexed.json-driven helper.
The trivial-leaf skip rule (`_path_contains_trivial_dir`) is applied during
the walk so node_modules/dist/etc. stay excluded.

Output shape (single-batch, default for small concerns):
    {
      "concern": "<name>",
      "package": "<package-path>",
      "subfolder": "<package>/src/<concern>/",
      "tree_text": "<ASCII tree, subfolder-relative>",
      "files": [{"path": "<project-rel>", "comment_rich_span": "<...>"}, ...],
      "source_stamp": "<sha256-prefix-16>",
      "truncated": true   # OPTIONAL: present when batch cap was hit
    }

Output shape (split-batch, when concern exceeds split threshold AND has ≥2
immediate child dirs — Plan F 3a):
    {
      "concern": "<parent name>",
      "package": "<package-path>",
      "subfolder": "<package>/src/<concern>/",
      "split": true,
      "parent_meta": {
        "tree_text": "<full ASCII tree of parent>",
        "subconcern_names": ["<child1>", "<child2>", ...],
        "loose_files": ["<rel>", ...]   # files at concern root, not in any subdir
      },
      "sub_concerns": [
        {
          "concern": "<child name>",
          "parent_concern": "<parent name>",
          "package": "<package-path>",
          "subfolder": "<package>/src/<concern>/<child>/",
          "tree_text": "...",
          "files": [...],
          "source_stamp": "..."
        },
        ...
      ],
      "source_stamp": "<aggregate sha256-prefix-16>"
    }

`source_stamp` (single-batch) is a SHA-256 prefix over sorted
(path, content_hash) pairs. Aggregate stamp (split-batch) is a SHA-256
prefix over sorted (sub_concern stamps + loose-file content hashes).
F.0 preflight uses these for incremental skip when re-running /generate-docs.

Split decision (Plan F 3a, 2026-05-08):
- Default threshold: 50 KB total span data (`--split-threshold-kb 50`).
- `--split-threshold-kb 0` disables split (always single-batch).
- Split fires only if total > threshold AND ≥ 2 immediate child dirs.
- Loose files (depth-0 files at concern root) are listed in `parent_meta.loose_files`
  but get no separate sub_concern doc in v0; orchestrator may surface them inline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

from ._setters_concern import _path_contains_trivial_dir

_PER_FILE_SPAN_CAP = 6 * 1024
_BATCH_SPAN_CAP = 60 * 1024
_TOP_LINE_COUNT = 30
_HAZARD_MARKERS = ("TODO", "FIXME", "HACK", "WARNING", "XXX")
_HAZARD_CONTEXT_BEFORE = 2
_HAZARD_CONTEXT_AFTER = 2

_DEFAULT_SPLIT_THRESHOLD_KB = 50


def _build_tree(concern_files: List[str], subfolder_prefix: str) -> str:
    """Build an ASCII tree from project-relative paths under subfolder_prefix.

    The first line is the subfolder header (e.g., `src/order/`). Subsequent
    lines use box-drawing connectors (├──/└──/│) with directories grouped
    above leaves at each level.
    """
    rels = sorted(
        {f[len(subfolder_prefix):] for f in concern_files if f.startswith(subfolder_prefix)}
    )
    root: Dict[str, object] = {}
    for rel in rels:
        parts = rel.split("/")
        node: Dict[str, object] = root
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = None  # leaf marker

    out_lines = [subfolder_prefix.rstrip("/") + "/"]

    def _walk(branch: Dict[str, object], prefix: str) -> None:
        # Directories before leaves; alphabetical within each group.
        items = sorted(
            branch.items(),
            key=lambda kv: (kv[1] is None, kv[0]),
        )
        for i, (name, child) in enumerate(items):
            last = i == len(items) - 1
            connector = "└── " if last else "├── "
            out_lines.append(f"{prefix}{connector}{name}")
            if isinstance(child, dict):
                ext_prefix = prefix + ("    " if last else "│   ")
                _walk(child, ext_prefix)

    _walk(root, "")
    return "\n".join(out_lines)


def _extract_comment_rich_span(content: str, max_bytes: int) -> str:
    """Extract top-of-file + hazard-marker context, capped at max_bytes.

    Always returns top _TOP_LINE_COUNT lines. For each line beyond the top
    that contains a hazard marker (TODO/FIXME/HACK/WARNING/XXX), include
    a small context window. Overlapping windows merge. Output uses 1-based
    line numbers; gaps between non-adjacent windows are marked with `...`.
    """
    if not content:
        return ""
    lines = content.split("\n")
    n = len(lines)
    top_end = min(_TOP_LINE_COUNT, n)
    ranges: List[Tuple[int, int]] = [(0, top_end)]
    for idx, line in enumerate(lines):
        if idx < top_end:
            continue
        for marker in _HAZARD_MARKERS:
            if marker in line:
                start = max(0, idx - _HAZARD_CONTEXT_BEFORE)
                end = min(n, idx + _HAZARD_CONTEXT_AFTER + 1)
                ranges.append((start, end))
                break
    ranges.sort()
    merged: List[Tuple[int, int]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    out: List[str] = []
    for i, (start, end) in enumerate(merged):
        if i > 0 and merged[i - 1][1] < start:
            out.append("...")
        for ln in range(start, end):
            out.append(f"{ln + 1:>4}: {lines[ln]}")
    span = "\n".join(out)
    if len(span.encode("utf-8")) > max_bytes:
        # Truncate at codepoint boundary near max_bytes.
        encoded = span.encode("utf-8")[:max_bytes]
        # Drop possibly-incomplete trailing UTF-8 byte sequence.
        try:
            span = encoded.decode("utf-8")
        except UnicodeDecodeError:
            span = encoded.decode("utf-8", errors="ignore")
        span = span.rstrip() + "\n...<file span truncated>"
    return span


def _build_spans_and_stamp(
    concern_files: List[str],
    project_root: Path,
    batch_cap: Optional[int] = _BATCH_SPAN_CAP,
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]], str]:
    """Read each file, extract comment-rich span, compute aggregate stamp.

    Returns (file_records, file_hashes, source_stamp).
    - file_records: ``[{"path": rel, "comment_rich_span": "..."}, ...]``
    - file_hashes:  ``[(rel, content_sha256_hex), ...]`` (sub-concern
      stamping uses a subset of these)
    - source_stamp: 16 hex chars of SHA-256 over sorted ``<rel>\\t<hash>``
      lines; deterministic across runs and input orderings (relies on
      upstream ``.as_posix()`` for cross-platform path normalization).

    ``batch_cap=None`` disables the per-batch span cap (every file gets
    its full extracted span). Used by the split-decision path so the
    caller can measure true total size before deciding whether to split.
    """
    file_records: List[Dict[str, str]] = []
    file_hashes: List[Tuple[str, str]] = []
    total_span_bytes = 0
    for rel in sorted(concern_files):
        abs_path = project_root / rel
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            file_hashes.append((rel, ""))
            file_records.append({"path": rel, "comment_rich_span": "<unreadable>"})
            continue
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        file_hashes.append((rel, content_hash))
        if batch_cap is not None and total_span_bytes >= batch_cap:
            file_records.append(
                {"path": rel, "comment_rich_span": "<...batch cap reached, span omitted...>"}
            )
            continue
        span = _extract_comment_rich_span(content, _PER_FILE_SPAN_CAP)
        total_span_bytes += len(span.encode("utf-8"))
        file_records.append({"path": rel, "comment_rich_span": span})

    stamp_input = "\n".join(f"{p}\t{h}" for p, h in sorted(file_hashes))
    source_stamp = hashlib.sha256(stamp_input.encode("utf-8")).hexdigest()[:16]
    return file_records, file_hashes, source_stamp


def _apply_batch_cap_to_records(
    records: List[Dict[str, str]], cap_bytes: int
) -> Tuple[List[Dict[str, str]], bool]:
    """Re-apply batch cap to a pre-built record list.

    Used by the split path when emitting a sub_concern: each sub_concern
    gets its own 60 KB cap so well-sized children never lose content even
    if the parent's total exceeded the threshold.

    Returns (capped_records, truncated_flag).
    """
    out: List[Dict[str, str]] = []
    total = 0
    truncated = False
    for r in records:
        span_bytes = len(r["comment_rich_span"].encode("utf-8"))
        if total >= cap_bytes:
            out.append(
                {"path": r["path"], "comment_rich_span": "<...batch cap reached, span omitted...>"}
            )
            truncated = True
            continue
        out.append(r)
        total += span_bytes
    return out, truncated


def _enumerate_immediate_dirs(subfolder_abs: Path, project_root: Path) -> List[str]:
    """Return alphabetical names of immediate child DIRs under subfolder_abs.

    Trivial-leaf dirs (node_modules, dist, etc.) are excluded so the
    split decision matches what the surviving file walk produces.
    """
    if not subfolder_abs.is_dir():
        return []
    out: List[str] = []
    for entry in sorted(subfolder_abs.iterdir()):
        if not entry.is_dir():
            continue
        try:
            rel = entry.relative_to(project_root).as_posix()
        except ValueError:
            continue
        # Pass a path with a trailing component so the trivial check sees the dir name.
        if _path_contains_trivial_dir(rel + "/x"):
            continue
        out.append(entry.name)
    return out


def _partition_files_by_immediate_dir(
    concern_files: List[str], subfolder_prefix: str, immediate_dirs: List[str]
) -> Tuple[Dict[str, List[str]], List[str]]:
    """Split concern_files into per-immediate-dir groups + a loose-file list.

    Returns (subdir_groups, loose_files).
    - subdir_groups[name] = files whose path under ``subfolder_prefix``
      starts with ``<name>/``.
    - loose_files: rel paths directly under ``subfolder_prefix`` with
      no further dir component.
    """
    subdir_groups: Dict[str, List[str]] = {d: [] for d in immediate_dirs}
    immediate_set = set(immediate_dirs)
    loose: List[str] = []
    for rel in concern_files:
        if not rel.startswith(subfolder_prefix):
            continue
        tail = rel[len(subfolder_prefix):]
        if "/" not in tail:
            loose.append(rel)
            continue
        first_dir = tail.split("/", 1)[0]
        if first_dir in immediate_set:
            subdir_groups[first_dir].append(rel)
        # Files under a trivial-leaf dir that survived the walk would land here
        # (defensive — _walk_concern_subfolder already filters them).
    return subdir_groups, loose


def _build_sub_concern(
    parent_concern: str,
    package: str,
    parent_subfolder_prefix: str,
    child_name: str,
    child_files: List[str],
    all_records: List[Dict[str, str]],
    all_hashes: List[Tuple[str, str]],
) -> Dict[str, object]:
    """Compose one sub_concern dict from pre-extracted records.

    Avoids re-reading files: the parent's uncapped pass already extracted
    every span. We just slice + re-cap per child + reuse `_stamp_from_hashes`
    so the per-child stamp formula stays in lockstep with F.0 preflight.
    """
    child_subfolder_prefix = f"{parent_subfolder_prefix}{child_name}/"
    child_set = set(child_files)
    child_records = [r for r in all_records if r["path"] in child_set]
    child_hashes = [(p, h) for p, h in all_hashes if p in child_set]
    capped_records, truncated = _apply_batch_cap_to_records(child_records, _BATCH_SPAN_CAP)
    source_stamp = _stamp_from_hashes(child_hashes)
    sub: Dict[str, object] = {
        "concern": child_name,
        "parent_concern": parent_concern,
        "package": package,
        "subfolder": child_subfolder_prefix,
        "tree_text": _build_tree(child_files, child_subfolder_prefix),
        "files": capped_records,
        "source_stamp": source_stamp,
    }
    if truncated:
        sub["truncated"] = True
    return sub


def _aggregate_stamp(parts: List[str]) -> str:
    """SHA-256 prefix-16 over ``"\\n".join(sorted(parts))``."""
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()[:16]


def _stamp_from_hashes(hashes: List[Tuple[str, str]]) -> str:
    """SHA-256 prefix-16 over sorted ``<path>\\t<content_sha256>`` lines.

    Same formula `_build_spans_and_stamp` uses internally; exposed for
    callers that already have the (path, hash) pairs in hand (e.g.,
    F.0 preflight reusing a parent walk's hashes to stamp a sub_concern
    subset without re-reading the files).
    """
    return hashlib.sha256(
        "\n".join(f"{p}\t{h}" for p, h in sorted(hashes)).encode("utf-8")
    ).hexdigest()[:16]


def _walk_concern_subfolder(
    project_root: Path, pkg: str, concern: str
) -> Tuple[Path, List[str]]:
    """Walk <project_root>/<pkg>/src/<concern>/ recursively.

    Returns (subfolder_abs, project_relative_paths). Files whose path
    contains a trivial-leaf directory (per `_path_contains_trivial_dir`)
    are skipped. Hidden dotfile-prefixed dirs are NOT skipped (callers
    supply --concern explicitly; not a wildcard scan).
    """
    subfolder_abs = (project_root / pkg / "src" / concern).resolve()
    rels: List[str] = []
    if not subfolder_abs.is_dir():
        return subfolder_abs, rels
    for path in sorted(subfolder_abs.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(project_root).as_posix()
        except ValueError:
            continue
        if _path_contains_trivial_dir(rel):
            continue
        rels.append(rel)
    return subfolder_abs, rels


def cmd_concern_input(args: argparse.Namespace) -> int:
    """Handler for `concern-input` subcommand. Returns CLI exit code."""
    devforge_dir = Path(args.devforge_dir)
    pkg = args.package
    concern = args.concern
    threshold_kb: int = getattr(args, "split_threshold_kb", _DEFAULT_SPLIT_THRESHOLD_KB)
    project_root = devforge_dir.parent.resolve()

    subfolder_abs, concern_files = _walk_concern_subfolder(project_root, pkg, concern)
    if not concern_files:
        if not subfolder_abs.is_dir():
            print(
                f"concern subfolder not found: {subfolder_abs} "
                f"(expected <project_root>/{pkg}/src/{concern}/)",
                file=sys.stderr,
            )
        else:
            print(
                f"concern {concern!r} subfolder is empty (or all files are "
                f"trivial-leaf): {subfolder_abs}",
                file=sys.stderr,
            )
        return 2

    subfolder_prefix = str(PurePosixPath(pkg) / "src" / concern) + "/"

    # Split-aware path: build all spans uncapped first so we can measure
    # true total size + regroup by child dir if we decide to split.
    split_enabled = threshold_kb > 0
    immediate_dirs: List[str] = []
    should_split = False
    all_records: List[Dict[str, str]] = []
    all_hashes: List[Tuple[str, str]] = []
    if split_enabled:
        all_records, all_hashes, _full_stamp = _build_spans_and_stamp(
            concern_files, project_root, batch_cap=None
        )
        total_bytes = sum(
            len(r["comment_rich_span"].encode("utf-8")) for r in all_records
        )
        threshold_bytes = threshold_kb * 1024
        immediate_dirs = _enumerate_immediate_dirs(subfolder_abs, project_root)
        should_split = total_bytes > threshold_bytes and len(immediate_dirs) >= 2

    loose_files: List[str] = []
    sub_concerns: List[Dict[str, object]] = []
    if should_split:
        subdir_groups, loose_files = _partition_files_by_immediate_dir(
            concern_files, subfolder_prefix, immediate_dirs
        )
        sub_stamps: List[str] = []
        for child_name in immediate_dirs:
            child_files = subdir_groups.get(child_name, [])
            if not child_files:
                continue
            sc = _build_sub_concern(
                concern, pkg, subfolder_prefix, child_name, child_files,
                all_records, all_hashes,
            )
            sub_concerns.append(sc)
            sub_stamps.append(str(sc["source_stamp"]))

        # Defensive: if every immediate child group ended up empty (only
        # loose files survive the walk), the split branch would emit
        # `split:true, sub_concerns:[]` — a shape no downstream consumer
        # handles. Fall back to single-batch in that case.
        if not sub_concerns:
            should_split = False

    if should_split:
        loose_set = set(loose_files)
        loose_hash_parts = [
            f"{p}\t{h}" for p, h in sorted(all_hashes) if p in loose_set
        ]
        agg_stamp = _aggregate_stamp(sub_stamps + loose_hash_parts)

        parent_meta = {
            "tree_text": _build_tree(concern_files, subfolder_prefix),
            "subconcern_names": [str(sc["concern"]) for sc in sub_concerns],
            "loose_files": sorted(loose_files),
        }

        output: Dict[str, object] = {
            "concern": concern,
            "package": pkg,
            "subfolder": subfolder_prefix,
            "split": True,
            "parent_meta": parent_meta,
            "sub_concerns": sub_concerns,
            "source_stamp": agg_stamp,
        }
    else:
        # Single-batch path. If we already built uncapped records during
        # the split-enabled measurement, re-cap them; otherwise build with
        # the cap applied directly.
        if split_enabled:
            capped_records, truncated = _apply_batch_cap_to_records(
                all_records, _BATCH_SPAN_CAP
            )
            stamp_input = "\n".join(f"{p}\t{h}" for p, h in sorted(all_hashes))
            source_stamp = hashlib.sha256(stamp_input.encode("utf-8")).hexdigest()[:16]
            spans = capped_records
        else:
            spans, _hashes, source_stamp = _build_spans_and_stamp(
                concern_files, project_root
            )
            truncated = any(
                "<...batch cap reached" in r["comment_rich_span"] for r in spans
            )

        tree_text = _build_tree(concern_files, subfolder_prefix)
        output = {
            "concern": concern,
            "package": pkg,
            "subfolder": subfolder_prefix,
            "tree_text": tree_text,
            "files": spans,
            "source_stamp": source_stamp,
        }
        if truncated:
            output["truncated"] = True

    print(json.dumps(output, indent=2))
    return 0


def _build_concern_input(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `concern-input` subcommand."""
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--devforge-dir", default=".devforge")
    p.add_argument(
        "--split-threshold-kb",
        type=int,
        default=_DEFAULT_SPLIT_THRESHOLD_KB,
        help=(
            "Total span data threshold (KB) above which a concern with ≥2 "
            "immediate child dirs gets split into sub_concerns. 0 disables "
            "split (always single-batch). Default 50."
        ),
    )
