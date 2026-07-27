# Spec-Check: 019-code-editor-toggle

**Feature**: 019-code-editor-toggle
**Date**: 2026-07-19

> **Scope:** /spec-check is a consistency prover, not a mind-reader. It checks whether your acceptance criteria contradict *each other* -- not whether they are what you *meant*. A single coherent-but-wrong AC will pass.

## Recommendation

**CONSISTENT** -- No contradiction found over the formalized subset.
**Formalization stability:** contradiction core reproduced in 0/2 formalization passes.

## How your ACs were read as logic

This is the translation to verify -- check that each reading below actually says what you meant. The proof in the next section (when present) is only as good as this reading.

- `has_scroll_sync_handler` (Bool) -- the CodeEditor declares a handler that synchronises scroll from the textarea to the pre element
- `has_debounced_snapshot_state` (Bool) -- the CodeEditor declares a debounced colored-snapshot state for the editing surface
- `toggle_has_testid` (Bool) -- the BodyEditor edit/preview toggle control carries a stable data-testid
- `raw_is_valid_json` (Bool) -- the raw text in the code area is valid JSON
- `renders_single_plain_segment` (Bool) -- the CodeEditor renders the raw text as a single plain (unhighlighted) segment
- `throws_on_render` (Bool) -- the CodeEditor throws an exception while rendering the raw text
- `reuses_jsontokens_unchanged` (Bool) -- the CodeEditor reuses the existing jsonTokens compose library unchanged for syntax highlighting
- `tab_switched` (Bool) -- the active request tab has just switched
- `scroll_offset` (Int) -- the vertical scroll offset of the code area in pixels
- `editing` (Bool) -- the CodeEditor is in edit mode (true) versus preview mode (false)
- `uses_innerhtml` (Bool) -- the CodeEditor inserts highlighted token text via innerHTML
- `tokens_escaped` (Bool) -- highlighted token text is inserted as escaped children
- `shared_line_box_height` (Bool) -- the gutter, preview, and edit textarea rows share one line-box height in both states
- `layer_mounted` (Enum) -- which rendering layer the CodeEditor currently mounts domain [preview, edit, both, none]
- `visible_testid` (Enum) -- which layer's data-testid the CodeEditor currently exposes domain [body-pre, textarea, both, none]
- `preview_clicked` (Bool) -- the user has clicked on the preview surface
- `caret_at_clicked_char` (Bool) -- the caret is placed at the clicked character position
- `click_past_text` (Bool) -- a preview click landed past the end of a line or below the text
- `caret_clamped` (Bool) -- the caret is clamped to the nearest character
- `transition_to_preview` (Bool) -- the CodeEditor is transitioning from edit to preview
- `tokenizer_runs_per_transition` (Int) -- number of times the tokenizer runs for a single switch-to-preview transition
- `spellcheck_disabled` (Bool) -- the edit textarea has spellcheck disabled
- `resize_disabled` (Bool) -- the edit textarea has resize disabled
- `tab_key_native` (Bool) -- the Tab key retains native behavior in the edit textarea
- `white_space_pre` (Bool) -- the edit textarea wraps with white-space pre (horizontal scroll, no soft-wrap)
- `soft_wrap` (Bool) -- the edit textarea soft-wraps long lines
- `exit_edit_trigger` (Bool) -- an exit-edit trigger fired (textarea blur or toggle control activation)
- `first_mount` (Bool) -- a request raw code area is mounting for the first time
- `keyboard_operation` (Bool) -- the user is operating the CodeEditor by keyboard
- `preview_focusable` (Bool) -- the preview surface is focusable
- `layer_visible` (Bool) -- either the preview or edit layer is currently visible
- `gutter_single_scroll_container` (Bool) -- the gutter tracks the visible layer within one shared scroll container
- `gutter_height_em_based` (Bool) -- the CodeEditor stylesheet uses an em-based gutter row height
- `uses_inline_toggle_styles` (Bool) -- the CodeEditor component uses inline element styles for the toggle states

