/**
 * CodeEditor.stories.tsx — Playwright CT fixture components for CodeEditor.
 *
 * Playwright experimental-ct-react requires mounted components to live in a
 * SEPARATE file from the test file. This file exports the fixtures consumed by
 * CodeEditor.ct.tsx.
 *
 * CodeEditor is a pure molecule — all context flows in via props; no tabsStore
 * interaction. Rebuilt (task 001) as an edit/preview conditional-mount toggle:
 * editing=true mounts ONLY the <textarea>; editing=false mounts ONLY the
 * highlighted <pre>. Tokenisation is synchronous (a {value,lang}-snapshot
 * useMemo gated to !editing) — there is NO debounce and NO setColored state, so
 * token spans (`.tk-*`) are present on the very first preview render.
 *
 * Styling context: tokens.css is NOT imported here — the global import in
 * `playwright/index.tsx` already makes the tokens available to every CT page.
 * Each fixture wraps its content in a `data-theme` container so per-theme token
 * overrides resolve deterministically; a fixed wrapper width keeps grid-track px
 * values deterministic.
 */

import { useState, type JSX } from 'react'
import { CodeEditor } from '@renderer/components/molecules/CodeEditor'
import type { RawLang } from '@renderer/lib/tabsStore'

// ─── Shared constants ─────────────────────────────────────────────────────────

/**
 * Multi-line JSON exercising every structural token kind plus a `{{var}}`
 * inside a string: tk-punc, tk-key, tk-num, tk-bool, tk-null, tk-str, tk-var.
 * Canonical single source for JSON_ALL_TOKENS — BodyEditor.stories.tsx imports
 * and re-exports this constant (no duplicate) for T7a contract parity; any
 * CT that needs it should import from BodyEditor.stories or here directly.
 */
export const JSON_ALL_TOKENS =
  '{\n  "key": 1,\n  "flag": true,\n  "nil": null,\n  "msg": "a {{x}} b"\n}'

/** Fixed width so the `.code-editor` grid tracks (36px 1fr) are deterministic. */
const WRAPPER_STYLE: React.CSSProperties = { width: '700px' }

/** Known vars set: `x` is valid so `{{x}}` renders as tk-var (not tk-var.missing). */
const VALID_VARS = new Set<string>(['x'])

/** Lang cycle order for the toggle fixture's lang-cycle button (recolor test). */
const LANG_CYCLE: RawLang[] = ['json', 'xml', 'html', 'text']

// ─── Additional body constants ────────────────────────────────────────────────

/**
 * Malformed (unterminated) JSON body — triggers the AC-4 degrade path in
 * compose(): JSON.parse throws → single plain token, no structural .tk-*.
 */
const MALFORMED_JSON_BODY = '{ "key": '

/**
 * Body with one unresolved var (`{{missing}}` absent from validVars={'x'}) so
 * the tk-var.missing CSS treatment is exercised. The surrounding text is plain.
 */
const MISSING_VAR_BODY = 'hello {{missing}} world'

/**
 * 100 lines × 80 chars each — overflows both axes in a 400×150px container.
 * Hoisted to module scope so it is computed once, not on each render.
 */
const SCROLL_BODY = Array.from({ length: 100 }, (_, i) => `line ${i}: ${'x'.repeat(80)}`).join('\n')

// ─── Fixtures ─────────────────────────────────────────────────────────────────

/**
 * Preview-state fixture (editing=false) — ONLY the highlighted <pre> mounts.
 *
 * Doubles as the light-theme fidelity fixture: `data-theme="light"` so tk-*
 * token vars resolve to light-theme literals, and VALID_VARS includes 'x' so
 * `{{x}}` in JSON_ALL_TOKENS renders as `.tk-var` (not `.tk-var.missing`).
 * Because tokenisation is synchronous, `.tk-*` spans are present on first render.
 */
