# /audit — Hotspot scoring (`--top N` mode)

Reference for `src/commands/audit/main.md` Phase 2.1. This documents the risk-score formula, default weights, knobs, and the CBM-required gate for the hotspot middle mode. The scoring math + ranking live in `.devforge/lib/audit_helper compute-hotspots`; this file is the contract — keep it in sync with the helper if either changes.

Hotspot mode is the risk-targeted middle path between **narrow** (one file / dir / `--uncommitted`) and **broad** (whole codebase). On very large repos broad mode is impractical (4 agents reading the world overwhelm the Top-10 ranker and per-agent context windows) and narrow misses cross-cutting patterns. `--top N` scores every candidate file by risk, takes the top N, and runs the full adversarial ensemble against just that set — periodic, bounded, signal-rich.

## Risk formula

```
risk(file) = w_c · churn_norm + w_k · callers_norm + w_s · size_norm
```

Per-file inputs:

- **churn** — commit count touching the file in the last 90 days (`git log --since=90.days.ago --oneline -- <file>`). Recent change concentrates risk. Computed by the helper itself (subprocess).
- **callers** — inbound-edge count to the symbols defined in the file (CBM `trace_path` aggregated). Heavy use means a bug here blasts wide. **Supplied by the orchestrator** as a `--callers` JSON payload — a subprocess helper cannot call MCP, so the orchestrator resolves caller counts via CBM and passes them in.
- **size** — non-blank lines of code. A weak tiebreaker only.

Each raw metric is **min-max normalized** to `[0, 1]` within the candidate set before weighting; the weighted sum is the file's score, also in `[0, 1]`. All-zero-churn (or any all-zero metric) normalizes without NaN.

## Default weights

```
w_c = 0.5   (churn)
w_k = 0.4   (callers)
w_s = 0.1   (size)
```

Recent-change-heavy + heavy-use-heavy; size only breaks ties. This default matches plan Decision 3 (OQ-1 resolved).

## Knobs

- **`--top N`** — how many top-ranked files to audit. Default `N = 25` (OQ-2 resolved). Hotspot is the recommended default mode for periodic audits on repos over ~50K LOC.
- **`--weights c=<>,k=<>,s=<>`** — override the default weights for tuning. The three weights must each be in `[0, 1]` and sum to `1.0` (within a small tolerance); the helper rejects malformed or non-summing weights.

Invoke (Phase 2.1):

```bash
.devforge/lib/audit_helper compute-hotspots --top N --callers '<json>' [--weights c=0.5,k=0.4,s=0.1]
```

## CBM-required gate (no grep fallback)

Hotspot scoring depends on caller counts from CBM. A grep-approximation (literal symbol search) is too noisy — common-named symbols (`get`, `set`, `init`) get false-high scores; renames between call sites mask true callers. Therefore, in hotspot mode, **CBM is required**: when the `--callers` payload is absent, `compute-hotspots` exits 2 with an install reminder (Decision 8). Copy the helper's stderr VERBATIM and end the turn. Narrow + broad modes do not score files, so they degrade gracefully without CBM.

## Next 10 Candidates tail

The helper always emits the positions N+1..N+10 by score as the "Next 10 Candidates" tail (OQ-5 resolved). `render-hotspot-summary` renders each as `file · score · (churn, callers, size)`. This appears in the report appendix (see `.claude/commands/audit/references/report-format.md`) so the user can sanity-check what was almost picked and re-tune weights if the ranking looks wrong.
