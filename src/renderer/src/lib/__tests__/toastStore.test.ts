/**
 * toastStore.test.ts
 *
 * Unit tests for the toast queue store and imperative toast() API.
 * Uses Vitest fake timers to control auto-dismiss timeouts deterministically.
 *
 * AC coverage:
 *   AC-22 — enqueue adds a toast + returns an id
 *   AC-8  — after duration elapses (fake timers), toast is auto-removed
 *   AC-9  — pauseTimer halts auto-dismiss; resumeTimer lets it dismiss after remaining time
 *   AC-10 — dismiss(id) removes only that toast, leaving others
 *           dismiss(unknown id) does not throw
 */
import { toastStore, toast } from '@renderer/lib/toastStore'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Reset the store to a clean empty state before each test. */
function resetStore(): void {
  toastStore.getState().clearAll()
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.useFakeTimers()
  resetStore()
})

afterEach(() => {
  resetStore()
  vi.useRealTimers()
})

// ---------------------------------------------------------------------------
// enqueue — AC-22
// ---------------------------------------------------------------------------

describe('enqueue', () => {
  it('adds a toast to the queue and returns a non-empty string id (AC-22)', () => {
    const id = toastStore.getState().enqueue('Hello')
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)

    const { toasts } = toastStore.getState()
    expect(toasts).toHaveLength(1)
    expect(toasts[0].id).toBe(id)
    expect(toasts[0].message).toBe('Hello')
  })

  it('sets variant to "info" by default', () => {
    toastStore.getState().enqueue('msg')
    expect(toastStore.getState().toasts[0].variant).toBe('info')
  })

  it('respects provided variant and duration options', () => {
    toastStore.getState().enqueue('msg', { variant: 'error', duration: 3000 })
    const t = toastStore.getState().toasts[0]
    expect(t.variant).toBe('error')
    expect(t.duration).toBe(3000)
  })

  it('assigns unique ids to multiple toasts', () => {
    const id1 = toastStore.getState().enqueue('first')
    const id2 = toastStore.getState().enqueue('second')
    expect(id1).not.toBe(id2)
    expect(toastStore.getState().toasts).toHaveLength(2)
  })
})

// ---------------------------------------------------------------------------
// Auto-dismiss — AC-8
// ---------------------------------------------------------------------------

