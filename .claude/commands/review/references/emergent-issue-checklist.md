=== EMERGENT CROSS-TASK ISSUE CHECKLIST ===

Hunt the ASSEMBLED feature diff for these four cross-task patterns. These are
EXAMPLES of what to look for, NOT a list of bugs you should find. If the
feature has none of them, report none. Every pattern here requires reading TWO
OR MORE tasks together — a finding you can state from a single task's diff is
out of scope (see the anti-relitigation preamble).

Every finding from this checklist MUST set its `Category:` field. Each section
below states which Category its findings map to. The available Category values
are: mislogic | system_design | best_practice | duplication | security |
blind_spot. Use only these.


Cross-task security holes  (Category: security)
- A trust/auth boundary one task establishes that another task bypasses — task
  A adds the guard, task B adds an endpoint, route, or code path that reaches
  the protected resource WITHOUT going through it. Anchor on the bypassing path
  (quote it in `Evidence:`) and name the boundary it skips by path and line.
- A validation that holds per-task but is SKIPPABLE once the composed flow
  exists — task A validates input on one entry, task B adds a second entry to
  the same downstream sink that does not. Anchor on the unvalidated second entry
  and name the validated first entry plus the shared sink by path and line.
- Secrets / permissions that interact across tasks — a credential, scope, or
  permission one task narrows that another task widens or re-exposes; a value
  one task treats as trusted that another task sources from untrusted input.
  Anchor on the widening / untrusted-source side and name the narrowing /
  trusting side by path and line.


Assembled-data-flow performance  (Category: system_design for an
architecture/data-flow cost; best_practice for a local idiom smell — see the
rule below)
- A query / loop / fetch pattern that is fine WITHIN one task but becomes N+1,
  O(n²), or a redundant refetch once the tasks COMPOSE into the full data flow
  — task A adds a per-row fetch helper, task B calls it inside a loop over a
  collection task A populates; or two tasks each fetch the same resource on the
  same request. Anchor on the composing caller that turns it costly (the loop,
  the duplicate fetch) and name the per-task piece it calls by path and line.
- Which Category: if the cost is an emergent property of how the tasks' layers
  or data flow are wired together (an N+1 born of one task looping over
  another's per-item call, a refetch across a layer boundary), it is
  `system_design`. If, after assembly, the costly construct is a single local
  idiom that should have been memoized/derived/batched in one spot (a
  per-render heavy computation now sitting on a composed render path), it is
  `best_practice`. State which one and why.


Cross-task duplication / divergence  (Category: duplication)
- Multiple tasks each adding a near-identical helper, type, validation, or
  component that should have been unified — each task open-coded its own copy
  of the same logic because neither saw the other's. Anchor on one copy (quote
  it in `Evidence:`), name the other copy / copies by path and line, and name
  what should be shared.
- Two DIVERGED copies of the same logic — two tasks that each implemented the
  same rule slightly differently (different threshold, different edge-case
  handling, different shape for the same concept), so the feature now carries
  contradictory copies of one thing. Anchor on the diverged copy, name the
  original copy by path and line, and point out the drift between them.


Cross-task architectural drift  (Category: system_design)
- Two tasks that each made a locally-reasonable choice that are GLOBALLY
  inconsistent — different patterns for the same concern (one task handles
  errors one way, another a contradictory way; one names/structures a thing one
  way, another diverges), so the assembled feature has no single answer. Anchor
  on one approach (quote it in `Evidence:`) and name the contradicting approach
  by path and line.
- A layering or dependency-direction violation visible ONLY across task
  boundaries — task A's layer reaches into task B's layer in a direction the
  architecture forbids, where neither task's diff alone crosses the boundary.
  Anchor on the import or call that crosses the boundary once the tasks are
  assembled (quote it in `Evidence:`) and name the layer it reaches into by path
  and line.
- An abstraction one task introduced that another task BYPASSED — task A adds a
  repository / service / wrapper meant to be the single way through, task B
  reaches around it to the underlying resource directly. Anchor on the bypass
  (quote it in `Evidence:`) and name the abstraction it reaches around by path
  and line.


Grounding rule (mandatory — same single-anchor discipline as /audit)
Every finding MUST include a verbatim Evidence quote copy-pasted from the actual
source. The cross-task interaction spans two files, but the `Evidence:` block
quotes exactly ONE of them — the ANCHOR file named in the finding's `File:`
field. Choose the anchor as the most damning defect site of the interaction —
usually the bypass / violation / divergence site (the code path that reaches the
protected resource, the second entry that skips validation, the diverged copy).
The `Evidence:` snippet MUST be a verbatim substring of that anchor file: the
report grounds a finding by checking the Evidence text against the single file in
`File:`, so a snippet copied from any other file is discarded as ungrounded. Do
NOT put a second file's code inside the `Evidence:` block, and do NOT use
`// from <fileA>` / `// from <fileB>` separators — the combined block is a
substring of neither file and the whole finding is silently dropped.

The cross-task PARTNER file — the other side of the interaction (the boundary
that is bypassed, the first validated entry, the original copy) — is named in
`Why it's wrong:` by path and line, not quoted in `Evidence:` (e.g. "the auth
boundary established in `src/auth.py:42` is bypassed by this code path"). Single
quote, prose partner: grounding proves the anchor snippet is real, and the
cross-task INTERACTION claim is then stress-tested by the refutation pass (a
refuter reads BOTH files before the finding reaches the report). So a single
anchor quote plus a path-and-line partner reference is sufficient and correct —
it is exactly how /audit grounds its cross-file findings. If you cannot name a
real defect site in one file and a real partner site in another, you cannot
report the finding.

A finding that is an OPINION or a best-practice PREFERENCE rather than a defect
provable from the quoted anchor plus the named partner MUST be marked Confidence
`Likely` or `Speculative` — never `Certain`. `Certain` is reserved for an
emergent defect provable from the quoted anchor against the named partner (a path
that demonstrably bypasses the named boundary, a copy that demonstrably diverged
from the named original). The verbatim quote stops fabrication; the Confidence
tier keeps subjective cross-task judgments honest.


For each finding from this checklist, write a `## Finding N` block with these
exact fields (the report parser reads them by name — match the labels verbatim):
- Severity (Critical | High | Medium | Info)
- File (relative path of the file the finding is anchored to)
- Line (the line number the finding is anchored to)
- Pattern (the matched cross-task pattern, one line — append the
  `[CONSTITUTION-VIOLATION]` tag here if a constitution principle is violated)
- Confidence (Certain | Likely | Speculative — see the Grounding rule above)
- Category (mislogic | system_design | best_practice | duplication | security |
  blind_spot)
- Evidence — a SINGLE fenced block holding ONE verbatim snippet copied from the
  anchor file named in `File:` (the defect site of the interaction). Quote one
  file only; the snippet must be a verbatim substring of that file or the finding
  is discarded as ungrounded (see the Grounding rule above)
- Why it's wrong (the cross-task interaction that makes it a defect — name the
  partner file by path and line here, since the partner is referenced in prose,
  not quoted in `Evidence:`)
- Remediation
