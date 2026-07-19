/**
 * CodeEditor — molecule
 *
 * Three-layer overlay code editor: gutter + aria-hidden <pre> (highlight layer)
 * + transparent <textarea> (single scroll source). The textarea drives height and
 * scroll position; onScroll syncs pre.scrollTop/Left via ref on each scroll event.
 * Textarea text is `color: transparent`; the aria-hidden pre renders syntax-colored
 * token spans on the same pixel grid. All token text is inserted as escaped JSX
 * children — no innerHTML / dangerouslySetInnerHTML (XSS-safe).
 *
 * resetKey contract: supply an opaque scalar (tab ID, request ID, etc.) that changes
 * whenever the consumer wants the editor to reset to scroll-top and invalidate the
 * debounced color snapshot. A new resetKey synchronously scrolls textarea and pre to
 * (0,0) and clears `colored`, then re-schedules compose() on the trailing debounce.
 *
 * Holds NO tabsStore or activeTabId awareness — all context flows in via props.
 */

import './CodeEditor.css'
import React, { memo, useRef, useState, useEffect, useMemo } from 'react'
import type { RawLang } from '@renderer/lib/tabsStore'
import { compose } from '@renderer/lib/jsonTokens'
import { isMissingVar } from '@renderer/lib/varTokens'

// ─── Constants ───────────────────────────────────────────────────────────────

const BODY_HIGHLIGHT_DEBOUNCE_MS = 100

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
   * Opaque reset scalar — change it to reset scroll to (0,0) and invalidate the
   * debounced color snapshot. Typically the active tab/request ID.
   */
  resetKey?: string | number
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * CodeEditor is memo-wrapped so parent re-renders (e.g. tab switches or store
 * updates unrelated to the editor's props) do not cascade into this component.
 * Shallow-equality on props is sufficient: value/lang/resetKey are primitives;
 * validVars is a stable singleton reference from envVars().
 */
export const CodeEditor = memo(function CodeEditor({
  value,
  lang,
  onChange,
  validVars,
  resetKey
}: CodeEditorProps): React.JSX.Element {
  /** Debounced highlight state: null until first compose() completes. */
  const [colored, setColored] = useState<{
    snapshot: string
    tokens: ReturnType<typeof compose>
  } | null>(null)

  /** Ref to the <pre> overlay for scroll synchronisation. */
  const preRef = useRef<HTMLPreElement>(null)

  /** Ref to the <textarea> — the single scroll source of the code area. */
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // On resetKey change: invalidate the colored snapshot AND reset the inner
  // code-area scroll. Without this, switching between tabs/requests would render
  // the new content at the previous scroll offset and desync the pre overlay.
  useEffect(() => {
    setColored(null)
    if (textareaRef.current) {
      textareaRef.current.scrollTop = 0
      textareaRef.current.scrollLeft = 0
    }
    if (preRef.current) {
      preRef.current.scrollTop = 0
      preRef.current.scrollLeft = 0
    }
  }, [resetKey])

  // Trailing debounce: schedule compose() whenever text, lang, OR resetKey
  // changes. Effect cleanup clears the timer on re-run AND on unmount.
  // resetKey is in the deps so a switch to a request with identical raw text+lang
  // still re-schedules compose() — the setColored(null) above cleared the cache,
  // and without re-arming here the highlight would stay off permanently on that tab.
  useEffect(() => {
    const timer = setTimeout(() => {
      const tokens = compose(value, lang, validVars)
      setColored({ snapshot: value, tokens })
    }, BODY_HIGHLIGHT_DEBOUNCE_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- validVars is the stable envVars() singleton; it is a frozen reference that never changes between renders, so omitting it from deps is safe
  }, [value, lang, resetKey])

  // ─── Code-area handlers ─────────────────────────────────────────────────

  /** Textarea is the single scroll source; pre follows via ref. */
  function handleTextareaScroll(e: React.UIEvent<HTMLTextAreaElement>): void {
    if (preRef.current) {
      preRef.current.scrollTop = e.currentTarget.scrollTop
      preRef.current.scrollLeft = e.currentTarget.scrollLeft
    }
  }

  function handleTextChange(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    onChange(e.currentTarget.value)
  }

  // ─── Derived values ─────────────────────────────────────────────────────

  // useMemo: split('\n') on large bodies is a 50k-char scan; skip it when text
  // is unchanged (e.g. store updates unrelated to the raw text leave it stable).
  const lineCount = useMemo(() => value.split('\n').length, [value])

  /** True only when the debounced snapshot matches the live text. */
  const showColored = colored !== null && colored.snapshot === value

  // Memoize gutter line-number divs: Array.from on a large body is a non-trivial
  // scan; skip it when lineCount is unchanged.
  const gutterDivs = useMemo(
    () => Array.from({ length: lineCount }, (_, i) => <div key={i}>{i + 1}</div>),
    [lineCount]
  )

  // Memoize colored token spans: colored.tokens.map() rebuilds the full React
  // element tree on every render. Skip it when neither the colored snapshot nor
  // validVars has changed.
  const tokenSpans = useMemo(
    () =>
      colored?.tokens.map((t, i) => (
        <span
          key={i}
          className={
            t.kind === 'plain'
              ? undefined
              : // tk-var: apply .missing via shared isMissingVar gate
                // (§3.6 DRY — same rule as KVTable's renderSegments).
                t.kind === 'tk-var' && isMissingVar(t.known, validVars)
                ? 'tk-var missing'
                : t.kind
          }
        >
          {t.text}
        </span>
      )) ?? null,
    [colored, validVars]
  )

  // ─── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="code-editor" data-testid="body-code-editor">
      {/* Gutter: one div per line, count matches live textarea line count */}
      <div className="gutter" data-testid="body-gutter" aria-hidden="true">
        {gutterDivs}
      </div>

      {/* Content: textarea (scroll source) + pre (highlight layer) stacked */}
      <div className="code-editor-content">
        {/*
         * pre sits behind the transparent textarea.
         * showColored: render compose() token spans.
         * plain-degrade: single span with live text when compose is stale.
         * All content is escaped JSX text — never innerHTML.
         */}
        <pre ref={preRef} data-testid="body-pre" aria-hidden="true">
          {showColored ? tokenSpans : <span>{value}</span>}
        </pre>

        {/* Textarea drives height + scroll; text is transparent (caret visible). */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleTextChange}
          onScroll={handleTextareaScroll}
          spellCheck={false}
          autoComplete="off"
          aria-label="Request body"
        />
      </div>
    </div>
  )
})
