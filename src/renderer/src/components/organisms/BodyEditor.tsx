/**
 * BodyEditor — organism
 *
 * Tagged-record SSOT: body lives in tab.spec.body (tabsStore). This component
 * reads and writes it exclusively via updateActiveSpec full-Body patches so
 * the store's ref-equality dirty guard fires correctly on every edit.
 *
 * Mount-all / hidden-toggle switch: ALL 6 panels are always mounted; only the
 * active panel is visible (others carry the HTML `hidden` attribute). Panels
 * are never unmounted, preserving scroll position across mode switches.
 *
 * Three-layer code area (raw mode): gutter | [textarea stacked over pre].
 * Textarea is the single scroll source; onScroll syncs pre.scrollTop/Left via
 * ref. Textarea text is `color: transparent`; the aria-hidden pre renders the
 * highlighted tokens on the same pixel grid.  All token text is inserted as
 * escaped JSX children — no innerHTML / dangerouslySetInnerHTML (XSS-safe).
 *
 * Live-immediate / debounced-coloring split (AC-23):
 *  - Plain text renders every keystroke (gutter line count + pre plain span).
 *  - compose() runs on a trailing debounce (BODY_HIGHLIGHT_DEBOUNCE_MS). When
 *    the colored snapshot matches body.raw.text the pre renders token spans;
 *    while typing it plain-degrades to a single var(--text) span.
 *
 * Urlencoded slot is a render-prop — KVTable is NOT imported here (§2.2).
 * form-data / binary / graphql show a built-in placeholder paragraph.
 *
 * Early-return guards prevent spurious store writes when the value is unchanged
 * (radio + lang-pill). Raw text and urlencoded rows skip the guard (genuine
 * content changes every call).
 */

import './BodyEditor.css'
import React, {
  memo,
  type ReactNode,
  useRef,
  useState,
  useEffect,
  useCallback,
  useMemo
} from 'react'
import { tabsStore, BLANK_BODY } from '@renderer/lib/tabsStore'
import type { RawBody, BodyType, RawLang, Row } from '@renderer/lib/tabsStore'
import { compose } from '@renderer/lib/jsonTokens'
import { isMissingVar } from '@renderer/lib/varTokens'
import { envVars } from '@renderer/lib/envVars'
import { EmptyPanel } from '@renderer/components/atoms/EmptyPanel'

// ─── Constants ───────────────────────────────────────────────────────────────

const BODY_HIGHLIGHT_DEBOUNCE_MS = 100

const BODY_TYPES: Array<{ value: BodyType; label: string }> = [
  { value: 'none', label: 'none' },
  { value: 'form-data', label: 'form-data' },
  { value: 'urlencoded', label: 'x-www-form-urlencoded' },
  { value: 'raw', label: 'raw' },
  { value: 'binary', label: 'binary' },
  { value: 'graphql', label: 'GraphQL' }
]

const RAW_LANGS: RawLang[] = ['json', 'xml', 'html', 'text']

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * BodyEditor is memo-wrapped so that parent re-renders (RequestSubTabs owns
 * several store subscriptions) do not cascade into BodyEditor. The only prop
 * `renderUrlencoded` is a module-level stable function reference; memo's
 * default shallow-equality check skips re-renders when neither the prop nor the
 * store slices read here have changed.
 */
