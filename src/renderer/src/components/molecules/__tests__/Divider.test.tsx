/**
 * Divider.test.tsx
 *
 * Isolation tests for the Divider molecule component.
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## Test surface
 *
 * - jsdom setup:   pointer-capture stubs; full DOM cleanup after each test.
 * - Divider:       drag clamp, keyboard, cancel, CSS-var units, px→ratio bug regression.
 *
 * Moved here from organisms/shell/__tests__/Shell.test.tsx as part of the
 * constitution §3.3/§3.4 co-location remediation — Divider isolation tests
 * must live next to molecules/Divider.tsx, not two tiers up in the Shell trio.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { Divider } from '@renderer/components/molecules/Divider'
import { SIDEBAR_MIN, SIDEBAR_MAX, PANE_MIN, PANE_MAX } from '@renderer/lib/settingsStore'
import { simulateDrag } from '@renderer/test-utils/simulateDrag'

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
// DOM cleanup between tests
//
// CSS vars written by Divider during drag survive React unmount on the
// global <html> element and must be removed after each test.
// ---------------------------------------------------------------------------

afterEach(() => {
  // Remove CSS vars Divider writes during drag
  document.documentElement.style.removeProperty('--sidebar-width')
  document.documentElement.style.removeProperty('--pane-ratio')
})

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
