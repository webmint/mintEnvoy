/**
 * Shell.test.tsx
 *
 * Interaction and contract tests for the Shell organism and its constituent
 * sub-organisms (Divider, Sidebar, PaneSplit, Titlebar, Statusbar).
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## Test surface
 *
 * - jsdom setup:   pointer-capture stubs; full DOM cleanup after each test.
 * - Divider:       drag clamp, keyboard, cancel, CSS-var units, px→ratio bug regression.
 * - Titlebar:      toggle click, toggleRef wiring, active class, smoke (no toggleRef).
 * - Statusbar:     role=status, children slot, className forwarding.
 * - Shell slots:   sidebar/tabs/panes/modals per-slot rendering; partial/absent cases.
 * - Shell effects: store→<html> data attrs + CSS vars; effect re-run; CSS-var unit form.
 * - Shell behaviors: Cmd-B (meta + ctrl), collapse/focus directional, window-resize clamp.
 * - App-level:     toast text routed; Shell present; no PrimitivesDemo content.
 * - Cleanup:       resize + Cmd-B after unmount do NOT mutate the store.
 */

import { render, screen, act, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Shell } from '@renderer/components/organisms/Shell'
import { Sidebar } from '@renderer/components/organisms/Sidebar'
import { Titlebar } from '@renderer/components/organisms/Titlebar'
import { Statusbar } from '@renderer/components/organisms/Statusbar'
import { PaneSplit } from '@renderer/components/organisms/PaneSplit'
import { Divider } from '@renderer/components/organisms/Divider'
import {
  settingsStore,
  SIDEBAR_MIN,
  SIDEBAR_MAX,
  PANE_MIN,
  PANE_MAX
} from '@renderer/lib/settingsStore'
import App from '@renderer/App'
import { toast } from '@renderer/lib/toastStore'

// ---------------------------------------------------------------------------
// jsdom setup: stub pointer-capture APIs (jsdom lacks them)
// ---------------------------------------------------------------------------

beforeAll(() => {
  Object.assign(HTMLElement.prototype, {
    setPointerCapture: vi.fn(),
    releasePointerCapture: vi.fn(),
    hasPointerCapture: vi.fn(() => false)
  })
})

afterAll(() => {
  // Restore prototype stubs (cast through unknown to satisfy TS strict delete)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const proto = HTMLElement.prototype as any
  delete proto.setPointerCapture
  delete proto.releasePointerCapture
  delete proto.hasPointerCapture
})

// ---------------------------------------------------------------------------
// DOM + store cleanup between tests
//
// NOTE: Two SEPARATE afterEach steps — the store reset() does NOT clean the
// DOM. Both survivors must be cleaned independently:
//   1. store reset() — restores all store fields to defaults.
//   2. HTML data-attrs — survive React unmount on the global <html>.
//   3. CSS vars — also survive React unmount on the global <html>.
// ---------------------------------------------------------------------------

afterEach(() => {
  // 1. Reset store
  settingsStore.getState().reset()
})

afterEach(() => {
  // 2. Remove data-attrs written by Shell's Effect 1
  delete document.documentElement.dataset.theme
  delete document.documentElement.dataset.accent
  delete document.documentElement.dataset.mstyle

  // 3. Remove CSS vars written by Shell's Effect 2 and by Divider during drag
  document.documentElement.style.removeProperty('--sidebar-width')
  document.documentElement.style.removeProperty('--pane-ratio')
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Fire a pointer-down/move/up sequence on an element to simulate a drag.
 *
 * jsdom PITFALL: jsdom does not implement `PointerEvent` as a constructor, so
 * `fireEvent.pointerDown/Move/Up` fall back to `new Event(...)` which does NOT
 * carry `clientX`/`clientY` (those are `MouseEvent` fields). This leaves
 * `event.clientX`/`event.clientY` as `undefined`, causing NaN in the Divider
 * pixel-delta calculation.
 *
 * Workaround: dispatch `MouseEvent` instances (which jsdom DOES support with
 * correct `clientX`/`clientY`) with the pointer event type name. React reads
 * the event's type name to route to the right synthetic handler, and reads
 * `clientX`/`clientY` from the native event — so this matches the Divider's
 * handler signature.
 *
 * NOTE: The Divider registers onPointerMove as a JSX prop ON the separator
 * element (not as a window listener), so dispatching events directly on the
 * element correctly reaches the handler. If the Divider ever moved its
 * pointer-move listener to window, these jsdom drag tests would need
 * window-level dispatch instead.
 */
function simulateDrag(
  el: HTMLElement,
  opts: {
    axis: 'x' | 'y'
    start: number
    end: number
  }
): void {
  const { axis, start, end } = opts
  const makeEvent = (type: string, coord: number): MouseEvent => {
    const clientX = axis === 'x' ? coord : 0
    const clientY = axis === 'y' ? coord : 0
    return new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      button: 0,
      buttons: 1,
      clientX,
      clientY
    })
  }

  el.dispatchEvent(makeEvent('pointerdown', start))
  el.dispatchEvent(makeEvent('pointermove', end))
  el.dispatchEvent(makeEvent('pointerup', end))
}

// ---------------------------------------------------------------------------
// Divider — CSS-var unit assertions
// ---------------------------------------------------------------------------

describe('Divider — CSS-var unit form', () => {
  it('writes --sidebar-width as px-suffixed string (e.g. "260px")', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="vertical"
        value={260}
        min={200}
        max={520}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        unit="px"
      />
    )

    const separator = screen.getByRole('separator')
    // Fire Home key to trigger CSS-var write at min=200
    fireEvent.keyDown(separator, { key: 'Home' })

    const val = document.documentElement.style.getPropertyValue('--sidebar-width')
    // Must end with "px" — not a bare number
    expect(val).toMatch(/px$/)
    expect(val).toBe('200px')
  })

  it('writes --pane-ratio as a bare unitless number (e.g. "0.5", NOT "0.5px")', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={0.5}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
      />
    )

    const separator = screen.getByRole('separator')
    fireEvent.keyDown(separator, { key: 'Home' })

    const val = document.documentElement.style.getPropertyValue('--pane-ratio')
    // Must NOT end with any unit suffix
    expect(val).not.toMatch(/px$/)
    expect(val).toBe(String(PANE_MIN))
  })
})

