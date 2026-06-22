/**
 * Toast.stories.tsx — Playwright CT fixture components for Toast.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not in the test file itself).
 * This file exports reusable fixture wrappers for Toast CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 */
import { useEffect } from 'react'
import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
import { toastStore } from '@renderer/lib/toastStore'
import type { ToastVariant } from '@renderer/lib/toastStore'

/** Props for the ToastWithSeededMessage fixture. */
export interface ToastWithSeededMessageProps {
  /** Message to enqueue when the component mounts in the browser. */
  message: string
  /**
   * Toast variant to use when seeding.
   * @default 'info'
   */
  variant?: ToastVariant
}

/**
 * Fixture component: mounts the full ToastProvider/Viewport stack and enqueues
 * a single toast on mount (via a browser-side useEffect) so there is always a
 * visible `<li class="toast">` for CT assertions.
 *
 * Cleanup: the toast store is cleared on unmount so tests are isolated.
 */
export function ToastWithSeededMessage({
  message,
  variant = 'info'
}: ToastWithSeededMessageProps): React.JSX.Element {
  useEffect(() => {
    toastStore.getState().enqueue(message, { variant })
    return () => {
      toastStore.getState().clearAll()
    }
  }, [message, variant])

  return (
    <ToastProvider>
      <ToastViewport />
    </ToastProvider>
  )
}
