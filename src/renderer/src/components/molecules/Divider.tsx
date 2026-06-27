/**
 * Divider — hand-rolled, presentational, pointer-event WAI-ARIA splitter.
 *
 * A reusable drag handle that separates two resizable panes. It is purely
 * presentational and store-free: the mounter supplies the current `value` and
 * wires `onCommit` to whatever store action it owns. This keeps the component
 * decoupled from any layout-state implementation.
 *
 * ## Drag interaction
 *
 * Drag is handled with the Pointer Events API so capture continues outside the
 * window. During a drag, the mounter-supplied `cssVar` custom property is written
 * directly onto `document.documentElement` inside a `requestAnimationFrame`
 * callback — no React state is updated per frame (≤16 ms frame NFR). On
 * `pointerup` the final value is clamped to `[min, max]` and committed via
 * `onCommit`.
 *
 * ## Keyboard interaction (WAI-ARIA window splitter pattern)
 *
 * | Key                        | Orientation | Behaviour                    |
 * |----------------------------|-------------|------------------------------|
 * | ArrowLeft / ArrowRight     | vertical    | Decrease / increase by step  |
 * | ArrowUp / ArrowDown        | horizontal  | Decrease / increase by step  |
 * | Home                       | both        | Commit `min`                 |
 * | End                        | both        | Commit `max`                 |
 *
 * ## WAI-ARIA
 *
 * `role="separator"` with `aria-orientation`, `aria-valuenow`, `aria-valuemin`,
 * and `aria-valuemax` matches the WAI-ARIA Window Splitter design pattern.
 *
 * ## Constraints
 *
 * - No store import — caller owns state via `onCommit`.
 * - No inline `style={{...}}` JSX attributes (AC-14). The only imperative style
 *   write is `document.documentElement.style.setProperty(cssVar, …)` during
 *   drag; that is a DOM mutation, not a JSX inline-style attribute.
 * - No `electron` or `node:` imports — renderer-only (§2.1 / §2.3).
 * - Hand-rolled — zero resize-library dependencies, matching the Tabs precedent.
 *
 * @module Divider
 */

import './Divider.css'

import { useEffect, useRef, type JSX } from 'react'
import { cx } from '@renderer/lib/cx'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Props for the {@link Divider} component.
 *
 * The mounter wires `value`, `onCommit`, and `cssVar` to its layout-state
 * store; `Divider` itself never reads or writes any store.
 *
 * Satisfies AC-4 (sidebar drag clamp), AC-9 (role=separator + aria-valuenow
 * + keyboard resize), AC-16 (pane drag clamp).
 */
export interface DividerProps {
  /**
   * Whether the split axis is vertical (the divider bar is a vertical line,
   * dragged left/right) or horizontal (bar is a horizontal line, dragged
   * up/down).
   */
  orientation: 'vertical' | 'horizontal'

  /**
   * Current position value in the mounter's value-space. For the sidebar this
   * is pixels (1:1 with pointer pixels). For the pane split this is a unitless
   * ratio (0–1); pixel↔value mapping is supplied via `getDragExtent`.
   * Reflected as `aria-valuenow`.
   */
  value: number

  /**
   * Minimum allowed position. Reflected as `aria-valuemin`.
   * `onCommit` is always called with a value ≥ `min`.
   */
  min: number

  /**
   * Maximum allowed position. Reflected as `aria-valuemax`.
   * `onCommit` is always called with a value ≤ `max`.
   */
  max: number

  /**
   * Accessible label for the splitter element.
   * Passed directly to `aria-label` on the `role="separator"` element.
   */
  ariaLabel: string

  /**
   * CSS custom-property name (including the leading `--`) written to
   * `document.documentElement` during drag, e.g. `"--sidebar-width"`.
   * This lets CSS layout respond at native frame-rate with zero React renders.
   */
  cssVar: string

  /**
   * Called with the clamped final value when the user finishes a drag
   * (`pointerup`) or commits via keyboard. The Divider always clamps to
   * `[min, max]` before calling `onCommit` — the mounter never needs to
   * re-clamp.
   */
  onCommit: (value: number) => void

