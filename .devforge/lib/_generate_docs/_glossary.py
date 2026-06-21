"""Track B.1 — Glossary helper.

Two subcommands:

  build-glossary-bundles   -- Walk docs/ corpus, cross-ref CBM per term,
                              rank candidates, emit JSON on stdout for LLM.
  set-glossary-entries     -- Consume LLM JSON (term + definition + related),
                              merge with bundles, validate, render docs/glossary.md.

Helper-owns-shape: this module owns markdown structure + validation rules.
LLM provides definition values via the set-glossary-entries setter API.

CBM invocations are wrapped in `_run_cbm_cli` (mirrors _preflight._run_index_repository).
All CBM calls return {"ran": False, ...} if binary absent; callers degrade gracefully.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._doc_corpus import (
    extract_term_occurrences,
    noise_filter,
    validate_cite_paths,
    walk_doc_corpus,
)

# ── Ranking weights (module-level constants — subject to A.3-style tuning) ──

_W1 = 1.0   # doc_freq weight
_W2 = 1.5   # code_freq weight
_W3 = 0.5   # is_exported_bonus weight

# ── CBM node labels that qualify for "code-anchored" classification ──────────

_CODE_ANCHOR_LABELS = frozenset(
    ["Function", "Method", "Class", "Type", "Interface", "Enum"]
)

# ── Glossary constants ───────────────────────────────────────────────────────

_MIN_TERMS = 30
_MAX_TERMS = 150
_DEFINITION_MAX_CHARS = 280
_USED_IN_INLINE_CAP = 3

# ── Stderr helpers (mirror _state._die / _info) ─────────────────────────────


def _die(message: str, code: int = 2) -> int:
    sys.stderr.write("generate_docs_helper: {0}\n".format(message))
    return code


def _info(message: str) -> None:
    sys.stderr.write("generate_docs_helper: {0}\n".format(message))


# ── CBM CLI wrapper ──────────────────────────────────────────────────────────


def _run_cbm_cli(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke `codebase-memory-mcp cli <tool_name> <payload-json>`.

    Mirrors _preflight._run_index_repository shape exactly.
    Returns a dict with at minimum {"ran": bool}.
    On CBM binary absent: {"ran": False, "reason": "..."}.
    On OSError: {"ran": False, "reason": "cli invocation failed: <exc>"}.
    On nonzero exit: result dict includes "stderr" key (capped at 500 chars).
    """
    if shutil.which("codebase-memory-mcp") is None:
        return {
            "ran": False,
            "reason": "codebase-memory-mcp binary not found on PATH",
            "duration_ms": 0,
        }
    start = time.monotonic()
    payload_str = json.dumps(payload)
    try:
        result = subprocess.run(
            ["codebase-memory-mcp", "cli", tool_name, payload_str],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {
            "ran": False,
            "reason": "cli invocation failed: {0}".format(exc),
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    duration_ms = int((time.monotonic() - start) * 1000)
    block: Dict[str, Any] = {
        "ran": True,
        "exit_code": result.returncode,
        "duration_ms": duration_ms,
    }
    # Two-pass parse: arrays take priority over objects.
    # CBM emits a {"level": "info", ...} metadata line BEFORE the actual
    # [...] result for graph queries; picking the first {} line would return
    # the metadata dict instead of the result array and silently break all
    # array-returning callers.  First pass: look for the first array line.
    # Second pass: only if no array found, look for the first object line.
    json_payload: Optional[Any] = None
    for line in (result.stdout or "").splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("[") and line_stripped.endswith("]"):
            try:
                json_payload = json.loads(line_stripped)
                break
            except json.JSONDecodeError:
                continue
    if json_payload is None:
        for line in (result.stdout or "").splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("{") and line_stripped.endswith("}"):
                try:
                    json_payload = json.loads(line_stripped)
                    break
                except json.JSONDecodeError:
                    continue
    if json_payload is not None:
        block["result"] = json_payload
    if result.returncode != 0:
        block["stderr"] = (result.stderr or "").strip()[:500]
    return block


# ── Term classification helpers ──────────────────────────────────────────────


def _classify_term(
    term: str,
    occurrences: List[Tuple[str, int, str]],
    bm25_threshold: float,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Return (classification, cbm_hit_or_None) for a single term.

    classification: "code-anchored" | "fuzzy-anchored" | "prose-only"
    cbm_hit: dict with keys qn, file, line, is_exported (or None for prose-only)

    Queries CBM in order:
      1. query_graph exact name match
      2. search_graph BM25 fallback (only if step 1 returns 0 hits)
    """
    # Step 1: exact match via query_graph.
    qg_result = _run_cbm_cli(
        "query_graph",
        {
            "query": (
                "MATCH (n) WHERE n.name = '{term}' "
                "RETURN n.qualified_name, labels(n), n.file_path, "
                "n.start_line, n.signature, n.is_exported"
            ).format(term=term.replace("'", "\\'"))
        },
    )
    if qg_result.get("ran") and qg_result.get("exit_code", 1) == 0:
        rows = qg_result.get("result", [])
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                labels = row.get("labels(n)") or row.get("labels") or []
                if not isinstance(labels, list):
                    labels = []
                if _CODE_ANCHOR_LABELS.intersection(labels):
                    hit = {
                        "qn": row.get("n.qualified_name") or row.get("qualified_name") or "",
                        "file": row.get("n.file_path") or row.get("file_path") or "",
                        "line": row.get("n.start_line") or row.get("start_line") or 0,
                        "is_exported": bool(row.get("n.is_exported") or row.get("is_exported")),
                    }
                    return "code-anchored", hit

    # Step 2: BM25 fallback via search_graph.
    sg_result = _run_cbm_cli("search_graph", {"query": term})
    if sg_result.get("ran") and sg_result.get("exit_code", 1) == 0:
        rows = sg_result.get("result", [])
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                rank = row.get("rank") or row.get("score") or 0
                try:
                    rank_float = float(rank)
                except (TypeError, ValueError):
                    rank_float = -999.0
                if rank_float >= bm25_threshold:
                    hit = {
                        "qn": row.get("qualified_name") or row.get("n.qualified_name") or "",
                        "file": row.get("file_path") or row.get("n.file_path") or "",
                        "line": row.get("start_line") or row.get("n.start_line") or 0,
                        "is_exported": bool(row.get("is_exported") or row.get("n.is_exported")),
                    }
                    return "fuzzy-anchored", hit

    # Step 3: prose-only — term must appear in ≥2 distinct md paths.
    distinct_paths = len(set(occ[0] for occ in occurrences))
    if distinct_paths >= 2:
        return "prose-only", None

    # Insufficient evidence — caller should discard this term.
    return "insufficient", None


def _fetch_code_freq(term: str) -> int:
    """Query CBM for edge count into a node named <term>.

    Returns 0 on any failure.
    """
    result = _run_cbm_cli(
        "query_graph",
        {
            "query": (
                "MATCH (n)<-[:CALLS|USAGE|DEFINES]-() "
                "WHERE n.name='{term}' RETURN count(*) AS count"
            ).format(term=term.replace("'", "\\'"))
        },
    )
    if not result.get("ran") or result.get("exit_code", 1) != 0:
        return 0
    rows = result.get("result", [])
    if isinstance(rows, list) and len(rows) > 0:
        row = rows[0]
        if isinstance(row, dict):
            val = row.get("count") or row.get("count(*) AS count") or 0
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0
    if isinstance(rows, dict):
        val = rows.get("count") or 0
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0
    return 0


def _fetch_related_set(term: str) -> List[str]:
    """Query CBM for SEMANTICALLY_RELATED neighbors of term.

    Returns [] on any failure.
    """
    result = _run_cbm_cli(
        "query_graph",
        {
            "query": (
                "MATCH (n)-[:SEMANTICALLY_RELATED]-(m) "
                "WHERE n.name='{term}' RETURN m.name LIMIT 5"
            ).format(term=term.replace("'", "\\'"))
        },
    )
    if not result.get("ran") or result.get("exit_code", 1) != 0:
        return []
    rows = result.get("result", [])
    if not isinstance(rows, list):
        return []
    names: List[str] = []
    for row in rows:
        if isinstance(row, dict):
            name = row.get("m.name") or row.get("name") or ""
            if name:
                names.append(str(name))
    return names


def _fetch_snippet(qn: str) -> Optional[str]:
    """Fetch first 5 lines of code snippet for qn via get_code_snippet.

    Return values:
      None  — CBM is unreachable (binary absent, OSError, or nonzero exit).
              Callers should treat this as an I/O failure (exit 1).
      ""    — CBM ran successfully but returned no snippet content.
              Callers should treat this as a validation failure (exit 2).
      str   — Non-empty snippet content (success).
    """
    result = _run_cbm_cli("get_code_snippet", {"qualified_name": qn, "max_lines": 5})
    if not result.get("ran") or result.get("exit_code", 1) != 0:
        return None
    r = result.get("result", {})
    if isinstance(r, dict):
        snippet = r.get("snippet") or r.get("code") or r.get("content") or ""
        return str(snippet)
    if isinstance(r, str):
        return r
    return ""


def _rank_combined(doc_freq: int, code_freq: int, is_exported: bool) -> float:
    """Compute combined rank score using module-level weight constants."""
    score = (
        _W1 * math.log(doc_freq + 1)
        + _W2 * math.log(code_freq + 1)
        + _W3 * (1.0 if is_exported else 0.0)
    )
    return score


def _doc_context_for(
    occurrences: List[Tuple[str, int, str]]
) -> str:
    """Join context snippets from occurrences with a space separator."""
    contexts = [occ[2] for occ in occurrences if occ[2]]
    return " ".join(contexts)


# ── SUBCMD 1: build-glossary-bundles ────────────────────────────────────────


def _build_build_glossary_bundles(p: argparse.ArgumentParser) -> None:
    p.add_argument("--devforge-dir", default=".devforge")
    p.add_argument("--top-n", default=80, type=int)
    p.add_argument("--bm25-threshold", default=-25.0, type=float)


def cmd_build_glossary_bundles(args: argparse.Namespace) -> int:
    """Walk docs/ corpus, rank terms via CBM, emit JSON bundles to stdout.

    Exit 0 on success (even if 0 bundles — caller handles empty list).
    Exit 2 on empty docs/ corpus or other validation failure.
    Exit 1 on I/O error.
    """
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    docs_root = project_root / "docs"
    noise_override = devforge_dir / "glossary-noise.txt"
    top_n: int = args.top_n
    bm25_threshold: float = args.bm25_threshold

    t_start = time.monotonic()

    # Step 1: Walk corpus.
    corpus = walk_doc_corpus(docs_root)
    if not corpus:
        return _die(
            "build-glossary-bundles: docs/ is empty or does not exist at {0}".format(
                docs_root
            )
        )
    _info("build-glossary-bundles: corpus has {0} files".format(len(corpus)))
    t_walk = time.monotonic()

    # Step 2: Extract + noise-filter terms.
    raw_occurrences = extract_term_occurrences(corpus)
    filtered_terms = noise_filter(
        raw_occurrences.keys(),
        override_path=noise_override if noise_override.exists() else None,
    )
    # Build deduplicated occurrences dict with only filtered terms.
    occurrences: Dict[str, List[Tuple[str, int, str]]] = {
        t: raw_occurrences[t] for t in filtered_terms if t in raw_occurrences
    }
    _info(
        "build-glossary-bundles: {0} candidate terms after noise-filter".format(
            len(occurrences)
        )
    )
    t_extract = time.monotonic()

    # Step 3: Classify and collect initial CBM results.
    classified: List[Tuple[str, str, Optional[Dict[str, Any]]]] = []
    for term in occurrences:
        cls, cbm_hit = _classify_term(term, occurrences[term], bm25_threshold)
        if cls == "insufficient":
            continue
        classified.append((term, cls, cbm_hit))
    _info(
        "build-glossary-bundles: {0} terms classified ({1} code-anchored, "
        "{2} fuzzy-anchored, {3} prose-only)".format(
            len(classified),
            sum(1 for _, c, _ in classified if c == "code-anchored"),
            sum(1 for _, c, _ in classified if c == "fuzzy-anchored"),
            sum(1 for _, c, _ in classified if c == "prose-only"),
        )
    )
    t_classify = time.monotonic()

    # Step 4: Rank.
    ranked: List[Tuple[str, str, Optional[Dict[str, Any]], float]] = []
    for term, cls, cbm_hit in classified:
        doc_freq = len(occurrences[term])
        code_freq = _fetch_code_freq(term) if cls != "prose-only" else 0
        is_exported = (cbm_hit or {}).get("is_exported", False) if cbm_hit else False
        score = _rank_combined(doc_freq, code_freq, bool(is_exported))
        ranked.append((term, cls, cbm_hit, score))

    ranked.sort(key=lambda x: x[3], reverse=True)
    ranked = ranked[:top_n]
    _info(
        "build-glossary-bundles: top-{0} terms selected after ranking".format(
            len(ranked)
        )
    )
    t_rank = time.monotonic()

    # Step 5: Build bundles.
    bundles: List[Dict[str, Any]] = []
    for term, cls, cbm_hit, _score in ranked:
        # doc_context: join all context snippets.
        doc_context = _doc_context_for(occurrences[term])

        # code_anchor: fetch snippet for code-anchored / fuzzy-anchored.
        code_anchor: Optional[Dict[str, Any]] = None
        if cbm_hit and cls in ("code-anchored", "fuzzy-anchored"):
            qn = cbm_hit.get("qn", "")
            # _fetch_snippet returns None when CBM is unreachable; degrade to
            # empty string in bundle output (build phase does not exit on this).
            raw_snippet = _fetch_snippet(qn) if qn else ""
            snippet = raw_snippet if raw_snippet is not None else ""
            code_anchor = {
                "qn": qn,
                "file": cbm_hit.get("file", ""),
                "line": cbm_hit.get("line", 0),
                "snippet": snippet,
            }
            if cls == "fuzzy-anchored":
                code_anchor["fuzzy"] = True

        # related_set: SEMANTICALLY_RELATED edges.
        related_set = _fetch_related_set(term)

        # cite_md_paths: unique paths where term occurs.
        cite_md_paths = list(dict.fromkeys(occ[0] for occ in occurrences[term]))

        bundle: Dict[str, Any] = {
            "term": term,
            "class": cls,
            "doc_context": doc_context,
            "code_anchor": code_anchor,
            "related_set": related_set,
            "cite_md_paths": cite_md_paths,
        }
        bundles.append(bundle)

    t_bundle = time.monotonic()

    # Step 6: Write JSON to stdout; report stats to stderr.
    sys.stdout.write(json.dumps(bundles, indent=2, sort_keys=False))
    sys.stdout.write("\n")

    _info(
        "build-glossary-bundles: timings — walk={0}ms extract={1}ms "
        "classify={2}ms rank={3}ms bundle={4}ms total={5}ms".format(
            int((t_walk - t_start) * 1000),
            int((t_extract - t_walk) * 1000),
            int((t_classify - t_extract) * 1000),
            int((t_rank - t_classify) * 1000),
            int((t_bundle - t_rank) * 1000),
            int((t_bundle - t_start) * 1000),
        )
    )
    return 0


# ── SUBCMD 2: set-glossary-entries ───────────────────────────────────────────


def _build_set_glossary_entries(p: argparse.ArgumentParser) -> None:
    p.add_argument("--entries", required=True)
    p.add_argument("--bundles-file", required=True)
    p.add_argument("--devforge-dir", default=".devforge")


def _validate_entries(
    entries: List[Dict[str, Any]],
    bundles_by_term: Dict[str, Dict[str, Any]],
    project_root: Path,
) -> Tuple[Optional[str], int]:
    """Validate the LLM-provided entries list.

    Returns (None, 0) on success.
    Returns (error_message, 2) on validation failure (bad data).
    Returns (error_message, 1) on I/O failure (CBM unreachable during snippet check).

    Checks (in order):
      - Count: 30 <= len <= 150
      - Each entry is a dict with term (str), definition (str), related_terms (list)
      - Term uniqueness (case-insensitive)
      - Term has matching bundle
      - Definition non-empty post-strip, <=280 chars, no newline (single paragraph)
      - cite_md_paths: all paths exist
      - prose-only: cite_md_paths >= 2
      - code-anchored / fuzzy-anchored: code_anchor present with non-empty qn;
        snippet fetched — None means CBM unreachable (exit 1), "" means invalid qn (exit 2)
      - related_terms: each appears as a term elsewhere in entries (no dangling refs)
    """
    n = len(entries)
    if n < _MIN_TERMS:
        return (
            "set-glossary-entries: too few entries: got {0}, need >= {1}".format(
                n, _MIN_TERMS
            ),
            2,
        )
    if n > _MAX_TERMS:
        return (
            "set-glossary-entries: too many entries: got {0}, need <= {1}".format(
                n, _MAX_TERMS
            ),
            2,
        )

    # Build lower-cased term index for uniqueness + related-ref checks.
    term_lower_seen: Dict[str, int] = {}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            return "set-glossary-entries: entry[{0}] is not a dict".format(i), 2
        term = entry.get("term")
        if not isinstance(term, str) or not term.strip():
            return (
                "set-glossary-entries: entry[{0}].term missing or non-string".format(i),
                2,
            )
        key = term.strip().lower()
        if key in term_lower_seen:
            return (
                "set-glossary-entries: duplicate term (case-insensitive): "
                "'{0}' at indices {1} and {2}".format(
                    term.strip(), term_lower_seen[key], i
                ),
                2,
            )
        term_lower_seen[key] = i

    # Build set of all term-lower keys for related-ref check.
    all_term_keys: frozenset = frozenset(term_lower_seen.keys())

    for i, entry in enumerate(entries):
        term = entry["term"].strip()
        term_lower = term.lower()

        # Definition.
        definition = entry.get("definition")
        if not isinstance(definition, str):
            return (
                "set-glossary-entries: entry[{0}] ({1}): definition must be a string".format(
                    i, term
                ),
                2,
            )
        definition_stripped = definition.strip()
        if not definition_stripped:
            return (
                "set-glossary-entries: entry[{0}] ({1}): definition is empty".format(
                    i, term
                ),
                2,
            )
        if len(definition_stripped) > _DEFINITION_MAX_CHARS:
            return (
                "set-glossary-entries: entry[{0}] ({1}): definition exceeds "
                "{2} chars (got {3})".format(
                    i, term, _DEFINITION_MAX_CHARS, len(definition_stripped)
                ),
                2,
            )
        if "\n" in definition_stripped:
            return (
                "set-glossary-entries: entry[{0}] ({1}): definition must be "
                "single paragraph (no newline)".format(i, term),
                2,
            )

        # related_terms type check.
        related_terms = entry.get("related_terms")
        if not isinstance(related_terms, list):
            return (
                "set-glossary-entries: entry[{0}] ({1}): related_terms must be a list".format(
                    i, term
                ),
                2,
            )

        # Bundle lookup.
        bundle = bundles_by_term.get(term_lower)
        if bundle is None:
            return (
                "set-glossary-entries: entry[{0}] ({1}): no matching bundle found".format(
                    i, term
                ),
                2,
            )

        # cite_md_paths from bundle.
        cite_paths = bundle.get("cite_md_paths") or []
        if not cite_paths:
            return (
                "set-glossary-entries: entry[{0}] ({1}): bundle has no cite_md_paths".format(
                    i, term
                ),
                2,
            )
        ok, missing = validate_cite_paths(cite_paths, project_root / "docs")
        if not ok:
            return (
                "set-glossary-entries: entry[{0}] ({1}): cite_md_paths not found: {2}".format(
                    i, term, missing
                ),
                2,
            )

        cls = bundle.get("class", "prose-only")

        # prose-only must have >= 2 cite paths.
        if cls == "prose-only" and len(cite_paths) < 2:
            return (
                "set-glossary-entries: entry[{0}] ({1}): prose-only requires "
                ">=2 cite_md_paths, got {2}".format(i, term, len(cite_paths)),
                2,
            )

        # code-anchored / fuzzy-anchored: code_anchor must have non-empty qn.
        if cls in ("code-anchored", "fuzzy-anchored"):
            code_anchor = bundle.get("code_anchor")
            if not code_anchor or not code_anchor.get("qn"):
                return (
                    "set-glossary-entries: entry[{0}] ({1}): {2} entry "
                    "requires code_anchor with qn in bundle".format(i, term, cls),
                    2,
                )
            # Verify the qn resolves via get_code_snippet.
            # None means CBM unreachable (I/O failure → exit 1).
            # "" means CBM ran but returned no content (bad qn → exit 2).
            snippet = _fetch_snippet(code_anchor["qn"])
            if snippet is None:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): CBM unreachable "
                    "while fetching snippet for qn '{2}'".format(
                        i, term, code_anchor["qn"]
                    ),
                    1,
                )
            if not snippet:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): get_code_snippet "
                    "returned empty for qn '{2}'".format(i, term, code_anchor["qn"]),
                    2,
                )

        # related_terms: each must appear as a term elsewhere in the entries.
        for ref in related_terms:
            if not isinstance(ref, str):
                return (
                    "set-glossary-entries: entry[{0}] ({1}): related_terms "
                    "element must be a string, got {2!r}".format(i, term, ref),
                    2,
                )
            ref_lower = ref.strip().lower()
            if ref_lower == term_lower:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): related_terms "
                    "must not self-reference".format(i, term),
                    2,
                )
            if ref_lower not in all_term_keys:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): related_terms "
                    "dangling reference '{2}' not in entries".format(i, term, ref),
                    2,
                )

        # aliases_to_avoid: optional; default = [].
        aliases_raw = entry.get("aliases_to_avoid")
        if aliases_raw is None:
            aliases_raw = []
        if not isinstance(aliases_raw, list):
            return (
                "set-glossary-entries: entry[{0}] ({1}): aliases_to_avoid must be a list".format(
                    i, term
                ),
                2,
            )
        alias_keys_seen: List[str] = []
        for alias in aliases_raw:
            if not isinstance(alias, str) or not alias.strip():
                return (
                    "set-glossary-entries: entry[{0}] ({1}): aliases_to_avoid element "
                    "must be a non-empty string, got {2!r}".format(i, term, alias),
                    2,
                )
            alias_lower = alias.strip().lower()
            if alias_lower == term_lower:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): aliases_to_avoid must not "
                    "include the term itself".format(i, term),
                    2,
                )
            if alias_lower in alias_keys_seen:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): aliases_to_avoid contains "
                    "duplicate (case-insensitive): '{2}'".format(i, term, alias.strip()),
                    2,
                )
            alias_keys_seen.append(alias_lower)
            if alias_lower in all_term_keys and alias_lower != term_lower:
                return (
                    "set-glossary-entries: entry[{0}] ({1}): aliases_to_avoid entry "
                    "'{2}' is the canonical term of another entry".format(
                        i, term, alias.strip()
                    ),
                    2,
                )

    return None, 0


def _escape_md_inline(text: str) -> str:
    """Escape characters that md previewers parse as raw HTML.

    `<S>` in a paragraph triggers strikethrough in WebStorm + GitHub renderers
    when no closing `</S>` follows. Generic-type syntax like `BLoC<S>` is
    legitimate technical content and must round-trip as literal text in the
    rendered output, so encode `&`, `<`, `>` to HTML entities. Order matters:
    escape `&` first, then the angle brackets, otherwise the `&` from the
    just-inserted entities gets re-encoded.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_glossary(
    entries: List[Dict[str, Any]],
    bundles_by_term: Dict[str, Dict[str, Any]],
) -> str:
    """Render docs/glossary.md content as a string.

    Entries sorted alphabetically (case-insensitive) by term.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = len(entries)

    lines: List[str] = []

    # Frontmatter.
    lines.append("---")
    lines.append("generated_by: /generate-docs (Phase B — glossary)")
    lines.append("last_indexed: {0}".format(today))
    lines.append("total_terms: {0}".format(total))
    lines.append("---")
    lines.append("")

    # H1 + intro.
    lines.append("# Project Glossary")
    lines.append("")
    lines.append(
        "Terms surfaced in `docs/` and cross-referenced against the CBM-indexed "
        "code graph. Code-anchored entries link to a canonical definition; "
        "prose-only entries have no code symbol but appear in narrative."
    )
    lines.append("")

    # Sort alphabetically case-insensitive.
    sorted_entries = sorted(entries, key=lambda e: e["term"].strip().lower())

    for entry in sorted_entries:
        term = entry["term"].strip()
        definition = entry["definition"].strip()
        related_terms: List[str] = entry.get("related_terms") or []
        term_lower = term.lower()
        bundle = bundles_by_term.get(term_lower) or {}
        cls = bundle.get("class", "prose-only")
        code_anchor = bundle.get("code_anchor")
        cite_paths: List[str] = bundle.get("cite_md_paths") or []

        lines.append("## {0}".format(_escape_md_inline(term)))
        lines.append("")
        lines.append(_escape_md_inline(definition))
        lines.append("")

        # "Defined" line (omit for prose-only).
        if cls != "prose-only" and code_anchor and code_anchor.get("qn"):
            qn = code_anchor["qn"]
            line_no = code_anchor.get("line", 0)
            fuzzy_suffix = " (fuzzy)" if cls == "fuzzy-anchored" else ""
            lines.append(
                "- **Defined**: `{qn}:{line}`{suffix}".format(
                    qn=qn, line=line_no, suffix=fuzzy_suffix
                )
            )

        # "Used in" line.
        if cite_paths:
            if len(cite_paths) <= _USED_IN_INLINE_CAP:
                inline_paths = ", ".join("`{0}`".format(p) for p in cite_paths)
                lines.append("- **Used in**: {0}".format(inline_paths))
            else:
                inline_paths = ", ".join(
                    "`{0}`".format(p) for p in cite_paths[:_USED_IN_INLINE_CAP]
                )
                others = len(cite_paths) - _USED_IN_INLINE_CAP
                lines.append(
                    "- **Used in**: {0} (and {1} others)".format(inline_paths, others)
                )

        # "Related" line (omit if empty).
        if related_terms:
            escaped_related = [_escape_md_inline(rt) for rt in related_terms]
            lines.append(
                "- **Related**: {0}".format(", ".join(escaped_related))
            )

        # "Aliases to AVOID" line (omit if empty/absent).
        aliases_to_avoid: List[str] = entry.get("aliases_to_avoid") or []
        if aliases_to_avoid:
            escaped_aliases = [_escape_md_inline(a) for a in aliases_to_avoid]
            lines.append(
                "- **Aliases to AVOID**: {0}".format(", ".join(escaped_aliases))
            )

        lines.append("")

    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via mkstemp + os.replace.

    Creates parent directory if needed.
    Raises OSError on failure (after unlinking the temp file).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".glossary-",
        suffix=".md",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_set_glossary_entries(args: argparse.Namespace) -> int:
    """Consume LLM entries JSON + bundles file, validate, render docs/glossary.md.

    Exit 0 on success.
    Exit 1 on I/O failure.
    Exit 2 on validation failure.
    """
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    glossary_path = project_root / "docs" / "glossary.md"

    # Step 1: Decode entries JSON.
    try:
        raw_entries = json.loads(args.entries)
    except json.JSONDecodeError as exc:
        return _die(
            "set-glossary-entries: --entries is not valid JSON: {0}".format(exc)
        )
    if not isinstance(raw_entries, list):
        return _die("set-glossary-entries: --entries must be a JSON array")

    # Step 2: Load bundles file.
    bundles_path = Path(args.bundles_file)
    try:
        bundles_text = bundles_path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            "generate_docs_helper: set-glossary-entries: cannot read bundles file: {0}\n".format(exc)
        )
        return 1
    try:
        raw_bundles = json.loads(bundles_text)
    except json.JSONDecodeError as exc:
        return _die(
            "set-glossary-entries: bundles file is not valid JSON: {0}".format(exc)
        )
    if not isinstance(raw_bundles, list):
        return _die("set-glossary-entries: bundles file must be a JSON array")

    # Build case-insensitive lookup by term.
    bundles_by_term: Dict[str, Dict[str, Any]] = {}
    for bundle in raw_bundles:
        if isinstance(bundle, dict) and isinstance(bundle.get("term"), str):
            bundles_by_term[bundle["term"].strip().lower()] = bundle

    # Step 3 + 4: Validate.
    error, err_code = _validate_entries(raw_entries, bundles_by_term, project_root)
    if error is not None:
        return _die(error, err_code)

    # Step 5: Render.
    content = _render_glossary(raw_entries, bundles_by_term)

    # Step 6: Write atomically.
    try:
        _atomic_write(glossary_path, content)
    except OSError as exc:
        sys.stderr.write(
            "generate_docs_helper: set-glossary-entries: failed to write {0}: {1}\n".format(
                glossary_path, exc
            )
        )
        return 1

    sys.stdout.write(str(glossary_path) + "\n")
    _info("set-glossary-entries: wrote {0}".format(glossary_path))
    return 0
