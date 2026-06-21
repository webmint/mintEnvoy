"""Phase 5 aggregator gate — verify-all.

Walks every recorded concern doc and every recorded package doc in the
state JSON, invokes `cmd_validate_doc` per path, aggregates results, and
exits 0 (all pass) or 2 (failures; stderr enumerates per-path violations).

Design decisions:
- No per-tier filters — verb always walks the entire state.
- Project-tier docs (docs/overview.md, docs/architecture.md) are
  existence-checked; if absent (Phase 4 not yet run) they are silently
  skipped (no error).  If present they are validated.
- Split-parent concern docs: the split state is NOT stored in state JSON
  (the `default_concern_record` has no `subconcerns` field). We default to
  leaf mode (`split=False`) for every concern.  TODO(orchestrator): if a
  future schema adds a `subconcerns` field, derive split=True from it.
- Aggregation uses `contextlib.redirect_stderr` + `io.StringIO` to capture
  errors produced by `cmd_validate_doc` without writing to the process's
  stderr mid-run; all failures are flushed to stderr at the end.

Stdlib only.  Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
from pathlib import Path
from typing import List, Tuple

from ._state import StateLoadError, _load_state
from ._validate_doc import _TIER_DOC_FILENAMES, _PROJECT_TIERS, cmd_validate_doc


def _build_verify_all(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `verify-all` subcommand.

    Only `--devforge-dir` is accepted (default `.devforge`).  No
    `--tier` / `--target` — the verb walks everything recorded in state.
    """
    p.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge)",
    )


def _validate_one(
    tier: str,
    target: str,
    devforge_dir: str,
    split: bool = False,
) -> List[str]:
    """Call cmd_validate_doc for (tier, target) and return any error lines.

    Captures stderr produced by cmd_validate_doc into a StringIO so
    mid-run partial output doesn't escape to the process stderr.
    Returns a list of error-line strings (empty list = OK).
    """
    args = argparse.Namespace(
        tier=tier,
        target=target,
        devforge_dir=devforge_dir,
        split=split,
    )
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        code = cmd_validate_doc(args)
    if code == 0:
        return []
    raw = buf.getvalue()
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    return lines if lines else [f"validate-doc exited {code} (no stderr)"]


def cmd_verify_all(args: argparse.Namespace) -> int:
    """Handler for `verify-all` subcommand.  Returns CLI exit code.

    Walks state JSON, calls validate-doc per (tier, target), aggregates
    failures.  Exit 0 = everything passes; exit 2 = at least one failure.
    """
    # Honor DEVFORGE_DIR env var (matches _state.py + sibling helpers) when
    # --devforge-dir was not explicitly provided. Tests + Phase 5 callers set
    # DEVFORGE_DIR to point at the project-local .devforge/; cmd_validate_doc
    # resolves project_root from devforge_dir.parent, so the env-derived path
    # must flow through to per-doc Namespace as well.
    devforge_dir = os.environ.get("DEVFORGE_DIR") or str(args.devforge_dir)
    devforge_path = Path(devforge_dir)
    project_root_override = os.environ.get("DEVFORGE_PROJECT_ROOT")
    if project_root_override:
        project_root = Path(project_root_override).resolve()
    else:
        project_root = devforge_path.resolve().parent

    # ── Load state ──────────────────────────────────────────────────────────
    try:
        state = _load_state()
    except StateLoadError as exc:
        print(f"verify-all: cannot load state: {exc}", file=sys.stderr)
        return 2

    packages = state.get("packages", {})

    # failures: list of (tier, target, [error_lines])
    failures: List[Tuple[str, str, List[str]]] = []

    # ── Package-tier docs ────────────────────────────────────────────────────
    for pkg_path in packages:
        for tier in ("package-overview", "package-architecture"):
            errors = _validate_one(tier, pkg_path, devforge_dir)
            if errors:
                failures.append((tier, pkg_path, errors))

    # ── Concern-tier docs ────────────────────────────────────────────────────
    for pkg_path, pkg_record in packages.items():
        concerns = pkg_record.get("concerns", {}) or {}
        for concern_name in concerns:
            target = f"{pkg_path}/{concern_name}"
            errors = _validate_one("concern", target, devforge_dir)
            if errors:
                failures.append(("concern", target, errors))

    # ── Project-tier docs (existence-check then validate) ────────────────────
    for tier in ("project-overview", "project-architecture"):
        filename = _TIER_DOC_FILENAMES[tier]
        doc_path = project_root / "docs" / filename
        if not doc_path.is_file():
            # Phase 4 not yet run — skip silently (no error).
            continue
        # Project tiers: target is ignored by cmd_validate_doc for path
        # resolution (uses project_root/docs/<filename> directly), but the
        # Namespace must carry it to satisfy the handler's attribute access.
        errors = _validate_one(tier, "__project__", devforge_dir)
        if errors:
            failures.append((tier, "__project__", errors))

    # ── Emit results ─────────────────────────────────────────────────────────
    if not failures:
        return 0

    for tier, target, error_lines in failures:
        print(f"FAIL tier={tier} target={target}:", file=sys.stderr)
        for line in error_lines:
            print(f"  {line}", file=sys.stderr)

    return 2
