"""Heuristic: duplication_ratio — fires when a NEW file added by the PR has
>= 80% content similarity with an existing file in the target repo.

Severity: medium

Logic:
    1. Parse the diff to identify new files (look for 'new file mode' header).
    2. For each new file, reconstruct its full content from the '+' lines.
    3. Scan candidate existing files in the target repo (same extension, limited to
       _CODE_EXTS; capped at _MAX_CANDIDATES sorted by basename similarity).
    4. Use difflib.SequenceMatcher to compute similarity ratio.
    5. Threshold: ratio >= _DUPLICATION_THRESHOLD → emit finding.

Bounds:
    - Only files with extensions in _CODE_EXTS are checked (both new and existing).
    - Skip if new file content is < _MIN_LINES_FOR_CHECK lines.
    - Cap candidate scan at _MAX_CANDIDATES files to bound runtime.

Finding schema:
    {
        "name": "duplication_ratio",
        "severity": "medium",
        "location": "<new_file_path>",
        "evidence": "matches <existing_file_path> at <ratio>"
    }

Git operations: NONE.  This heuristic reads only state.diff and the filesystem
at state.target.  No subprocess, no git commands.
"""

from __future__ import annotations

import difflib
import os
import re
from typing import Any, Dict, List, Optional, Tuple

_DUPLICATION_THRESHOLD = 0.80
_MIN_LINES_FOR_CHECK = 50
_MAX_CANDIDATES = 200

_CODE_EXTS = frozenset([
    ".py", ".ts", ".tsx", ".vue", ".js", ".jsx", ".go", ".java", ".rb", ".rs",
])

# Matches `new file mode NNNN` in a diff block.
_NEW_FILE_MODE_RE = re.compile(r"^new file mode", re.MULTILINE)

# Matches a unified diff file header for new files: `+++ b/<path>`
_NEW_FILE_PATH_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)

# Matches an added content line (not the +++ header or a blank added line).
_ADDED_CONTENT_LINE_RE = re.compile(r"^\+([^+\n].*)$", re.MULTILINE)

# Matches a diff block header to split per-file sections.
_DIFF_BLOCK_RE = re.compile(r"^diff --git ", re.MULTILINE)


def _split_diff_blocks(diff: str) -> List[str]:
    """Split a unified diff into per-file blocks.

    Args:
        diff: Raw unified diff string.

    Returns:
        List of per-file diff block strings.
    """
    positions = [m.start() for m in _DIFF_BLOCK_RE.finditer(diff)]
    if not positions:
        return []
    blocks = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(diff)
        blocks.append(diff[start:end])
    return blocks


def _extract_new_files(diff: str) -> List[Tuple[str, str]]:
    """Extract (path, content) tuples for new files added in the diff.

    A new file is identified by the presence of `new file mode` in its block.
    Content is reconstructed from '+' lines (not '+++' headers) in the block.

    Args:
        diff: Raw unified diff string.

    Returns:
        List of (relative_path, content) tuples.  Files with extensions not in
        _CODE_EXTS are excluded.
    """
    results = []
    for block in _split_diff_blocks(diff):
        if not _NEW_FILE_MODE_RE.search(block):
            continue

        path_match = _NEW_FILE_PATH_RE.search(block)
        if not path_match:
            continue
        path = path_match.group(1).strip()

        _, ext = os.path.splitext(path)
        if ext.lower() not in _CODE_EXTS:
            continue

        added_lines = _ADDED_CONTENT_LINE_RE.findall(block)
        content = "\n".join(added_lines)
        results.append((path, content))

    return results


def _find_candidate_files(
    target: str, ext: str, new_path: str
) -> List[str]:
    """Walk the target repo to find candidate files with the same extension.

    Candidates are sorted by basename similarity (closer basename = higher
    priority) and capped at _MAX_CANDIDATES.

    Args:
        target: Absolute path to the repository root.
        ext:    File extension to match (e.g. ".py").
        new_path: Relative path of the new file (for basename comparison).

    Returns:
        List of absolute file paths, sorted by descending basename similarity,
        capped at _MAX_CANDIDATES.
    """
    new_basename = os.path.basename(new_path).lower()
    candidates = []
    for dirpath, dirnames, filenames in os.walk(target):
        # Skip hidden directories in-place so os.walk prunes them.
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            _, fext = os.path.splitext(fname)
            if fext.lower() != ext:
                continue
            abs_path = os.path.join(dirpath, fname)
            similarity = difflib.SequenceMatcher(
                None, new_basename, fname.lower()
            ).ratio()
            candidates.append((similarity, abs_path))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in candidates[:_MAX_CANDIDATES]]


def _best_match(
    new_content: str, candidate_paths: List[str]
) -> Optional[Tuple[str, float]]:
    """Find the candidate file with the highest content similarity to new_content.

    Args:
        new_content:     Reconstructed content of the new file.
        candidate_paths: List of absolute paths to compare against.

    Returns:
        (abs_path, ratio) for the best match if ratio >= _DUPLICATION_THRESHOLD,
        or None if no candidate meets the threshold.
    """
    best_path: Optional[str] = None
    best_ratio = 0.0
    for abs_path in candidate_paths:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                existing_content = fh.read()
        except OSError:
            continue
        ratio = difflib.SequenceMatcher(None, new_content, existing_content).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_path = abs_path
    if best_path is not None and best_ratio >= _DUPLICATION_THRESHOLD:
        return (best_path, best_ratio)
    return None


def run(state: Any) -> List[Dict[str, Any]]:
    """Check new files in the diff for high similarity with existing repo files.

    Args:
        state: PRReviewState instance.  Reads state.diff and state.target.

    Returns:
        List of findings — one per new file that exceeds the similarity threshold.
        Empty if no smells detected.
    """
    diff = state.diff or ""
    if not diff:
        return []

    target = state.target or ""
    if not target or not os.path.isdir(target):
        return []

    new_files = _extract_new_files(diff)
    findings: List[Dict[str, Any]] = []

    for rel_path, content in new_files:
        line_count = content.count("\n") + 1 if content.strip() else 0
        if line_count < _MIN_LINES_FOR_CHECK:
            continue

        _, ext = os.path.splitext(rel_path)
        candidates = _find_candidate_files(target, ext.lower(), rel_path)
        if not candidates:
            continue

        match = _best_match(content, candidates)
        if match is None:
            continue

        match_path, ratio = match
        # Make the path relative to target for readability.
        try:
            display_path = os.path.relpath(match_path, target)
        except ValueError:
            display_path = match_path

        findings.append({
            "name": "duplication_ratio",
            "severity": "medium",
            "location": rel_path,
            "evidence": "matches {existing} at {ratio:.2f}".format(
                existing=display_path, ratio=ratio
            ),
        })

    return findings