export const BodyEditor = memo(function BodyEditor({
  renderUrlencoded
}: {
  /** Render-prop slot for the urlencoded key-value table (no direct KVTable import). */
  renderUrlencoded: (rows: readonly Row[], onRowsChange: (r: Row[]) => void) => ReactNode
}): React.JSX.Element {
  // Both reads are unconditional — Rules of Hooks
  const updateActiveSpec = tabsStore((s) => s.updateActiveSpec)
  const activeTabId = tabsStore((s) => s.activeTabId)
  const body = tabsStore((s) => s.tabs.find((t) => t.id === s.activeTabId)?.spec.body ?? BLANK_BODY)

  /** Ref array for roving-tabIndex focus management (one slot per radio). */
  const radioRefs = useRef<(HTMLElement | null)[]>([])

  /** Debounced highlight state: null until first compose() completes. */
  const [colored, setColored] = useState<{
    snapshot: string
    tokens: ReturnType<typeof compose>
  } | null>(null)

  /** Ref to the <pre> overlay for scroll synchronisation. */
  const preRef = useRef<HTMLPreElement>(null)

  /** Ref to the raw-body <textarea> — the single scroll source of the code area. */
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // On request-tab switch: invalidate the colored snapshot AND reset the inner
  // code-area scroll. BodyEditor is mounted once (no per-tab key), so its single
  // textarea persists across request tabs; RequestSubTabs' panel-scrollTop reset
  // does not reach this nested textarea, so without this the new tab's body would
  // appear at the previous tab's scroll offset (and the pre overlay would desync).
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
  }, [activeTabId])

  // Trailing debounce: schedule compose() whenever text, lang, OR the active tab
  // changes. Effect cleanup (return) clears the timer on re-run AND on unmount.
  // `activeTabId` is in the deps so a switch to a tab with IDENTICAL raw text+lang
  // still re-schedules compose() — the setColored(null) above cleared the cache,
  // and without re-arming here the highlight would stay off permanently on that tab.
  // envVars() returns a stable singleton (see envVars.ts); calling it here is safe.
  useEffect(() => {
    const timer = setTimeout(() => {
      const tokens = compose(body.raw.text, body.raw.lang, envVars())
      setColored({ snapshot: body.raw.text, tokens })
    }, BODY_HIGHLIGHT_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [body.raw.text, body.raw.lang, activeTabId])

  // ─── Typed update helpers ───────────────────────────────────────────────

  function setRaw(raw: RawBody): void {
    updateActiveSpec({ body: { ...body, raw } })
  }

  /**
   * Stable callback for the urlencoded KVTable render-prop. Reads the current
   * body from the store's getState() rather than closing over the render-time
   * `body` value, so the callback identity is stable across BodyEditor re-renders
   * (raw-mode keystrokes do not cause unnecessary KVTable re-renders).
   */
  const handleUrlencodedRowsChange = useCallback(
    (next: Row[]) => {
      const state = tabsStore.getState()
      const currentBody =
        state.tabs.find((t) => t.id === state.activeTabId)?.spec.body ?? BLANK_BODY
      updateActiveSpec({ body: { ...currentBody, urlencoded: { rows: next } } })
    },
    [updateActiveSpec]
  )

  // ─── Radio handlers ─────────────────────────────────────────────────────

  function handleRadioSelect(next: BodyType): void {
    if (next === body.active) return // early-return: no-op when already active
    updateActiveSpec({ body: { ...body, active: next } })
  }

  function handleRadioKeyDown(e: React.KeyboardEvent<HTMLElement>, index: number): void {
    const len = BODY_TYPES.length
    let nextIndex = -1

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      nextIndex = (index + 1) % len
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      nextIndex = (index - 1 + len) % len
    } else if (e.key === ' ' || e.key === 'Enter') {
      handleRadioSelect(BODY_TYPES[index].value)
      return
    }

    if (nextIndex >= 0) {
      e.preventDefault()
      handleRadioSelect(BODY_TYPES[nextIndex].value)
      radioRefs.current[nextIndex]?.focus()
    }
  }

  // ─── Lang-pill handler ──────────────────────────────────────────────────

  function handleLangCycle(): void {
    const idx = RAW_LANGS.indexOf(body.raw.lang)
    const next = RAW_LANGS[(idx + 1) % RAW_LANGS.length]
    // No equality guard: cycling always advances to a different lang, so the
    // write is never a no-op (unlike the radio/menu re-select case).
    setRaw({ ...body.raw, lang: next })
  }

  // ─── Code-area handlers ─────────────────────────────────────────────────

  /** Textarea is the single scroll source; pre follows via ref. */
  function handleTextareaScroll(e: React.UIEvent<HTMLTextAreaElement>): void {
    if (preRef.current) {
      preRef.current.scrollTop = e.currentTarget.scrollTop
      preRef.current.scrollLeft = e.currentTarget.scrollLeft
    }
  }

  function handleTextChange(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    setRaw({ ...body.raw, text: e.currentTarget.value })
  }

  // ─── Derived values ─────────────────────────────────────────────────────

  // useMemo: split('\n') on large raw bodies is a 50k-char scan; skip it when text
  // is unchanged (e.g. urlencoded-edit-driven re-renders leave raw text stable).
  const lineCount = useMemo(() => body.raw.text.split('\n').length, [body.raw.text])
  /** True only when the debounced snapshot matches the live text (and same lang). */
  const showColored = colored !== null && colored.snapshot === body.raw.text

  /**
   * Live env-var set — same stable singleton envVars() returns in v1; grows non-empty
   * once the T14 env store lands. Used in the missing-var render guard below.
   */
  const validVars = envVars()

  // Memoize gutter line-number divs: Array.from on a large body is a non-trivial
  // scan; skip it when lineCount is unchanged (finding 2).
  const gutterDivs = useMemo(
    () => Array.from({ length: lineCount }, (_, i) => <div key={i}>{i + 1}</div>),
    [lineCount]
  )

  // Memoize colored token spans: colored.tokens.map() rebuilds the full React
  // element tree on every render (incl. every urlencoded keystroke). Skip it when
  // neither the colored snapshot nor validVars has changed (finding 3).
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
    <div className="body-editor">
      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <div className="body-toolbar" data-testid="body-toolbar">
        <div className="body-radiogroup" role="radiogroup" aria-label="Request body type">
          {BODY_TYPES.map(({ value, label }, i) => (
            <div
              key={value}
              ref={(el) => {
                radioRefs.current[i] = el
              }}
              role="radio"
              aria-checked={body.active === value}
              tabIndex={body.active === value ? 0 : -1}
              className={`body-radio${body.active === value ? ' active' : ''}`}
              data-testid="body-radio"
              onClick={() => handleRadioSelect(value)}
              onKeyDown={(e) => handleRadioKeyDown(e, i)}
            >
              <span className="dot" />
              {label}
            </div>
          ))}
        </div>

        <div className="right">
          {/* Lang pill: only meaningful in raw mode */}
          <button
            type="button"
            className="lang-pill"
            data-testid="body-lang-pill"
            aria-label={`Raw body language: ${body.raw.lang}`}
            hidden={body.active !== 'raw'}
            onClick={handleLangCycle}
          >
            {body.raw.lang.toUpperCase()}
          </button>
        </div>
      </div>

      {/* ── Panels — mount-all / hidden-toggle: ALL 6 always in DOM ──────── */}

      {/* none — no payload */}
      <div hidden={body.active !== 'none'} />

      {/* raw — three-layer code area */}
      <div hidden={body.active !== 'raw'}>
        <div className="code-editor" data-testid="body-code-editor">
          {/* Gutter: one div per line, count matches live textarea line count */}
          <div className="gutter" data-testid="body-gutter">
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
              {showColored ? tokenSpans : <span>{body.raw.text}</span>}
            </pre>

            {/* Textarea drives height + scroll; text is transparent (caret visible). */}
            <textarea
              ref={textareaRef}
              value={body.raw.text}
              onChange={handleTextChange}
              onScroll={handleTextareaScroll}
              spellCheck={false}
              autoComplete="off"
              aria-label="Request body"
            />
          </div>
        </div>
      </div>

      {/* urlencoded — render-prop slot. handleUrlencodedRowsChange is stable via
          useCallback so KVTable (memo'd in App.tsx) skips re-renders while the
          urlencoded panel is hidden and urlencoded.rows is reference-stable. */}
      <div hidden={body.active !== 'urlencoded'}>
        {renderUrlencoded(body.urlencoded.rows, handleUrlencodedRowsChange)}
      </div>

      {/* form-data — placeholder */}
      <div hidden={body.active !== 'form-data'}>
        <EmptyPanel />
      </div>

      {/* binary — placeholder */}
      <div hidden={body.active !== 'binary'}>
        <EmptyPanel />
      </div>

      {/* graphql — placeholder */}
      <div hidden={body.active !== 'graphql'}>
        <EmptyPanel />
      </div>
    </div>
  )
})