// ---------------------------------------------------------------------------
// Divider — keyboard step magnitude as DISTINCT assertions
// ---------------------------------------------------------------------------

describe('Divider — keyboard step magnitudes', () => {
  it('sidebar ArrowRight commits value + 8px step', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="vertical"
        value={300}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        unit="px"
      />
    )

    const separator = screen.getByRole('separator')
    fireEvent.keyDown(separator, { key: 'ArrowRight' })

    // Default keyboard step is 8px
    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(308)
  })

  it('pane ArrowDown commits value + 0.02 ratio step', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={0.5}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
        keyboardStep={0.02}
      />
    )

    const separator = screen.getByRole('separator')
    fireEvent.keyDown(separator, { key: 'ArrowDown' })

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    // 0.5 + 0.02 = 0.52; allow small float epsilon
    expect(committed).toBeCloseTo(0.52, 5)
  })
})

// ---------------------------------------------------------------------------
// Divider — clamp at exact bounds, below-min, above-max, NaN
// ---------------------------------------------------------------------------

describe('Divider — keyboard clamp (sidebar/vertical)', () => {
  function renderSidebarDivider(value: number): {
    onCommit: ReturnType<typeof vi.fn>
    separator: HTMLElement
  } {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="vertical"
        value={value}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        unit="px"
      />
    )
    return { onCommit, separator: screen.getByRole('separator') }
  }

  it('Home commits exact min bound (200)', () => {
    const { onCommit, separator } = renderSidebarDivider(300)
    fireEvent.keyDown(separator, { key: 'Home' })
    expect(onCommit).toHaveBeenCalledWith(SIDEBAR_MIN)
    expect(document.documentElement.style.getPropertyValue('--sidebar-width')).toBe(
      `${SIDEBAR_MIN}px`
    )
  })

  it('End commits exact max bound (520)', () => {
    const { onCommit, separator } = renderSidebarDivider(300)
    fireEvent.keyDown(separator, { key: 'End' })
    expect(onCommit).toHaveBeenCalledWith(SIDEBAR_MAX)
    expect(document.documentElement.style.getPropertyValue('--sidebar-width')).toBe(
      `${SIDEBAR_MAX}px`
    )
  })

  it('ArrowLeft at min is clamped to min (no negative)', () => {
    const { onCommit, separator } = renderSidebarDivider(SIDEBAR_MIN)
    fireEvent.keyDown(separator, { key: 'ArrowLeft' })
    expect(onCommit).toHaveBeenCalledWith(SIDEBAR_MIN)
  })

  it('ArrowRight at max is clamped to max (no overflow)', () => {
    const { onCommit, separator } = renderSidebarDivider(SIDEBAR_MAX)
    fireEvent.keyDown(separator, { key: 'ArrowRight' })
    expect(onCommit).toHaveBeenCalledWith(SIDEBAR_MAX)
  })

  it('wrong-axis arrows (ArrowUp/ArrowDown on vertical) are no-ops', () => {
    const { onCommit, separator } = renderSidebarDivider(300)
    fireEvent.keyDown(separator, { key: 'ArrowUp' })
    fireEvent.keyDown(separator, { key: 'ArrowDown' })
    expect(onCommit).not.toHaveBeenCalled()
  })
})

describe('Divider — keyboard clamp (pane/horizontal)', () => {
  function renderPaneDivider(value: number): {
    onCommit: ReturnType<typeof vi.fn>
    separator: HTMLElement
  } {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={value}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
        keyboardStep={0.02}
      />
    )
    return { onCommit, separator: screen.getByRole('separator') }
  }

  it('Home commits exact min bound (0.15)', () => {
    const { onCommit, separator } = renderPaneDivider(0.5)
    fireEvent.keyDown(separator, { key: 'Home' })
    expect(onCommit).toHaveBeenCalledWith(PANE_MIN)
    expect(document.documentElement.style.getPropertyValue('--pane-ratio')).toBe(String(PANE_MIN))
  })

  it('End commits exact max bound (0.85)', () => {
    const { onCommit, separator } = renderPaneDivider(0.5)
    fireEvent.keyDown(separator, { key: 'End' })
    expect(onCommit).toHaveBeenCalledWith(PANE_MAX)
    expect(document.documentElement.style.getPropertyValue('--pane-ratio')).toBe(String(PANE_MAX))
  })

  it('ArrowUp at min is clamped to min (no underflow)', () => {
    const { onCommit, separator } = renderPaneDivider(PANE_MIN)
    fireEvent.keyDown(separator, { key: 'ArrowUp' })
    expect(onCommit).toHaveBeenCalledWith(PANE_MIN)
  })

  it('ArrowDown at max is clamped to max (no overflow)', () => {
    const { onCommit, separator } = renderPaneDivider(PANE_MAX)
    fireEvent.keyDown(separator, { key: 'ArrowDown' })
    expect(onCommit).toHaveBeenCalledWith(PANE_MAX)
  })

  it('wrong-axis arrows (ArrowLeft/ArrowRight on horizontal) are no-ops', () => {
    const { onCommit, separator } = renderPaneDivider(0.5)
    fireEvent.keyDown(separator, { key: 'ArrowLeft' })
    fireEvent.keyDown(separator, { key: 'ArrowRight' })
    expect(onCommit).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Divider — non-primary mouse button does not start drag
// ---------------------------------------------------------------------------

describe('Divider — non-primary button does not start drag', () => {
  it('button=2 (right-click) does not initiate a drag sequence', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="vertical"
        value={300}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        unit="px"
      />
    )

    const separator = screen.getByRole('separator')
    // Right mouse button (button=2) with pointerType='mouse' — should not start drag.
    //
    // jsdom lacks PointerEvent so we simulate it with MouseEvent events, but
    // MouseEvent doesn't have a `pointerType` property. The Divider guard is:
    //   if (event.button !== 0 && event.pointerType === 'mouse') return
    // We patch `pointerType` onto the event to make it behave as a real PointerEvent.
    const makeRightClickEvent = (type: string, clientX: number): MouseEvent => {
      const evt = new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        button: 2,
        buttons: 2,
        clientX
      })
      Object.defineProperty(evt, 'pointerType', { value: 'mouse', configurable: true })
      return evt
    }

    separator.dispatchEvent(makeRightClickEvent('pointerdown', 0))
    separator.dispatchEvent(makeRightClickEvent('pointermove', 100))
    separator.dispatchEvent(makeRightClickEvent('pointerup', 100))

    expect(onCommit).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Divider — pointercancel resets CSS var without calling onCommit
// ---------------------------------------------------------------------------

describe('Divider — pointercancel mid-drag', () => {
  it('cancels without calling onCommit and resets CSS var to committed value', () => {
    const onCommit = vi.fn()
    const startValue = 300

    render(
      <Divider
        orientation="vertical"
        value={startValue}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        unit="px"
      />
    )

    const separator = screen.getByRole('separator')
    // Use MouseEvent to ensure clientX is correctly set (jsdom lacks PointerEvent)
    separator.dispatchEvent(
      new MouseEvent('pointerdown', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 1,
        clientX: 0
      })
    )
    separator.dispatchEvent(
      new MouseEvent('pointermove', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 1,
        clientX: 50
      })
    )
    // Now cancel the drag
    separator.dispatchEvent(new MouseEvent('pointercancel', { bubbles: true, cancelable: true }))

    // onCommit must NOT have been called
    expect(onCommit).not.toHaveBeenCalled()

    // CSS var must reset to committed value (the value prop = 300)
    // Note: the var is set synchronously in handlePointerCancel
    const cssVal = document.documentElement.style.getPropertyValue('--sidebar-width')
    expect(cssVal).toBe(`${startValue}px`)
  })
})

// ---------------------------------------------------------------------------
// Divider — aria-valuenow tracks the value prop
// ---------------------------------------------------------------------------

describe('Divider — aria-valuenow', () => {
  it('reflects the value prop on initial render', () => {
    render(
      <Divider
        orientation="vertical"
        value={350}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={vi.fn()}
        unit="px"
      />
    )

    expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '350')
  })

  it('updates aria-valuenow when value prop changes via re-render', () => {
    const { rerender } = render(
      <Divider
        orientation="vertical"
        value={350}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={vi.fn()}
        unit="px"
      />
    )

    rerender(
      <Divider
        orientation="vertical"
        value={400}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={vi.fn()}
        unit="px"
      />
    )

    expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow', '400')
  })
})

