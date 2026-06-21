"""Error wrapper + validators + UTC timestamp."""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path
from typing import Tuple

from ._schema import NFR_NAMED_CLASS_RE, NFR_NUMERIC_THRESHOLD_RE, NFR_VAGUE_BLOCKLIST


def _die(message: str, code: int = 1) -> int:
    sys.stderr.write("specify_helper: {0}\n".format(message))
    return code


def _validate_scalar(value: str, field_name: str) -> str:
    stripped = (value or "").strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


def _validate_enum(
    value: str, field_name: str, allowed: Tuple[str, ...],
) -> str:
    if value not in allowed:
        raise ValueError(
            "{0}: value {1!r} not in allowed {2!r}".format(
                field_name, value, allowed,
            )
        )
    return value


def _validate_nfr_quantifier(quantifier: str) -> Tuple[bool, str]:
    """Validate an NFR --quantifier value.

    Accept: numeric threshold + unit (e.g. "10K users @ p95 < 200ms")
            OR named-class compliance citation (e.g. "PCI-DSS Level 1").
    Reject: empty, vague adjective alone, or anything matching neither shape.

    Returns (ok, error_message).
    """
    qstripped = (quantifier or "").strip()
    if not qstripped:
        return False, "nfr: --quantifier required and non-empty"
    if qstripped.lower() in NFR_VAGUE_BLOCKLIST:
        return False, (
            "nfr: vague quantifier {0!r} rejected. "
            "Use numeric threshold + unit (e.g. '10K users @ p95 < 200ms') "
            "OR named-class citation (e.g. 'PCI-DSS Level 1', 'SOC 2 Type II')."
            .format(quantifier)
        )
    if NFR_NUMERIC_THRESHOLD_RE.search(qstripped):
        return True, ""
    if NFR_NAMED_CLASS_RE.search(qstripped):
        return True, ""
    return False, (
        "nfr: quantifier requires numeric threshold with unit "
        "(ms/s/users/req/rps/GB/%/$/connections/rows/etc.) "
        "OR named-class citation (PCI-DSS / SOC 2 / ISO XXXXX / GDPR / etc.). "
        "Bare adjective rejected as vague."
    )


def _validate_constitution_anchor_ref(
    ref: str,
    devforge_dir: str,
) -> Tuple[bool, str]:
    """Validate that `ref` points at a real section in <install_root>/constitution.md.

    install_root is the parent of `.devforge/`. `ref` is e.g. "§3.6" or "3.6"
    — both accepted; the grep matches `^### §<N.M>` OR `^### <N.M>`.
    """
    raw = (ref or "").strip()
    if not raw:
        return False, "constitution_anchor: --constitution-ref required and non-empty"
    bare = raw.lstrip("§").strip()
    install_root = Path(devforge_dir).resolve().parent
    constitution = install_root / "constitution.md"
    if not constitution.is_file():
        return False, (
            "constitution_anchor: constitution.md not found at {0} — run /constitute first"
            .format(constitution)
        )
    pattern = re.compile(
        r"^###\s+§?{0}\b".format(re.escape(bare)),
        re.MULTILINE,
    )
    try:
        text = constitution.read_text(encoding="utf-8")
    except OSError as err:
        return False, (
            "constitution_anchor: cannot read {0}: {1}".format(constitution, err)
        )
    if not pattern.search(text):
        return False, (
            "constitution_anchor: §{0} not found in constitution.md".format(bare)
        )
    return True, ""


def _validate_external_system(
    protocol: str,
    contract_doc_ref: str,
) -> Tuple[bool, str]:
    """Validate that an external_system constraint cites a contract."""
    has_protocol = bool((protocol or "").strip())
    has_contract = bool((contract_doc_ref or "").strip())
    if not has_protocol and not has_contract:
        return False, (
            "external_system: requires --protocol (e.g. 'REST', 'gRPC', 'SAML 2.0') "
            "OR --contract-doc-ref (path to OpenAPI / proto file)"
        )
    return True, ""


def _utc_timestamp() -> str:
    """ISO-8601 UTC timestamp at second precision (deterministic format)."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
