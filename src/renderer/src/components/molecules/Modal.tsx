/**
 * Modal — molecule component wrapping Radix Dialog.
 *
 * Provides a controlled modal dialog with:
 * - Focus trap while open (Radix FocusScope — AC-6)
 * - Escape-to-close dispatching `onOpenChange(false)` (Radix DismissableLayer — AC-7)
 * - Focus return to trigger element on close (Radix FocusScope — AC-3)
 * - Viewport-covering overlay / scrim (Dialog.Overlay — AC-6)
 * - Body scroll lock (Radix RemoveScroll, applied inside Dialog.Overlay — AC-6)
 * - Animations gated behind `@media (prefers-reduced-motion: reduce)` (AC-14)
 * - Escaped JSX text rendering for title/description — never dangerouslySetInnerHTML (CWE-79)
 * - No inline styles (AC-18)
 * - No Node/Electron imports (AC-19)
 * - Strictly typed, no `any` (§3.1)
 *
 * ## Usage
 *
 * ```tsx
 * import { Modal } from '@renderer/components/molecules/Modal'
 *
 * function Example(): React.JSX.Element {
 *   const [open, setOpen] = React.useState(false)
 *
 *   return (
 *     <>
 *       <button onClick={() => setOpen(true)}>Open</button>
 *       <Modal
 *         open={open}
 *         onOpenChange={setOpen}
 *         title="Confirm deletion"
 *         description="This action cannot be undone."
 *       >
 *         <button onClick={() => setOpen(false)}>Cancel</button>
 *         <button onClick={() => { doDelete(); setOpen(false) }}>Delete</button>
 *       </Modal>
 *     </>
 *   )
 * }
 * ```
 *
 * ## Accessibility
 *
 * - Always supply a `title` prop (renders as Dialog.Title — the accessible name).
 *   If you must suppress the visible title, use a screen-reader-only class
 *   and supply `aria-label` on the Dialog.Content via `contentProps`.
 * - Dialog.Description is optional; supply it for additional context.
 *
 * ## Security
 *
 * `title` and `description` are rendered as JSX text children (React text nodes).
 * React escapes all text children — arbitrary strings including HTML injection
 * payloads are rendered as literal text, never parsed as markup (CWE-79).
 * `dangerouslySetInnerHTML` is NEVER used.
 *
 * @module Modal
 */

import './Modal.css'

import { Dialog } from 'radix-ui'
import { cx } from '@renderer/lib/cx'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Props passed through to Dialog.Content (excludes className, managed internally). */
export type ModalContentProps = Omit<
  React.ComponentPropsWithoutRef<typeof Dialog.Content>,
  'className'
>

/** Public props for the Modal component. */
export interface ModalProps {
  /**
   * Controls whether the modal is open.
   * The caller owns this state (controlled component — AC-11).
   */
  open: boolean

  /**
   * Called when Radix requests an open-state change (Escape key, overlay click,
   * or any internal Radix close trigger).  The new requested state is passed as
   * the argument; the caller decides whether to honor it.  AC-11.
   */
  onOpenChange: (open: boolean) => void

  /**
   * Visible title rendered inside Dialog.Title — required for an accessible name.
   * Rendered as a JSX text node (escaped; never treated as HTML — CWE-79).
   * To hide the title visually, apply a sr-only class via `titleClassName`.
   */
  title: string

  /**
   * Optional accessible description rendered inside Dialog.Description.
   * Rendered as a JSX text node (escaped — CWE-79).
   */
  description?: string

  /** Additional class name applied to Dialog.Content. */
  className?: string

  /**
   * Optional trigger element.  When provided it is wrapped by Dialog.Trigger
   * so Radix can track it for focus-return after close (AC-3).
   * The trigger must be a single focusable element (button, anchor, etc.).
   */
  trigger?: React.ReactNode

  /**
   * Modal body content — rendered inside Dialog.Content after the title/description.
   */
  children?: React.ReactNode