// ---------------------------------------------------------------------------
// Divider — pane drag px→ratio conversion (the bug regression)
//
// CRITICAL: jsdom's getBoundingClientRect().height returns 0 by default which
// would bypass the px→ratio conversion (falling back to 1:1 pixel mapping).
// We test the Divider in isolation with a mocked getDragExtent so the
// conversion is always exercised.
// ---------------------------------------------------------------------------

describe('Divider — pane drag px→ratio conversion (regression: bug fix)', () => {
  const EXTENT = 800 // simulated container height in pixels

  function renderPaneDividerWithExtent(startValue = 0.5): {
    onCommit: ReturnType<typeof vi.fn>
    separator: HTMLElement
  } {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={startValue}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
        keyboardStep={0.02}
        getDragExtent={() => EXTENT}
      />
    )
    return { onCommit, separator: screen.getByRole('separator') }
  }

  it('PROPORTIONAL: dragging 80px on an 800px extent commits paneRatio ≈ start + 0.1 (NOT start + 80)', () => {
    const startValue = 0.5
    const { onCommit, separator } = renderPaneDividerWithExtent(startValue)

    simulateDrag(separator, { axis: 'y', start: 0, end: 80 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    // With extent=800, delta=80px → valueDelta = 80/800 = 0.1
    expect(committed).toBeCloseTo(startValue + 0.1, 3)
    // Crucially, it must NOT be start + 80 (the bug)
    expect(committed).not.toBeCloseTo(startValue + 80, 1)
  })

  it('SMALL drag (2px on 800px extent) does NOT jump to a clamp bound', () => {
    const startValue = 0.5
    const { onCommit, separator } = renderPaneDividerWithExtent(startValue)

    simulateDrag(separator, { axis: 'y', start: 0, end: 2 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    // 2px / 800px = 0.0025 delta → committed ≈ 0.5025, nowhere near 0.85 bound
    expect(committed).toBeGreaterThan(0.5)
    expect(committed).toBeLessThan(0.51)
  })

  it('getDragExtent returning 0 falls back to 1:1 (no NaN/Infinity in store)', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={0.5}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
        keyboardStep={0.02}
        getDragExtent={() => 0}
      />
    )

    const separator = screen.getByRole('separator')
    // Drag 5px — with extent=0, fallback is 1:1, so delta = 5
    // clampPaneRatio will clamp the resulting 0.5+5=5.5 to PANE_MAX=0.85
    simulateDrag(separator, { axis: 'y', start: 0, end: 5 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    // Must be a finite number
    expect(Number.isFinite(committed)).toBe(true)
    // Must be within valid range (clamped at PANE_MAX)
    expect(committed).toBeGreaterThanOrEqual(PANE_MIN)
    expect(committed).toBeLessThanOrEqual(PANE_MAX)
  })

  it('getDragExtent returning null falls back to 1:1 (no NaN reaches the commit)', () => {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={0.5}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
        keyboardStep={0.02}
        getDragExtent={() => null}
      />
    )

    const separator = screen.getByRole('separator')
    simulateDrag(separator, { axis: 'y', start: 0, end: 5 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    expect(Number.isFinite(committed)).toBe(true)
    // Must also be within valid range — catches a missing clamp backstop
    expect(committed).toBeGreaterThanOrEqual(PANE_MIN)
    expect(committed).toBeLessThanOrEqual(PANE_MAX)
  })

  it('drag clamps to PANE_MAX when result would exceed bounds', () => {
    const { onCommit, separator } = renderPaneDividerWithExtent(0.5)

    // Drag 400px down on 800px extent → ratio +0.5, total 1.0, must clamp to PANE_MAX
    simulateDrag(separator, { axis: 'y', start: 0, end: 400 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(PANE_MAX)
  })

  it('drag clamps to PANE_MIN when result would go below bounds', () => {
    const { onCommit, separator } = renderPaneDividerWithExtent(0.5)

    // Drag 400px up → ratio -0.5, total 0.0, must clamp to PANE_MIN
    simulateDrag(separator, { axis: 'y', start: 0, end: -400 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(PANE_MIN)
  })

  it('mid-drag CSS var is UNCLAMPED; only the committed (pointerup) value is clamped', () => {
    // Use fake timers so we can manually flush the rAF to read the CSS var
    // at the exact moment after pointermove but before pointerup.
    vi.useFakeTimers()

    const onCommit = vi.fn()
    render(
      <Divider
        orientation="horizontal"
        value={0.5}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={onCommit}
        unit=""
        keyboardStep={0.02}
        getDragExtent={() => EXTENT}
      />
    )

    const separator = screen.getByRole('separator')

    // pointerdown at y=0 initialises drag with startValue=0.5
    separator.dispatchEvent(
      new MouseEvent('pointerdown', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 1,
        clientY: 0
      })
    )

    // pointermove 680px down → candidate = 0.5 + 680/800 = 1.35, which is > PANE_MAX (0.85)
    separator.dispatchEvent(
      new MouseEvent('pointermove', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 1,
        clientY: 680
      })
    )

    // Flush the pending rAF so the CSS var is written (with the unclamped candidate)
    vi.runAllTimers()

    const midDragVar = document.documentElement.style.getPropertyValue('--pane-ratio')
    const midDragValue = Number(midDragVar)

    // Mid-drag CSS var must be the UNCLAMPED candidate (> PANE_MAX)
    // This distinguishes "live drag reflects raw position" from "always clamped"
    expect(midDragValue).toBeGreaterThan(PANE_MAX)

    // Now release — committed value must be clamped to PANE_MAX
    separator.dispatchEvent(
      new MouseEvent('pointerup', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 0,
        clientY: 680
      })
    )

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    expect(committed).toBe(PANE_MAX)

    vi.useRealTimers()
  })
})

// ---------------------------------------------------------------------------
// Divider — cancelAnimationFrame called on unmount mid-drag
// ---------------------------------------------------------------------------

describe('Divider — cancelAnimationFrame on unmount', () => {
  it('calls cancelAnimationFrame if rAF is pending at unmount time', () => {
    // Use fake timers so the rAF callback does NOT flush before unmount;
    // this leaves drag.rafId non-null, making the cleanup assertion meaningful.
    vi.useFakeTimers()

    const cancelSpy = vi.spyOn(globalThis, 'cancelAnimationFrame')

    const { unmount } = render(
      <Divider
        orientation="vertical"
        value={300}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={vi.fn()}
        unit="px"
      />
    )

    const separator = screen.getByRole('separator')
    // pointerdown initialises drag state
    separator.dispatchEvent(
      new MouseEvent('pointerdown', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 1,
        clientX: 0
      })
    )
    // pointermove schedules an rAF; with fake timers it stays pending
    separator.dispatchEvent(
      new MouseEvent('pointermove', {
        bubbles: true,
        cancelable: true,
        button: 0,
        buttons: 1,
        clientX: 50
      })
    )

    // Unmount while the rAF is still pending — the useEffect cleanup must cancel it.
    unmount()

    // The cleanup must have called cancelAnimationFrame with the pending id.
    // This assertion FAILS if the cleanup is removed from the component.
    expect(cancelSpy).toHaveBeenCalled()

    cancelSpy.mockRestore()
    vi.useRealTimers()
  })
})

// ---------------------------------------------------------------------------
// Divider — className prop is forwarded
// ---------------------------------------------------------------------------

describe('Divider — className forwarding', () => {
  it('forwards className onto the separator element', () => {
    render(
      <Divider
        orientation="vertical"
        value={300}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={vi.fn()}
        unit="px"
        className="my-custom-divider"
      />
    )

    const separator = screen.getByRole('separator')
    expect(separator).toHaveClass('my-custom-divider')
    // Base class still present alongside custom class
    expect(separator).toHaveClass('divider')
  })
})

// ---------------------------------------------------------------------------
// Sidebar — renders children and forwards className
// ---------------------------------------------------------------------------

describe('Sidebar — slot and className', () => {
  it('renders children inside the sidebar when expanded', () => {
    render(
      <Sidebar>
        <span data-testid="sb-child">Nav</span>
      </Sidebar>
    )
    expect(screen.getByTestId('sb-child')).toBeInTheDocument()
  })

  it('forwards className onto the <aside> element', () => {
    render(
      <Sidebar className="my-sidebar">
        <span>Nav</span>
      </Sidebar>
    )
    const aside = document.querySelector('aside.sidebar')
    expect(aside).toHaveClass('my-sidebar')
  })

  it('does not render children or separator when sidebarCollapsed is true', () => {
    act(() => {
      settingsStore.getState().toggleSidebar() // collapse
    })

    render(
      <Sidebar>
        <span data-testid="sb-child">Nav</span>
      </Sidebar>
    )
    expect(screen.queryByTestId('sb-child')).toBeNull()
    expect(screen.queryByRole('separator')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// PaneSplit — className forwarding
// ---------------------------------------------------------------------------

describe('PaneSplit — className forwarding', () => {
  it('forwards className onto the container element', () => {
    render(<PaneSplit className="my-pane-split" />)
    const container = document.querySelector('.pane-split')
    expect(container).toHaveClass('my-pane-split')
  })
})

// ---------------------------------------------------------------------------
// Titlebar
// ---------------------------------------------------------------------------

describe('Titlebar', () => {
  it('clicking the sidebar-toggle button toggles sidebarCollapsed in the store', async () => {
    const user = userEvent.setup()
    render(<Titlebar />)

    expect(settingsStore.getState().sidebarCollapsed).toBe(false)

    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })
    await user.click(toggleBtn)

    expect(settingsStore.getState().sidebarCollapsed).toBe(true)
  })

  it('toggleRef.current points at EXACTLY the sidebar-toggle button', () => {
    const toggleRef = { current: null as HTMLButtonElement | null }
    render(<Titlebar toggleRef={toggleRef} />)

    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })
    expect(toggleRef.current).toBe(toggleBtn)
  })

  it('toggle button carries titlebar__icon-btn--active class WHILE sidebarCollapsed is true', () => {
    act(() => {
      settingsStore.getState().toggleSidebar() // collapse
    })

    render(<Titlebar />)

    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })
    expect(toggleBtn).toHaveClass('titlebar__icon-btn--active')
  })

  it('toggle button does NOT carry titlebar__icon-btn--active class when sidebar is expanded', () => {
    // Default state is expanded
    render(<Titlebar />)

    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })
    expect(toggleBtn).not.toHaveClass('titlebar__icon-btn--active')
  })

  it('smoke: renders without error when toggleRef is not provided (optional prop)', () => {
    expect(() => render(<Titlebar />)).not.toThrow()
    expect(screen.getByRole('button', { name: /toggle sidebar/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Statusbar
// ---------------------------------------------------------------------------

describe('Statusbar', () => {
  it('renders with role="status" and accessible name "Status bar"', () => {
    render(<Statusbar />)
    expect(screen.getByRole('status', { name: /status bar/i })).toBeInTheDocument()
  })

  it('renders arbitrary children inside the status region', () => {
    render(
      <Statusbar>
        <span data-testid="status-child">v1.0</span>
      </Statusbar>
    )
    expect(screen.getByTestId('status-child')).toBeInTheDocument()
    // Child is inside the status region
    const statusEl = screen.getByRole('status', { name: /status bar/i })
    expect(statusEl).toContainElement(screen.getByTestId('status-child'))
  })

  it('merges className alongside the statusbar BEM root class', () => {
    render(<Statusbar className="my-statusbar" />)
    const footer = document.querySelector('footer.statusbar')
    expect(footer).toHaveClass('my-statusbar')
    expect(footer).toHaveClass('statusbar')
  })
})

// ---------------------------------------------------------------------------
// Shell — slot rendering (AC-7)
// ---------------------------------------------------------------------------

describe('Shell — slot rendering (AC-7)', () => {
  it('renders arbitrary children in the sidebar slot', () => {
    render(<Shell sidebar={<span data-testid="slot-sidebar">SidebarContent</span>} />)
    expect(screen.getByTestId('slot-sidebar')).toBeInTheDocument()
  })

  it('renders arbitrary children in the tabs slot inside shell__tabs wrapper', () => {
    render(<Shell tabs={<span data-testid="slot-tabs">TabsContent</span>} />)
    const tabsEl = screen.getByTestId('slot-tabs')
    expect(tabsEl).toBeInTheDocument()
    // tabs slot is wrapped in shell__tabs
    expect(tabsEl.closest('.shell__tabs')).toBeInTheDocument()
  })

  it('does NOT render shell__tabs wrapper when tabs prop is absent', () => {
    render(<Shell />)
    expect(document.querySelector('.shell__tabs')).toBeNull()
  })

  it('renders arbitrary children in panes.request slot', () => {
    render(<Shell panes={{ request: <span data-testid="slot-request">RequestContent</span> }} />)
    expect(screen.getByTestId('slot-request')).toBeInTheDocument()
  })

  it('renders arbitrary children in panes.response slot', () => {
    render(<Shell panes={{ response: <span data-testid="slot-response">ResponseContent</span> }} />)
    expect(screen.getByTestId('slot-response')).toBeInTheDocument()
  })

  it('renders modals at the Shell root level (not inside workspace or sidebar)', () => {
    render(<Shell modals={<div data-testid="slot-modal">ModalContent</div>} />)
    const modal = screen.getByTestId('slot-modal')
    expect(modal).toBeInTheDocument()
    // modals must be a direct child of .shell root
    expect(modal.parentElement).toHaveClass('shell')
  })

  it('renders only request when response is absent (partial panes)', () => {
    render(<Shell panes={{ request: <span data-testid="slot-req-only">RequestOnly</span> }} />)
    expect(screen.getByTestId('slot-req-only')).toBeInTheDocument()
  })

  it('renders only response when request is absent (partial panes)', () => {
    render(<Shell panes={{ response: <span data-testid="slot-res-only">ResponseOnly</span> }} />)
    expect(screen.getByTestId('slot-res-only')).toBeInTheDocument()
  })

  it('renders with no panes provided (neither request nor response)', () => {
    expect(() => render(<Shell />)).not.toThrow()
    // The PaneSplit still mounts (it has no content but renders its container)
    expect(document.querySelector('.pane-split')).toBeInTheDocument()
  })

  it('Statusbar children slot renders content (AC-7 exercised for Statusbar)', () => {
    render(
      <Statusbar>
        <span data-testid="statusbar-slot">SyncStatus</span>
      </Statusbar>
    )
    expect(screen.getByTestId('statusbar-slot')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Shell — store→<html> effects (AC-6)
// ---------------------------------------------------------------------------

describe('Shell — store→<html> data attributes and CSS vars (AC-6)', () => {
  it('writes data-theme="light" on document.documentElement on mount', () => {
    render(<Shell />)
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('writes data-accent and data-mstyle on mount', () => {
    render(<Shell />)
    expect(document.documentElement.dataset.accent).toBe('mint')
    expect(document.documentElement.dataset.mstyle).toBe('soft')
  })

  it('writes --sidebar-width as "260px" (px-suffixed) on mount', () => {
    render(<Shell />)
    expect(document.documentElement.style.getPropertyValue('--sidebar-width')).toBe('260px')
  })

  it('writes --pane-ratio as "0.5" (bare unitless) on mount', () => {
    render(<Shell />)
    expect(document.documentElement.style.getPropertyValue('--pane-ratio')).toBe('0.5')
  })

  it('EFFECT RE-RUN: changing theme in store updates data-theme on html', () => {
    render(<Shell />)
    expect(document.documentElement.dataset.theme).toBe('light')

    act(() => {
      settingsStore.getState().setTheme('dark')
    })

    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('EFFECT RE-RUN: changing accent in store updates data-accent on html', () => {
    render(<Shell />)
    act(() => {
      settingsStore.getState().setAccent('violet')
    })
    expect(document.documentElement.dataset.accent).toBe('violet')
  })

  it('EFFECT RE-RUN: changing mstyle in store updates data-mstyle on html', () => {
    render(<Shell />)
    act(() => {
      settingsStore.getState().setMstyle('chip')
    })
    expect(document.documentElement.dataset.mstyle).toBe('chip')
  })

  it('EFFECT RE-RUN: changing sidebarWidth in store updates --sidebar-width CSS var', () => {
    render(<Shell />)
    act(() => {
      settingsStore.getState().setSidebarWidth(400)
    })
    expect(document.documentElement.style.getPropertyValue('--sidebar-width')).toBe('400px')
  })

  it('EFFECT RE-RUN: changing paneRatio in store updates --pane-ratio CSS var', () => {
    render(<Shell />)
    act(() => {
      settingsStore.getState().setPaneRatio(0.3)
    })
    expect(document.documentElement.style.getPropertyValue('--pane-ratio')).toBe('0.3')
  })
})

// ---------------------------------------------------------------------------
// Shell — Cmd-B / Ctrl-B global toggle (AC-5)
// ---------------------------------------------------------------------------

describe('Shell — Cmd-B / Ctrl-B global sidebar toggle (AC-5)', () => {
  it('metaKey+b keydown toggles sidebarCollapsed from false to true', () => {
    render(<Shell />)
    expect(settingsStore.getState().sidebarCollapsed).toBe(false)

    const event = new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true })
    const preventSpy = vi.spyOn(event, 'preventDefault')
    document.dispatchEvent(event)

    expect(settingsStore.getState().sidebarCollapsed).toBe(true)
    expect(preventSpy).toHaveBeenCalled()
  })

  it('ctrlKey+b keydown also toggles sidebarCollapsed (distinct dispatch)', () => {
    render(<Shell />)
    expect(settingsStore.getState().sidebarCollapsed).toBe(false)

    const event = new KeyboardEvent('keydown', { key: 'b', ctrlKey: true, bubbles: true })
    const preventSpy = vi.spyOn(event, 'preventDefault')
    document.dispatchEvent(event)

    expect(settingsStore.getState().sidebarCollapsed).toBe(true)
    expect(preventSpy).toHaveBeenCalled()
  })

  it('second metaKey+b dispatch toggles back from true to false', () => {
    render(<Shell />)

    // First toggle → collapsed
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true }))
    expect(settingsStore.getState().sidebarCollapsed).toBe(true)

    // Second toggle → expanded
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true }))
    expect(settingsStore.getState().sidebarCollapsed).toBe(false)
  })

  it('Cmd-B fires regardless of focused element (fires on document, not element)', () => {
    render(<Shell />)

    // Focus some inner element
    const workspace = document.querySelector('.shell__workspace') as HTMLElement | null
    workspace?.focus()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true }))

    expect(settingsStore.getState().sidebarCollapsed).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Shell — collapse/focus directionality (AC-5 / grill F3)
// ---------------------------------------------------------------------------

describe('Shell — focus-return on collapse (AC-5 / grill F3)', () => {
  it('DISTINCT: collapsing unmounts the separator (queryByRole separator is null)', () => {
    render(<Shell />)
    // Sidebar is expanded → separator exists
    expect(screen.queryByRole('separator', { name: /resize sidebar/i })).toBeInTheDocument()

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true })
      )
    })

    // DISTINCT assertion: separator is gone
    expect(screen.queryByRole('separator', { name: /resize sidebar/i })).toBeNull()
  })

  it('DISTINCT: collapsing moves focus to the Titlebar sidebar-toggle button', () => {
    render(<Shell />)
    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })

    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true })
      )
    })

    // DISTINCT assertion: toggle has focus
    expect(toggleBtn).toHaveFocus()
  })

  it('expanding (collapsed→expanded) does NOT move focus to toggle button', () => {
    // Start collapsed
    act(() => {
      settingsStore.getState().toggleSidebar()
    })

    // Render a wrapper with a separate focusable element
    const { container } = render(
      <div>
        <button data-testid="other-btn">Other</button>
        <Shell />
      </div>
    )

    const otherBtn = container.querySelector('[data-testid="other-btn"]') as HTMLElement
    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })

    // Focus the "other" button so we know where focus starts
    act(() => {
      otherBtn.focus()
    })
    expect(document.activeElement).toBe(otherBtn)

    // Expand the sidebar (collapsed=true → expanded=false)
    act(() => {
      document.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true })
      )
    })

    // On expand, focus must NOT be moved to the toggle button —
    // only collapse (false→true) triggers focus-return.
    expect(document.activeElement).toBe(otherBtn)
    expect(document.activeElement).not.toBe(toggleBtn)
  })

  it('mounting with sidebarCollapsed: true does NOT steal focus on mount', () => {
    // Set store to collapsed BEFORE rendering
    act(() => {
      settingsStore.getState().toggleSidebar()
    })

    // Focus some element before render
    document.body.focus()

    render(<Shell />)

    // Focus must not have been captured by the Shell mount
    // (The toggle button should NOT be focused — mount guard is in place)
    const toggleBtn = screen.getByRole('button', { name: /toggle sidebar/i })
    expect(toggleBtn).not.toHaveFocus()
  })
})

