import './KVTable.css'
import { type JSX, type ClipboardEvent, useId, useRef, useLayoutEffect } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { cx } from '@renderer/lib/cx'
import { tokenizeVars, isMissingVar } from '@renderer/lib/varTokens'
import type { VarSegment } from '@renderer/lib/varTokens'
import { envVars } from '@renderer/lib/envVars'
import type { Row } from '@renderer/lib/tabsStore'

const EMPTY_ROWS: readonly Row[] = Object.freeze([])

/**
 * Stable module-level selector for the controlled arm of the storeRows
 * subscription. Always returns EMPTY_ROWS (the same reference), so zustand
 * never re-subscribes when the KVTable is in controlled mode — avoiding dead
 * work on the hot path (every keystroke in raw body mode triggers a store
 * write, which would otherwise invoke an inline closure unnecessarily).
 */
const EMPTY_ROWS_SELECTOR = (): readonly Row[] => EMPTY_ROWS

type Column = 'key' | 'value' | 'description'

/**
 * Discriminated-prop union for KVTable.
 *
 * **Field arm** — store-bound: edits dispatch through `tabsStore.updateActiveSpec`.
 *   `{ field: 'params' | 'headers'; validVars?: ReadonlySet<string> }`
 *
 * **Controlled arm** — caller-owned rows: edits call `onRowsChange` and never
 *   touch the tabsStore. Used for x-www-form-urlencoded body mode.
 *   `{ rows: readonly Row[]; onRowsChange: (r: Row[]) => void; validVars?: ReadonlySet<string> }`
 *
 * `validVars` — known variable names for the `.missing` highlight gate; applies
 *   to both arms. Defaults to `envVars()` (empty in v1 → all tokens neutral
 *   `.var`, none `.missing`).
 */
type KVTableProps = (
  | {
      /** The RequestSpec field to bind: 'params' or 'headers'. */
      field: 'params' | 'headers'
    }
  | {
      /** Caller-owned rows (controlled mode — x-www-form-urlencoded body). */
      rows: readonly Row[]
      /** Called with the next full rows array on every edit. */
      onRowsChange: (r: Row[]) => void
    }
) & {
  /** Known variable names for the .missing highlight gate. */
  validVars?: ReadonlySet<string>
}

/**
 * Editable key-value table. Accepts either a store-bound field arm
 * (`field: 'params' | 'headers'`) or a controlled arm (`rows` + `onRowsChange`).
 * Renders stored rows plus one virtual trailing empty row for appending.
 * Key and value cells highlight `{{var}}` tokens via an aria-hidden overlay;
 * description renders verbatim. Supports auto-promote, delete-with-focus-recovery,
 * and multi-line paste collapsing.
 */