export function CodeEditorPreviewFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={JSON_ALL_TOKENS}
        lang="json"
        onChange={() => {}}
        validVars={VALID_VARS}
        editing={false}
        onEditingChange={() => {}}
      />
      <span data-testid="ce-preview-ready" />
    </div>
  )
}

/** Back-compat alias — some fidelity tests read the light-theme preview mount. */
export const CodeEditorLightFixture = CodeEditorPreviewFixture

/**
 * Edit-state fixture (editing=true) — ONLY the plain <textarea> mounts.
 *
 * Used for the edit-state line-box read (AC-9) and the textarea-attribute
 * contract (AC-15: spellcheck=false, resize:none, white-space:pre).
 */
export function CodeEditorEditFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={JSON_ALL_TOKENS}
        lang="json"
        onChange={() => {}}
        validVars={VALID_VARS}
        editing
        onEditingChange={() => {}}
      />
      <span data-testid="ce-edit-ready" />
    </div>
  )
}

/**
 * Dark-theme preview fixture — mirrors CodeEditorPreviewFixture with
 * `data-theme="dark"` so the CT can assert dark-theme literal hex values for
 * tk-key, tk-str, tk-num, tk-bool.
 */
export function CodeEditorDarkFixture(): JSX.Element {
  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <CodeEditor
        value={JSON_ALL_TOKENS}
        lang="json"
        onChange={() => {}}
        validVars={VALID_VARS}
        editing={false}
        onEditingChange={() => {}}
      />
      <span data-testid="ce-dark-ready" />
    </div>
  )
}

/**
 * Controlled toggle harness — wires `onEditingChange` back to local state so the
 * component's REAL edit-entry paths flip the mounted layer:
 *   - clicking the <pre> (caret-at-click, AC-12/13) enters edit,
 *   - focusing the <pre> + Enter/Space (keyboard entry, AC-18) enters edit,
 *   - the layer swap is observable (AC-10/11 conditional mount, AC-14 recolor).
 *
 * `startEditing` seeds the initial state (default preview). The lang-cycle
 * button advances `lang` while in preview so the recolor-in-preview path
 * (AC-14) is exercised without a keystroke.
 *
 * data-testids:
 *   ce-toggle-ready  — mounted, ready for assertions
 *   ce-cycle-lang    — advance lang (recolor in preview)
 */
export function CodeEditorToggleFixture({
  startEditing = false
}: {
  startEditing?: boolean
}): JSX.Element {
  const [editing, setEditing] = useState(startEditing)
  const [langIdx, setLangIdx] = useState(0)
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={JSON_ALL_TOKENS}
        lang={LANG_CYCLE[langIdx]}
        onChange={() => {}}
        validVars={VALID_VARS}
        editing={editing}
        onEditingChange={setEditing}
      />
      <button
        type="button"
        data-testid="ce-cycle-lang"
        onClick={() => setLangIdx((i) => (i + 1) % LANG_CYCLE.length)}
      >
        Cycle lang
      </button>
      <span data-testid="ce-toggle-ready" />
    </div>
  )
}

/**
 * Empty-body toggle fixture — `value=''` in a height-bounded (700×240px) wrapper.
 * The preview `<pre>` collapses to ~one line at the top, so most of the `.code-editor`
 * container is the dead zone the whole-area click-to-edit fix targets. `editing` is
 * wired to `onEditingChange` so a click on the container's dead space enters edit.
 */
export function CodeEditorEmptyToggleFixture(): JSX.Element {
  const [editing, setEditing] = useState(false)
  return (
    <div data-theme="light" style={{ width: '700px', height: '240px' }}>
      <CodeEditor
        value=""
        lang="json"
        onChange={() => {}}
        validVars={VALID_VARS}
        editing={editing}
        onEditingChange={setEditing}
      />
      <span data-testid="ce-empty-ready" />
    </div>
  )
}

