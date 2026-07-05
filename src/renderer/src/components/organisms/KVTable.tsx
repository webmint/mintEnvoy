import './KVTable.css'
import { type JSX, type ClipboardEvent, useRef, useLayoutEffect } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { cx } from '@renderer/lib/cx'
import { tokenizeVars } from '@renderer/lib/varTokens'
import type { VarSegment } from '@renderer/lib/varTokens'
import { envVars } from '@renderer/lib/envVars'
import type { Row } from '@renderer/lib/requestSpec'

const EMPTY_ROWS: readonly Row[] = Object.freeze([])

type Column = 'key' | 'value' | 'description'

/**
 * Editable key-value table bound to the active tab's `params` or `headers`
 * field in the tabsStore. Renders stored rows plus one virtual trailing empty
 * row for appending. Key and value cells highlight `{{var}}` tokens via an
 * aria-hidden overlay; description renders verbatim. Supports auto-promote,
 * delete-with-focus-recovery, and multi-line paste collapsing.
 *
 * @param field     - Which RequestSpec field to bind: `'params'` or `'headers'`.
 * @param validVars - Known variable names; absent tokens are marked `.missing`
 *                    when the set is non-empty. Defaults to `envVars()` (empty
 *                    in v1 → all tokens neutral `.var`, none `.missing`).
 */
export function KVTable({
  field,
  validVars = envVars()
}: {
  /** The RequestSpec field to bind: 'params' or 'headers'. */
  field: 'params' | 'headers'
  /** Known variable names for the .missing highlight gate. */
  validVars?: ReadonlySet<string>
}): JSX.Element {
  const updateActiveSpec = tabsStore((s) => s.updateActiveSpec)
  const rows = tabsStore((s): readonly Row[] => {
    const tab = s.tabs.find((t) => t.id === s.activeTabId)
    return tab ? tab.spec[field] : EMPTY_ROWS
  })

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
      const isMissing = validVars.size > 0 && !validVars.has(seg.name)
      return (
        <span key={i} className={cx('var', isMissing && 'missing')}>
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

  /** Dispatches a row update; avoids the computed-property type ambiguity. */
  function writeRows(nextRows: Row[]): void {
    if (field === 'params') {
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
      <div className="kv-header">
        <div />
        <div>KEY</div>
        <div>VALUE</div>
        <div>DESCRIPTION</div>
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
                  aria-label="Delete row"
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
