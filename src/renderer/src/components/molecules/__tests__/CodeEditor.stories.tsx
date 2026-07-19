/**
 * CodeEditor.stories.tsx — Playwright CT fixture components for CodeEditor.
 *
 * Playwright experimental-ct-react requires mounted components to live in a
 * SEPARATE file from the test file. This file exports the fixtures consumed by
 * CodeEditor.ct.tsx.
 *
 * CodeEditor is a pure molecule — all context flows in via props; no tabsStore
 * interaction. Fixtures are simple React wrappers: no store seeding, no async
 * useEffect. The `ce-ready` span is present on the first render (synchronous).
 *
 * Styling context: tokens.css is NOT imported here — the global import in
 * `playwright/index.tsx` already makes the tokens available to every CT page.
 * Each fixture wraps its content in a `data-theme` container so per-theme token
 * overrides resolve deterministically; a fixed wrapper width keeps grid-track px
 * values deterministic.
 */

import { useState, type JSX } from 'react'
import { CodeEditor } from '@renderer/components/molecules/CodeEditor'

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

// ─── Additional body constants ────────────────────────────────────────────────

/**
 * Malformed (unterminated) JSON body — triggers the AC-17 / AC-2 degrade path
 * in compose(): JSON.parse throws → single plain token, no structural .tk-*.
 */
const MALFORMED_JSON_BODY = '{ "key": '

/**
 * Body with one unresolved var (`{{missing}}` absent from validVars={'x'}) so
 * the tk-var.missing CSS treatment is exercised. The surrounding text is plain.
 */
const MISSING_VAR_BODY = 'hello {{missing}} world'

/**
 * 100 lines × 80 chars each — overflows both axes in a 400×150px container.
 * Hoisted to module scope so it is computed once, not on each render (Finding 6).
 */
const SCROLL_BODY = Array.from({ length: 100 }, (_, i) => `line ${i}: ${'x'.repeat(80)}`).join('\n')

// ─── Fixtures ─────────────────────────────────────────────────────────────────

/**
 * Light-theme fidelity fixture.
 *
 * Wraps CodeEditor in `data-theme="light"` (mirrors BodyEditor.stories' wrapper)
 * so tk-* token vars resolve to light-theme literals. VALID_VARS includes 'x' so
 * `{{x}}` in JSON_ALL_TOKENS renders as `.tk-var` (not `.tk-var.missing`).
 */
export function CodeEditorLightFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor value={JSON_ALL_TOKENS} lang="json" onChange={() => {}} validVars={VALID_VARS} />
      <span data-testid="ce-ready" />
    </div>
  )
}

/**
 * Dark-theme fidelity fixture.
 *
 * Mirrors CodeEditorLightFixture with `data-theme="dark"` so the CT can assert
 * dark-theme literal hex values for tk-key, tk-str, tk-num, tk-bool.
 */
export function CodeEditorDarkFixture(): JSX.Element {
  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <CodeEditor value={JSON_ALL_TOKENS} lang="json" onChange={() => {}} validVars={VALID_VARS} />
      <span data-testid="ce-dark-ready" />
    </div>
  )
}

/**
 * resetKey-driver harness.
 *
 * Holds `rk` (a number) via useState(0). Clicking `ce-bump-resetkey` increments
 * it, passing the new value to CodeEditor's `resetKey` prop. `value` is a
 * controlled constant (JSON_ALL_TOKENS) so text+lang are IDENTICAL across the
 * resetKey change — the test isolates the resetKey effect on `setColored(null)`,
 * debounce re-arm, and scroll-reset.
 *
 * data-testids:
 *   ce-ready          — component mounted, ready for assertions
 *   ce-bump-resetkey  — click to increment resetKey
 */
export function CodeEditorResetKeyFixture(): JSX.Element {
  const [rk, setRk] = useState(0)
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={JSON_ALL_TOKENS}
        lang="json"
        onChange={() => {}}
        validVars={VALID_VARS}
        resetKey={rk}
      />
      <button type="button" data-testid="ce-bump-resetkey" onClick={() => setRk((k) => k + 1)}>
        Bump resetKey
      </button>
      <span data-testid="ce-ready" />
    </div>
  )
}

