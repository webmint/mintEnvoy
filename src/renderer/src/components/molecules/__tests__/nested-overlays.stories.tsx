/**
 * nested-overlays.stories.tsx — Playwright CT fixture components for AC-12.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not in the test file itself).
 * This file exports reusable fixture wrappers for nested-overlay CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 *
 * Covers AC-12:
 *   - Escape closes only the TOPMOST overlay (dropdown inside modal → Escape
 *     closes dropdown, modal stays open; second Escape closes modal).
 *   - Focus trap / return nest correctly at each close.
 *   - z-order: toast renders above modal scrim.
 *   - Reduced-motion: Modal + Toast both have animation-name:none when
 *     prefers-reduced-motion:reduce is active.
 */

import { useEffect, useState } from 'react'
import { Modal } from '@renderer/components/molecules/Modal'
import { Dropdown } from '@renderer/components/molecules/Dropdown'
import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
import { toastStore } from '@renderer/lib/toastStore'

// ---------------------------------------------------------------------------
// NestedOverlayFixture
// ---------------------------------------------------------------------------

/**
 * Fixture for AC-12 nested-overlay Escape-layering test.
 *
 * Renders:
 *   - A trigger button that opens the Modal.
 *   - Inside the Modal: a Dropdown trigger button that opens a 2-item menu.
 *   - The whole tree is wrapped in ToastProvider/Viewport for AC-12 toast-over-
 *     modal assertions.
 *
 * data-testids:
 *   ct-overlay-modal-trigger    — button that opens the modal
 *   ct-overlay-dropdown-trigger — button inside the modal that opens the dropdown
 *   ct-overlay-toast-btn        — button inside the modal that fires a toast
 *   ct-overlay-modal-status     — text: "open" | "closed" (reflects modal state)
 *   ct-overlay-dropdown-status  — text: "open" | "closed" (reflects dropdown state)
 */
export function NestedOverlayFixture(): React.JSX.Element {
  const [modalOpen, setModalOpen] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)

  /** Clear the toast store on unmount so tests are isolated. */
  useEffect(() => {
    return () => {
      toastStore.getState().clearAll()
    }
  }, [])

  return (
    <ToastProvider>
      {/* Status indicators — read by CT assertions without relying on ARIA queries */}
      <div data-testid="ct-overlay-modal-status">{modalOpen ? 'open' : 'closed'}</div>
      <div data-testid="ct-overlay-dropdown-status">{dropdownOpen ? 'open' : 'closed'}</div>

      {/*
       * Pass the open button as the `trigger` prop so Radix Dialog.Trigger
       * wraps it and sets triggerRef — enabling correct focus-return on close
       * (AC-12).  In controlled mode, Dialog.Trigger still registers itself
       * so onCloseAutoFocus can call triggerRef.current.focus().
       */}
      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="Nested overlay test"
        description="A dropdown and a toast fire from inside this modal."
        trigger={
          <button data-testid="ct-overlay-modal-trigger" onClick={() => setModalOpen(true)}>
            Open modal
          </button>
        }
      >
        {/* Dropdown nested inside the modal body */}
        <Dropdown
          open={dropdownOpen}
          onOpenChange={setDropdownOpen}
          trigger={<button data-testid="ct-overlay-dropdown-trigger">Open dropdown</button>}
          items={[
            { id: 'item-a', label: 'Item A', onSelect: () => setDropdownOpen(false) },
            { id: 'item-b', label: 'Item B', onSelect: () => setDropdownOpen(false) }
          ]}
        />

        {/* Toast trigger */}
        <button
          data-testid="ct-overlay-toast-btn"
          onClick={() => {
            toastStore.getState().enqueue('Toast over modal', { variant: 'info' })
          }}
        >
          Fire toast
        </button>
      </Modal>

      {/* ToastViewport portals to body with z-index: max — above all overlays */}
      <ToastViewport />
    </ToastProvider>
  )
}

// ---------------------------------------------------------------------------
// ReducedMotionComposedFixture
// ---------------------------------------------------------------------------

/**
 * Fixture for the composed reduced-motion test (Finding 5).
 *
 * Renders a Modal (immediately open) and fires a Toast on mount so both
 * .modal-content / .modal-overlay and .toast are in the DOM simultaneously.
 * Intended to be mounted after `page.emulateMedia({ reducedMotion: 'reduce' })`
 * so the CT can assert that both elements have `animation-name: none`.
 *
 * data-testids:
 *   rm-modal-trigger — button wired to open the modal (for fixture completeness)
 */
export function ReducedMotionComposedFixture(): React.JSX.Element {
  const [modalOpen, setModalOpen] = useState(true)

  /** Fire a toast and clear the store on unmount. */
  useEffect(() => {
    toastStore.getState().enqueue('Reduced-motion toast', { variant: 'info' })
    return () => {
      toastStore.getState().clearAll()
    }
  }, [])

  return (
    <ToastProvider>
      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title="Reduced-motion modal"
        trigger={
          <button data-testid="rm-modal-trigger" onClick={() => setModalOpen(true)}>
            Open modal
          </button>
        }
      >
        <p>Modal body</p>
      </Modal>
      <ToastViewport />
    </ToastProvider>
  )
}
