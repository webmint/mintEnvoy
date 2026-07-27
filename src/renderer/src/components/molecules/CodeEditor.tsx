/**
 * CodeEditor — molecule
 *
 * Edit/preview toggle code editor: mounts a plain textarea (editing=true) XOR
 * a highlighted <pre> (editing=false) — never both. The `editing` boolean is
 * controlled by the parent (BodyEditor); CodeEditor holds NO store awareness.
 *
 * Preview → edit: click the preview (caret placed at clicked character) or press
 * Enter/Space while the preview is focused. A shared focus-on-mount useEffect
 * (keyed on `editing`) focuses the textarea on ALL entry paths (click / keyboard
 * Enter-Space / toggle button).
 * Edit → preview: textarea blur OR onEditingChange(false) from parent (toggle).
 *
 * Tokenize (F-001): compose() runs via a {value,lang}-snapshot-cache useMemo
 * gated to !editing — once per switch-to-preview, first mount, and tab-switch /
 * lang-cycle. Never per keystroke (the pre is unmounted while editing, so compose
 * is unreachable during edit).
 *
 * resetKey contract: supply an opaque scalar that changes whenever the consumer
 * wants the editor to reset scroll to (0,0). Scroll also resets on every toggle
 * via the natural fresh-mount of the swapped layer.
 *
 * All token text is inserted as escaped JSX children — no innerHTML (AC-8).
 */

import './CodeEditor.css'
import React, { memo, useRef, useEffect, useMemo } from 'react'
import type { RawLang } from '@renderer/lib/tabsStore'
import { compose } from '@renderer/lib/jsonTokens'
import { isMissingVar } from '@renderer/lib/varTokens'
import { cx } from '@renderer/lib/cx'

// ─── Types ───────────────────────────────────────────────────────────────────

interface CodeEditorProps {
  /** Current text value of the editor. */
  value: string
  /** Language for syntax highlighting (json | xml | html | text). */
  lang: RawLang
  /** Called on every text change event with the new full string. */
  onChange: (v: string) => void
  /** Known env-var names; vars absent from this set render as missing. */
  validVars: ReadonlySet<string>
  /**
   * Opaque reset scalar — change it to reset the code-area scroll to (0,0).
   * Typically the active tab/request ID.
   */
  resetKey?: string | number
  /**
   * Whether the editor is in edit mode (textarea visible) or preview mode
   * (highlighted pre visible). Controlled by the parent; defaults to false
   * (preview). Wired by BodyEditor (task 002).
   */
  editing?: boolean
  /**
   * Called when the edit/preview state should change. Provided by the parent.
   * Wired by BodyEditor (task 002).
   */
  onEditingChange?: (next: boolean) => void
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * CodeEditor is memo-wrapped so parent re-renders (e.g. tab switches or store
 * updates unrelated to the editor's props) do not cascade into this component.
 * Shallow-equality on props is sufficient: value/lang/resetKey/editing are
 * primitives; validVars is a stable singleton reference from envVars().
 */
export const CodeEditor = memo(function CodeEditor({
  value,
  lang,
  onChange,
  validVars,
  resetKey,
  editing = false,
  onEditingChange
}: CodeEditorProps): React.JSX.Element {
  /** Ref to the <pre> preview — used for caret-at-click coordinate mapping. */
  const preRef = useRef<HTMLPreElement>(null)

  /** Ref to the <textarea> — focused on every edit-mode entry. */
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  /**
   * Stashes the caret offset computed at preview click time so the
   * focus-on-mount effect can apply setSelectionRange after the textarea mounts.
   */
  const pendingCaretOffset = useRef<number | null>(null)

  // On resetKey change: reset the visible layer's scroll to (0,0). Only one
  // ref is non-null at a time (conditional-mount); both are null-guarded.
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.scrollTop = 0
      textareaRef.current.scrollLeft = 0
    }
    if (preRef.current) {
      preRef.current.scrollTop = 0
      preRef.current.scrollLeft = 0
    }
  }, [resetKey])

