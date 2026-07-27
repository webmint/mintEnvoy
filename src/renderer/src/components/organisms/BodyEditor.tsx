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
 * Raw-mode code area is delegated to the CodeEditor molecule, which owns the
 * three-layer overlay, debounced highlighting, scroll sync, and reset-on-tab
 * behaviour. BodyEditor passes resetKey={activeTabId} so CodeEditor resets
 * scroll and invalidates the color snapshot on tab switch.
 *
 * Urlencoded slot is a render-prop — KVTable is NOT imported here (§2.2).
 * form-data / binary / graphql show a built-in placeholder paragraph.
 *
 * Early-return guards prevent spurious store writes when the value is unchanged
 * (radio + lang-pill). Raw text and urlencoded rows skip the guard (genuine
 * content changes every call).
 */

import './BodyEditor.css'
import React, { memo, type ReactNode, useRef, useCallback, useState } from 'react'
import { tabsStore, BLANK_BODY } from '@renderer/lib/tabsStore'
import type { RawBody, BodyType, RawLang, Row } from '@renderer/lib/tabsStore'
import { envVars } from '@renderer/lib/envVars'
import { EmptyPanel } from '@renderer/components/atoms/EmptyPanel'
import { CodeEditor } from '@renderer/components/molecules/CodeEditor'

// ─── Constants ───────────────────────────────────────────────────────────────

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

  /** Ephemeral editing state: true = textarea edit mode, false = highlighted preview. */
  const [editing, setEditing] = useState(false)
  /**
   * Render-phase reset (AC-6 return-to-preview): detect an activeTabId change
   * during rendering and reset editing to false in the same render cycle.
   *
   * This is React's documented set-state-in-render idiom — NOT a useEffect and
   * NOT a ref written during render. The reset is atomic with the tab switch:
   * React discards the current render output, immediately re-renders with
   * editing=false, and the user never sees a flash of the stale editing mode on
   * the newly-selected tab.
   */
  const [prevTab, setPrevTab] = useState(activeTabId)
  if (activeTabId !== prevTab) {
    setPrevTab(activeTabId)
    setEditing(false)
  }

  /** Ref array for roving-tabIndex focus management (one slot per radio). */
  const radioRefs = useRef<(HTMLElement | null)[]>([])

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

  // ─── Derived values ─────────────────────────────────────────────────────

  /**
   * Live env-var set — stable singleton from envVars(); passed to CodeEditor
   * so the missing-var highlight gate uses the same reference as the rest of
   * the app.
   */
  const validVars = envVars()

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
          {/* Edit/preview toggle: only meaningful in raw mode, mirrors lang-pill gating.
              onMouseDown calls preventDefault so clicking while editing does not blur
              the textarea before onClick fires the toggle. */}
          <button
            type="button"
            className="body-edit-toggle"
            data-testid="body-edit-toggle"
            // Toggle-button a11y: aria-pressed carries the current edit/preview
            // state to AT (WCAG 4.1.2 Name/Role/Value). NO aria-label — the button's
            // visible text ("Edit"/"Preview") is its accessible name, so Label-in-Name
            // (WCAG 2.5.3) holds (a stable aria-label like "Edit mode" would NOT
            // contain the visible "Preview" text and would violate 2.5.3).
            aria-pressed={editing}
            hidden={body.active !== 'raw'}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => setEditing((v) => !v)}
          >
            {editing ? 'Preview' : 'Edit'}
          </button>
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

      {/* raw — three-layer code area (delegated to CodeEditor molecule) */}
      <div hidden={body.active !== 'raw'}>
        <CodeEditor
          resetKey={activeTabId}
          value={body.raw.text}
          lang={body.raw.lang}
          onChange={(text) => setRaw({ ...body.raw, text })}
          validVars={validVars}
          editing={editing}
          onEditingChange={setEditing}
        />
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