  /**
   * Optional class name applied to Dialog.Title.
   * Use a screen-reader-only class here to visually hide the title while
   * preserving accessibility.
   */
  titleClassName?: string

  /**
   * Extra props forwarded to Dialog.Content (e.g. aria-label when no visible
   * title is provided, onPointerDownOutside to prevent overlay-click-to-close).
   * `className` is excluded — use the `className` prop above instead.
   */
  contentProps?: ModalContentProps
}

// ---------------------------------------------------------------------------
// Modal component
// ---------------------------------------------------------------------------

/**
 * Controlled modal dialog built on Radix Dialog primitives.
 *
 * Accessibility behaviour is provided by Radix:
 * - **Focus trap** (FocusScope): Tab cycles inside the open dialog; focus
 *   cannot escape to the document while the modal is open (AC-6).
 * - **Focus return** (FocusScope): when the dialog closes, focus returns to
 *   the element that triggered it, or to the Dialog.Trigger child (AC-3).
 * - **Escape close** (DismissableLayer): pressing Escape fires
 *   `onOpenChange(false)`; the caller controls whether the dialog actually
 *   closes (AC-7).
 * - **Scroll lock** (RemoveScroll, inside Dialog.Overlay): body scroll is
 *   locked while the overlay is rendered (AC-6).
 * - **ARIA wiring**: Dialog.Root sets `role="dialog"` + `aria-modal="true"`;
 *   Dialog.Title provides the accessible name via `aria-labelledby`.
 *
 * @param props - See {@link ModalProps}.
 */
export function Modal({
  open,
  onOpenChange,
  title,
  description,
  className,
  trigger,
  children,
  titleClassName,
  contentProps
}: ModalProps): React.JSX.Element {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {/* Dialog.Trigger is rendered only when a trigger element is supplied.
          Radix tracks this element so focus returns to it on close (AC-3). */}
      {trigger !== undefined && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}

      {/* Dialog.Portal renders the overlay and content outside the current DOM
          tree (appended to document.body), ensuring correct stacking without
          needing z-index hacks in the parent hierarchy. */}
      <Dialog.Portal>
        {/* Dialog.Overlay — the scrim / backdrop.
            Radix mounts RemoveScroll here, which locks body scroll while
            the overlay is in the DOM (AC-6).
            The `.modal-overlay` class handles positioning and appearance. */}
        <Dialog.Overlay className="modal-overlay" />

        {/* Dialog.Content — the dialog panel.
            Radix mounts FocusScope here (focus trap, AC-6) and
            DismissableLayer (Escape → onOpenChange(false), AC-7).
            Focus returns to the trigger element when this unmounts (AC-3). */}
        <Dialog.Content className={cx('modal-content', className)} {...contentProps}>
          {/* Dialog.Title provides the accessible name (aria-labelledby).
              Rendered as escaped text — never dangerouslySetInnerHTML (CWE-79).
              Use `titleClassName="modal-title--sr-only"` to hide the title
              visually while preserving it in the accessibility tree. */}
          <Dialog.Title className={cx('modal-title', titleClassName)}>{title}</Dialog.Title>

          {/* Dialog.Description provides an optional accessible description
              (aria-describedby).  Rendered as escaped text — never HTML (CWE-79). */}
          {description !== undefined && (
            <Dialog.Description className="modal-description">{description}</Dialog.Description>
          )}

          {/* Caller-provided body content */}
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ---------------------------------------------------------------------------
// Named re-export of Radix Dialog.Close for callers that need a close button
// inside the modal body without managing state themselves.
// ---------------------------------------------------------------------------

/**
 * Close button primitive — a thin re-export of `Dialog.Close`.
 *
 * Wrap your close button element with this so Radix wires `onOpenChange(false)`
 * automatically on click, without the caller needing to pass the setter down.
 *
 * @example
 * ```tsx
 * <Modal open={open} onOpenChange={setOpen} title="Settings">
 *   <ModalClose asChild>
 *     <button>Cancel</button>
 *   </ModalClose>
 * </Modal>
 * ```
 */
export const ModalClose = Dialog.Close
