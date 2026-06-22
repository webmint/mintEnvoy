/**
 * Toast.test.tsx
 *
 * Interaction tests for the Toast molecule component.
 *
 * Test surface:
 *   - Enqueuing via the store renders the toast message as text in the DOM.
 *   - Closing one toast removes only it, leaving other toasts intact.
 *   - Hover/focus pause calls the store's pauseTimer action (DOM event wiring).
 *   - AC-8 integration: finite-duration toast auto-dismisses from the DOM
 *     after its timer fires (fake timers).
 *   - SECURITY: an XSS payload in message is rendered as literal text — no
 *     <img> or <script> elements are created (CWE-79, AC-8/22 escaping).
 *   - Variant CSS class is applied correctly.
 *
 * Radix Toast requires a `Toast.Provider` context; we set it up via the
 * exported `ToastProvider` + `ToastViewport` wrappers.
 *
 * Radix Toast timing (its internal duration) is disabled at the provider level
 * (duration=Infinity), so we do not need fake timers here — the store's own
 * timer tests live in toastStore.test.ts. Pause/resume assertions are
 * store-driven (spy on the store action).
 *
 * Note on `act()` warnings: Radix Toast internally uses Presence and
 * DismissableLayer which trigger async React effects. Using `await act()`
 * for every enqueue flushes these effects within the act boundary, eliminating
 * the warnings.
 */

import { render, screen, fireEvent, act } from '@testing-library/react'
import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
import { toastStore, toast } from '@renderer/lib/toastStore'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Render the full provider + viewport wrapping arbitrary children. */
function renderWithToastProvider(children?: React.ReactNode): ReturnType<typeof render> {
  return render(
    <ToastProvider>
      {children}
      <ToastViewport />
    </ToastProvider>
  )
}

/** Reset the store to empty before every test. */
function resetStore(): void {
  toastStore.getState().clearAll()
}

/** Enqueue a toast and flush all resulting React effects. */
async function enqueue(
  message: string,
  variant?: 'info' | 'success' | 'warning' | 'error'
): Promise<string> {
  let id = ''
  await act(async () => {
    id = toastStore.getState().enqueue(message, variant ? { variant } : undefined)
  })
  return id
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  resetStore()
})

