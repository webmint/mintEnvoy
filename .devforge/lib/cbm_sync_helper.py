"""cbm_sync_helper — keep CBM index aligned with parent repo HEAD.

Two subcommands:

  write — read parent HEAD via `git rev-parse HEAD`, write
          `.devforge/cbm-last-indexed-sha` atomically.
  check — compare stamp to current HEAD, print one of four state
          tokens on stdout: `current` / `missing` / `drift <a>..<b>`
          / `not-a-git-repo`.

State tokens (stdout, single line, newline-terminated):

  current             — stamp.git_sha == current HEAD
  missing             — no stamp file (or stamp JSON is corrupt /
                        missing the git_sha field)
  drift <a>..<b>      — stamp records <a>, current HEAD is <b>
  not-a-git-repo      — `git rev-parse HEAD` failed (no git repo,
                        no HEAD commit, or git binary missing)

Exit codes:

  0 — success (every state above except not-a-git-repo)
  1 — write: I/O failure persisting the stamp file
  2 — check / write: not-a-git-repo (no HEAD to compare or stamp)
      or argparse usage error (no subcommand)

Stamp shape — `.devforge/cbm-last-indexed-sha`:

  {"git_sha": "<40-char sha>", "indexed_at": "<iso8601 utc>"}

Schema version field deliberately omitted per CBM-SYNC-PLAN §Design
summary (resolved 2026-05-11 — defer until empirical need).

Path resolution honors `DEVFORGE_DIR` (test override), else derives
from this script's own location: `<target>/.devforge/lib/<this>.py`
sits one directory below `<target>/.devforge/`, where the stamp lives.

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STAMP_FILE_NAME = "cbm-last-indexed-sha"
SPEC_STAMPS_FILE_NAME = "spec-stamps.jsonl"


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _stamp_path():
    """Resolve the stamp file path at call time (not import time).

    Honors `DEVFORGE_DIR` for tests + unusual layouts. Without it, the
    path derives from this file's own location.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / STAMP_FILE_NAME
    return Path(__file__).resolve().parent.parent / STAMP_FILE_NAME


# ---------------------------------------------------------------------------
# Git probe.
# ---------------------------------------------------------------------------


def _git_head():
    """Return current parent-repo HEAD sha, or None if no HEAD is resolvable.

    None covers three failure modes treated identically by the protocol:
    (a) cwd is not inside any git repo, (b) cwd is in a fresh repo with
    no commits, (c) git binary not on PATH.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    if not sha:
        return None
    return sha


# ---------------------------------------------------------------------------
# Stamp I/O.
# ---------------------------------------------------------------------------


def _read_stamp():
    """Return stamp dict or None if file is missing / corrupt / wrong shape."""
    path = _stamp_path()
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_stamp(sha):
    """Atomically write stamp file. Raises OSError on failure.

    Uses tempfile.mkstemp in the stamp's parent dir so os.replace is
    atomic on a single filesystem. On any failure mid-write, removes
    the temp file and re-raises.
    """
    target = _stamp_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "git_sha": sha,
        "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    fd, tmp_path = tempfile.mkstemp(
        prefix="cbm-stamp-",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Subcommand implementations.
# ---------------------------------------------------------------------------


def cmd_write(args):
    sha = _git_head()
    if sha is None:
        sys.stderr.write(
            "cbm_sync_helper: not a git repository (or no HEAD commit)\n"
        )
        return 2
    try:
        _write_stamp(sha)
    except OSError as err:
        sys.stderr.write("cbm_sync_helper: cannot write stamp: {0}\n".format(err))
        return 1
    return 0


def _spec_stamps_path():
    """Resolve `.devforge/spec-stamps.jsonl` path — sibling of CBM stamp."""
    return _stamp_path().parent / SPEC_STAMPS_FILE_NAME


def _install_root():
    """Resolve the install root (parent of `.devforge/`)."""
    return _stamp_path().parent.parent


def _normalize_spec_path(spec_path):
    """Convert spec_path to a stable form for stamp keying.

    Stores relative-to-install-root when the absolute path lies under
    install_root; otherwise stores the absolute resolved path.
    """
    abs_spec = Path(spec_path).resolve()
    root = _install_root().resolve()
    try:
        return str(abs_spec.relative_to(root))
    except ValueError:
        return str(abs_spec)


def _find_latest_stamp(stored_path):
    """Return the most-recent stamp record for stored_path, or None.

    JSONL is append-only; last matching record wins. Corrupt lines are
    skipped silently (no exception bubbled).
    """
    stamps = _spec_stamps_path()
    if not stamps.is_file():
        return None
    latest = None
    try:
        text = stamps.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        if rec.get("spec_path") == stored_path:
            latest = rec
    return latest


_AFFECTED_AREAS_FILE_RE = re.compile(r"`([^`\n]+\.[a-zA-Z0-9]+)`")


def _parse_affected_areas(spec_md_path):
    """Extract cited file paths from spec.md §4 Affected Areas section.

    Conservative extraction: scan from the `## 4.` heading to the next
    `## N.` heading at the same level; pull backticked path-like
    tokens (containing a dot extension). Returns deduplicated list,
    preserving first-occurrence order.
    """
    try:
        text = Path(spec_md_path).read_text(encoding="utf-8")
    except OSError:
        return []
    start = re.search(r"^##\s+4\.\s", text, re.MULTILINE)
    if not start:
        return []
    section_start = start.end()
    next_h2 = re.search(
        r"^##\s+\d+\.\s", text[section_start:], re.MULTILINE,
    )
    section_end = (
        section_start + next_h2.start() if next_h2 else len(text)
    )
    section = text[section_start:section_end]
    files = []
    seen = set()
    for match in _AFFECTED_AREAS_FILE_RE.finditer(section):
        path = match.group(1).strip()
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return files


def _git_toplevel():
    """Return git repo root (Path), or None if cwd is not in a git repo.

    Cited files in spec.md §4 are relative to the git repo root, NOT the
    install_root derived from DEVFORGE_DIR (which may be elsewhere in
    test layouts). Use this for `_file_changed_since` lookups.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    top = result.stdout.strip()
    if not top:
        return None
    return Path(top)


