# Research: Fix gutter/line misalignment in the raw-mode code editor and extract it from BodyEditor into a reusable CodeEditor component with a reusable JSON tokenizer lib


**Date**: 2026-07-16
**Topic**: Fix gutter/line misalignment in the raw-mode code editor and extract it from BodyEditor into a reusable CodeEditor component with a reusable JSON tokenizer lib
**Mode**: Enhancement
**Verdict**: Feasible with caveats

## Summary

Investigation of the shipped code contradicts two of the ticket's three premises. The gutter alignment bug is ALREADY fixed at BodyEditor.css:30, which pins the gutter row to an absolute calc(12.5px*1.65)=20.625px (not 1.65em) with a comment describing the exact mismatch the ticket cites; the buggy 1.65em form survives only in the stale design/styles.css reference (line 1208). The JSON tokenizer is ALREADY an exported reusable lib (jsonTokens.ts compose()), so 'extract tokenizer to a lib' is done, and its named 'second consumer' response-body does not exist as a component yet. The one genuine, unfinished deliverable is a behavior-preserving extraction of the inline raw editor (BodyEditor.tsx:296-327 plus its scroll/debounce/colored state) into a standalone reusable CodeEditor. The chief design risk, and the reason to do more than a verbatim copy-paste, is that the alignment fix is a duplicated 12.5px literal rather than one shared line-box unit, so a naive lift-and-shift re-introduces gutter drift for any future reuse consumer that changes font metrics.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Raw-mode hand-rolled code editor (inline in BodyEditor) is crooked: gutter line numbers drift out of alignment with code lines, accumulating downward |
| Affected area | src/renderer/src/components/organisms/BodyEditor.tsx + BodyEditor.css (raw editor + inline JSON tokenizer); new reusable CodeEditor component + reusable JSON-tokenizer lib; response-body as tokenizer second consumer |
| Repro / Current | Open BodyEditor raw mode with multi-line JSON. Gutter rows = 1.65em @ 11.5px = 18.975px each; <pre> rows = 12.5px * 1.65 = 20.625px each. 1.65px/row deficit compounds down the gutter, numbers sink relative to their code lines |
| Desired | Extract editor into standalone reusable CodeEditor; pin ONE absolute line-box height (20.625px) across textarea, pre, and gutter rows (never 1.65em on gutter); keep overlay mechanism (transparent textarea over aria-hidden highlighted pre, single scroll container); extract JSON tokenizer to reusable lib. Gutter numbers stay aligned to code rows at any line count |
| Scope | feature-wide |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| shipped gutter height (alignment fix ALREADY present) | src/renderer/src/components/organisms/BodyEditor.css:30 | Uses absolute height:calc(12.5px*1.65)=20.625px with explanatory comment (lines 26-29); the crooked-gutter bug the ticket describes does NOT exist in the shipped component | primary |
| inline raw editor markup (genuine extraction target) | src/renderer/src/components/organisms/BodyEditor.tsx:296 | gutter + pre-overlay + transparent textarea + scroll-sync all inline in BodyEditor raw panel (296-327) plus colored/debounce/scroll state above; this is the only unfinished ask | primary |
| JSON tokenizer already a reusable exported lib | src/renderer/src/lib/jsonTokens.ts:344 | canonical pattern - reusable: compose() is exported entry-point; JSON-only pass, malformed degrades to plain (AC-17), var-in-string overlay. 'Extract tokenizer to lib' is ALREADY done; no new lib needed | primary |
| sibling already-extracted tokenizer lib | src/renderer/src/lib/varTokens.ts:81 | canonical pattern - reusable: tokenizeVars() is a parallel shared lib; confirms the extract-to-lib idiom is established project convention | primary |
| design reference still carries the buggy gutter rule | design/styles.css:1208 | reference mockup has height:calc(1.65em) with gutter font 11.5px = 18.975px; the ticket's cited root cause is accurate for the REFERENCE only, not the app — supports the 'already fixed in code' primary framing | primary |
| no shared line-box token (reuse fragility) | src/renderer/src/components/organisms/BodyEditor.css:30 | runner-up support: tokens.css defines NO line-box unit; gutter row height duplicates the 12.5px*1.65 literal while .code-editor:23 sets font-size:12.5px separately. A reuse consumer overriding font metrics re-drifts the gutter unless extraction parametrizes one shared line-box unit | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Two of the three ticket asks are already satisfied in shipped code: the gutter alignment is fixed at BodyEditor.css:30 with an absolute line-box (calc(12.5px*1.65)=20.625px, not 1.65em), and the JSON tokenizer is already an exported reusable lib (jsonTokens.ts compose()). The ticket's cited crooked-gutter root cause is accurate only for the stale design/styles.css reference (line 1208, calc(1.65em)), not the app. The genuine remaining deliverable is a behavior-preserving extraction of the inline raw editor (BodyEditor.tsx:296-327 + its scroll/debounce state) into a standalone reusable CodeEditor. Chief design risk: the alignment fix is a duplicated literal rather than a shared line-box unit, so a copy-paste extraction re-introduces gutter drift for any reuse consumer that changes font metrics.

