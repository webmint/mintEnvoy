"""Per-source-file .md skeleton flow for the per-md validator-loop Part B architecture.

This module owns:
  - `render-file-skeletons` subcommand (Step B.1 of VALIDATOR-LOOP-B-PLAN.md):
    walks index.json and writes empty .md skeletons as filesystem forcing function.
  - `write-file-doc` subcommand (Step B.3 of VALIDATOR-LOOP-B-PLAN.md):
    fills a skeleton with structured front-matter + body header. The LLM calls
    this helper instead of using the Write tool freehand — helper-owns-shape.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional

from generate_docs_schema import ANNOTATION_CONFIDENCE_VALUES

from ._md_frontmatter import render_frontmatter
from ._render import _project_root
from ._setters_concern import _load_index_files, _path_contains_trivial_dir
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_concern,
    _require_package,
    _state_file_path,
)
from ._validation import _validate_in_enum, _validate_string
from ._validators_file_doc import _recompute_content_hash


def cmd_render_file_skeletons(args: argparse.Namespace) -> int:
    """Walk index.json files for the concern subfolder; write empty .md skeletons.

    B.1 is filesystem-only — no state mutation occurs. The index.json is the
    authoritative file list; a missing index is a hard failure (DO NOT degrade
    gracefully) because without it the skeleton set is incomplete and the B.2
    forcing function breaks.
    """
    try:
        _validate_string(args.package, "--package")
        _validate_string(args.concern, "--concern")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)

    if _require_package(state, args.package) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.package
            ),
            code=2,
        )

    if _require_concern(state, args.package, args.concern) is None:
        return _die(
            "concern {0!r} not registered under {1}; run add-concern first".format(
                args.concern, args.package
            ),
            code=2,
        )

    devforge_dir = _state_file_path().parent
    project_root = _project_root()

    files = _load_index_files(devforge_dir, args.package)
    # DO NOT degrade gracefully on missing index — see B.1 §step 5. The index
    # is the structural backbone; silent skip would break the Part-B forcing
    # function entirely.
    if files is None:
        return _die(
            "index.json missing or package {0!r} not in index"
            " — run init-forge build-index first".format(args.package),
            code=2,
        )

    subfolder_prefix = "src/{0}/".format(args.concern)

    created = 0
    preexisting = 0
    any_matched = False

    for rel_path in files:
        if not rel_path.startswith(subfolder_prefix):
            continue
        if _path_contains_trivial_dir(rel_path):
            continue

        suffix = rel_path[len(subfolder_prefix):]
        # Skip directory-only entries (rel_path equals subfolder_prefix exactly).
        # Without this guard the target would become "<docs>/<P>/<C>/.md" — a
        # spurious hidden dotfile.
        if not suffix:
            continue
        any_matched = True
        target = (
            project_root
            / "docs"
            / args.package
            / args.concern
            / (suffix + ".md")
        )

        if target.exists():
            preexisting += 1
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"")
        except OSError as err:
            return _die(
                "failed to write {0}: {1}".format(target, err),
                code=1,
            )
        created += 1

    if not any_matched:
        sys.stderr.write(
            "render-file-skeletons: no source files under {0} for {1}/{2}"
            " — concern subfolder may not exist\n".format(
                subfolder_prefix, args.package, args.concern
            )
        )

    sys.stdout.write(
        "render-file-skeletons {0}/{1}: created={2} preexisting={3}\n".format(
            args.package, args.concern, created, preexisting
        )
    )
    return 0


def cmd_write_file_doc(args: argparse.Namespace) -> int:
    """Fill a per-source-file .md with structured front-matter + body header.

    Helper computes content_hash from the cite-file:start..end slice (same
    hash logic as the validator's _recompute_content_hash) so the LLM never
    authors hash values. Overwrites
    existing content unconditionally: this is the fill operation; the skeleton
    written by B.1 is intentionally replaced here.

    Exit codes:
      0 — success (file written)
      2 — validation failure (incl. cite range out-of-bounds)
      1 — OS error / cite-file not readable
    """
    # --- Boundary validation ---
    try:
        _validate_string(args.md_path, "write-file-doc --md-path")
        _validate_string(args.label, "write-file-doc --label")
        _validate_in_enum(
            args.confidence,
            ANNOTATION_CONFIDENCE_VALUES,
            "write-file-doc --confidence",
        )
        _validate_string(args.cite_file, "write-file-doc --cite-file")
        _validate_string(args.model_version, "write-file-doc --model-version")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        cite_start = int(args.cite_start)
        cite_end = int(args.cite_end)
    except (TypeError, ValueError) as err:
        return _die(
            "write-file-doc --cite-start/--cite-end: must be integers: {0}".format(err),
            code=2,
        )

    if cite_start < 1:
        return _die(
            "write-file-doc --cite-start: must be >= 1, got {0}".format(cite_start),
            code=2,
        )
    if cite_end < cite_start:
        return _die(
            "write-file-doc --cite-end ({0}) must be >= --cite-start ({1})".format(
                cite_end, cite_start
            ),
            code=2,
        )

    # --- Resolve target md path ---
    md_path = Path(args.md_path)
    if not md_path.is_absolute():
        md_path = _project_root() / md_path

    # --- Resolve cite-file + compute content_hash ---
    cite_path = Path(args.cite_file)
    if not cite_path.is_absolute():
        cite_path = _project_root() / cite_path
    if not cite_path.exists():
        return _die(
            "write-file-doc: cite-file not found: {0}".format(cite_path),
            code=2,
        )
    try:
        content_hash = _recompute_content_hash(cite_path, cite_start, cite_end)
    except ValueError as err:
        return _die(
            "write-file-doc: {0}".format(err),
            code=2,
        )
    except OSError as err:
        return _die(
            "write-file-doc: cannot read cite-file {0}: {1}".format(cite_path, err),
            code=1,
        )

    # --- Build record and render ---
    record = {
        "label": args.label,
        "confidence": args.confidence,
        "evidence_file": args.cite_file,
        "evidence_start": cite_start,
        "evidence_end": cite_end,
        "content_hash": content_hash,
        "model_version": args.model_version,
    }

    # Body header: the original source filename (md_path minus the trailing .md).
    filename = md_path.name
    if filename.endswith(".md"):
        source_name = filename[:-3]
    else:
        source_name = filename
    body_header = "# {0}\n".format(source_name)

    try:
        content = render_frontmatter(record, body_header)
    except ValueError as err:
        return _die(str(err), code=2)

    # --- Write file (overwrite; no idempotency guard per spec) ---
    try:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(content, encoding="utf-8")
    except OSError as err:
        return _die(
            "write-file-doc: failed to write {0}: {1}".format(md_path, err),
            code=1,
        )

    nbytes = len(content.encode("utf-8"))
    sys.stdout.write(
        "write-file-doc {0}: {1} bytes\n".format(md_path, nbytes)
    )
    return 0