export function KVTable(props: KVTableProps): JSX.Element {
  const isControlled = 'rows' in props
  const validVars = props.validVars ?? envVars()

  // Stable id prefix — prevents duplicate HTML ids when multiple KVTable
  // instances coexist (e.g. params, headers, and urlencoded on the same page).
  const kv_id = useId()

  // Both tabsStore subscriptions are unconditional (Rules of Hooks).
  const updateActiveSpec = tabsStore((s) => s.updateActiveSpec)
  // In controlled mode use the stable module-level EMPTY_ROWS_SELECTOR so
  // zustand avoids re-subscribing on every render (inline closures always
  // produce a new reference, triggering a re-subscribe even though the result
  // is reference-stable). Field mode still needs an inline closure to capture
  // props.field; the dead-work optimisation only targets the controlled arm.
  const storeRows = tabsStore(
    isControlled
      ? EMPTY_ROWS_SELECTOR
      : (s): readonly Row[] => {
          // Type guard mirrors the original: when props has no 'field', fall
          // back to EMPTY_ROWS. Unreachable in practice (isControlled === false
          // guarantees 'field' in props), but required for type narrowing.
          if (!('field' in props)) return EMPTY_ROWS
          const tab = s.tabs.find((t) => t.id === s.activeTabId)
          return tab ? tab.spec[props.field] : EMPTY_ROWS
        }
  )
  // Pick the live rows value after both hooks have run.
  const rows = isControlled ? props.rows : storeRows

  /** Set before a state write that should move focus after the DOM commit. */
  const pendingFocus = useRef<{ rowIndex: number; column: Column } | null>(null)
  /** Maps "${rowIndex}:${column}" → the live input element. */
  const refMap = useRef<Map<string, HTMLInputElement>>(new Map())

  // After every commit that has a pending focus request, move focus pre-paint.
  useLayoutEffect(() => {
    if (pendingFocus.current) {
      const { rowIndex, column } = pendingFocus.current
      refMap.current.get(`${rowIndex}:${column}`)?.focus()
      pendingFocus.current = null
    }
  })

  /** Returns a ref callback that registers/unregisters the input in refMap. */
  function setInputRef(rowIndex: number, column: Column) {
    return (el: HTMLInputElement | null): void => {
      const key = `${rowIndex}:${column}`
      if (el) {
        refMap.current.set(key, el)
      } else {
        refMap.current.delete(key)
      }
    }
  }

  /** Tokenises text and returns highlight spans for the overlay layer. */
  function renderSegments(text: string): JSX.Element[] {
    const segments: VarSegment[] = tokenizeVars(text)
    return segments.map((seg, i): JSX.Element => {
      if (seg.kind === 'plain') {
        return <span key={i}>{seg.text}</span>
      }
      // isMissingVar: shared gate — true only when validVars is non-empty (env
      // vars loaded) AND the name is absent from the set (§3.6 DRY, Finding 4).
      const missing = isMissingVar(validVars.has(seg.name), validVars)
      return (
        <span key={i} className={cx('var', missing && 'missing')}>
          {seg.raw}
        </span>
      )
    })
  }

  /**
   * If the pasted text contains newlines, prevent the default paste and insert
   * with newlines collapsed to spaces. Single-line pastes fall through.
   */
  function handlePaste(e: ClipboardEvent<HTMLInputElement>, onChange: (v: string) => void): void {
    const pasted = e.clipboardData.getData('text')
    if (!pasted.includes('\n')) return
    e.preventDefault()
    const input = e.currentTarget
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    const collapsed = pasted.replace(/\n/g, ' ')
    onChange(input.value.slice(0, start) + collapsed + input.value.slice(end))
  }

  /**
   * Dispatches a row update.
   * - Controlled mode (`'rows' in props`): calls `onRowsChange` and returns
   *   immediately — `updateActiveSpec` is NEVER invoked, so the tabsStore is
   *   never written (AC-11 negative invariant). Downstream tests (tasks 008/011)
   *   must assert this with a spy on `updateActiveSpec`, not just a positive
   *   `onRowsChange` call.
   * - Field mode: dispatches `params`/`headers` through `updateActiveSpec` (unchanged).
   */
  function writeRows(nextRows: Row[]): void {
    if ('rows' in props) {
      props.onRowsChange(nextRows)
      return
    }
    if (props.field === 'params') {
      updateActiveSpec({ params: nextRows })
    } else {
      updateActiveSpec({ headers: nextRows })
    }
  }

  function handleRealChange(rowIndex: number, col: Column, newText: string): void {
    writeRows(
      rows.map((r, i): Row => {
        if (i !== rowIndex) return r
        if (col === 'key') return { ...r, key: newText }
        if (col === 'value') return { ...r, value: newText }
        return { ...r, description: newText }
      })
    )
  }

  function handleToggle(rowIndex: number): void {
    writeRows(rows.map((r, i): Row => (i === rowIndex ? { ...r, enabled: !r.enabled } : r)))
  }

  function handleDelete(rowIndex: number, col: Column): void {
    // Clamp adjacent index so deleting the sole real row focuses the virtual row (index 0).
    const adjacentIndex = Math.max(0, Math.min(rowIndex, rows.length - 2))
    pendingFocus.current = { rowIndex: adjacentIndex, column: col }
    writeRows(rows.filter((_, i) => i !== rowIndex))
  }

  /** Promotes the virtual trailing row by appending a real row carrying the edit. */
  function handleVirtualKeyValue(col: 'key' | 'value', newText: string): void {
    const newRow: Row = {
      enabled: true,
      key: col === 'key' ? newText : '',
      value: col === 'value' ? newText : '',
      description: ''
    }
    writeRows([...rows, newRow])
  }

  /**
   * On Enter in the virtual trailing row, move focus to the (now current)
   * virtual row's key cell. After any prior promotion rows.length has already
   * advanced, so this naturally targets the newest virtual row.
   */
  function handleVirtualEnter(): void {
    refMap.current.get(`${rows.length}:key`)?.focus()
  }

  // The virtual trailing empty row is never stored; it derives from render state.
  const renderedRows: Row[] = [...rows, { enabled: false, key: '', value: '', description: '' }]

  return (
    <div className="kv">
      {/* Column headers carry stable ids so inputs can reference them via
          aria-describedby — lighter than role=grid/columnheader restructuring
          and doesn't override the per-row aria-label (Finding 9). */}
      <div className="kv-header">
        <div />
        <div id={`${kv_id}-col-key`}>KEY</div>
        <div id={`${kv_id}-col-value`}>VALUE</div>
        <div id={`${kv_id}-col-desc`}>DESCRIPTION</div>
        <div />
      </div>

      {renderedRows.map((row, index) => {
        const isVirtual = index === rows.length
        const isDisabled = !isVirtual && !row.enabled

        return (
          <div key={index} className={cx('kv-row', isDisabled && 'disabled', isVirtual && 'empty')}>
            {/* Checkbox — inert (no-op) for the virtual trailing row */}
            <div className="kv-check">
              <input
                type="checkbox"
                checked={row.enabled}
                disabled={isVirtual}
                onChange={() => {
                  if (!isVirtual) handleToggle(index)
                }}
                aria-label={isVirtual ? 'Enable new row' : `Toggle row ${index + 1}`}
              />
            </div>

            {/* Key cell — overlay input + aria-hidden highlight layer */}
            <div className={cx('kv-cell', 'key')}>
              <div className="kv-input-wrap">
                <div className="kv-highlight" aria-hidden>
                  {renderSegments(row.key)}
                </div>
                <input
                  ref={setInputRef(index, 'key')}
                  value={row.key}
                  placeholder="Key"
                  aria-label={isVirtual ? 'Key for new row' : `Key for row ${index + 1}`}
                  aria-describedby={`${kv_id}-col-key`}
                  onChange={(e) => {
                    if (isVirtual) {
                      handleVirtualKeyValue('key', e.target.value)
                    } else {
                      handleRealChange(index, 'key', e.target.value)
                    }
                  }}
                  onPaste={(e) => {
                    const cb = isVirtual
                      ? (v: string) => handleVirtualKeyValue('key', v)
                      : (v: string) => handleRealChange(index, 'key', v)
                    handlePaste(e, cb)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && isVirtual) handleVirtualEnter()
                  }}
                />
              </div>
            </div>

            {/* Value cell — overlay input + aria-hidden highlight layer */}
            <div className={cx('kv-cell', 'value')}>
              <div className="kv-input-wrap">
                <div className="kv-highlight" aria-hidden>
                  {renderSegments(row.value)}
                </div>
                <input
                  ref={setInputRef(index, 'value')}
                  value={row.value}
                  placeholder="Value"
                  aria-label={isVirtual ? 'Value for new row' : `Value for row ${index + 1}`}
                  aria-describedby={`${kv_id}-col-value`}
                  onChange={(e) => {
                    if (isVirtual) {
                      handleVirtualKeyValue('value', e.target.value)
                    } else {
                      handleRealChange(index, 'value', e.target.value)
                    }
                  }}
                  onPaste={(e) => {
                    const cb = isVirtual
                      ? (v: string) => handleVirtualKeyValue('value', v)
                      : (v: string) => handleRealChange(index, 'value', v)
                    handlePaste(e, cb)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && isVirtual) handleVirtualEnter()
                  }}
                />
              </div>
            </div>

            {/* Description cell — plain input, no tokenisation (R10) */}
            <div className="kv-cell">
              <input
                ref={setInputRef(index, 'description')}
                value={row.description}
                placeholder="Description"
                aria-label={
                  isVirtual ? 'Description for new row' : `Description for row ${index + 1}`
                }
                aria-describedby={`${kv_id}-col-desc`}
                readOnly={isVirtual}
                onChange={(e) => {
                  if (!isVirtual) handleRealChange(index, 'description', e.target.value)
                }}
                onPaste={(e) => {
                  if (!isVirtual) {
                    handlePaste(e, (v) => handleRealChange(index, 'description', v))
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && isVirtual) handleVirtualEnter()
                }}
              />
            </div>

            {/* Delete action — absent for the virtual trailing row */}
            <div className="kv-actions">
              {!isVirtual && (
                <button
                  type="button"
                  aria-label={`Delete row ${index + 1}`}
                  onClick={() => handleDelete(index, 'key')}
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
