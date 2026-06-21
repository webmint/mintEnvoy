"""PR metadata + diff intake for pr_review_helper.

`run(target, pr_number, repo, ticket_text, devforge_dir)` is the Phase 1
entry point. It:

  1. Fetches PR metadata via `gh pr view --json`.
  2. Fetches the raw unified diff via `gh pr diff`.
  3. Extracts linked issue URLs from `closingIssuesReferences` (preferred)
     or falls back to regex extraction from the PR body when the structured
     field is empty.
  4. Builds a PRReviewState instance with the fetched data.
  5. Writes it atomically to
       <target>/<devforge_dir>/pr-reviews/<pr_number>/state.json
     creating parent directories as needed.
  6. Returns the output dict the LLM / CLI layer prints as JSON.

Linked issues format: full URL ("https://github.com/owner/repo/issues/123").
Full URLs are durable across repo-context loss and match the format that
`closingIssuesReferences` returns natively. Short-ref style ("#123") is NOT
used even when parsing from body text — all references are normalised to the
full-URL form for consistency.

`closingIssuesReferences` vs body regex:
  If `gh pr view --json closingIssuesReferences` returns a non-empty list,
  that list is used directly (each item has a `url` field).  If the list is
  empty (e.g. no "Fixes #N" keywords in the PR body), the PR body is scanned
  with a regex that matches short-ref style (#N) OR full GitHub issue URLs.
  Short refs (#N) are expanded to full URLs using the `repo` argument:
    #N  →  https://github.com/<repo>/issues/<N>
  Deduplication and ascending sort are applied to the final list in both paths.

Subprocess error handling:
  Any non-zero exit from `gh` raises ValueError with a message that includes
  the exit code and the captured stderr. The _cli layer catches ValueError
  and propagates it as `_die(...)`.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import subprocess
import tempfile
from typing import List

from ._state import PRReviewState, state_path


# ---------------------------------------------------------------------------
# gh invocation helpers.
# ---------------------------------------------------------------------------

_GH_PR_VIEW_FIELDS = (
    "title,body,additions,deletions,baseRefName,headRefName,"
    "files,state,author,url,number,closingIssuesReferences,commits"
)


def _fetch_pr_view(repo: str, pr_number: int, cwd: str) -> dict:
    """Invoke `gh pr view` and return parsed JSON.

    Args:
        repo:      owner/name string passed to --repo.
        pr_number: PR number to fetch.
        cwd:       Working directory for the subprocess (typically the reviewer's
                   local clone of the target repo, but any directory works since
                   we pass --repo explicitly).

    Returns:
        Parsed JSON dict from gh pr view --json output.

    Raises:
        ValueError: if `gh` exits non-zero.
    """
    cmd = [
        "gh", "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", _GH_PR_VIEW_FIELDS,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise ValueError(
            "gh pr view exited {code}: {stderr}".format(
                code=result.returncode,
                stderr=result.stderr.strip(),
            )
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "gh pr view returned non-JSON output: {exc}\nstdout={out!r}".format(
                exc=exc,
                out=result.stdout[:200],
            )
        ) from exc


def _fetch_pr_diff(repo: str, pr_number: int, cwd: str) -> str:
    """Invoke `gh pr diff` and return the raw unified diff text.

    Args:
        repo:      owner/name string passed to --repo.
        pr_number: PR number to fetch.
        cwd:       Working directory for the subprocess.

    Returns:
        Raw unified diff string (may be empty for PRs with no file changes).

    Raises:
        ValueError: if `gh` exits non-zero.
    """
    cmd = [
        "gh", "pr", "diff", str(pr_number),
        "--repo", repo,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise ValueError(
            "gh pr diff exited {code}: {stderr}".format(
                code=result.returncode,
                stderr=result.stderr.strip(),
            )
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Linked issue extraction.
# ---------------------------------------------------------------------------

# Matches a full GitHub issue URL anywhere in body text.
_FULL_ISSUE_URL_RE = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/(\d+)"
)

# Matches short-ref style #NNN (preceded by non-word char or start of string,
# followed by non-digit to avoid matching commit SHAs like #abc123).
# Only split when the # is truly a short issue ref, NOT a section anchor.
# This regex requires the # to follow a word boundary and the digits to be
# a standalone number (no trailing letter = not a SHA).
_SHORT_REF_RE = re.compile(r"(?<!\w)#(\d+)(?!\w)")


def _extract_linked_issues(pr_body: str, repo: str) -> List[str]:
    """Extract linked issue URLs from a PR body.

    Extracts:
      - Full GitHub issue URLs matching https://github.com/.../issues/<N>
      - Short refs matching #<N> (expanded to full URL using `repo`)

    Result is deduped (by exact URL string) then sorted ascending by issue number.

    Format: always full URL "https://github.com/<repo>/issues/<N>".
    Short refs are expanded: #123 → https://github.com/<repo>/issues/123.

    The `repo` argument is the "owner/name" string (same as --repo flag).
    """
    if not pr_body:
        return []

    seen_urls: set = set()
    result: List[str] = []

    # Full URLs first — keep URL as-is, dedup by the exact URL string.
    for match in _FULL_ISSUE_URL_RE.finditer(pr_body):
        url = match.group(0)
        if url not in seen_urls:
            seen_urls.add(url)
            result.append(url)

    # Short refs — expand to full URL using repo, dedup by expanded URL string.
    for match in _SHORT_REF_RE.finditer(pr_body):
        number = int(match.group(1))
        url = "https://github.com/{repo}/issues/{number}".format(
            repo=repo, number=number
        )
        if url not in seen_urls:
            seen_urls.add(url)
            result.append(url)

    # Sort ascending by issue number (extracted from the trailing /N segment).
    def _issue_number(url: str) -> int:
        tail = url.rsplit("/", 1)[-1]
        try:
            return int(tail)
        except ValueError:
            return 0

    result.sort(key=_issue_number)
    return result


def _issues_from_closing_refs(closing_refs: List[dict], repo: str) -> List[str]:
    """Build linked-issue URL list from `closingIssuesReferences` API field.

    Each entry in `closing_refs` has at minimum a `url` key (GitHub Issues URL).
    Returns sorted, deduped list of full URLs.
    """
    seen: set = set()
    result: List[str] = []
    for ref in closing_refs:
        url = ref.get("url", "")
        if url and url not in seen:
            seen.add(url)
            result.append(url)

    def _issue_number(url: str) -> int:
        tail = url.rsplit("/", 1)[-1]
        try:
            return int(tail)
        except ValueError:
            return 0

    result.sort(key=_issue_number)
    return result


# ---------------------------------------------------------------------------
# Commit subject extraction.
# ---------------------------------------------------------------------------


def _extract_commit_subjects(commits: List[dict]) -> List[str]:
    """Extract the subject line (first line) from each commit in the commits list.

    The `commits` field from `gh pr view --json commits` returns a list of
    objects. Each object has a `messageHeadline` key containing the commit
    subject, and a `messageBody` key for the rest. We use `messageHeadline`
    directly since that is the subject line; fall back to the first line of
    `message` if `messageHeadline` is absent.

    Args:
        commits: List of commit dicts from gh pr view JSON output.

    Returns:
        List of commit subject strings (one per commit), preserving order.
        Empty strings are excluded — a commit with no subject is skipped.
    """
    subjects: List[str] = []
    for entry in commits:
        # gh returns messageHeadline as the subject.
        subject = entry.get("messageHeadline", "")
        if not subject:
            # Fallback: first line of the full message field.
            message = entry.get("message", "")
            subject = message.split("\n", 1)[0] if message else ""
        if subject:
            subjects.append(subject)
    return subjects


# ---------------------------------------------------------------------------
# Ticket file reader.
# ---------------------------------------------------------------------------


def _read_ticket_file(path: str) -> str:
    """Read UTF-8 ticket text from a file.

    Args:
        path: Filesystem path to the ticket text file.

    Returns:
        File contents as a string.

    Raises:
        ValueError: if the file does not exist or cannot be read.
    """
    if not os.path.isfile(path):
        raise ValueError(
            "ticket file not found: {path!r}".format(path=path)
        )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read ticket file {path!r}: {exc}".format(path=path, exc=exc)
        ) from exc


# ---------------------------------------------------------------------------
# Atomic state writer.
# ---------------------------------------------------------------------------


# TODO(Step 7+): consolidate _write_state across _intake.py / _blast.py /
# _bundle.py / _handoff_import.py / _scope_drift.py (5 copies). Extract to
# _state.py.write_state when next verb would otherwise create a 6th copy.
def _write_state(target_path: str, state: PRReviewState) -> None:
    """Write PRReviewState as JSON to target_path atomically.

    Uses tempfile.mkstemp in the same directory as the target file, then
    os.replace for the rename — ensuring crash safety and no partial writes.

    Args:
        target_path: Absolute path to the destination state.json file.
                     Parent directory must already exist.
        state:       PRReviewState instance to serialise.

    Raises:
        OSError: if the write or rename fails.
    """
    target_dir = os.path.dirname(target_path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="state-", suffix=".tmp.json", dir=target_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(state), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(
    target: str,
    pr_number: int,
    repo: str,
    ticket_text: str = "",
    devforge_dir: str = ".devforge",
) -> dict:
    """Fetch PR metadata + diff, build state, write state.json, return output dict.

    Args:
        target:       Absolute (or relative) path to the reviewer's local
                      repo root. Used as cwd for gh subprocess calls AND as
                      the base for the state file path.
        pr_number:    PR number (positive int).
        repo:         GitHub repo in "owner/name" format (passed to --repo).
        ticket_text:  Optional ticket text (JIRA / Linear prose). Empty string
                      when not provided — that is a valid intake state.
        devforge_dir: Name of the devforge directory under target (default
                      ".devforge"). State path is
                      <target>/<devforge_dir>/pr-reviews/<pr_number>/state.json.

    Returns:
        dict with keys:
          status           — "ok"
          state_path       — absolute path of the written state.json
          pr_number        — int
          repo             — str
          files_changed    — int (len of files array from gh pr view)
          additions        — int
          deletions        — int
          title            — str (PR title)
          ticket_text_length — int (len of ticket_text)

    Raises:
        ValueError: on gh CLI errors (non-zero exit) or JSON parse failures
                    from gh output.
    """
    abs_target = os.path.abspath(target)
    abs_devforge = os.path.join(abs_target, devforge_dir)

    # Fetch from gh (both calls may raise ValueError on non-zero exit).
    pr_view = _fetch_pr_view(repo=repo, pr_number=pr_number, cwd=abs_target)
    diff = _fetch_pr_diff(repo=repo, pr_number=pr_number, cwd=abs_target)

    # Extract linked issues — prefer structured API field; fall back to regex.
    closing_refs = pr_view.get("closingIssuesReferences") or []
    if closing_refs:
        linked_issues = _issues_from_closing_refs(closing_refs, repo)
    else:
        pr_body_text = pr_view.get("body") or ""
        linked_issues = _extract_linked_issues(pr_body_text, repo)

    # Extract commit subjects.
    commits = pr_view.get("commits") or []
    commit_subjects = _extract_commit_subjects(commits)

    # Build state.
    title = pr_view.get("title") or ""
    state = PRReviewState(
        pr_number=pr_number,
        repo=repo,
        pr_title=title,
        diff=diff,
        pr_body=pr_view.get("body") or "",
        linked_issues=linked_issues,
        ticket_text=ticket_text,
        commit_subjects=commit_subjects,
    )

    # Compute and create state file path.
    sp = state_path(abs_devforge, pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)

    _write_state(sp, state)

    files_changed = len(pr_view.get("files") or [])
    additions = pr_view.get("additions") or 0
    deletions = pr_view.get("deletions") or 0

    return {
        "status": "ok",
        "state_path": sp,
        "pr_number": pr_number,
        "repo": repo,
        "files_changed": files_changed,
        "additions": additions,
        "deletions": deletions,
        "title": title,
        "ticket_text_length": len(ticket_text),
    }