/**
 * Preview scroll fixture — editing=false so the <pre> is the single scrollable
 * layer. A 100-line × 80-char body far exceeds the 150px height and the 400px
 * width, so both axes genuinely overflow. A resetKey driver lets the scroll-reset
 * test trigger `useEffect([resetKey])` and assert the pre's scroll returns to 0.
 *
 * data-testids:
 *   ce-scroll-ready          — mounted, ready for assertions
 *   ce-bump-resetkey-scroll  — click to increment resetKey
 */
export function CodeEditorScrollFixture(): JSX.Element {
  const [rk, setRk] = useState(0)
  return (
    <div data-theme="light" style={{ width: '400px', height: '150px' }}>
      <CodeEditor
        value={SCROLL_BODY}
        lang="text"
        onChange={() => {}}
        validVars={new Set<string>()}
        editing={false}
        onEditingChange={() => {}}
        resetKey={rk}
      />
      <button
        type="button"
        data-testid="ce-bump-resetkey-scroll"
        onClick={() => setRk((k) => k + 1)}
      >
        Bump resetKey scroll
      </button>
      <span data-testid="ce-scroll-ready" />
    </div>
  )
}

/**
 * AC-13 font-override fixture (preview).
 *
 * Wraps CodeEditor in a container that declares `font-size: 20px` and
 * `line-height: 3` — metrics deliberately different from the component's own
 * 12.5px / 1.65 values. `--code-line-h` is re-declared by the `.code-editor`
 * class as a fixed `calc(12.5px * 1.65)`, so the gutter rows and the pre must
 * remain at 20.625px regardless of what the ancestor container declares.
 * editing=false → only the <pre> mounts (the edit-state row height is verified
 * separately by the AC-9 edit read on CodeEditorEditFixture).
 */
export function CodeEditorFontOverrideFixture(): JSX.Element {
  return (
    <div data-theme="light" style={{ ...WRAPPER_STYLE, fontSize: '20px', lineHeight: '3' }}>
      <CodeEditor
        value={JSON_ALL_TOKENS}
        lang="json"
        onChange={() => {}}
        validVars={VALID_VARS}
        editing={false}
        onEditingChange={() => {}}
      />
      <span data-testid="ce-font-override-ready" />
    </div>
  )
}

/**
 * AC-4 malformed-JSON degrade fixture (preview).
 *
 * Passes an unterminated JSON body (`MALFORMED_JSON_BODY`) with `lang="json"`.
 * compose() calls JSON.parse, receives a SyntaxError, and returns a single
 * `{ kind: 'plain', text }` token synchronously (the AC-4 degrade path). No
 * structural tk-* spans ever appear. MEMORY `jsontokens-jsonparse-is-ac17-detector`:
 * the JSON.parse pre-validation IS the degrade detector — it must not be removed.
 */
export function CodeEditorMalformedFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={MALFORMED_JSON_BODY}
        lang="json"
        onChange={() => {}}
        validVars={new Set<string>()}
        editing={false}
        onEditingChange={() => {}}
      />
      <span data-testid="ce-malformed-ready" />
    </div>
  )
}

/**
 * .tk-var.missing fixture (preview).
 *
 * Body contains `{{missing}}` with `validVars={new Set(['x'])}` — `missing` is
 * absent from the known-vars set, so `isMissingVar(known=false, validVars)`
 * returns true and CodeEditor applies the `'tk-var missing'` className. The CSS
 * rule `.tk-var.missing { color: var(--m-delete); text-decoration: line-through
 * dotted; }` renders the unresolved var with strikethrough. `lang="text"` keeps
 * the fixture minimal — the var pass runs on all langs.
 */
export function CodeEditorMissingVarFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={MISSING_VAR_BODY}
        lang="text"
        onChange={() => {}}
        validVars={new Set<string>(['x'])}
        editing={false}
        onEditingChange={() => {}}
      />
      <span data-testid="ce-missing-var-ready" />
    </div>
  )
}
