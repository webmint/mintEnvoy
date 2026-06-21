"""Source Map V3 consumer (single-source maps only).

Decoder for the .vue.ts.map sidecar emitted by tools/vue-to-ts.mjs. Resolves
generated-position queries (in the compiled .vue.ts) back to the original
.vue source position so cite-back in concern docs can point at the original
file rather than the intermediate.

Stdlib only. Multi-source maps are rejected explicitly; vue-to-ts always
emits single-source maps.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


_BASE64 = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)
_BASE64_INDEX = {c: i for i, c in enumerate(_BASE64)}


class SourceMapError(Exception):
    pass


class MalformedSourceMapError(SourceMapError):
    pass


class MappingNotFoundError(SourceMapError):
    pass


@dataclass
class _Segment:
    gen_col: int
    source_idx: int
    orig_line: int
    orig_col: int
    name_idx: Optional[int]


@dataclass
class SourceMap:
    version: int
    sources: List[str]
    sources_content: Optional[List[str]]
    mappings: str
    _decoded_lines: List[List[_Segment]] = field(default_factory=list, repr=False)


def _decode_vlq(s: str) -> List[int]:
    """Decode a base64-VLQ segment string into a list of signed ints."""
    out: List[int] = []
    value = 0
    shift = 0
    for ch in s:
        digit = _BASE64_INDEX.get(ch)
        if digit is None:
            raise MalformedSourceMapError(
                f"invalid base64 character {ch!r} in mappings"
            )
        cont = (digit >> 5) & 1
        value |= (digit & 31) << shift
        shift += 5
        if not cont:
            sign = value & 1
            magnitude = value >> 1
            out.append(-magnitude if sign else magnitude)
            value = 0
            shift = 0
    if shift != 0:
        raise MalformedSourceMapError(
            "unterminated VLQ value at end of segment"
        )
    return out


def _decode_mappings(mappings: str) -> List[List[_Segment]]:
    """Walk a mappings string into per-line segment lists.

    Field deltas accumulate per V3 spec: gen_col resets each line; source_idx,
    orig_line, orig_col, and name_idx persist across lines.
    """
    src_idx = 0
    orig_line = 0
    orig_col = 0
    name_idx = 0
    lines: List[List[_Segment]] = []
    for line_str in mappings.split(";"):
        gen_col = 0
        line: List[_Segment] = []
        if line_str:
            for seg_str in line_str.split(","):
                if not seg_str:
                    continue
                fields = _decode_vlq(seg_str)
                if len(fields) not in (1, 4, 5):
                    raise MalformedSourceMapError(
                        f"segment must have 1, 4, or 5 fields, got {len(fields)}"
                    )
                gen_col += fields[0]
                if len(fields) == 1:
                    line.append(_Segment(gen_col, -1, -1, -1, None))
                    continue
                src_idx += fields[1]
                orig_line += fields[2]
                orig_col += fields[3]
                if len(fields) == 5:
                    name_idx += fields[4]
                    line.append(
                        _Segment(gen_col, src_idx, orig_line, orig_col, name_idx)
                    )
                else:
                    line.append(
                        _Segment(gen_col, src_idx, orig_line, orig_col, None)
                    )
        lines.append(line)
    return lines


def parse_sourcemap(text: str) -> SourceMap:
    """Parse a Source Map V3 JSON string. Raises MalformedSourceMapError on any defect."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedSourceMapError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MalformedSourceMapError("sourcemap root must be a JSON object")
    version = data.get("version")
    if version != 3:
        raise MalformedSourceMapError(
            f"unsupported sourcemap version (need 3, got {version!r})"
        )
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise MalformedSourceMapError("sources must be a non-empty list")
    if not all(isinstance(s, str) for s in sources):
        raise MalformedSourceMapError("sources entries must be strings")
    if len(sources) > 1:
        raise MalformedSourceMapError(
            f"multi-source maps not supported in v0 (sources length = {len(sources)})"
        )
    sources_content = data.get("sourcesContent")
    if sources_content is not None:
        if not isinstance(sources_content, list):
            raise MalformedSourceMapError("sourcesContent must be a list")
        if len(sources_content) != len(sources):
            raise MalformedSourceMapError(
                f"sourcesContent length ({len(sources_content)}) must match "
                f"sources length ({len(sources)})"
            )
    mappings = data.get("mappings")
    if not isinstance(mappings, str):
        raise MalformedSourceMapError("mappings must be a string")
    sm = SourceMap(
        version=version,
        sources=sources,
        sources_content=sources_content,
        mappings=mappings,
    )
    sm._decoded_lines = _decode_mappings(mappings)
    return sm


