/**
 * Toast — molecule component rendering the toast notification queue.
 *
 * Subscribes to `toastStore` and renders each `ToastItem` as a Radix
 * `Toast.Root` with a leading variant icon, a body (title text + description),
 * and a close button.
 *
 * ## Export shape (for task 008 — App root mounting)
 *
 * ```tsx
 * import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
 *
 * // In your App root (render once):
 * <ToastProvider>
 *   {children}
 *   <ToastViewport />
 * </ToastProvider>
 * ```
 *
 * `ToastProvider` wraps `Toast.Provider` from Radix; it accepts children and
 * wires up the store-driven rendering (a `ToastList` hidden inside the
 * provider's context). `ToastViewport` wraps Radix's `Toast.Viewport` and
 * applies the project's semantic classes.
 *
 * ## Security
 *
 * `item.message` (caller-supplied) is rendered as a JSX text node:
 *   `<Toast.Title className="toast__title">{item.message}</Toast.Title>`
 * React escapes all text children, so arbitrary strings — including HTML
 * injection payloads — are rendered as literal text, never parsed as markup.
 * `dangerouslySetInnerHTML` is NEVER used for user-supplied content (CWE-79).
 *
 * ## Pause / resume wiring
 *
 * Radix exposes `onPause` / `onResume` callbacks on `Toast.Root` that fire on
 * pointer-enter, pointer-leave, focus, and blur. We wire these directly to
 * `toastStore.getState().pauseTimer(id)` / `resumeTimer(id)`, making the store
 * the single source of truth for countdown state.
 *
 * @module Toast
 */

import './Toast.css'

import { memo } from 'react'
import { Toast } from 'radix-ui'
import { cx } from '@renderer/lib/cx'
import { toastStore } from '@renderer/lib/toastStore'
import { Icon } from '@renderer/components/atoms/Icon'
import type { ToastItem, ToastVariant } from '@renderer/lib/toastStore'
import type { IconName } from '@renderer/components/atoms/icons'

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Map each toast variant to its leading icon name from the project icon set. */
const VARIANT_ICON: Record<ToastVariant, IconName> = {
  info: 'info',
  success: 'check',
  warning: 'alert',
  error: 'alert'
}

/** Accessible label for the leading icon — announced by screen readers alongside the toast title. */
const VARIANT_LABEL: Record<ToastVariant, string> = {
  info: 'Info',
  success: 'Success',
  warning: 'Warning',
  error: 'Error'
}

// ---------------------------------------------------------------------------
// ToastItem component (single toast)
// ---------------------------------------------------------------------------

/** Props for a single rendered toast item. */
interface ToastItemProps {
  item: ToastItem
}

/**
 * Renders a single Radix `Toast.Root` for one `ToastItem`.
 *
 * - `open` is always `true`; dismissal is driven by calling `dismiss(id)` which
 *   removes the item from the store array — the component simply unmounts.
 * - `duration={Infinity}` disables Radix's own internal timer so our store
 *   timer is the sole source of truth for auto-dismiss timing.
 * - `onPause` / `onResume` wire Radix's built-in pointer/focus callbacks to
 *   the store's `pauseTimer` / `resumeTimer` actions.
 * - `onOpenChange` handles swipe-to-dismiss (Radix fires `false` after a swipe).
 * - Wrapped in `React.memo` so the N-1 unaffected toasts skip re-render when
 *   one toast's timer is paused or resumed. The store's `.map()` returns the
 *   same object reference for unchanged items, so memo's shallow compare works.
 */
const ToastItemComponent = memo(function ToastItemComponent({
  item
}: ToastItemProps): React.JSX.Element {
  const { id, message, variant } = item

  function handlePause(): void {
    toastStore.getState().pauseTimer(id)
  }

  function handleResume(): void {
    toastStore.getState().resumeTimer(id)
  }

  function handleClose(): void {
    toastStore.getState().dismiss(id)
  }

  return (
    <Toast.Root
      open={true}
      onOpenChange={(open) => {
        // Radix fires false after a swipe gesture — treat as dismiss
        if (!open) {
          handleClose()
        }
      }}
      onPause={handlePause}
      onResume={handleResume}
      // Disable Radix's built-in countdown; the toastStore owns auto-dismiss.
      duration={Infinity}
      className={cx('toast', `toast--${variant}`)}
    >
      {/* Leading variant icon — decorative when title carries the variant label */}
      <span className="toast__icon">
        <Icon name={VARIANT_ICON[variant]} size={14} label={VARIANT_LABEL[variant]} />
      </span>

      {/* Toast body: title carries the message text as escaped JSX children.
          React renders children as text nodes — no HTML parsing, no XSS risk. */}
      <div className="toast__body">
        <Toast.Title className="toast__title">{message}</Toast.Title>
        {/* Description is omitted at this layer; callers wishing to add a
            subtitle may extend this component and render Toast.Description
            conditionally when description text is available. */}
      </div>

      {/* Close button — Radix.Close fires onOpenChange(false) on click, which
          the onOpenChange handler above routes to handleClose(). No onClick
          needed here; adding one would cause dismiss(id) to fire twice. */}
      <Toast.Close className="toast__close" aria-label="Close notification">
        {/* Icon without label → decorative (aria-hidden="true" applied by Icon) */}
        <Icon name="x" size={12} />
      </Toast.Close>
    </Toast.Root>
  )
})

// ---------------------------------------------------------------------------
// ToastList — internal list of active toasts
// ---------------------------------------------------------------------------

/**
 * Renders all active toasts from the store.
 * Must be rendered inside a `Toast.Provider` context.
 */
function ToastList(): React.JSX.Element {
  const toasts = toastStore((state) => state.toasts)

  return (
    <>
      {toasts.map((item) => (
        <ToastItemComponent key={item.id} item={item} />
      ))}
    </>
  )
}

// ---------------------------------------------------------------------------
// Public exports
// ---------------------------------------------------------------------------

/** Props for ToastProvider. */
export interface ToastProviderProps {
  /** Application subtree that will have access to the toast context. */
  children: React.ReactNode
}

/**
 * Provider component — mount this once at the App root (task 008).
 *
 * Wraps Radix `Toast.Provider`, renders the `ToastList` inside it, and
 * accepts the application's child tree so the viewport portal has a stable
 * context root.
 *
 * The provider uses `label="Notification"` for Radix's screen-reader
 * announcements, and `duration={Infinity}` at the provider level as a safety
 * net (individual toasts also override duration to Infinity).
 *
 * @example
 * ```tsx
 * <ToastProvider>
 *   <App />
 *   <ToastViewport />
 * </ToastProvider>
 * ```
 */
export function ToastProvider({ children }: ToastProviderProps): React.JSX.Element {
  return (
    <Toast.Provider label="Notification" duration={Infinity}>
      {children}
      <ToastList />
    </Toast.Provider>
  )
}

/**
 * Viewport component — mount this once inside `ToastProvider`, typically as a
 * sibling of the application root (after children), so it renders above all
 * other content.
 *
 * Applies the `.toast-viewport` semantic class for fixed positioning and
 * stacking order.
 *
 * @example
 * ```tsx
 * <ToastProvider>
 *   <App />
 *   <ToastViewport />
 * </ToastProvider>
 * ```
 */
export function ToastViewport(): React.JSX.Element {
  return <Toast.Viewport className="toast-viewport" />
}