  // Shared focus-on-mount effect: on every editing false→true transition, focus
  // the freshly-mounted textarea and apply any stashed caret offset.
  // Covers ALL edit-entry paths (click / keyboard Enter-Space / toggle button).
  // Keyed on `editing` alone — focus() is idempotent, no editingViaClick flag needed.
  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus()
      if (pendingCaretOffset.current !== null) {
        const offset = pendingCaretOffset.current
        pendingCaretOffset.current = null
        textareaRef.current.setSelectionRange(offset, offset)
      }
    }
  }, [editing])

  // ─── Caret-at-click helper ──────────────────────────────────────────────

  /**
   * Maps pointer coordinates on the <pre> to a character offset in `value`.
   * Uses caretPositionFromPoint (standard) with caretRangeFromPoint
   * (WebKit/Chromium/Electron fallback). Returns end-of-text on a null hit;
   * clamps the result to [0, value.length].
   */
  function computeCaretOffset(x: number, y: number): number {
    const pre = preRef.current
    if (!pre) return value.length

    let targetNode: Node | null = null
    let targetOffset = 0

    if (document.caretPositionFromPoint) {
      // Standard (Firefox, Chromium 128+)
      const pos = document.caretPositionFromPoint(x, y)
      if (pos !== null) {
        targetNode = pos.offsetNode
        targetOffset = pos.offset
      }
    } else if (document.caretRangeFromPoint) {
      // WebKit / Electron
      const range = document.caretRangeFromPoint(x, y)
      if (range !== null) {
        targetNode = range.startContainer
        targetOffset = range.startOffset
      }
    }

    if (targetNode === null) return value.length

    // Measure text length from the <pre> start to the caret hit point
    const rangeFromStart = document.createRange()
    rangeFromStart.setStart(pre, 0)
    rangeFromStart.setEnd(targetNode, targetOffset)
    const charOffset = rangeFromStart.toString().length
    return Math.max(0, Math.min(charOffset, value.length))
  }

  // ─── Event handlers ─────────────────────────────────────────────────────

  /**
   * Click anywhere in the code area (preview): stash the caret offset and enter
   * edit mode. Hoisted from the <pre> to the grid container so a short/empty body
   * — whose <pre> only spans the rendered lines — is still fully clickable rather
   * than leaving dead space below the text. The offset is still measured against
   * the <pre>; a click below the last line clamps to end-of-text (AC-13).
   */
  function handlePreviewClick(e: React.MouseEvent<HTMLDivElement>): void {
    pendingCaretOffset.current = computeCaretOffset(e.clientX, e.clientY)
    onEditingChange?.(true)
  }

  /**
   * Keydown on the focusable preview <pre>: Enter or Space enters edit mode.
   * The shared focus-on-mount effect will focus the textarea post-mount.
   */
  function handlePreviewKeyDown(e: React.KeyboardEvent<HTMLPreElement>): void {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onEditingChange?.(true)
    }
  }

  /** Textarea blur: exit edit mode, return to preview (F-002 blur half). */
  function handleTextareaBlur(): void {
    onEditingChange?.(false)
  }

  function handleTextChange(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    onChange(e.currentTarget.value)
  }

  // ─── Derived values ─────────────────────────────────────────────────────

  // useMemo: split('\n') on large bodies is a 50k-char scan; skip it when text
  // is unchanged (e.g. store updates unrelated to the raw text leave it stable).
  const lineCount = useMemo(() => value.split('\n').length, [value])

  /**
   * Tokenize gate (F-001): compose() runs ONLY when the pre is the mounted
   * layer (!editing). Keyed on {value, lang} so compose runs once per
   * switch-to-preview, first mount, and tab-switch/lang-cycle — never per
   * keystroke (the pre is unmounted while editing, making this gate unreachable).
   * validVars is the stable envVars() singleton; included for dep completeness.
   */
  const tokenResult = useMemo(
    () => (!editing ? compose(value, lang, validVars) : null),
    [editing, value, lang, validVars]
  )

  // Memoize gutter line-number divs: Array.from on a large body is a non-trivial
  // scan; skip it when lineCount is unchanged.
  const gutterDivs = useMemo(
    () => Array.from({ length: lineCount }, (_, i) => <div key={i}>{i + 1}</div>),
    [lineCount]
  )

  // Memoize token spans: rebuilds the full React element tree; skip when neither
  // the token result nor validVars has changed.
  const tokenSpans = useMemo(
    () =>
      tokenResult?.map((t, i) => (
        <span
          key={i}
          className={
            t.kind === 'plain'
              ? undefined
              : // tk-var: compose .missing via cx() + the shared isMissingVar gate
                // (§4 cx() conditional-class rule; §3.6 DRY — same as KVTable).
                t.kind === 'tk-var'
                ? cx('tk-var', isMissingVar(t.known, validVars) && 'missing')
                : t.kind
          }
        >
          {t.text}
        </span>
      )) ?? null,
    [tokenResult, validVars]
  )

  // ─── Render ─────────────────────────────────────────────────────────────

  return (
    <div
      className="code-editor"
      data-testid="body-code-editor"
      data-editing={editing}
      // Whole-area click-to-edit (preview only): the <pre> spans only the rendered
      // lines, so a short/empty body would leave most of the editor a dead zone.
      // Hoisting onClick to the container makes the full surface enter edit; in
      // edit mode the textarea owns clicks so the handler is detached. This is a
      // purely additive hit target — the focusable `<pre role="button">` below
      // remains the single accessible (keyboard-named) edit-entry control, so the
      // container stays an unmarked presentational wrapper (no role/tabIndex).
      onClick={editing ? undefined : handlePreviewClick}
    >
      {/* Gutter: one div per line, count matches the visible layer's line count */}
      <div className="gutter" data-testid="body-gutter" aria-hidden="true">
        {gutterDivs}
      </div>

      {/* Content: textarea (edit) XOR pre (preview) — never both mounted (AC-10) */}
      <div className="code-editor-content">
        {editing ? (
          /* Edit mode: plain textarea, visible text colour, native UX */
          <textarea
            ref={textareaRef}
            // rows={lineCount} so the textarea grows to its full content height like
            // the preview <pre> does. Without it the textarea keeps its intrinsic
            // 2-row height and clips any line past the second (e.g. a brace on line
            // 3 was hidden); the outer editor container owns the scroll.
            rows={lineCount}
            value={value}
            onChange={handleTextChange}
            onBlur={handleTextareaBlur}
            spellCheck={false}
            autoComplete="off"
            aria-label="Request body"
          />
        ) : (
          /* Preview mode: highlighted <pre>, focusable, click / Enter-Space enters edit */
          <pre
            ref={preRef}
            data-testid="body-pre"
            role="button"
            tabIndex={0}
            onKeyDown={handlePreviewKeyDown}
            aria-label="Request body preview — press Enter or Space to edit"
          >
            {tokenSpans}
          </pre>
        )}
      </div>
    </div>
  )
})