- **AC-1** "The CodeEditor shall not declare a textarea-to-pre scroll-synchronisation handler." -> `NOT has_scroll_sync_handler`
- **AC-2** "The CodeEditor shall not declare a debounced colored-snapshot state for the editing surface." -> `NOT has_debounced_snapshot_state`
- **AC-3** "The BodyEditor shall provide an edit/preview toggle control carrying a stable data-testid." -> `toggle_has_testid`
- **AC-4** "IF the raw text is not valid JSON, THEN the CodeEditor shall render it as a single plain segment without throwing." -> `IF NOT raw_is_valid_json THEN renders_single_plain_segment AND NOT throws_on_render`
- **AC-5** "The CodeEditor shall reuse the existing jsonTokens compose library unchanged for syntax highlighting." -> `reuses_jsontokens_unchanged`
- **AC-6** "WHEN the active request tab switches, the CodeEditor shall reset the code-area scroll offset and return to preview." -> `IF tab_switched THEN scroll_offset = 0 AND NOT editing`
- **AC-8** "The CodeEditor shall insert all highlighted token text as escaped children and never via innerHTML." -> `NOT uses_innerhtml AND tokens_escaped`
- **AC-9** "The CodeEditor shall keep the gutter, the preview, and the edit textarea rows on one shared line-box height in both states." -> `shared_line_box_height`
- **AC-10** "WHILE editing is false the CodeEditor shall render only the preview pre, and while editing is true it shall render only the plain textarea, never mounting both together." -> `IF editing THEN layer_mounted = edit`
- **AC-11** "The CodeEditor shall expose only the currently visible layer data-testid, namely body-pre in preview and the textarea in edit." -> `IF NOT editing THEN visible_testid = body-pre`
- **AC-12** "WHEN the user clicks the preview, the CodeEditor shall enter edit mode and place the caret at the clicked character." -> `IF preview_clicked THEN editing AND caret_at_clicked_char`
- **AC-13** "IF a preview click lands past the end of a line or below the text, THEN the CodeEditor shall clamp the caret to the nearest character." -> `IF click_past_text THEN caret_clamped`
- **AC-14** "WHEN the CodeEditor switches to preview, the system shall run the tokenizer exactly once for that transition rather than per keystroke." -> `IF transition_to_preview THEN tokenizer_runs_per_transition = 1`
- **AC-15** "WHILE editing is true, the textarea shall disable spellcheck, disable resize, keep the Tab key native, and wrap with white-space pre giving horizontal scroll and no soft-wrap." -> `IF editing THEN spellcheck_disabled AND resize_disabled AND tab_key_native AND white_space_pre AND NOT soft_wrap`
- **AC-16** "WHEN the textarea loses focus or the toggle control is activated, the CodeEditor shall leave edit mode and return to preview." -> `IF exit_edit_trigger THEN NOT editing`
- **AC-17** "WHEN a request raw code area first mounts, the CodeEditor shall start in preview." -> `IF first_mount THEN NOT editing`
- **AC-18** "WHERE the user operates by keyboard, the preview shall be focusable and Enter or Space shall enter edit mode." -> `IF keyboard_operation THEN preview_focusable`
- **AC-19** "WHILE either layer is visible, the gutter shall track that layer within one scroll container." -> `IF layer_visible THEN gutter_single_scroll_container`
- **AC-22** "The CodeEditor stylesheet shall not use an em-based gutter row height." -> `NOT gutter_height_em_based`
- **AC-23** "The CodeEditor component shall not use inline element styles for the toggle states." -> `NOT uses_inline_toggle_styles`

> Note: conditional (IF/WHEN) acceptance criteria are checked under the assumption their trigger can fire -- the solver does not independently verify reachability.

## Coverage

**Checked 20 of 23 acceptance criteria** (3 unformalizable).

- AC-1: formalized
- AC-2: formalized
- AC-3: formalized
- AC-4: formalized
- AC-5: formalized
- AC-6: formalized
- AC-7: skipped_prose (behave identically to pre-change behavior is a subjective behavioral-equivalence claim; nothing to contradict.)
- AC-8: formalized
- AC-9: formalized
- AC-10: formalized
- AC-11: formalized
- AC-12: formalized
- AC-13: formalized
- AC-14: formalized
- AC-15: formalized
- AC-16: formalized
- AC-17: formalized
- AC-18: formalized
- AC-19: formalized
- AC-20: skipped_prose (documentation-content requirement; non-logical.)
- AC-21: skipped_prose (build/tooling gate; not a spec-logic predicate.)
- AC-22: formalized
- AC-23: formalized
