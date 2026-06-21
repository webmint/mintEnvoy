"""Concern + package + render-doc handlers + their argparse builders.

`_merge_project_skeleton` lives here too — it's used by `cmd_init_doc`
and depends on `_replace_or_substitute` from `_blocks`, so co-locating
it with `cmd_init_doc` keeps the import DAG clean (no
`_skeletons → _blocks` back-edge).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .._md_frontmatter import FrontmatterParseError, parse_frontmatter, render_frontmatter
from ._blocks import (
    _interleave_annotations,
    _replace_concerns_block,
    _replace_cross_cuts_block,
    _replace_files_block,
    _replace_layers_block,
    _replace_or_substitute,
    _replace_packages_block,
    _replace_patterns_block,
    _replace_purpose_block,
    _replace_subconcerns_block,
    _TREE_FENCE_OPEN,
)
from ._renderers import (
    _decode_entry_list,
    _render_concerns_bullets,
    _render_files_bullets,
    _render_layers_bullets,
    _render_patterns_bullets,
    _render_subconcerns_bullets,
)
from ._skeletons import (
    _PROJECT_ARCHITECTURE_OWNED_ANCHORS,
    _PROJECT_OVERVIEW_OWNED_ANCHORS,
    _VALID_TIERS,
    _build_concern_skeleton,
    _build_concern_split_skeleton,
    _build_package_architecture_skeleton,
    _build_package_overview_skeleton,
    _build_project_architecture_skeleton,
    _build_project_overview_skeleton,
    _common_target_args,
    _doc_path_for,
    _load_active,
    _skeleton_path,
)


def _merge_project_skeleton(
    doc_path: Path,
    fresh_skeleton: str,
    owned_anchors_with_placeholders: Tuple[Tuple[str, str], ...],
) -> str:
    """Merge an existing project-tier doc with a freshly built skeleton.

    Cold start (file missing or unparseable): return ``fresh_skeleton``
    verbatim — caller writes it as-is.

    Existing file (typical case): preserve the entire existing body
    EXCEPT the owned-anchor sections (those are reset to placeholders so
    setters can refill cleanly). Frontmatter is merged: existing keys
    stay; fresh keys (e.g. ``last_indexed``, ``source_stamp``) override.

    Owned anchors that don't exist in the existing file (cold-install
    stubs that haven't been touched by /generate-docs yet) are appended
    in their declared order at the end of the body.

    Owned anchors that DO exist in the existing file are reset in-place
    via the same regex `_replace_or_substitute` setters use — body
    becomes ``<!-- TODO: ... -->`` placeholder again, ready for the
    setter to replace.
    """
    # Cold start: no existing file → use fresh skeleton verbatim.
    if not doc_path.is_file():
        return fresh_skeleton
    try:
        existing_text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return fresh_skeleton

    try:
        existing_fm, existing_body = parse_frontmatter(existing_text)
    except FrontmatterParseError:
        # Stub file may ship without frontmatter (install-shipped stubs at
        # docs/overview.md / docs/architecture.md have an H1 + section
        # anchors but no `---` block). Treat the whole file as body and
        # take frontmatter exclusively from the fresh skeleton.
        existing_fm = {}
        existing_body = existing_text

    try:
        fresh_fm, _fresh_body = parse_frontmatter(fresh_skeleton)
    except FrontmatterParseError:  # pragma: no cover — fresh always parses
        return fresh_skeleton

    merged_fm: Dict[str, Any] = {**existing_fm, **fresh_fm}

    # Normalize edge whitespace so re-runs are byte-stable.
    body = existing_body.strip("\n")

    # First pass: determine which declared anchors already exist in body.
    def _anchor_in_body(anchor: str, text: str) -> bool:
        return bool(re.search(
            r"^## " + re.escape(anchor) + r"( \(|$|\n)",
            text,
            re.MULTILINE,
        ))

    existing_anchors: set = {
        anchor
        for anchor, _ in owned_anchors_with_placeholders
        if _anchor_in_body(anchor, body)
    }

    # Second pass: process each declared anchor in order.
    for idx, (anchor, placeholder) in enumerate(owned_anchors_with_placeholders):
        if anchor in existing_anchors:
            # Anchor is present: reset its content to the placeholder.
            body = _replace_or_substitute(body, placeholder, anchor, placeholder)
        else:
            # Anchor is missing: find the first later-declared anchor that
            # currently exists in the body (or was already inserted).
            insertion_target: Optional[str] = None
            for later_anchor, _ in owned_anchors_with_placeholders[idx + 1:]:
                if later_anchor in existing_anchors:
                    insertion_target = later_anchor
                    break

            new_section = f"## {anchor}\n\n{placeholder}"
            if insertion_target is not None:
                # Insert immediately before the insertion_target heading.
                target_pattern = re.compile(
                    r"^## " + re.escape(insertion_target) + r"\b",
                    re.MULTILINE,
                )
                m = target_pattern.search(body)
                if m:
                    insert_pos = m.start()
                    # Ensure two newlines of separation on both sides.
                    before = body[:insert_pos].rstrip("\n")
                    after = body[insert_pos:]
                    body = before + "\n\n" + new_section + "\n\n" + after
                    # Collapse runs of 3+ newlines to exactly 2.
                    body = re.sub(r"\n{3,}", "\n\n", body)
                else:
                    # Fallback: insertion_target not found by regex → append.
                    body = body.rstrip("\n") + "\n\n" + new_section
            else:
                # No later anchor in body → append at end.
                body = body.rstrip("\n") + "\n\n" + new_section

            # Mark this anchor as now existing so subsequent missing anchors
            # can use it as an insertion target.
            existing_anchors.add(anchor)

        body = body.rstrip("\n")

    return render_frontmatter(merged_fm, "\n" + body + "\n")


def cmd_init_doc(args: argparse.Namespace) -> int:
    if args.tier not in _VALID_TIERS:
        print(f"unknown tier {args.tier!r}", file=sys.stderr)
        return 2
    try:
        frontmatter = json.loads(args.frontmatter)
    except json.JSONDecodeError as exc:
        print(f"--frontmatter must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(frontmatter, dict):
        print("--frontmatter must decode to a JSON object", file=sys.stderr)
        return 2

    is_split = bool(getattr(args, "split", False))
    if is_split and args.tier != "concern":
        print(
            f"--split is only valid with tier=concern; got tier={args.tier!r}",
            file=sys.stderr,
        )
        return 2

    if args.tier == "concern":
        if is_split:
            # Parent concern doc: aggregator with Sub-concerns + Purpose.
            # NO `## Structure` (children carry their own trees) → --tree
            # is ignored when --split true.
            skeleton_text = _build_concern_split_skeleton(frontmatter)
        else:
            if not args.tree:
                print(
                    "--tree is required for tier=concern (pass concern-input's tree_text)",
                    file=sys.stderr,
                )
                return 2
            skeleton_text = _build_concern_skeleton(frontmatter, args.tree)
    elif args.tier == "package-overview":
        skeleton_text = _build_package_overview_skeleton(frontmatter)
    elif args.tier == "package-architecture":
        skeleton_text = _build_package_architecture_skeleton(frontmatter)
    elif args.tier == "project-overview":
        skeleton_text = _build_project_overview_skeleton(frontmatter, args.target)
    elif args.tier == "project-architecture":
        skeleton_text = _build_project_architecture_skeleton(frontmatter, args.target)
    else:  # pragma: no cover — guard above already filters
        print(f"unhandled tier {args.tier!r}", file=sys.stderr)
        return 2

    doc_path = _doc_path_for(args)

    # Project-tier docs may carry user/constitute-owned anchors alongside
    # generate-docs's own. Merge instead of wholesale-overwrite so those
    # anchors survive re-runs. Concern + package tiers are 100%
    # generate-docs territory — wholesale overwrite stays correct there.
    if args.tier == "project-overview":
        skeleton_text = _merge_project_skeleton(
            doc_path, skeleton_text, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
    elif args.tier == "project-architecture":
        skeleton_text = _merge_project_skeleton(
            doc_path, skeleton_text, _PROJECT_ARCHITECTURE_OWNED_ANCHORS
        )

    skel_path = _skeleton_path(doc_path)
    skel_path.parent.mkdir(parents=True, exist_ok=True)
    skel_path.write_text(skeleton_text, encoding="utf-8")
    if doc_path.is_file():
        doc_path.unlink()
    print(str(skel_path))
    return 0


def cmd_set_doc_purpose(args: argparse.Namespace) -> int:
    if args.tier not in ("concern", "package-overview", "project-overview"):
        print(
            f"set-doc-purpose supports tier in (concern, package-overview, project-overview); "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc at {doc_path} or {_skeleton_path(doc_path)} — run init-doc first",
            file=sys.stderr,
        )
        return 2
    new_content = _replace_purpose_block(content, args.text)
    path.write_text(new_content, encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_structure(args: argparse.Namespace) -> int:
    if args.tier != "concern":
        print(
            f"set-doc-structure supports tier=concern only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    annotations: Dict[str, str] = {}
    if args.annotations:
        try:
            decoded = json.loads(args.annotations)
        except json.JSONDecodeError as exc:
            print(f"--annotations must be valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(decoded, dict):
            print("--annotations must decode to a JSON object", file=sys.stderr)
            return 2
        annotations = {str(k): str(v) for k, v in decoded.items()}

    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc at {doc_path} — run init-doc first",
            file=sys.stderr,
        )
        return 2
    if _TREE_FENCE_OPEN not in content:
        print(
            f"no `{_TREE_FENCE_OPEN}` code fence in {path}; init-doc first",
            file=sys.stderr,
        )
        return 2
    new_content = _interleave_annotations(content, annotations)
    path.write_text(new_content, encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_concerns(args: argparse.Namespace) -> int:
    if args.tier != "package-overview":
        print(
            f"set-doc-concerns supports tier=package-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.concerns, "concerns")
    if entries is None:
        return 2
    bullet_text = _render_concerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_concerns_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_files(args: argparse.Namespace) -> int:
    if args.tier != "package-overview":
        print(
            f"set-doc-files supports tier=package-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.files, "files")
    if entries is None:
        return 2
    bullet_text = _render_files_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_files_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_layers(args: argparse.Namespace) -> int:
    if args.tier not in ("package-architecture", "project-architecture"):
        print(
            f"set-doc-layers supports tier in (package-architecture, project-architecture); "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.layers, "layers")
    if entries is None:
        return 2
    bullet_text = _render_layers_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_layers_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_patterns(args: argparse.Namespace) -> int:
    if args.tier != "package-architecture":
        print(
            f"set-doc-patterns supports tier=package-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.patterns, "patterns")
    if entries is None:
        return 2
    bullet_text = _render_patterns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_patterns_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_packages(args: argparse.Namespace) -> int:
    if args.tier != "project-overview":
        print(
            f"set-doc-packages supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.packages, "packages")
    if entries is None:
        return 2
    bullet_text = _render_concerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_packages_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_cross_cuts(args: argparse.Namespace) -> int:
    if args.tier != "project-architecture":
        print(
            f"set-doc-cross-cuts supports tier=project-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.cross_cuts, "cross-cuts")
    if entries is None:
        return 2
    bullet_text = _render_concerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_cross_cuts_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_doc_subconcerns(args: argparse.Namespace) -> int:
    """Plan F 3a: write the parent concern's `## Sub-concerns` bulleted list."""
    if args.tier != "concern":
        print(
            f"set-doc-subconcerns supports tier=concern only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.subconcerns, "subconcerns")
    if entries is None:
        return 2
    bullet_text = _render_subconcerns_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(
            f"no skeleton or doc at {doc_path} or {_skeleton_path(doc_path)} — "
            "run init-doc --split true first",
            file=sys.stderr,
        )
        return 2
    if "## Sub-concerns" not in content:
        print(
            f"{path} has no `## Sub-concerns` section — was init-doc called "
            "with --split true?",
            file=sys.stderr,
        )
        return 2
    path.write_text(_replace_subconcerns_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_render_doc(args: argparse.Namespace) -> int:
    if args.tier not in _VALID_TIERS:
        print(f"unknown tier {args.tier!r}", file=sys.stderr)
        return 2
    doc_path = _doc_path_for(args)
    if args.out:
        doc_path = Path(args.out)
    skel_path = _skeleton_path(doc_path)
    if not skel_path.is_file():
        print(f"no skeleton at {skel_path} — run init-doc first", file=sys.stderr)
        return 2
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(str(skel_path), str(doc_path))
    print(str(doc_path))
    return 0


# ── argparse factories ──────────────────────────────────────────────────────


def _build_init_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, _VALID_TIERS)
    p.add_argument("--frontmatter", required=True, help="JSON object of frontmatter key/value pairs")
    p.add_argument(
        "--tree",
        default="",
        help="ASCII tree text (REQUIRED for tier=concern unless --split true)",
    )
    p.add_argument(
        "--split",
        action="store_true",
        help=(
            "tier=concern only: emit parent-aggregator skeleton (Purpose + "
            "Sub-concerns; no Structure). Used by Plan F 3a split-dispatch."
        ),
    )


def _build_set_doc_purpose(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern", "package-overview", "project-overview"))
    p.add_argument("--text", required=True)


def _build_set_doc_structure(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern",))
    p.add_argument(
        "--annotations",
        default="",
        help="JSON object {leaf_basename: annotation_text}",
    )


def _build_set_doc_concerns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-overview",))
    p.add_argument(
        "--concerns",
        required=True,
        help='JSON array [{"name": "...", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_files(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-overview",))
    p.add_argument(
        "--files",
        required=True,
        help='JSON array [{"name": "<basename>", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_layers(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-architecture", "project-architecture"))
    p.add_argument(
        "--layers",
        required=True,
        help='JSON array [{"name": "...", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_patterns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("package-architecture",))
    p.add_argument(
        "--patterns",
        required=True,
        help='JSON array [{"name": "...", "rule": "...", "cite": "..."}]',
    )


def _build_set_doc_packages(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--packages",
        required=True,
        help='JSON array [{"name": "<pkg-path>", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_cross_cuts(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--cross-cuts",
        dest="cross_cuts",
        required=True,
        help='JSON array [{"name": "...", "role": "...", "cite": "..."}]',
    )


def _build_set_doc_subconcerns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("concern",))
    p.add_argument(
        "--subconcerns",
        required=True,
        help=(
            'JSON array [{"name": "<>", "purpose_summary": "<>", '
            '"doc_path": "<rel-path-to-child-index.md>"}]'
        ),
    )


def _build_render_doc(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, _VALID_TIERS)
    p.add_argument(
        "--out",
        default="",
        help="Output path override (default: docs/<target>/<tier-filename>)",
    )