// ---------------------------------------------------------------------------
// Shell — window-resize re-clamp (AC-17)
// ---------------------------------------------------------------------------

// Coverage split note (AC-17):
// This block covers the RENDERER-SIDE clamp/re-clamp only — the JS logic in Shell's
// Effect 3 that re-clamps sidebarWidth and paneRatio after a window resize event.
// The complementary guarantee — the OS-window minWidth floor set via BrowserWindow options
// in src/main/index.ts (task 010) — is the runtime guarantee and is NOT unit-testable
// in jsdom, so /verify must read both the store action and main/index.ts for full AC-17 coverage.
describe('Shell — window-resize re-clamp (AC-17)', () => {
  it('clamps out-of-bounds sidebarWidth back to SIDEBAR_MAX on resize', () => {
    render(<Shell />)

    // Seed an out-of-bounds value directly into the store
    act(() => {
      settingsStore.setState({ sidebarWidth: 9999 })
    })

    // Trigger resize
    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    expect(settingsStore.getState().sidebarWidth).toBe(SIDEBAR_MAX)
  })

  it('clamps negative sidebarWidth back to SIDEBAR_MIN on resize', () => {
    render(<Shell />)

    act(() => {
      settingsStore.setState({ sidebarWidth: -5 })
    })

    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    expect(settingsStore.getState().sidebarWidth).toBe(SIDEBAR_MIN)
  })

  it('clamps out-of-bounds paneRatio (>0.85) back to PANE_MAX on resize', () => {
    render(<Shell />)

    act(() => {
      settingsStore.setState({ paneRatio: 2 })
    })

    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    expect(settingsStore.getState().paneRatio).toBe(PANE_MAX)
  })

  it('clamps negative paneRatio back to PANE_MIN on resize', () => {
    render(<Shell />)

    act(() => {
      settingsStore.setState({ paneRatio: -1 })
    })

    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    expect(settingsStore.getState().paneRatio).toBe(PANE_MIN)
  })
})

