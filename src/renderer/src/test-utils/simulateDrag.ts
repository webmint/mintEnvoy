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
export function simulateDrag(
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