  /**
   * Unit string appended to the numeric value when writing the CSS custom
   * property. Defaults to `'px'` for pixel-length vars (e.g. `--sidebar-width`
   * → `"260px"`). Pass `''` for a unitless var (e.g. `--pane-ratio` → `"0.5"`)
   * so that `flex: var(--pane-ratio)` receives a bare number as its flex-grow
   * factor rather than an invalid `"0.5px"`.
   */
  unit?: string

  /**
   * Returns the pixel length of the resize axis (the full extent of the
   * container the value spans). When provided and non-zero, the raw pointer
   * pixel delta is divided by this extent to produce the value-space delta,
   * enabling ratio-valued Dividers (e.g. `--pane-ratio` in 0–1 space).
   *
   * Called once per pointer-move and once on pointer-up (measured live so the
   * mapping stays correct after window resize).
   *
   * If absent, returns `null`, or returns `0`, the Divider falls back to a
   * 1:1 pixel→value mapping (the default sidebar behaviour).
   */
  getDragExtent?: () => number | null

  /**
   * Value added (or subtracted) per arrow-key press.
   *
   * Defaults to `8` (pixels) — correct for a pixel-valued sidebar Divider.
   * Pass a smaller value (e.g. `0.02`) for a ratio-valued Divider so that
   * a single key-press moves the split by ~2% of the container height.
   */
  keyboardStep?: number