// ---------------------------------------------------------------------------
// Shell — listener cleanup after unmount
// ---------------------------------------------------------------------------

describe('Shell — listener cleanup after unmount', () => {
  it('window resize after unmount does NOT mutate the store', () => {
    const { unmount } = render(<Shell />)

    unmount()

    // After unmount, seed an out-of-bounds value; if the resize listener were
    // still active it would re-clamp sidebarWidth back to SIDEBAR_MAX.
    act(() => {
      settingsStore.getState().reset()
      settingsStore.setState({ sidebarWidth: 9999 })
    })

    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    // If the listener was cleaned up, sidebarWidth remains 9999 (unclamped)
    expect(settingsStore.getState().sidebarWidth).toBe(9999)
  })

  it('Cmd-B after unmount does NOT toggle the store', () => {
    const { unmount } = render(<Shell />)
    unmount()

    const before = settingsStore.getState().sidebarCollapsed

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', metaKey: true, bubbles: true }))

    expect(settingsStore.getState().sidebarCollapsed).toBe(before)
  })
})

// ---------------------------------------------------------------------------
// Divider — sidebar (vertical) pointer drag (AC-4)
//
// The pane/horizontal drag is fully tested above with simulateDrag + a mocked
// getDragExtent.  This block exercises the VERTICAL / sidebar code path
// end-to-end via pointer drag — no getDragExtent, no explicit unit prop
// (defaults: 1:1 px mapping, unit='px') — matching exactly how Sidebar.tsx
// mounts the Divider.
//
// Without these tests a vertical-specific regression (e.g. accidentally reading
// clientY instead of clientX, or breaking the 1:1 mapping) would go
// undetected.
// ---------------------------------------------------------------------------

