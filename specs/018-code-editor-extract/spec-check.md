# Spec-Check: 018-code-editor-extract

**Feature**: 018-code-editor-extract
**Date**: 2026-07-16

> **Scope:** /spec-check is a consistency prover, not a mind-reader. It checks whether your acceptance criteria contradict *each other* -- not whether they are what you *meant*. A single coherent-but-wrong AC will pass.

## Recommendation

**CONSISTENT** -- No contradiction found over the formalized subset.
**Formalization stability:** contradiction core reproduced in 0/2 formalization passes.

## How your ACs were read as logic

This is the translation to verify -- check that each reading below actually says what you meant. The proof in the next section (when present) is only as good as this reading.

- `bodyeditor_declares_overlay` (Bool) -- the BodyEditor component still declares the inline three-layer code-area overlay markup
- `codeeditor_module_provided` (Bool) -- the renderer provides a reusable CodeEditor component module
- `codeeditor_tier` (Enum) -- the component-layer tier where the CodeEditor module resides domain [atoms, molecules, organisms]
- `stylesheet_colocated` (Bool) -- a CodeEditor stylesheet exists co-located with the component
- `json_valid` (Bool) -- the raw text being rendered is valid JSON
- `render_single_plain_segment` (Bool) -- the raw text is rendered as a single plain (unhighlighted) segment
- `render_throws` (Bool) -- rendering the raw text throws an error
- `var_in_json_string` (Bool) -- a {{var}} placeholder appears inside a JSON string or key
- `variable_overlay_wins` (Bool) -- the variable overlay wins the highlight tie-break at that position
- `panel_hidden` (Bool) -- an inactive body-mode panel is currently hidden
- `scroll_preserved` (Bool) -- the hidden panel's DOM-local scroll state is preserved
- `caret_preserved` (Bool) -- the hidden panel's caret state is preserved
- `tokens_escaped_children` (Bool) -- highlighted token text is inserted as escaped React children
- `uses_innerhtml` (Bool) -- highlighted token text is inserted via innerHTML
- `tab_switched` (Bool) -- the active request tab has just switched
- `scroll_offset_reset` (Bool) -- the code-area scroll offset is reset
- `colored_snapshot_invalidated` (Bool) -- the colored highlight snapshot is invalidated
- `testids_preserved` (Bool) -- the body-code-editor, body-gutter, and body-pre data-testids are preserved on the extracted editor
- `user_edits_json` (Bool) -- a user edits raw JSON inside the CodeEditor
- `syntax_highlighting_produced` (Bool) -- syntax highlighting is produced for the edited JSON
- `jsontokens_lib_unchanged` (Bool) -- the existing jsonTokens compose lib is reused unchanged
- `shared_linebox_unit_defined` (Bool) -- the CodeEditor defines one shared line-box unit driving textarea, pre, and gutter row heights
- `font_metrics_overridden` (Bool) -- a consumer overrides the code font metrics
- `rows_equal_height` (Bool) -- the gutter, pre, and textarea rows compute to equal height
- `mounted_with_props` (Bool) -- a consumer mounts the CodeEditor with value, lang, onChange, and validVars props
- `self_contained_editor` (Bool) -- the CodeEditor renders self-contained, owning its own compose debounce and colored state
- `computed_style_channel_available` (Bool) -- the live-renderer computed-style channel is available
- `fidelity_status` (Enum) -- the status assigned to a design-fidelity assertion domain [PASS, UNVERIFIED, FAIL]
- `fidelity_contract_unchanged` (Bool) -- the tk-* token colors, code-editor grid, and gutter geometry remain unchanged from the T7a fidelity contract
- `row_height_unit` (Enum) -- the CSS unit used for the gutter/pre/textarea row (line-box) height domain [absolute, em]
- `docs_describe_roles` (Bool) -- the documentation describes CodeEditor as a reusable molecule and BodyEditor as its consumer
- `typecheck_pass` (Bool) -- the renderer passes type-check after the extraction
- `lint_pass` (Bool) -- the renderer passes lint after the extraction