  /** Additional CSS class applied to the outermost element. */
  className?: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Pixels moved per keyboard arrow-key press. */
const KEYBOARD_STEP = 8

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Clamps `v` to the inclusive range `[lo, hi]`.
 *
 * @param v - The value to clamp.
 * @param lo - Lower bound (inclusive).
 * @param hi - Upper bound (inclusive).
 */
function clamp(v: number, lo: number, hi: number): number {
  if (!Number.isFinite(v)) return lo
  return Math.min(Math.max(v, lo), hi)
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Reusable, presentational drag-handle that separates two resizable panes.
 *
 * The mounter supplies the current `value` and handles `onCommit`. The
 * Divider handles all pointer and keyboard interactions internally and always
 * clamps before calling `onCommit`.
 *
 * @param props - See {@link DividerProps}.
 *
 * AC-4: sidebar drag clamp (vertical orientation).
 * AC-9: role=separator, aria-valuenow, keyboard resize.
 * AC-16: pane drag clamp (horizontal orientation).
 */
export function Divider({
  orientation,
  value,
  min,
  max,
  ariaLabel,
  cssVar,
  onCommit,
  unit = 'px',
  getDragExtent,
  keyboardStep = KEYBOARD_STEP,
  className
}: DividerProps): JSX.Element {
  /**
   * Ref holding drag state so no React re-renders occur during pointer move.
   * `startPointer` is the client coordinate at pointerdown.
   * `startValue` is the `value` prop at pointerdown.
   * `rafId` tracks a pending rAF so we cancel before scheduling a new one.
   */
  const dragRef = useRef<{
    startPointer: number
    startValue: number
    rafId: number | null
  } | null>(null)

  /**
   * Cancel any pending rAF on unmount so it does not fire into a stale
   * closure. This is a real path: the sidebar can be collapsed (Cmd-B) while
   * the Divider is mid-drag, which unmounts this component.
   */
  useEffect(() => {
    return () => {
      const drag = dragRef.current
      if (drag?.rafId !== null && drag?.rafId !== undefined) {
        cancelAnimationFrame(drag.rafId)
      }
    }
  }, [])

  // -------------------------------------------------------------------------
  // Pointer handlers
  // -------------------------------------------------------------------------

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>): void {
    // Only respond to the primary pointer (left mouse / single touch).
    if (event.button !== 0 && event.pointerType === 'mouse') return

    event.preventDefault()
    ;(event.currentTarget as HTMLDivElement).setPointerCapture(event.pointerId)

    dragRef.current = {
      startPointer: orientation === 'vertical' ? event.clientX : event.clientY,
      startValue: value,
      rafId: null
    }
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>): void {
    const drag = dragRef.current
    if (drag === null) return

    const currentPointer = orientation === 'vertical' ? event.clientX : event.clientY
    const pixelDelta = currentPointer - drag.startPointer
    const extent = getDragExtent ? getDragExtent() : null
    const valueDelta = extent ? pixelDelta / extent : pixelDelta
    const candidate = drag.startValue + valueDelta

    // Cancel any pending rAF to avoid stacking frames.
    if (drag.rafId !== null) {
      cancelAnimationFrame(drag.rafId)
    }

    drag.rafId = requestAnimationFrame(() => {
      drag.rafId = null
      // Write the CSS custom property directly — no React state update.
      document.documentElement.style.setProperty(cssVar, `${candidate}${unit}`)
    })
  }

  function handlePointerUp(event: React.PointerEvent<HTMLDivElement>): void {
    const drag = dragRef.current
    if (drag === null) return

    // Cancel any still-pending rAF.
    if (drag.rafId !== null) {
      cancelAnimationFrame(drag.rafId)
    }

    dragRef.current = null
    ;(event.currentTarget as HTMLDivElement).releasePointerCapture(event.pointerId)

    const currentPointer = orientation === 'vertical' ? event.clientX : event.clientY
    const pixelDelta = currentPointer - drag.startPointer
    const extent = getDragExtent ? getDragExtent() : null
    const valueDelta = extent ? pixelDelta / extent : pixelDelta
    const clamped = clamp(drag.startValue + valueDelta, min, max)

    // Ensure the CSS var is at the committed (clamped) value.
    document.documentElement.style.setProperty(cssVar, `${clamped}${unit}`)

    onCommit(clamped)
  }

  /**
   * Handles `pointercancel` — fired when the OS steals input (e.g. gesture
   * conflict, scroll hijack). A cancelled gesture commits nothing: the CSS var
   * is reset to the last committed `value` and `dragRef` is nulled out without
   * calling `onCommit`.
   */
  function handlePointerCancel(event: React.PointerEvent<HTMLDivElement>): void {
    const drag = dragRef.current
    if (drag === null) return

    // Cancel any pending rAF so it does not fire into a stale closure.
    if (drag.rafId !== null) {
      cancelAnimationFrame(drag.rafId)
    }

    dragRef.current = null

    // Release capture if the browser still holds it.
    const el = event.currentTarget as HTMLDivElement
    if (el.hasPointerCapture(event.pointerId)) {
      el.releasePointerCapture(event.pointerId)
    }

    // Reset the CSS var to the last committed value — do NOT call onCommit.
    document.documentElement.style.setProperty(cssVar, `${value}${unit}`)
  }

  // -------------------------------------------------------------------------
  // Keyboard handler (WAI-ARIA window splitter pattern)
  // -------------------------------------------------------------------------

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>): void {
    const isVertical = orientation === 'vertical'
    let delta = 0

    switch (event.key) {
      case 'ArrowLeft':
        if (!isVertical) return
        delta = -keyboardStep
        break
      case 'ArrowRight':
        if (!isVertical) return
        delta = keyboardStep
        break
      case 'ArrowUp':
        if (isVertical) return
        delta = -keyboardStep
        break
      case 'ArrowDown':
        if (isVertical) return
        delta = keyboardStep
        break
      case 'Home': {
        event.preventDefault()
        document.documentElement.style.setProperty(cssVar, `${min}${unit}`)
        onCommit(min)
        return
      }
      case 'End': {
        event.preventDefault()
        document.documentElement.style.setProperty(cssVar, `${max}${unit}`)
        onCommit(max)
        return
      }
      default:
        return // Do not preventDefault for unhandled keys.
    }

    event.preventDefault()
    const clamped = clamp(value + delta, min, max)
    document.documentElement.style.setProperty(cssVar, `${clamped}${unit}`)
    onCommit(clamped)
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div
      role="separator"
      aria-orientation={orientation}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-label={ariaLabel}
      tabIndex={0}
      className={cx('divider', `divider--${orientation}`, className)}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      onKeyDown={handleKeyDown}
    >
      {/* Inner visual handle — provides a narrow drag-target affordance. */}
      <div className="divider__handle" aria-hidden="true" />
    </div>
  )
}
