=== DESIGN-LEVEL ATTACK CHECKLIST ===

Hunt the proposed design for these attack vectors. These are EXAMPLES of failure
classes to look for, NOT a list of defects you should find. If the design has
none of them, report none — a sound design honestly yields few or no findings.
Every finding MUST carry a verbatim Evidence quote (the `## Finding N` output
contract below the checklist states the exact field shape — match it; do not
restate it here). Each vector names what to QUOTE as the grounded Evidence and
which `Category` its findings carry.

The available Category values are: `mislogic | system_design | best_practice |
duplication | security | blind_spot`. Use only these. A **constitution violation**
has no category of its own — tag it `blind_spot` and put a `[CONSTITUTION-VIOLATION]`
marker in the `Pattern` line and `Why it's wrong` (matching `/audit` and `/review`).


Architectural failure modes  (Category: system_design)
- Layering / SOLID violations the plan introduces — a component the plan adds that
  takes on multiple responsibilities, a god-component the design grows, a
  dependency direction the architecture forbids that the plan's structure crosses.
  Quote the plan section (the File Impact row, the component description, the data
  flow) that declares the offending structure; name the layer / boundary it
  breaks.
- The holistic "should this approach exist at all" — a design that solves the
  problem at the wrong altitude (a new subsystem where a config flag would do; a
  bespoke mechanism where an existing one fits). Quote the plan's own statement of
  the approach and argue, from it, that the approach is disproportionate to the
  spec's WHAT.


Plan-vs-reality mismatches  (Category: duplication for a reinvention; system_design
or blind_spot for a wrong assumption — the HIGHEST-VALUE catch)
- Duplicate-by-new-file / reinvention — the plan declares it will CREATE a helper,
  type, validation, component, or utility that the codebase ALREADY has. This is
  the most expensive design error to miss because it is invisible in the plan's
  markdown — you find it via the Ring-2 query (`search_graph` / `search_code` for
  the existing thing the plan reinvents, wherever it lives). Quote the plan's File
  Impact / "create X" line in `Evidence:`, name the existing implementation by
  path (found via Ring 2) in `Why it's wrong:` — a "search-before-building"
  violation. (Category: `duplication`.)
- Wrong assumptions about existing code — the plan states how an existing function
  / module / contract behaves, and the actual code (read in Ring 0 / Ring 1, or
  located via Ring 2) behaves differently. Quote the plan's assumption in
  `Evidence:`; name the real source file + line whose behavior contradicts it in
  `Why it's wrong:`. (Category: `system_design` for a structural mismatch,
  `blind_spot` for an unhandled real-code edge the plan assumed away.)


Security attack surface  (Category: security)
- Auth / session / token handling the design routes incorrectly; PII the plan
  exposes; access control the design omits; an unauthenticated path the plan opens
  to a protected resource; untrusted input the design routes into a dangerous sink
  without validation. Quote the plan / spec text that declares the offending data
  flow or boundary; name the protected resource or the trust boundary it crosses.


Scalability / performance ceilings  (Category: system_design for an
architecture/data-flow cost; best_practice for an idiom smell)
- An operation the design runs over a large collection; an N+1 the plan's data
  flow walks into; a missing pagination / caching the design needs at the volume
  the spec implies; a hot path the plan makes slow. Quote the plan's description of
  the operation or data flow; argue the ceiling from the spec's stated scale. If
  the cost is an emergent property of how the design wires its layers/data flow →
  `system_design`; if it is a single local idiom that should be batched / memoized
  / derived → `best_practice`. State which and why.


Ignored edge cases  (Category: blind_spot, or mislogic for a control-flow
contradiction)
- States, failure paths, and inputs the design does not handle — an error path the
  plan's happy-path flow omits, a state transition the design leaves undefined, an
  input shape the plan assumes away. Quote the plan section that defines the flow;
  name the unhandled state / input. Respect the spec's Out-of-Scope (§6): a
  deliberately-excluded case is NOT an ignored edge case.


Stale external claims  (Category: best_practice)
- The plan names a deprecated / removed library API, a wrong version, or an
  anti-pattern dependency choice. This fires ONLY when the plan names an external
  dependency — VERIFY the claim against current docs (context7 primary;
  WebFetch/WebSearch only for CVEs/advisories). Evidence is the dual-grounding web
  citation: a re-fetchable `library@version` (via context7) or URL PLUS the quoted
  doc passage that contradicts the plan's claim — there is no `source_root` file
  for a web attack, so the citation stands in for the verbatim source quote.
  VERIFY the plan's claim; do NOT hunt alternatives — a "better option exists" hit
  is an upstream discovery signal, flagged, not adopted.


Constitution violations  (tag [CONSTITUTION-VIOLATION]; Category: blind_spot)
- A design decision that breaks a non-negotiable rule the project's
  `constitution.md` declares. Quote BOTH the plan/spec decision AND the
  constitution rule it breaks (the constitution is in your read-context). A
  constitution violation is ALWAYS Critical, never downgraded regardless of
  confidence; mark it `[CONSTITUTION-VIOLATION]` in the `Pattern` and `Why it's
  wrong`.


Grounding rule (mandatory — same single-anchor discipline as /audit and /review)
Every finding MUST include a verbatim Evidence quote copy-pasted from exactly ONE
artifact — the one named in the finding's `File:` field. `File:` is polymorphic:
it holds `plan.md`, `spec.md`, the constitution path, OR a real source file
`path/to/src.ext` from the Ring-0/Ring-1 blast radius — all of them resolve under
`source_root`, so the same grounding check validates them all. The `Evidence:`
snippet MUST be a verbatim substring of that single anchor file; a snippet that
mixes two files, or copies from a file other than the one in `File:`, is discarded
as ungrounded. When a finding spans two artifacts (the plan declares X, the
existing code does Y), quote ONE — the most damning anchor — in `Evidence:` and
name the partner by path and line in `Why it's wrong:` (prose, not quoted). The
single web-attack exception: an external-claim finding has no `source_root` file,
so its Evidence is the re-fetchable web citation + quoted doc passage (see Stale
external claims above).

A finding that is a design PREFERENCE rather than a defect provable from the
quoted anchor MUST be marked Confidence `Likely` or `Speculative` — never
`Certain`. `Certain` is reserved for a defect demonstrated mechanically from the
quoted evidence (a duplicate that demonstrably already exists, a deprecated API
the docs quote-as-removed, a constitution rule the plan quote-as-breaks). The
verbatim quote stops fabrication; the Confidence tier keeps subjective design
judgments honest. If you cannot quote text proving the design is broken, you
cannot report the finding.
