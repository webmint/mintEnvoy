/**
 * toastStore.ts
 *
 * Module-level zustand store for managing the toast notification queue.
 *
 * This module:
 *   - has NO node / electron imports (renderer-only, constitution §2.3, AC-19)
 *   - exports a single module-level store instance (avoid per-consumer instantiation)
 *   - mutates state only via store actions (constitution §4)
 *   - exposes an imperative toast() API for fire-and-forget usage
 *
 * Usage:
 *   // Imperative (from any module):
 *   toast('Saved!', { variant: 'success' })
 *   toast.error('Something went wrong')
 *
 *   // Reactive (inside a React component):
 *   const toasts = toastStore(state => state.toasts)
 */
import { create } from 'zustand'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Allowed visual variants for a toast notification. */
export type ToastVariant = 'info' | 'success' | 'warning' | 'error'

/**
 * A single toast notification item held in the queue.
 * id and duration are always present; variant and message are always set.
 */
export interface ToastItem {
  /** Unique identifier for this toast (crypto.randomUUID). */
  id: string
  /** Human-readable message to display. */
  message: string
  /** Visual treatment for the toast. Defaults to 'info'. */
  variant: ToastVariant
  /** Total display duration in milliseconds. Defaults to 5000ms. */
  duration: number
  /** Whether the auto-dismiss countdown is currently paused (e.g. on hover). */
  paused: boolean
  /**
   * Milliseconds remaining on the auto-dismiss countdown.
   *
   * Before the first pause this equals `duration`; after each pause/resume
   * cycle it holds the time left as of the most recent `startedAt`.
   */
  remaining: number
  /** Wall-clock timestamp (Date.now()) when the current timer interval started. */
  startedAt: number
}

/** Options accepted by enqueue() and the toast() imperative API. */
export interface ToastOptions {
  /** Visual variant. Defaults to 'info'. */
  variant?: ToastVariant
  /** Auto-dismiss duration in milliseconds. Defaults to 5000. */
  duration?: number
}

// ---------------------------------------------------------------------------
// Internal timer registry (kept outside rendered state for cleanliness)
// ---------------------------------------------------------------------------

/** Map from toast id → active setTimeout handle. */
const timerHandles = new Map<string, ReturnType<typeof setTimeout>>()

/** Clear the timeout for a toast id if one is registered. */
function clearToastTimer(id: string): void {
  const handle = timerHandles.get(id)
  if (handle !== undefined) {
    clearTimeout(handle)
    timerHandles.delete(id)
  }
}

/** Schedule auto-dismiss for a toast after `ms` milliseconds. */
function scheduleTimer(id: string, ms: number): void {
  clearToastTimer(id) // guard against double-scheduling
  const handle = setTimeout(() => {
    timerHandles.delete(id)
    toastStore.getState().dismiss(id)
  }, ms)
  timerHandles.set(id, handle)
}

// ---------------------------------------------------------------------------
// Store state + actions
// ---------------------------------------------------------------------------

interface ToastState {
  /** Ordered queue of active toasts; first element is oldest. */
  toasts: ToastItem[]

  /**
   * Add a toast to the queue and start its auto-dismiss timer.
   * @returns The generated id for the new toast.
   */
  enqueue: (message: string, opts?: ToastOptions) => string

  /**
   * Remove a single toast by id and cancel its timer.
   * No-ops gracefully if the id is not found.
   */
  dismiss: (id: string) => void

  /**
   * Pause the auto-dismiss countdown for the given toast (e.g. on mouse-enter).
   * Records the remaining time so resumeTimer() can restart from there.
   * No-ops if the toast is not found or is already paused.
   */
  pauseTimer: (id: string) => void

  /**
   * Resume a previously paused auto-dismiss countdown.
   * Restarts the timer from the remaining time recorded at pause.
   * No-ops if the toast is not found or is not paused.
   */
  resumeTimer: (id: string) => void

