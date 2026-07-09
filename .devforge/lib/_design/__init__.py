"""Internal package for design_helper (the design-anchor + binding apparatus
for design fidelity — plan 40 Phase 2, reframed to the anchor/binding schema
in plan 53 Phase 3).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `design_helper` or `design_helper.main`.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Current verbs:
  validate-binding        — validate a per-feature binding JSON (route + >=1
                            anchor_selector/built_testid pair) against
                            specs/[feature]/design-manifest.json
  extract-spacing-scale   — extract spacing scale from styles.css (OQ-6 relaxation)
  check-design-source     — warn (non-blocking) when a non-file design source
                            is declared but no enforceable reference exists
  compare                 — run the deterministic intent-reader x built-reader
                            x comparator engine (plan 53 Phase 4/5): reads a
                            built measurement bag (+ optional intent bag +
                            binding), applies the always-on anchor-free
                            sanity floor (overflow/clip/font-not-loaded) and
                            the anchor-gated value/geometry fidelity checks,
                            and emits a {status, ...} ComparisonResult
                            distinguishing NOT_COVERED / CLEAN / DEFECT

The comparator's inputs are measurement "bags" (`_bag.py`) produced by two
THIN, decision-free JS `evaluate_script` collectors under `js/`:
`js/built_reader.js` (web DOM, keyed by built_testid) and
`js/intent_reader.js` (the rendered html design anchor, keyed by anchor CSS
selector). ALL predicates live in Python (`_floor.py` anchor-free checks,
`_fidelity.py` anchor-gated checks, `_comparator.py` orchestration) — the JS
assets never decide anything, only measure (OQ-A resolution: jsdom has no
layout engine or font loading, so decision logic must be Python-side to stay
unit-testable against synthetic bag fixtures).

RETIRED (plan 53 Phase 3): resolve-reference and init-manifest, along with the
data-ref / disposition-manifest schema they fed (see `_schema.py`'s module
docstring). The anchor (`specs/[feature]/design-anchor.json`) captures design
INTENT at intake; the binding (this package's current schema) is authored
later at `/breakdown` as the built-side wiring.

Later phases (Phase 6/7) wire `design-auditor` + `/review` + `/breakdown` to
call the `compare` verb — no changes to this file required for that wiring.
"""

from ._cli import main

__all__ = ["main"]