describe('Divider — sidebar (vertical) pointer drag (AC-4)', () => {
  function renderSidebarDividerForDrag(startValue = 260): {
    onCommit: ReturnType<typeof vi.fn>
    separator: HTMLElement
  } {
    const onCommit = vi.fn()
    render(
      <Divider
        orientation="vertical"
        value={startValue}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        // No getDragExtent → 1:1 px mapping
        // No unit → defaults to 'px'
      />
    )
    return { onCommit, separator: screen.getByRole('separator') }
  }

  it('PROPORTIONAL 1:1 px drag: +80px on X axis commits 260 + 80 = 340 (proves clientX is read, not clientY)', () => {
    const { onCommit, separator } = renderSidebarDividerForDrag(260)

    simulateDrag(separator, { axis: 'x', start: 0, end: 80 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(340)
  })

  it('CLAMP AT MAX: drag +400px (260+400=660 > 520) commits SIDEBAR_MAX (520)', () => {
    const { onCommit, separator } = renderSidebarDividerForDrag(260)

    simulateDrag(separator, { axis: 'x', start: 0, end: 400 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(SIDEBAR_MAX)
  })

  it('CLAMP AT MIN: drag -200px (260-200=60 < 200) commits SIDEBAR_MIN (200)', () => {
    const { onCommit, separator } = renderSidebarDividerForDrag(260)

    simulateDrag(separator, { axis: 'x', start: 0, end: -200 })

    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(SIDEBAR_MIN)
  })

  it('CSS VAR UNIT: committed value is written as px-suffixed string (e.g. "340px"), not a bare number', () => {
    const { separator } = renderSidebarDividerForDrag(260)

    simulateDrag(separator, { axis: 'x', start: 0, end: 80 })

    const val = document.documentElement.style.getPropertyValue('--sidebar-width')
    // Must be "340px" — distinguishes sidebar px unit from pane's bare-number unit
    expect(val).toBe('340px')
    expect(val).toMatch(/px$/)
  })
})

// ---------------------------------------------------------------------------
// App-level — toast text routed + Shell present + no PrimitivesDemo (AC-8)
// ---------------------------------------------------------------------------

describe('App — toast routing and shell presence (grill F2 / AC-8)', () => {
  it('renders the Shell (.shell root element) inside App', () => {
    render(<App />)
    expect(document.querySelector('.shell')).toBeInTheDocument()
  })

  it('does not render any PrimitivesDemo content', () => {
    render(<App />)
    // PrimitivesDemo would contain specific identifiable content; we check common markers
    expect(document.querySelector('[data-testid="primitives-demo"]')).toBeNull()
    expect(screen.queryByText(/primitives demo/i)).toBeNull()
  })

  it('toast text appears inside .toast-viewport after calling toast()', async () => {
    render(<App />)

    await act(async () => {
      toast('Hello toast text')
    })

    const viewport = document.querySelector('.toast-viewport')
    expect(viewport).toBeInTheDocument()
    // Assert toast TEXT is routed — not just that viewport exists
    expect(screen.getByText('Hello toast text')).toBeInTheDocument()
    // The text is inside the viewport
    expect(viewport).toContainElement(screen.getByText('Hello toast text'))
  })
})

// ---------------------------------------------------------------------------
// Shell Effect 2 — idempotent-write guard (fix regression)
//
// Shell's Effect 2 skips document.documentElement.style.setProperty when the
// CSS var already holds the same value. This prevents a double-write when
// the Divider has already written the committed value on pointerup and the
// Effect 2 re-runs because the store updated.
// ---------------------------------------------------------------------------

describe('Shell — Effect 2 idempotent-write guard', () => {
  it('skips setProperty for --sidebar-width when the DOM already holds the same value', () => {
    // 1. Mount Shell — Effect 2 writes '--sidebar-width: 260px' (the default).
    render(<Shell />)
    expect(document.documentElement.style.getPropertyValue('--sidebar-width')).toBe('260px')

    // 2. Change to a different value first, so Effect 2 runs once and sets '400px'.
    act(() => {
      settingsStore.getState().setSidebarWidth(400)
    })
    expect(document.documentElement.style.getPropertyValue('--sidebar-width')).toBe('400px')

    // 3. Pre-write the committed value to the DOM — this mimics the Divider's
    //    pointerup write that happens before the store update propagates.
    document.documentElement.style.setProperty('--sidebar-width', '400px')

    // 4. Spy AFTER the pre-write so we only capture calls from this point on.
    const spy = vi.spyOn(document.documentElement.style, 'setProperty')

    // 5. Trigger Effect 2 with the same value — store already has 400, but
    //    setSidebarWidth(400) is a no-op in terms of state change (clamp returns 400).
    //    We need to re-trigger the effect: force it by setting a new value then back,
    //    OR use setState to set the same numeric value.
    //    The cleanest path: set to a different value, then set back to 400.
    act(() => {
      settingsStore.getState().setSidebarWidth(300)
    })
    // Effect ran: DOM → '300px'; clear the spy to isolate the next call.
    spy.mockClear()
    // Pre-set DOM to 400px again.
    document.documentElement.style.setProperty('--sidebar-width', '400px')
    spy.mockClear()

    // 6. Now setSidebarWidth(400) — Effect 2 sees sidebarWidth=400 and DOM='400px'.
    //    The guard condition: style.getPropertyValue('--sidebar-width') === '400px' → skip.
    act(() => {
      settingsStore.getState().setSidebarWidth(400)
    })

    // 7. Assert the guard skipped the redundant write for this specific var.
    //    The spy must NOT have been called with ('--sidebar-width', '400px').
    //    (It may have been called for '--pane-ratio' which is a different var.)
    const sidebarWidthCalls = spy.mock.calls.filter((args) => args[0] === '--sidebar-width')
    expect(sidebarWidthCalls).toHaveLength(0)

    spy.mockRestore()
  })
})

// ---------------------------------------------------------------------------
// Divider — clamp NaN guard (fix regression)
//
// The clamp helper returns lo when v is not finite. For a vertical Divider
// with value=NaN, ArrowRight computes clamp(NaN + 8, 200, 520) = 200 (lo).
// ---------------------------------------------------------------------------

describe('Divider — clamp NaN guard', () => {
  it('ArrowRight with value=NaN resolves to min (200) via clamp NaN guard', () => {
    const onCommit = vi.fn()

    render(
      <Divider
        orientation="vertical"
        value={NaN}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={onCommit}
        unit="px"
      />
    )

    const separator = screen.getByRole('separator')
    // ArrowRight on vertical: handler computes clamp(NaN + 8, 200, 520).
    // Without the guard: NaN propagates → onCommit(NaN).
    // With the guard: clamp returns lo=200 → onCommit(200).
    fireEvent.keyDown(separator, { key: 'ArrowRight' })

    expect(onCommit).toHaveBeenCalledTimes(1)
    const committed = onCommit.mock.calls[0][0] as number
    expect(committed).toBe(SIDEBAR_MIN) // 200, NOT NaN
    expect(Number.isFinite(committed)).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// PaneSplit — end-to-end drag → setPaneRatio (fix regression)
//
// PaneSplit wires Divider's onCommit to (r) => settingsStore.getState().setPaneRatio(r).
// This test proves the wire-up commits a proportional ratio to the store.
// ---------------------------------------------------------------------------

describe('PaneSplit — drag commits proportional paneRatio to store', () => {
  it('simulateDrag on horizontal separator updates paneRatio proportionally (delta/height)', () => {
    // jsdom's getBoundingClientRect() returns height=0 by default, which would
    // make getDragExtent() return 0 and fall back to 1:1 mapping (pixel = ratio).
    // Stub it to return a real height so the px→ratio conversion is exercised.
    const rectSpy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      height: 800,
      width: 1000,
      top: 0,
      left: 0,
      right: 1000,
      bottom: 800,
      x: 0,
      y: 0,
      toJSON: () => ({})
    } as DOMRect)

    // Initialise --pane-ratio so Shell Effect 2 is not needed here.
    document.documentElement.style.setProperty('--pane-ratio', '0.5')

    const startRatio = settingsStore.getState().paneRatio // 0.5 (default)

    render(<PaneSplit />)

    const separator = screen.getByRole('separator', { name: /resize request and response panes/i })

    // Drag 80px downward on the y-axis.
    // With height=800: valueDelta = 80/800 = 0.1 → newRatio ≈ 0.5 + 0.1 = 0.6.
    simulateDrag(separator, { axis: 'y', start: 0, end: 80 })

    const finalRatio = settingsStore.getState().paneRatio
    expect(finalRatio).not.toBe(startRatio)
    // 0.5 + 0.1 = 0.6, well within [0.15, 0.85] bounds.
    expect(finalRatio).toBeCloseTo(0.6, 3)
    // Must be a finite number in valid range.
    expect(Number.isFinite(finalRatio)).toBe(true)
    expect(finalRatio).toBeGreaterThanOrEqual(PANE_MIN)
    expect(finalRatio).toBeLessThanOrEqual(PANE_MAX)

    rectSpy.mockRestore()
  })
})