**Confidence**: Confirmed

## Runner-up framing

| Field | Value |
|---|---|
| Frame | The alignment fix at BodyEditor.css:30 is a hardcoded literal calc(12.5px * 1.65) that duplicates .code-editor's font-size/line-height; a REUSABLE CodeEditor whose consumer overrides font metrics re-drifts the gutter. The correct fix-layer for reuse is a single shared line-box unit (CSS var/token), not a duplicated literal — so an extraction that copies css:30 verbatim re-introduces the very fragility the ticket wants gone. |
| Falsifier | A shared line-box token/var (e.g. --code-line-h) already referenced by BOTH .code-editor pre rows and .gutter > div rows exists, making the height reuse-safe with no duplicated literal. |
| Confidence vs primary | comparable |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| User's suspected cause: shipped gutter uses height:calc(1.65em) resolving against gutter font 11.5px (18.975px) while pre rows are 20.625px, so misalignment compounds downward | Inspect the shipped BodyEditor.css .gutter>div rule; if height is an absolute calc(12.5px*1.65)=20.625px (not 1.65em), the mechanism is refuted for the running app | no |
| The genuine deliverable is a behavior-preserving extraction of the inline raw editor into a standalone reusable CodeEditor; the alignment fix (BodyEditor.css:30) and the tokenizer lib (jsonTokens.ts) are already shipped, so those two asks are already satisfied | If BodyEditor.css:30 used 1.65em on the gutter OR compose() in jsonTokens.ts were not an exported lib, real fix/extract work would remain | no |
| An extraction that copies BodyEditor.css:30's hardcoded 12.5px literal re-drifts the gutter for any reuse consumer that overrides code font-size/line-height; a reusable CodeEditor needs one shared line-box unit (CSS var) driving textarea+pre+gutter rows | A shared line-box CSS var/token referenced by BOTH .code-editor pre rows and .gutter>div rows already exists in tokens.css or BodyEditor.css | no |
| Pre-building tokenizer reusability for a 'response-body' second consumer is speculative: no response-body/JSON-response-viewer component exists in the codebase today | A response JSON viewer organism (e.g. ResponseBody/ResponseViewer) exists and renders JSON that could consume compose() | no |

## Approaches (HOW to change)

### Extract to CodeEditor with one shared line-box unit
- **Description**: Move the inline raw editor (gutter + aria-hidden pre overlay + transparent textarea + scroll-sync + colored/debounce state) into a standalone reusable CodeEditor component with co-located CSS; reuse jsonTokens.compose() unchanged; pin ONE shared line-box unit (a CSS var) driving textarea, pre, and gutter row heights so reuse is drift-safe. BodyEditor raw slot becomes a <CodeEditor> consumer.
- **Addresses hypothesis**: B, C
- **Does NOT cover**: A, D
- **Pros**: Honors the ticket intent (one absolute line-box across textarea/pre/gutter) as a single source, not a duplicated literal; Reuses the already-exported tokenizer lib (no reinvention); Behavior-preserving: overlay mechanism, JSON-only .tk-* vocab, var tie-break, malformed degrade, XSS-safe render all inherited from jsonTokens.compose(); Removes the runner-up reuse-fragility before a second consumer ever lands
- **Cons**: Touches the CSS line-box surface (introduces one var) beyond a pure move; Slightly larger diff than a verbatim lift-and-shift
- **Complexity**: Med