def apply_mapping(
    sm: SourceMap,
    gen_line: int,
    gen_col: int = 1,
    nearest: bool = False,
) -> Tuple[str, int, int]:
    """Resolve a 1-based generated position to a 1-based original position.

    Returns (source_path, orig_line, orig_col); source_path is verbatim from
    the map's `sources[0]` (caller canonicalises to project-root-relative).

    Strict mode (default, `nearest=False`): pick the largest segment on
    `gen_line` whose `gen_col` is <= the requested column. Raises
    MappingNotFoundError when the line has no segments, when no segment is
    at-or-before the requested column, or when the matched segment is
    gen-col-only (1-field; no original position).

    Nearest mode (`nearest=True`): used for cite-back over sparse maps —
    Vue's compiler emits no segments for synthesized boilerplate lines (the
    defineComponent wrapper, __expose()/__returned__, etc.), so a strict
    lookup at a Function's start_line frequently misses. With nearest=True,
    if `gen_line` has no usable segment, walk BACKWARD line-by-line to the
    most recent line that does, and return ITS last mapped segment. Returns
    the orig position of the closest mapped point at-or-before the query.
    Still raises MappingNotFoundError if no mapping exists at all on or
    before the query.
    """
    if gen_line < 1:
        raise MappingNotFoundError(f"gen_line must be >= 1 (got {gen_line})")
    if gen_col < 1:
        raise MappingNotFoundError(f"gen_col must be >= 1 (got {gen_col})")
    if not sm._decoded_lines:
        raise MappingNotFoundError("source map has no mapped lines")
    line_idx = gen_line - 1
    col_idx = gen_col - 1

    # Strict pass on the query line: largest source-mapped seg with gen_col <= col_idx.
    chosen: Optional[_Segment] = None
    if line_idx < len(sm._decoded_lines):
        for seg in sm._decoded_lines[line_idx]:
            if seg.gen_col > col_idx:
                break
            if seg.source_idx >= 0:
                chosen = seg

    if chosen is None:
        if not nearest:
            if line_idx >= len(sm._decoded_lines):
                raise MappingNotFoundError(
                    f"gen_line {gen_line} beyond mapped lines ({len(sm._decoded_lines)})"
                )
            if not sm._decoded_lines[line_idx]:
                raise MappingNotFoundError(f"no segments on gen_line {gen_line}")
            # Either no seg at-or-before col, or the at-or-before seg is gen-col-only.
            raise MappingNotFoundError(
                f"no source-mapped segment covers gen_line {gen_line} col {gen_col}"
            )
        # Nearest mode: walk backward through prior lines, take their LAST
        # source-mapped seg. (The query line was already exhausted strictly.)
        if line_idx >= len(sm._decoded_lines):
            scan_idx = len(sm._decoded_lines) - 1
        else:
            scan_idx = line_idx - 1
        while scan_idx >= 0:
            for seg in sm._decoded_lines[scan_idx]:
                if seg.source_idx >= 0:
                    chosen = seg
            if chosen is not None:
                break
            scan_idx -= 1
        if chosen is None:
            raise MappingNotFoundError(
                f"nearest: no mapped segment at or before gen_line {gen_line}"
            )

    return (
        sm.sources[chosen.source_idx],
        chosen.orig_line + 1,
        chosen.orig_col + 1,
    )