/**
 * Scroll fixture.
 *
 * CodeEditor in a 400 × 150 px bounded container with a 100-line × 80-char body
 * so the textarea's content (100 × 20.625 px ≈ 2062 px) far exceeds the 150 px
 * visible height — textarea is scrollable when constrained. Also includes a
 * resetKey driver so the scroll-reset test can trigger `useEffect([resetKey])`
 * in CodeEditor and assert all four scroll offsets return to 0.
 *
 * data-testids:
 *   ce-scroll-ready          — component mounted, ready for assertions
 *   ce-bump-resetkey-scroll  — click to increment resetKey
 */
export function CodeEditorScrollFixture(): JSX.Element {
  const [rk, setRk] = useState(0)
  // SCROLL_BODY — 100 lines × 80 chars each, module-scope constant — overflows the
  // 150px height (vertical) and, given a monospace font at ~7.5px per char, also
  // the 400px width (horizontal).
  return (
    <div data-theme="light" style={{ width: '400px', height: '150px' }}>
      <CodeEditor
        value={SCROLL_BODY}
        lang="text"
        onChange={() => {}}
        validVars={new Set<string>()}
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
 * AC-13 font-override fixture.
 *
 * Wraps CodeEditor in a container that declares `font-size: 20px` and
 * `line-height: 3` — metrics deliberately different from the component's
 * own 12.5px / 1.65 values. The `--code-line-h` custom property is
 * re-declared by the `.code-editor` class as a fixed `calc(12.5px * 1.65)`
 * px value, so the gutter rows, pre, and textarea must all remain at
 * 20.625 px regardless of what the ancestor container declares.
 *
 * Note on `--code-line-h` CSS-override feasibility via parent: the
 * `.code-editor` class rule re-declares `--code-line-h` at the element
 * level, so setting the custom property on a PARENT wrapper would be
 * overridden and would NOT propagate. An inline-style override directly on
 * `.code-editor` would win — but that requires touching the component's
 * internal element, which is impossible from a fixture without modifying
 * production code. That variant is therefore skipped; AC-13 is fully
 * verified through the font-independence path (the test below).
 */
export function CodeEditorFontOverrideFixture(): JSX.Element {
  return (
    <div data-theme="light" style={{ ...WRAPPER_STYLE, fontSize: '20px', lineHeight: '3' }}>
      <CodeEditor value={JSON_ALL_TOKENS} lang="json" onChange={() => {}} validVars={VALID_VARS} />
      <span data-testid="ce-font-override-ready" />
    </div>
  )
}

/**
 * AC-17 / AC-2 malformed-JSON degrade fixture.
 *
 * Passes an unterminated JSON body (`MALFORMED_JSON_BODY`) with `lang="json"`.
 * compose() will call JSON.parse, receive a SyntaxError, and return a single
 * `{ kind: 'plain', text }` token (the AC-17 degrade path). No structural
 * tk-* spans should ever appear.
 *
 * Mirrors BodyEditor.stories.tsx BodyEditorMalformedJsonFixture.
 */
export function CodeEditorMalformedFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={MALFORMED_JSON_BODY}
        lang="json"
        onChange={() => {}}
        validVars={new Set<string>()}
      />
      <span data-testid="ce-malformed-ready" />
    </div>
  )
}

/**
 * .tk-var.missing fixture.
 *
 * Body contains `{{missing}}` with `validVars={new Set(['x'])}` — `missing`
 * is absent from the known-vars set, so `isMissingVar(known=false, validVars)`
 * returns true and CodeEditor applies the `'tk-var missing'` className. The
 * CSS rule `.tk-var.missing { color: var(--m-delete); text-decoration:
 * line-through dotted; }` renders the unresolved var with strikethrough.
 *
 * Uses `lang="text"` to keep the fixture minimal — the var pass runs on all
 * langs, so JSON structural tokenisation is not required here.
 *
 * Positive counterpart (`.tk-var` WITHOUT `.missing`) is already covered by
 * the AC-17 test suite which uses CodeEditorLightFixture: `{{x}}` is in
 * VALID_VARS so it renders `.tk-var` (not `.tk-var.missing`) and
 * `assertResolvesToToken` asserts it binds to `--accent`.
 */
export function CodeEditorMissingVarFixture(): JSX.Element {
  return (
    <div data-theme="light" style={WRAPPER_STYLE}>
      <CodeEditor
        value={MISSING_VAR_BODY}
        lang="text"
        onChange={() => {}}
        validVars={new Set<string>(['x'])}
      />
      <span data-testid="ce-missing-var-ready" />
    </div>
  )
}
