"""Step 4 probe-tier classification utilities.

_classify_probe_tier walks a decision tree from probe_feasibility flags +
test_infra state + Chrome MCP presence to a tier (1 / 1.5 / 2 / 3) plus
actor (llm/user), test_framework, test_path, script_path, and
discriminator text. _read_test_infra_status reads .devforge/init.yaml
lazily (avoids module-level circular import with init_helper).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Union


# Extension → file suffix for test_path construction.
_FRAMEWORK_EXTENSION_MAP = {
    "vitest": ".spec.ts",
    "jest": ".spec.ts",
    "mocha": ".spec.ts",
    "jasmine": ".spec.ts",
    "pytest": ".py",
    "nose2": ".py",
    "go-test": "_test.go",
    "cargo-test": ".rs",
    "rspec": "_spec.rb",
    "minitest": "_test.rb",
    "playwright": ".spec.ts",
    "cypress": ".spec.ts",
}

# Frameworks whose extension maps to .spec.ts (so they validate against handoff_schema enum).
# handoff_schema._VALID_TEST_FRAMEWORK = {vitest, jest, pytest, go-test, cargo-test, rspec}
# We must only pass these to the schema — others are not in the enum.
_SCHEMA_VALID_FRAMEWORKS = frozenset({"vitest", "jest", "pytest", "go-test", "cargo-test", "rspec"})


def _chrome_mcp_available():
    # type: () -> bool
    """Detect Chrome MCP availability via env var (test-mockable).

    Returns True when DEVFORGE_CHROME_MCP_AVAILABLE == "1", False otherwise.
    Conservative: env-var-driven for test-mockability.
    """
    return os.environ.get("DEVFORGE_CHROME_MCP_AVAILABLE", "") == "1"


def _read_test_infra_status(devforge_dir):
    # type: (Union[str, "os.PathLike[str]"]) -> Tuple[Optional[str], Optional[dict]]
    """Read .devforge/init.yaml and extract test_infra block.

    Returns (status, full_dict). On missing init.yaml / parse error → (None, None).
    """
    init_yaml = Path(devforge_dir) / "init.yaml"
    if not init_yaml.is_file():
        return (None, None)
    try:
        # Import lazily to avoid module-level circular dependency.
        # Ensure the lib dir (parent of _research/) is on sys.path so
        # `import init_helper` resolves the sibling module.
        _lib_dir = str(Path(__file__).resolve().parent.parent)
        if _lib_dir not in sys.path:
            sys.path.insert(0, _lib_dir)
        import init_helper  # noqa: F401
        text = init_yaml.read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
        ti = state.get("test_infra")
        if isinstance(ti, dict):
            return (ti.get("status"), ti)
    except (OSError, UnicodeDecodeError, init_helper.YamlParseError) as err:
        sys.stderr.write(
            "_read_test_infra_status: degraded read of {0}: {1}\n".format(init_yaml, err)
        )
    return (None, None)


def _pick_framework_from_test_infra(test_infra):
    # type: (Optional[dict]) -> Optional[str]
    """Pick a test framework from test_infra dict in priority order: frontend → backend → e2e.

    Returns the first non-None bucket value if it is in the schema-valid set,
    else None.
    """
    if not isinstance(test_infra, dict):
        return None
    for bucket in ("frontend", "backend", "e2e"):
        val = test_infra.get(bucket)
        if val and val in _SCHEMA_VALID_FRAMEWORKS:
            return val
    return None


def _classify_probe_tier(
    feasibility,        # type: dict
    test_infra_status,  # type: Optional[str]
    chrome_mcp,         # type: bool
    test_infra,         # type: Optional[dict]
    topic_slug,         # type: str
    research_date,      # type: str
):
    # type: (...) -> dict
    """Classify probe tier from feasibility flags + test_infra + chrome_mcp.

    Decision tree per RESEARCH-HANDOFF-PLAN.md Step 4:
    1. is_test_code=True → tier=3 (circular gate: tier-1 probe of test code is meaningless)
    2. data_shape_only=True AND NOT (auth_required OR network_dependent OR timing_dependent):
       - test_infra absent/None → tier=1.5
       - otherwise → tier=1
    3. auth_required=True OR network_dependent=True:
       - chrome_mcp → tier=2
       - else → tier=3
    4. fallback → tier=3

    Note: there is no override surface (finalize-handoff has no --probe-tier arg).
    Future override-handling would re-evaluate this function with user-supplied context.

    Returns a dict matching the Probe dataclass field subset:
    {tier, actor, test_framework, test_path, script_path, is_first_test_for_file,
     runner_up_confirms_if, both_disproved_if}
    """
    # Step 1: circular gate — test code cannot be tier-1 probed meaningfully.
    if feasibility.get("is_test_code") is True:
        tier = "3"
        actor = "user"
    elif (
        feasibility.get("data_shape_only") is True
        and not feasibility.get("auth_required")
        and not feasibility.get("network_dependent")
        and not feasibility.get("timing_dependent")
    ):
        # data_shape_only path — tier depends on test infra.
        if test_infra_status == "absent" or test_infra_status is None:
            tier = "1.5"
            actor = "llm"
        else:
            tier = "1"
            actor = "llm"
    elif feasibility.get("auth_required") is True or feasibility.get("network_dependent") is True:
        # Network/auth path — chrome MCP determines tier.
        if chrome_mcp:
            tier = "2"
            actor = "llm"
        else:
            tier = "3"
            actor = "user"
    else:
        # Fallback: no clear feasibility signal.
        tier = "3"
        actor = "user"

    # Populate test_framework / test_path / script_path / is_first_test_for_file.
    test_framework = None   # type: Optional[str]
    test_path = None        # type: Optional[str]
    script_path = None      # type: Optional[str]
    is_first_test_for_file = False

    if tier == "1":
        framework = _pick_framework_from_test_infra(test_infra)
        if framework is None:
            # test_infra says "present" but no recognized framework found —
            # demote to tier=1.5 (inconsistent state: status=present, all buckets empty/unknown).
            tier = "1.5"
            actor = "llm"
        else:
            ext = _FRAMEWORK_EXTENSION_MAP.get(framework, ".spec.ts")
            test_framework = framework
            test_path = "tests/research/{0}.probe{1}".format(topic_slug, ext)
            is_first_test_for_file = True  # Conservative: assume new test file.

    if tier == "1.5":
        script_path = "research/{0}-{1}/probe-script.mjs".format(research_date, topic_slug)
        test_framework = None
        is_first_test_for_file = False

    # Populate discriminator text for runner_up and both_disproved.
    if tier in ("1", "1.5"):
        runner_up_confirms_if = (
            "if test FAILS but with different assertion outcome "
            "→ runner-up applies; LLM evaluates output diff"
        )
        both_disproved_if = (
            "if test PASSES with current code "
            "→ both hypotheses are wrong; widen investigation"
        )
    else:
        runner_up_confirms_if = "tbd — manual observation required"
        both_disproved_if = "tbd"

    return {
        "tier": tier,
        "actor": actor,
        "test_framework": test_framework,
        "test_path": test_path,
        "script_path": script_path,
        "is_first_test_for_file": is_first_test_for_file,
        "runner_up_confirms_if": runner_up_confirms_if,
        "both_disproved_if": both_disproved_if,
    }