- **AC-1** "The BodyEditor component shall no longer declare the inline three-layer code-area overlay markup." -> `NOT bodyeditor_declares_overlay`
- **AC-9** "The renderer shall provide a reusable CodeEditor component module in the molecules tier." -> `codeeditor_module_provided AND codeeditor_tier = molecules`
- **AC-10** "The renderer shall provide a CodeEditor stylesheet co-located with the component." -> `stylesheet_colocated`
- **AC-2** "IF the raw text is not valid JSON, THEN the system shall render it as a single plain segment without throwing." -> `IF NOT json_valid THEN render_single_plain_segment AND NOT render_throws`
- **AC-3** "WHEN a {{var}} placeholder appears inside a JSON string or key, the system shall let the variable overlay win the tie-break." -> `IF var_in_json_string THEN variable_overlay_wins`
- **AC-4** "WHILE an inactive body-mode panel is hidden, the system shall preserve that panel's DOM-local scroll and caret state." -> `IF panel_hidden THEN scroll_preserved AND caret_preserved`
- **AC-5** "The system shall insert all highlighted token text as escaped children and never via innerHTML." -> `tokens_escaped_children AND NOT uses_innerhtml`
- **AC-6** "WHEN the active request tab switches, the system shall reset the code-area scroll offset and invalidate the colored snapshot." -> `IF tab_switched THEN scroll_offset_reset AND colored_snapshot_invalidated`
- **AC-8** "The system shall preserve the body-code-editor, body-gutter, and body-pre data-testids on the extracted editor." -> `testids_preserved`
- **AC-11** "WHEN a user edits raw JSON in the CodeEditor, the system shall produce syntax highlighting by reusing the existing jsonTokens compose lib unchanged." -> `IF user_edits_json THEN syntax_highlighting_produced AND jsontokens_lib_unchanged`
- **AC-12** "The CodeEditor shall define one shared line-box unit that sets the row height of the textarea, the highlighted pre lines, and the gutter divs." -> `shared_linebox_unit_defined`
- **AC-13** "IF a consumer overrides the code font metrics, THEN the gutter, pre, and textarea rows shall remain equal in height." -> `IF font_metrics_overridden THEN rows_equal_height`
- **AC-14** "WHEN a consumer mounts the CodeEditor with value, lang, onChange, and validVars props, the system shall render a self-contained editor that owns its own compose debounce and colored state." -> `IF mounted_with_props THEN self_contained_editor`
- **AC-15** "The CodeEditor shall reside in the molecules tier so an organism can consume it without a sibling-organism import." -> `codeeditor_tier = molecules`
- **AC-16** "WHILE the live-renderer computed-style channel is unavailable, the system shall mark fidelity assertions UNVERIFIED rather than PASS." -> `IF NOT computed_style_channel_available THEN fidelity_status = UNVERIFIED AND fidelity_status != PASS`
- **AC-17** "The system shall keep the tk-* token colors, the code-editor grid, and the gutter geometry unchanged from the T7a fidelity contract." -> `fidelity_contract_unchanged`
- **AC-21** "The gutter, pre, and textarea rows shall each compute to the same absolute line-box height derived from the code font-size times its line-height." -> `rows_equal_height AND row_height_unit = absolute`
- **AC-18** "The documentation shall describe CodeEditor as a reusable molecule and BodyEditor as its consumer." -> `docs_describe_roles`
- **AC-19** "The renderer shall pass type-check and lint after the extraction." -> `typecheck_pass AND lint_pass`
- **AC-20** "The CodeEditor stylesheet shall not use an em-based row height on the gutter." -> `row_height_unit != em`

> Note: conditional (IF/WHEN) acceptance criteria are checked under the assumption their trigger can fire -- the solver does not independently verify reachability.

## Coverage

**Checked 20 of 21 acceptance criteria** (1 unformalizable).

- AC-1: formalized
- AC-9: formalized
- AC-10: formalized
- AC-2: formalized
- AC-3: formalized
- AC-4: formalized
- AC-5: formalized
- AC-6: formalized
- AC-7: skipped_prose (behave identically to the pre-extraction BodyEditor is a vague qualitative behavioral-equivalence claim with no crisp logical predicate to test)
- AC-8: formalized
- AC-11: formalized
- AC-12: formalized
- AC-13: formalized
- AC-14: formalized
- AC-15: formalized
- AC-16: formalized
- AC-17: formalized
- AC-21: formalized
- AC-18: formalized
- AC-19: formalized
- AC-20: formalized