afterEach(() => {
  resetStore()
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// Rendering — AC-8 / AC-22
// ---------------------------------------------------------------------------

describe('rendering', () => {
  it('renders a toast message as visible text when enqueued via the store', async () => {
    renderWithToastProvider()
    await enqueue('Hello from store')
    expect(screen.getByText('Hello from store')).toBeInTheDocument()
  })

  it('renders a toast message via the imperative toast() API', async () => {
    renderWithToastProvider()
    await act(async () => {
      toast('Imperative toast')
    })
    expect(screen.getByText('Imperative toast')).toBeInTheDocument()
  })

  it('renders multiple toasts simultaneously', async () => {
    renderWithToastProvider()
    await act(async () => {
      toast('First toast')
      toast('Second toast')
    })
    expect(screen.getByText('First toast')).toBeInTheDocument()
    expect(screen.getByText('Second toast')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Close / dismiss — AC-10
// ---------------------------------------------------------------------------

describe('close button — AC-10', () => {
  it('clicking Close on one toast removes only it, leaving others intact', async () => {
    renderWithToastProvider()

    await act(async () => {
      toast('Stay')
      toast('Go away')
    })

    // Both toasts must be present initially
    expect(screen.getByText('Stay')).toBeInTheDocument()
    expect(screen.getByText('Go away')).toBeInTheDocument()

    // Find the Close button inside the "Go away" toast <li>
    const goToastRoot = screen.getByText('Go away').closest('li')
    expect(goToastRoot).toBeInTheDocument()
    const closeButton = goToastRoot?.querySelector('button[aria-label="Close notification"]')
    expect(closeButton).toBeInTheDocument()

    await act(async () => {
      fireEvent.click(closeButton!)
    })

    // "Go away" is removed; "Stay" remains
    expect(screen.queryByText('Go away')).not.toBeInTheDocument()
    expect(screen.getByText('Stay')).toBeInTheDocument()

    // Store corroboration: only one toast remains
    expect(toastStore.getState().toasts).toHaveLength(1)
    expect(toastStore.getState().toasts[0].message).toBe('Stay')
  })

  it('closing a toast calls dismiss(id) on the store', async () => {
    renderWithToastProvider()

    const dismissSpy = vi.spyOn(toastStore.getState(), 'dismiss')

    let toastId: string = ''
    await act(async () => {
      toastId = toast('Dismiss me')
    })

    const toastText = screen.getByText('Dismiss me')
    const toastRoot = toastText.closest('li')
    const closeButton = toastRoot?.querySelector('button[aria-label="Close notification"]')

    await act(async () => {
      fireEvent.click(closeButton!)
    })

    expect(dismissSpy).toHaveBeenCalledWith(toastId)
  })
})

// ---------------------------------------------------------------------------
// Hover / focus pause — AC-9
// ---------------------------------------------------------------------------

describe('pause on hover / focus — AC-9', () => {
  it('pauseTimer stops the countdown when called (wires to onPause)', async () => {
    renderWithToastProvider()

    const pauseSpy = vi.spyOn(toastStore.getState(), 'pauseTimer')

    let toastId: string = ''
    await act(async () => {
      toastId = toast('Pause me', { duration: 10_000 })
    })

    // Directly invoke via the store (mirrors what Toast.Root's onPause wires to)
    await act(async () => {
      toastStore.getState().pauseTimer(toastId)
    })

    expect(pauseSpy).toHaveBeenCalledWith(toastId)
    // Toast is still in DOM — countdown is paused, not dismissed
    expect(screen.getByText('Pause me')).toBeInTheDocument()
    expect(toastStore.getState().toasts[0].paused).toBe(true)
  })

  it('resumeTimer restarts the countdown when called (wires to onResume)', async () => {
    renderWithToastProvider()

    const resumeSpy = vi.spyOn(toastStore.getState(), 'resumeTimer')

    let toastId: string = ''
    await act(async () => {
      toastId = toast('Resume me', { duration: 10_000 })
    })

    // Pause first, then resume
    await act(async () => {
      toastStore.getState().pauseTimer(toastId)
    })

    await act(async () => {
      toastStore.getState().resumeTimer(toastId)
    })

    expect(resumeSpy).toHaveBeenCalledWith(toastId)
    expect(toastStore.getState().toasts[0].paused).toBe(false)
    // Toast is still present — not auto-dismissed during the test (fake timer needed for that)
    expect(screen.getByText('Resume me')).toBeInTheDocument()
  })

  it('pointermove on the viewport wrapper fires pauseTimer via onPause prop wiring', async () => {
    // Radix Toast wires pause/resume via custom events dispatched on the viewport
    // element. The Radix Viewport component attaches `pointermove` (pause) and
    // `pointerleave` (resume) listeners on an internal wrapper <div> that wraps
    // the viewport <ol>. Both events bubble, so firing them on the <ol> reaches
    // the wrapper's listener.
    //
    // pointerleave does NOT bubble natively, so we dispatch it directly on the
    // wrapper div (the immediate parent of the <ol>) to guarantee Radix's
    // `handlePointerLeaveResume` fires.
    renderWithToastProvider()

    const pauseSpy = vi.spyOn(toastStore.getState(), 'pauseTimer')
    const resumeSpy = vi.spyOn(toastStore.getState(), 'resumeTimer')

    await act(async () => {
      toast('Hover me', { duration: 10_000 })
    })

    // The Radix viewport is the <ol>; its parent is the internal wrapper <div>
    const viewport = document.querySelector('ol.toast-viewport')
    expect(viewport).toBeInTheDocument()
    const wrapper = viewport!.parentElement
    expect(wrapper).toBeInTheDocument()

    // pointermove bubbles from <ol> up to the wrapper's listener →
    // dispatches toast.viewportPause CustomEvent on the viewport →
    // Toast.Root effect calls onPause() → pauseTimer(id)
    await act(async () => {
      fireEvent.pointerMove(viewport!)
    })
    expect(pauseSpy).toHaveBeenCalledTimes(1)

    // pointerleave does not bubble; fire it directly on the wrapper div so
    // Radix's addEventListener("pointerleave", handlePointerLeaveResume) fires.
    await act(async () => {
      fireEvent.pointerLeave(wrapper!)
    })
    expect(resumeSpy).toHaveBeenCalledTimes(1)
  })

  it('focus / blur on Toast.Root <li> fires pauseTimer/resumeTimer via onPause/onResume', async () => {
    renderWithToastProvider()

    const pauseSpy = vi.spyOn(toastStore.getState(), 'pauseTimer')
    const resumeSpy = vi.spyOn(toastStore.getState(), 'resumeTimer')

    await act(async () => {
      toast('Focus me', { duration: 10_000 })
    })

    const toastLi = screen.getByText('Focus me').closest('li')
    expect(toastLi).toBeInTheDocument()

    await act(async () => {
      fireEvent.focus(toastLi!)
    })
    expect(pauseSpy).toHaveBeenCalledTimes(1)

    await act(async () => {
      fireEvent.blur(toastLi!)
    })
    expect(resumeSpy).toHaveBeenCalledTimes(1)
  })
})

// ---------------------------------------------------------------------------
// AC-8 integration — store timer → DOM removal
// ---------------------------------------------------------------------------

describe('auto-dismiss integration — AC-8', () => {
  it('toast is removed from DOM after its duration elapses (fake timers)', async () => {
    vi.useFakeTimers()

    try {
      renderWithToastProvider()

      // Enqueue a toast with a short, finite duration
      await act(async () => {
        toast('Short-lived toast', { duration: 2_000 })
      })

      // Toast must be visible before the timer fires
      expect(screen.getByText('Short-lived toast')).toBeInTheDocument()

      // Advance fake timers past the duration → scheduleTimer's setTimeout fires
      // → dismiss(id) removes the item from the store → React re-renders
      await act(async () => {
        vi.advanceTimersByTime(2_500)
      })

      // The toast must no longer be in the DOM
      expect(screen.queryByText('Short-lived toast')).not.toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })
})

// ---------------------------------------------------------------------------
// SECURITY — CWE-79 / XSS escaping
// ---------------------------------------------------------------------------

describe('security — XSS: message is rendered as escaped text, never as HTML', () => {
  it('renders an XSS img payload as literal text — no <img> element created', async () => {
    const xssPayload = '<img src=x onerror=alert(1)>'
    renderWithToastProvider()

    await act(async () => {
      toast(xssPayload)
    })

    // The literal payload text is present as a text node
    expect(screen.getByText(xssPayload)).toBeInTheDocument()

    // No <img> must have been parsed from the payload
    // (the only images in the document come from the toast icon SVGs)
    const images = document.querySelectorAll('img')
    expect(images).toHaveLength(0)
  })

  it('renders a script-injection payload as literal text — payload is escaped, not parsed as HTML', async () => {
    const scriptPayload = '</Toast><script>alert(1)</script>'
    renderWithToastProvider()

    await act(async () => {
      toast(scriptPayload)
    })

    // 1. The literal payload string must appear as text in the DOM
    const titleEl = screen.getByText(scriptPayload)
    expect(titleEl).toBeInTheDocument()

    // 2. The toast subtree's innerHTML must NOT contain an actual <script tag —
    //    i.e. the payload is present as escaped text, not as markup.
    const toastLi = titleEl.closest('li')
    expect(toastLi).toBeInTheDocument()
    expect(toastLi!.innerHTML).not.toContain('<script')

    // 3. Defensive belt-and-suspenders: no <script> element anywhere in the
    //    document (guards against future regressions that add dangerouslySetInnerHTML).
    //    Note: jsdom does not execute <script> tags injected via innerHTML, but
    //    checking presence is still a meaningful escaping regression signal.
    expect(document.querySelectorAll('script')).toHaveLength(0)
  })

  it('renders an attribute-injection payload as safe text', async () => {
    const attrPayload = '" onmouseover="alert(1)" data-x="'
    renderWithToastProvider()

    await act(async () => {
      toast(attrPayload)
    })

    // React serialises children to text nodes, preventing attribute injection
    expect(screen.getByText(attrPayload)).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Variant → CSS class mapping
// ---------------------------------------------------------------------------

describe('variant class mapping', () => {
  const variants = ['info', 'success', 'warning', 'error'] as const

  for (const variant of variants) {
    it(`applies "toast toast--${variant}" class for variant="${variant}"`, async () => {
      renderWithToastProvider()

      await enqueue('variant test', variant)

      const toastText = screen.getByText('variant test')
      const toastRoot = toastText.closest('li')

      expect(toastRoot).toHaveClass('toast')
      expect(toastRoot).toHaveClass(`toast--${variant}`)
    })
  }
})
