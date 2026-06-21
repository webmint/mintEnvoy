"""Read verbatim bytes for a 1-indexed inclusive line range from a file.

`extract-snippet` is a language-agnostic mechanical primitive that emits
the exact bytes (between line ends, INCLUDING the trailing newline of
`end` if present) of `<file>` from line `<start>` to line `<end>`.

Motivation: `add-package-export --code-snippet` and friends compare
their argument to the source slice via whitespace-normalized equality.
LLMs frequently strip leading whitespace when transcribing indented
snippets (Vue templates, Python class bodies, etc.), producing
`[snippet-verbatim]` validation errors with no clean recovery path.
Piping `extract-snippet`'s stdout directly into `--code-snippet "$(...)"`
eliminates that error class because the bytes are mechanically
identical to the source.

Behavior contract:

- Lines are 1-indexed (matches `--cite-start` / `--cite-end`
  conventions used by every other helper subcommand).
- The range is INCLUSIVE on both ends.
- The file is read as UTF-8 with `errors="replace"` so an unexpected
  byte never crashes the helper. Source-of-truth comparison is done by
  the validator after normalization, so replacement chars produce a
  visible mismatch downstream rather than a silent crash here.
- Line endings are PRESERVED verbatim. The downstream validator
  normalizes CRLF -> LF before equality comparison (see
  `_validators_shared._normalize_for_compare`) so either choice round-trips
  cleanly; preserving keeps `extract-snippet` purely mechanical (no
  surprise mutation).

Exit codes:
- 0 on success (bytes written to stdout).
- 2 on validation errors (file missing/unreadable, invalid range,
  end < start, end > file line count).

This module never reads or writes the helper's state file. It does not
mutate state, so it lives apart from `_setters` / `_setters_concern`.
File-system reads are the only side effect.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import sys
from pathlib import Path

from ._state import _die
from ._validation import _validate_line_range, _validate_string


def cmd_extract_snippet(args: argparse.Namespace) -> int:
    """Emit verbatim bytes of `<file>` for lines `<start>`..`<end>` (incl).

    `args.file` may be relative (resolved against the current working
    directory — the orchestrator is expected to invoke from the project
    root) or absolute. Symlinks are followed by `Path.read_bytes`.
    """
    try:
        _validate_string(args.file, "extract-snippet --file")
        _validate_line_range(args.start, args.end, "extract-snippet")
    except ValueError as err:
        return _die(str(err))
    src_path = Path(args.file)
    if not src_path.exists():
        return _die(
            "extract-snippet: file {0!r} does not exist".format(args.file)
        )
    if not src_path.is_file():
        return _die(
            "extract-snippet: path {0!r} is not a regular file".format(args.file)
        )
    try:
        # Read as bytes then decode with replacement so a stray byte
        # doesn't abort the helper. `errors="replace"` substitutes U+FFFD
        # for malformed bytes; the validator's snippet-verbatim check
        # would surface the mismatch downstream if the source is also
        # read with the same policy.
        raw = src_path.read_bytes()
    except OSError as err:
        return _die(
            "extract-snippet: cannot read {0!r}: {1}".format(args.file, err)
        )
    text = raw.decode("utf-8", errors="replace")
    # `splitlines(keepends=True)` preserves '\n', '\r\n', '\r' on each
    # line so output bytes are identical to source bytes for the slice.
    lines = text.splitlines(keepends=True)
    line_count = len(lines)
    if args.start > line_count:
        return _die(
            "extract-snippet: --start {0} exceeds file line count {1} for "
            "{2!r}".format(args.start, line_count, args.file)
        )
    if args.end > line_count:
        return _die(
            "extract-snippet: --end {0} exceeds file line count {1} for "
            "{2!r}".format(args.end, line_count, args.file)
        )
    out = "".join(lines[args.start - 1:args.end])
    sys.stdout.write(out)
    return 0