  /**
   * Remove all toasts and cancel all timers.
   * Useful for cleanup in tests and on app unmount.
   */
  clearAll: () => void
}

/**
 * The single, module-level zustand store for toast notifications.
 *
 * Consumers should prefer selectors over reading the full store:
 *   const toasts = toastStore(state => state.toasts)
 *
 * Named `toastStore` per project naming convention (Store suffix, §3.3).
 */
export const toastStore = create<ToastState>((set, get) => ({
  toasts: [],

  enqueue(message, opts) {
    const id = crypto.randomUUID()
    const duration = opts?.duration ?? 5000
    const variant: ToastVariant = opts?.variant ?? 'info'
    const now = Date.now()

    const item: ToastItem = {
      id,
      message,
      variant,
      duration,
      paused: false,
      remaining: duration,
      startedAt: now
    }

    set((state) => ({ toasts: [...state.toasts, item] }))
    scheduleTimer(id, duration)

    return id
  },

  dismiss(id) {
    const { toasts } = get()
    const exists = toasts.some((t) => t.id === id)
    if (!exists) {
      // No-op for unknown id (§3.2: never throw on unknown dismiss)
      return
    }
    clearToastTimer(id)
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
  },

  pauseTimer(id) {
    const { toasts } = get()
    const toast = toasts.find((t) => t.id === id)
    if (!toast || toast.paused) return

    const elapsed = Date.now() - toast.startedAt
    const remaining = Math.max(0, toast.remaining - elapsed)

    clearToastTimer(id)
    set((state) => ({
      toasts: state.toasts.map((t) => (t.id === id ? { ...t, paused: true, remaining } : t))
    }))
  },

  resumeTimer(id) {
    const { toasts } = get()
    const toast = toasts.find((t) => t.id === id)
    if (!toast || !toast.paused) return

    const now = Date.now()
    // Read `toast.remaining` from the pre-set snapshot deliberately: set() is
    // async in Zustand's batching model, so we capture the value before
    // calling set(), then pass that same snapshot to scheduleTimer() after —
    // ensuring the scheduled delay matches exactly what was written to state.
    set((state) => ({
      toasts: state.toasts.map((t) => (t.id === id ? { ...t, paused: false, startedAt: now } : t))
    }))
    scheduleTimer(id, toast.remaining)
  },

  clearAll() {
    const { toasts } = get()
    for (const t of toasts) {
      clearToastTimer(t.id)
    }
    set({ toasts: [] })
  }
}))

// ---------------------------------------------------------------------------
// Imperative toast() API
// ---------------------------------------------------------------------------

/**
 * Convenience function — enqueues a toast from outside React components.
 *
 * @param message  Text to display in the toast.
 * @param opts     Optional variant and duration overrides.
 * @returns        The generated toast id.
 *
 * @example
 *   toast('File saved', { variant: 'success' })
 *   toast.error('Request failed')
 *   const id = toast('Working…', { duration: 10_000 })
 *   // later: toastStore.getState().dismiss(id)
 */
export function toast(message: string, opts?: ToastOptions): string {
  return toastStore.getState().enqueue(message, opts)
}

/** Shorthand for toast(message, { variant: 'info' }). */
toast.info = (message: string, opts?: Omit<ToastOptions, 'variant'>): string =>
  toast(message, { ...opts, variant: 'info' })

/** Shorthand for toast(message, { variant: 'success' }). */
toast.success = (message: string, opts?: Omit<ToastOptions, 'variant'>): string =>
  toast(message, { ...opts, variant: 'success' })

/** Shorthand for toast(message, { variant: 'warning' }). */
toast.warning = (message: string, opts?: Omit<ToastOptions, 'variant'>): string =>
  toast(message, { ...opts, variant: 'warning' })

/** Shorthand for toast(message, { variant: 'error' }). */
toast.error = (message: string, opts?: Omit<ToastOptions, 'variant'>): string =>
  toast(message, { ...opts, variant: 'error' })