describe('auto-dismiss (AC-8)', () => {
  it('removes the toast after its duration elapses', () => {
    toastStore.getState().enqueue('auto', { duration: 2000 })
    expect(toastStore.getState().toasts).toHaveLength(1)

    vi.advanceTimersByTime(2000)

    expect(toastStore.getState().toasts).toHaveLength(0)
  })

  it('does not remove the toast before the duration elapses', () => {
    toastStore.getState().enqueue('not yet', { duration: 2000 })
    vi.advanceTimersByTime(1999)
    expect(toastStore.getState().toasts).toHaveLength(1)
  })

  it('uses 5000ms default duration when none is provided', () => {
    toastStore.getState().enqueue('default timer')
    vi.advanceTimersByTime(4999)
    expect(toastStore.getState().toasts).toHaveLength(1)

    vi.advanceTimersByTime(1)
    expect(toastStore.getState().toasts).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// pauseTimer / resumeTimer — AC-9
// ---------------------------------------------------------------------------

describe('pauseTimer / resumeTimer (AC-9)', () => {
  it('halts auto-dismiss while paused: timer does not fire during pause', () => {
    const id = toastStore.getState().enqueue('pause me', { duration: 4000 })

    // Advance 1s, then pause
    vi.advanceTimersByTime(1000)
    toastStore.getState().pauseTimer(id)

    // Advance another 5s (well past the original deadline)
    vi.advanceTimersByTime(5000)

    // Toast must still be in the queue
    expect(toastStore.getState().toasts).toHaveLength(1)
    // Data-model assertions: paused flag set and remaining reflects 3000ms left
    expect(toastStore.getState().toasts[0].paused).toBe(true)
    expect(toastStore.getState().toasts[0].remaining).toBe(3000)
  })

  it('resumes from remaining time after pause and auto-dismisses', () => {
    const id = toastStore.getState().enqueue('pause me', { duration: 4000 })

    // Advance 1s, then pause (3000ms should remain)
    vi.advanceTimersByTime(1000)
    toastStore.getState().pauseTimer(id)

    // Data-model assertion: paused flag is true after pauseTimer
    expect(toastStore.getState().toasts[0].paused).toBe(true)

    // Advance 2s more while paused — should NOT dismiss
    vi.advanceTimersByTime(2000)
    expect(toastStore.getState().toasts).toHaveLength(1)

    // Resume — timer restarts from ~3000ms remaining
    toastStore.getState().resumeTimer(id)

    // Data-model assertion: paused flag is false after resumeTimer
    expect(toastStore.getState().toasts[0].paused).toBe(false)

    // Advance 2999ms — still alive
    vi.advanceTimersByTime(2999)
    expect(toastStore.getState().toasts).toHaveLength(1)

    // Advance 1ms more — now dismissed
    vi.advanceTimersByTime(1)
    expect(toastStore.getState().toasts).toHaveLength(0)
  })

  it('survives multi-cycle pause/resume and dismisses after cumulative remaining time', () => {
    // Enqueue a 6000ms toast
    const id = toastStore.getState().enqueue('multi-cycle', { duration: 6000 })

    // --- Cycle 1 ---
    // Advance 1000ms (5000ms remaining)
    vi.advanceTimersByTime(1000)
    toastStore.getState().pauseTimer(id)
    expect(toastStore.getState().toasts[0].paused).toBe(true)
    expect(toastStore.getState().toasts[0].remaining).toBe(5000)

    // Advance 2000ms while paused (time does not count)
    vi.advanceTimersByTime(2000)
    expect(toastStore.getState().toasts).toHaveLength(1)

    toastStore.getState().resumeTimer(id)
    expect(toastStore.getState().toasts[0].paused).toBe(false)

    // --- Cycle 2 ---
    // Advance 2000ms more (3000ms remaining)
    vi.advanceTimersByTime(2000)
    toastStore.getState().pauseTimer(id)
    expect(toastStore.getState().toasts[0].paused).toBe(true)
    expect(toastStore.getState().toasts[0].remaining).toBe(3000)

    // Advance 3000ms while paused (still should NOT dismiss)
    vi.advanceTimersByTime(3000)
    expect(toastStore.getState().toasts).toHaveLength(1)

    toastStore.getState().resumeTimer(id)
    expect(toastStore.getState().toasts[0].paused).toBe(false)

    // --- Final countdown ---
    // 2999ms more — toast must still be alive
    vi.advanceTimersByTime(2999)
    expect(toastStore.getState().toasts).toHaveLength(1)

    // 1ms more — exactly at 3000ms remaining after last resume → dismissed
    vi.advanceTimersByTime(1)
    expect(toastStore.getState().toasts).toHaveLength(0)
  })

  it('no-ops pauseTimer on unknown id', () => {
    expect(() => toastStore.getState().pauseTimer('__no__')).not.toThrow()
  })

  it('no-ops resumeTimer on unknown id', () => {
    expect(() => toastStore.getState().resumeTimer('__no__')).not.toThrow()
  })

  it('no-ops pauseTimer when already paused', () => {
    const id = toastStore.getState().enqueue('pause', { duration: 4000 })
    vi.advanceTimersByTime(500)
    toastStore.getState().pauseTimer(id)

    // Capture remaining after first pause
    const remaining = toastStore.getState().toasts[0].remaining

    // Advance a bit then pause again — remaining should not change
    vi.advanceTimersByTime(200)
    toastStore.getState().pauseTimer(id)
    expect(toastStore.getState().toasts[0].remaining).toBe(remaining)
  })

  it('no-ops resumeTimer when not paused', () => {
    const id = toastStore.getState().enqueue('no pause', { duration: 4000 })
    // Never paused — resumeTimer should be a safe no-op
    expect(() => toastStore.getState().resumeTimer(id)).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// dismiss — AC-10
// ---------------------------------------------------------------------------

describe('dismiss (AC-10)', () => {
  it('removes only the targeted toast and leaves others', () => {
    const id1 = toastStore.getState().enqueue('first')
    const id2 = toastStore.getState().enqueue('second')
    const id3 = toastStore.getState().enqueue('third')

    toastStore.getState().dismiss(id2)

    const { toasts } = toastStore.getState()
    expect(toasts).toHaveLength(2)
    expect(toasts.map((t) => t.id)).toContain(id1)
    expect(toasts.map((t) => t.id)).not.toContain(id2)
    expect(toasts.map((t) => t.id)).toContain(id3)
  })

  it('does NOT throw when given an unknown id (constitution §3.2)', () => {
    expect(() => toastStore.getState().dismiss('__nope__')).not.toThrow()
  })

  it('cancels the auto-dismiss timer so the toast does not reappear', () => {
    const id = toastStore.getState().enqueue('cancel me', { duration: 2000 })
    toastStore.getState().dismiss(id)
    expect(toastStore.getState().toasts).toHaveLength(0)

    // Advancing time must not cause further mutations or errors
    expect(() => vi.advanceTimersByTime(3000)).not.toThrow()
    expect(toastStore.getState().toasts).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// clearAll
// ---------------------------------------------------------------------------

describe('clearAll', () => {
  it('removes every toast and prevents their timers from firing', () => {
    toastStore.getState().enqueue('a', { duration: 1000 })
    toastStore.getState().enqueue('b', { duration: 2000 })
    toastStore.getState().enqueue('c', { duration: 3000 })

    toastStore.getState().clearAll()
    expect(toastStore.getState().toasts).toHaveLength(0)

    // All timers cancelled — no mutations after advancing time
    expect(() => vi.advanceTimersByTime(5000)).not.toThrow()
    expect(toastStore.getState().toasts).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// Imperative toast() API
// ---------------------------------------------------------------------------

describe('toast() imperative API', () => {
  it('enqueues a toast and returns its id', () => {
    const id = toast('Hello')
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
    expect(toastStore.getState().toasts[0].id).toBe(id)
  })

  it('toast.success sets variant to success and returns a non-empty string id', () => {
    const id = toast.success('Done!')
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
    expect(toastStore.getState().toasts[0].variant).toBe('success')
  })

  it('toast.error sets variant to error and returns a non-empty string id', () => {
    const id = toast.error('Oops!')
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
    expect(toastStore.getState().toasts[0].variant).toBe('error')
  })

  it('toast.warning sets variant to warning and returns a non-empty string id', () => {
    const id = toast.warning('Watch out')
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
    expect(toastStore.getState().toasts[0].variant).toBe('warning')
  })

  it('toast.info sets variant to info and returns a non-empty string id', () => {
    const id = toast.info('FYI')
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
    expect(toastStore.getState().toasts[0].variant).toBe('info')
  })

  it('toast convenience wrappers accept duration override', () => {
    toast.success('Done!', { duration: 1000 })
    expect(toastStore.getState().toasts[0].duration).toBe(1000)
  })
})