### Verbatim lift-and-shift extraction
- **Description**: Move the raw-editor markup, state, and CSS as-is into a new CodeEditor component including the current hardcoded calc(12.5px*1.65) gutter literal; BodyEditor consumes it. No token de-duplication.
- **Addresses hypothesis**: B
- **Does NOT cover**: A, C, D
- **Pros**: Minimal risk, purely mechanical; Fastest; preserves current pixel-exact fidelity byte-for-byte
- **Cons**: Re-ships the duplicated 12.5px literal, so the runner-up reuse-fragility persists for future consumers; Does not realize the ticket spirit of ONE pinned line-box height shared across textarea/pre/gutter
- **Complexity**: Low

**Recommended approach**: Extract to CodeEditor with one shared line-box unit — This approach uniquely satisfies the ticket's literal instruction to pin ONE absolute line-box measure across all three layers of the editor — the number strip, the highlight layer, and the input layer — where the current build fixes only the number strip via a duplicated hardcoded literal. It REUSES the exported canonical highlighter at src/renderer/src/lib/jsonTokens.ts:344 (compose()) rather than writing a new one, so the .tk-* palette, {{var}} precedence inside strings, malformed-input degrade-to-plain (AC-17), and XSS-safe escaped-children output are preserved by construction and unchanged_behavior holds. It also removes the reuse fragility (tokens.css defines no single line-box source at present) before another call site is added. Acknowledged uncertainty: the fidelity contract is proven from a live-renderer computed-style channel, so the refactor must be re-checked UNVERIFIED-not-PASS to confirm zero visual movement.

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Search before building (Key Rules #12) | Canonical reusable tokenizer already exists at src/renderer/src/lib/jsonTokens.ts:344 (compose()) and sibling varTokens.ts:81; the CodeEditor MUST import and reuse compose() rather than write a new tokenizer — reuse beats reinvention |
| SOLID, DRY, KISS (Key Rules #11) | Enables the recommended approach: the duplicated 12.5px line-box literal (BodyEditor.css:30 vs .code-editor:23 font-size) is a DRY violation that a shared line-box unit resolves; single-source line-box height is the KISS-correct fix for a reusable component |
| Minimal changes / never modify outside scope (Key Rules #3, Never #5) | Constrains scope to the raw code editor + its extraction; none/urlencoded modes, the mode strip, and the token color/grid/gutter contract values must stay unchanged vs T7a — do NOT build the non-existent response-body consumer speculatively |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Med | New CodeEditor.tsx + CodeEditor.css (~120 lines moved from BodyEditor); one shared line-box CSS var; BodyEditor raw slot shrinks to a <CodeEditor> consumer; move colored/debounce/scroll state with it. No tokenizer changes |
| Risk | Med | Overlay pixel-grid alignment (textarea over pre) is fidelity-sensitive; the shared line-box refactor could shift row height if the var value differs from 20.625px. Mount-all hidden-panel scroll preservation and the AC-23 debounce split must survive the move |
| Verify cost | Med | Re-run BodyEditor CT + add CodeEditor CT; assert gutter/pre/textarea row heights equal via live computed-style channel (UNVERIFIED not PASS if the channel is absent); confirm token color/grid/gutter contract UNCHANGED vs T7a |

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Raw-mode hand-rolled code editor (inline in BodyEditor) is crooked: gutter line numbers drift out of alignment with code lines, accumulating downward — Extract editor into standalone reusable CodeEditor; pin ONE absolute line-box height (20.625px) across textarea, pre, and gutter rows (never 1.65em on gutter); keep overlay mechanism (transparent textarea over aria-hidden highlighted pre, single scroll container); extract JSON tokenizer to reusable lib. Gutter numbers stay aligned to code rows at any line count"

Research reference: research/2026-07-16-fix-gutter-line-misalignment.md
Key facts:
- Mode: Enhancement
- Symptom: Raw-mode hand-rolled code editor (inline in BodyEditor) is crooked: gutter line numbers drift out of alignment with code lines, accumulating downward
- Desired: Extract editor into standalone reusable CodeEditor; pin ONE absolute line-box height (20.625px) across textarea, pre, and gutter rows (never 1.65em on gutter); keep overlay mechanism (transparent textarea over aria-hidden highlighted pre, single scroll container); extract JSON tokenizer to reusable lib. Gutter numbers stay aligned to code rows at any line count
- Recommended approach: Extract to CodeEditor with one shared line-box unit
- Hypothesis addressed: B, C
- Hypotheses NOT covered: A, D
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