def _file_changed_since(file_path, stamp_sha, repo_root):
    """Return True iff `git log <stamp_sha>..HEAD -- <file_path>` is non-empty."""
    target = (Path(repo_root) / file_path)
    try:
        result = subprocess.run(
            [
                "git", "log", "--oneline",
                "{0}..HEAD".format(stamp_sha),
                "--", str(target),
            ],
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool(result.stdout.strip())


def cmd_stamp_spec(args):
    """Append (spec_path, git_sha, timestamp) to .devforge/spec-stamps.jsonl.

    Append-only; multiple invocations on the same spec_path are allowed.
    The most-recent matching record wins at `check-spec` time.
    """
    sha = _git_head()
    if sha is None:
        sys.stderr.write(
            "cbm_sync_helper stamp-spec: not a git repository "
            "(or no HEAD commit)\n"
        )
        return 2
    stored_path = _normalize_spec_path(args.spec_path)
    record = {
        "spec_path": stored_path,
        "git_sha": sha,
        "stamped_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    stamps = _spec_stamps_path()
    try:
        stamps.parent.mkdir(parents=True, exist_ok=True)
        with stamps.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError as err:
        sys.stderr.write(
            "cbm_sync_helper stamp-spec: cannot write stamp: {0}\n".format(err)
        )
        return 1
    return 0


def cmd_check_spec(args):
    """Compare spec stamp to current state; emit token + cited-file deltas.

    Output (stdout, single line, newline-terminated):

      current
      missing
      drift <stamp_sha>..<head_sha> <file-1> <file-2> ...
      not-a-git-repo

    `drift` fires only when (a) stamp exists, (b) HEAD differs from stamp,
    AND (c) at least one file cited in spec.md §4 Affected Areas has
    changed since the stamp. HEAD advancing on files NOT cited in §4 is
    not drift — the spec didn't claim that surface.
    """
    sha = _git_head()
    if sha is None:
        sys.stdout.write("not-a-git-repo\n")
        return 2
    stored_path = _normalize_spec_path(args.spec_path)
    stamp = _find_latest_stamp(stored_path)
    if stamp is None:
        sys.stdout.write("missing\n")
        return 0
    stamp_sha = stamp.get("git_sha")
    if not isinstance(stamp_sha, str) or not stamp_sha:
        sys.stdout.write("missing\n")
        return 0
    if stamp_sha == sha:
        sys.stdout.write("current\n")
        return 0
    abs_spec = Path(args.spec_path).resolve()
    if not abs_spec.is_file():
        sys.stdout.write(
            "drift {0}..{1}\n".format(stamp_sha, sha)
        )
        return 0
    repo_root = _git_toplevel() or _install_root()
    cited = _parse_affected_areas(abs_spec)
    changed = [
        cited_file
        for cited_file in cited
        if _file_changed_since(cited_file, stamp_sha, repo_root)
    ]
    if not changed:
        sys.stdout.write("current\n")
        return 0
    sys.stdout.write(
        "drift {0}..{1} {2}\n".format(
            stamp_sha, sha, " ".join(changed),
        )
    )
    return 0


def cmd_check(args):
    sha = _git_head()
    if sha is None:
        sys.stdout.write("not-a-git-repo\n")
        return 2
    stamp = _read_stamp()
    if stamp is None:
        sys.stdout.write("missing\n")
        return 0
    stamp_sha = stamp.get("git_sha")
    if not isinstance(stamp_sha, str) or not stamp_sha:
        sys.stdout.write("missing\n")
        return 0
    if stamp_sha == sha:
        sys.stdout.write("current\n")
        return 0
    sys.stdout.write("drift {0}..{1}\n".format(stamp_sha, sha))
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cbm_sync_helper",
        description="Keep CBM index aligned with parent repo HEAD.",
    )
    sub = parser.add_subparsers(dest="subcommand")

    sp = sub.add_parser(
        "write",
        help="Stamp current HEAD into .devforge/cbm-last-indexed-sha.",
    )
    sp.set_defaults(func=cmd_write)

    sp = sub.add_parser(
        "check",
        help="Compare stamp to current HEAD; print state token on stdout.",
    )
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser(
        "stamp-spec",
        help="Stamp spec.md at current HEAD into .devforge/spec-stamps.jsonl (append-only).",
    )
    sp.add_argument(
        "spec_path",
        help="Path to spec.md (absolute or relative to install root).",
    )
    sp.set_defaults(func=cmd_stamp_spec)

    sp = sub.add_parser(
        "check-spec",
        help="Compare spec stamp to current state; emit current/missing/drift on stdout.",
    )
    sp.add_argument(
        "spec_path",
        help="Path to spec.md (absolute or relative to install root).",
    )
    sp.set_defaults(func=cmd_check_spec)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
