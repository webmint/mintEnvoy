/**
 * Modal.stories.tsx — Playwright CT fixture components for Modal.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not in the test file itself).
 * This file exports reusable fixture wrappers for Modal CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 */

import { useState } from 'react'
import { Modal } from '@renderer/components/molecules/Modal'

// ---------------------------------------------------------------------------
// ModalFixture — a self-contained controlled modal for CT mounting
// ---------------------------------------------------------------------------

/** Props for the ModalFixture component. */
export interface ModalFixtureProps {
  /** Whether the modal starts open. */
  initialOpen?: boolean
  /** Title to render inside the modal. */
  title?: string
}

/**
 * Fixture component: renders a controlled Modal with a Dialog.Trigger button so
 * CT tests have a full interactive widget to probe.
 *
 * The modal starts open by default for reduced-motion animation assertions,
 * so there is always a `.modal-content` element to inspect.
 *
 * For focus-return tests (AC-3), pass `initialOpen={false}` and click
 * `ct-modal-trigger` — the Dialog.Trigger-wrapped button — to open. Radix
 * tracks that element and returns focus to it when the dialog closes.
 */
export function ModalFixture({
  initialOpen = true,
  title = 'CT test modal'
}: ModalFixtureProps): React.JSX.Element {
  const [open, setOpen] = useState(initialOpen)

  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title={title}
      description="CT fixture description"
      trigger={<button data-testid="ct-modal-trigger">Open modal</button>}
    >
      <button data-testid="ct-inner-btn" onClick={() => setOpen(false)}>
        Close
      </button>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// FocusTrapFixture — modal with multiple focusable elements for trap boundary
// ---------------------------------------------------------------------------

/**
 * Fixture for focus-trap boundary tests (AC-6).
 *
 * The modal body intentionally contains THREE focusable elements (an input, a
 * secondary button, and a close button) so the Tab-cycle boundary test can:
 *   - focus the LAST element and press Tab → assert focus wraps to the FIRST
 *   - focus the FIRST element and press Shift+Tab → assert focus wraps to the LAST
 *
 * data-testids used by the focus-trap CT test:
 *   ct-trap-first  — first focusable element inside the modal body
 *   ct-trap-second — second focusable element
 *   ct-trap-last   — last focusable element (third, just before the built-in close X)
 */
export function FocusTrapFixture(): React.JSX.Element {
  const [open, setOpen] = useState(true)

  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title="Focus trap test modal"
      trigger={<button data-testid="ct-trap-trigger">Open modal</button>}
    >
      <input data-testid="ct-trap-first" placeholder="First focusable" />
      <button data-testid="ct-trap-second">Second focusable</button>
      <button data-testid="ct-trap-last" onClick={() => setOpen(false)}>
        Close (last)
      </button>
    </Modal>
  )
}
