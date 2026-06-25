/**
 * PrimitivesDemo — dev-only visual QA gallery for all UI primitives.
 *
 * Renders every primitive component (Icon, Dropdown, Modal, Toast, Tabs) in
 * all documented states so developers can visually inspect and manually QA
 * them without running the full app.
 *
 * ## Dev-only guard
 *
 * The component guards itself with an early `if (!import.meta.env.DEV) return null`
 * as belt-and-suspenders protection if the caller omits the gate.
 *
 * ## Mounting
 *
 * PrimitivesDemo is currently NOT mounted in App.tsx. It is registered and
 * available for development use but is not wired into the composition root.
 * A future feature (feature 005) will handle mounting.
 *
 * @module PrimitivesDemo
 */
import './PrimitivesDemo.css'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Icon } from '@renderer/components/atoms/Icon'
import { Dropdown, DropdownItem, DropdownSeparator } from '@renderer/components/molecules/Dropdown'
import { Modal, ModalClose } from '@renderer/components/molecules/Modal'
import { Tabs, TabDescriptor } from '@renderer/components/molecules/Tabs'
import { toast } from '@renderer/lib/toastStore'
import { selectNeighborId } from '@renderer/lib/tabsStore'

// ---------------------------------------------------------------------------
// Icon section
// ---------------------------------------------------------------------------

/** Renders the Icon atom in several states for visual QA. */
function IconSection(): React.JSX.Element {
  return (
    <section className="demo-section">
      <h2 className="demo-section__title">Icon</h2>

      {/* Grid of icons at default (16px) size */}
      <div className="demo-row">
        <h3 className="demo-row__label">16px — decorative (aria-hidden)</h3>
        <div className="demo-icon-grid">
          <Icon name="send" size={16} />
          <Icon name="search" size={16} />
          <Icon name="check" size={16} />
          <Icon name="alert" size={16} />
          <Icon name="info" size={16} />
          <Icon name="trash" size={16} />
          <Icon name="copy" size={16} />
          <Icon name="cog" size={16} />
        </div>
      </div>

      {/* Larger size */}
      <div className="demo-row">
        <h3 className="demo-row__label">24px — decorative</h3>
        <div className="demo-icon-grid">
          <Icon name="send" size={24} />
          <Icon name="search" size={24} />
          <Icon name="check" size={24} />
          <Icon name="alert" size={24} />
          <Icon name="info" size={24} />
          <Icon name="bolt" size={24} />
          <Icon name="star" size={24} />
          <Icon name="moon" size={24} />
        </div>
      </div>

      {/* Accessible icon with label */}
      <div className="demo-row">
        <h3 className="demo-row__label">Labeled (accessible &mdash; role=&quot;img&quot;)</h3>
        <div className="demo-icon-grid">
          <Icon name="send" size={20} label="Send request" />
          <Icon name="trash" size={20} label="Delete item" />
          <Icon name="info" size={20} label="Information" />
        </div>
      </div>

      {/* Unknown name → fallback diamond placeholder */}
      <div className="demo-row">
        <h3 className="demo-row__label">Unknown name → fallback diamond</h3>
        <div className="demo-icon-grid">
          {/* Cast to IconName: demonstrating that resolveIcon never throws */}
          <Icon name={'__not_a_real_icon__' as Parameters<typeof Icon>[0]['name']} size={20} />
        </div>
      </div>

      {/* Spin modifier */}
      <div className="demo-row">
        <h3 className="demo-row__label">Spin modifier (icon--spin)</h3>
        <div className="demo-icon-grid">
          <Icon name="cog" size={20} className="icon--spin" />
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Dropdown section
// ---------------------------------------------------------------------------

/** Renders the Dropdown molecule in several states for visual QA. */
function DropdownSection(): React.JSX.Element {
  const [basicOpen, setBasicOpen] = useState(false)
  const [iconOpen, setIconOpen] = useState(false)
  const [childrenOpen, setChildrenOpen] = useState(false)

  return (
    <section className="demo-section">
      <h2 className="demo-section__title">Dropdown</h2>

      {/* Basic items array API */}
      <div className="demo-row">
        <h3 className="demo-row__label">Items array API (disabled item included)</h3>
        <Dropdown
          open={basicOpen}
          onOpenChange={setBasicOpen}
          trigger={
            <button className="demo-button" type="button">
              Open menu
              <Icon name="chevronDown" size={14} />
            </button>
          }
          items={[
            {
              id: 'copy',
              label: 'Copy URL',
              onSelect: () => {
                toast.success('URL copied')
              }
            },
            {
              id: 'share',
              label: 'Share',
              onSelect: () => {
                toast.info('Share triggered')
              }
            },
            {
              id: 'disabled-item',
              label: 'Unavailable action',
              onSelect: () => {},
              disabled: true
            }
          ]}
        />
      </div>

      {/* Items with icons */}
      <div className="demo-row">
        <h3 className="demo-row__label">Items with leading icons</h3>
        <Dropdown
          open={iconOpen}
          onOpenChange={setIconOpen}
          trigger={
            <button className="demo-button" type="button">
              Actions
              <Icon name="more" size={14} />
            </button>
          }
          items={[
            {
              id: 'save',
              label: 'Save',
              icon: 'save',
              onSelect: () => {
                toast.success('Saved')
              }
            },
            {
              id: 'download',
              label: 'Download',
              icon: 'download',
              onSelect: () => {
                toast.info('Downloading…')
              }
            },
            {
              id: 'delete',
              label: 'Delete',
              icon: 'trash',
              onSelect: () => {
                toast.error('Deleted')
              }
            },
            {
              id: 'disabled-with-icon',
              label: 'Locked action',
              icon: 'lock',
              onSelect: () => {},
              disabled: true
            }
          ]}
        />
      </div>

      {/* Children API with separator and label */}
      <div className="demo-row">
        <h3 className="demo-row__label">Children API (separator + label)</h3>
        <Dropdown
          open={childrenOpen}
          onOpenChange={setChildrenOpen}
          trigger={
            <button className="demo-button" type="button">
              File
            </button>
          }
        >
          <DropdownItem
            onSelect={() => {
              toast.info('New file')
            }}
            icon="plus"
          >
            New file
          </DropdownItem>
          <DropdownItem
            onSelect={() => {
              toast.info('Opened')
            }}
            icon="folderOpen"
          >
            Open…
          </DropdownItem>
          <DropdownSeparator />
          <DropdownItem
            onSelect={() => {
              toast.success('Saved')
            }}
            icon="save"
          >
            Save
          </DropdownItem>
          <DropdownItem onSelect={() => {}} disabled>
            Export (unavailable)
          </DropdownItem>
        </Dropdown>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Modal section
// ---------------------------------------------------------------------------

/** Renders the Modal molecule in several states for visual QA. */
function ModalSection(): React.JSX.Element {
  const [basicOpen, setBasicOpen] = useState(false)
  const [descOpen, setDescOpen] = useState(false)
  const [nestedOpen, setNestedOpen] = useState(false)
  const [nestedDropdownOpen, setNestedDropdownOpen] = useState(false)

  return (
    <section className="demo-section">
      <h2 className="demo-section__title">Modal</h2>

      {/* Basic modal — title + children + close */}
      <div className="demo-row">
        <h3 className="demo-row__label">Basic modal (title + close button)</h3>
        <button
          className="demo-button"
          type="button"
          onClick={() => {
            setBasicOpen(true)
          }}
        >
          Open basic modal
        </button>
        <Modal open={basicOpen} onOpenChange={setBasicOpen} title="Basic modal">
          <p className="demo-modal-body">
            This is the modal body. Press <kbd>Escape</kbd>, click the overlay, or the button below
            to close.
          </p>
          <div className="demo-modal-actions">
            <ModalClose asChild>
              <button className="demo-button" type="button">
                Close
              </button>
            </ModalClose>
          </div>
        </Modal>
      </div>

      {/* Modal with description */}
      <div className="demo-row">
        <h3 className="demo-row__label">Modal with description</h3>
        <button
          className="demo-button"
          type="button"
          onClick={() => {
            setDescOpen(true)
          }}
        >
          Open modal with description
        </button>
        <Modal
          open={descOpen}
          onOpenChange={setDescOpen}
          title="Confirm action"
          description="This action cannot be undone. Are you sure you want to proceed?"
        >
          <div className="demo-modal-actions">
            <ModalClose asChild>
              <button className="demo-button" type="button">
                Cancel
              </button>
            </ModalClose>
            <button
              className="demo-button demo-button--primary"
              type="button"
              onClick={() => {
                toast.success('Action confirmed')
                setDescOpen(false)
              }}
            >
              Confirm
            </button>
          </div>
        </Modal>
      </div>

      {/* Modal containing a Dropdown (z-index nesting) */}
      <div className="demo-row">
        <h3 className="demo-row__label">Modal containing a Dropdown (nesting QA)</h3>
        <button
          className="demo-button"
          type="button"
          onClick={() => {
            setNestedOpen(true)
          }}
        >
          Open modal with nested dropdown
        </button>
        <Modal
          open={nestedOpen}
          onOpenChange={setNestedOpen}
          title="Modal with nested dropdown"
          description="The dropdown inside should render above the modal overlay."
        >
          <div className="demo-modal-body">
            <Dropdown
              open={nestedDropdownOpen}
              onOpenChange={setNestedDropdownOpen}
              trigger={
                <button className="demo-button" type="button">
                  Nested dropdown
                  <Icon name="chevronDown" size={14} />
                </button>
              }
              items={[
                {
                  id: 'opt-a',
                  label: 'Option A',
                  onSelect: () => {
                    toast.info('Option A selected')
                  }
                },
                {
                  id: 'opt-b',
                  label: 'Option B',
                  onSelect: () => {
                    toast.info('Option B selected')
                  }
                }
              ]}
            />
          </div>
          <div className="demo-modal-actions">
            <ModalClose asChild>
              <button className="demo-button" type="button">
                Close
              </button>
            </ModalClose>
          </div>
        </Modal>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Toast section
// ---------------------------------------------------------------------------

/** Fires multiple toasts in rapid succession for queue/stacking QA. */
function fireStack(): void {
  toast.info('Stack: info message')
  toast.success('Stack: success message')
  toast.warning('Stack: warning message')
  toast.error('Stack: error message')
}

/** Renders the Toast molecule's imperative API buttons for manual QA. */
function ToastSection(): React.JSX.Element {
  // Track handles from the rapid-fire burst so they can be cleared on unmount.
  // Without cleanup, stale timers fire toast() after the component unmounts,
  // which triggers state updates on an unmounted tree (dev-only, but noisy).
  const rapidTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    const handles = rapidTimersRef.current
    return () => {
      handles.forEach(clearTimeout)
      handles.length = 0
    }
  }, [])

  /** Fires toasts with a very short delay to exercise queue under load. */
  function fireRapid(): void {
    for (let i = 1; i <= 5; i++) {
      // Use setTimeout to spread them across the JS task queue; this produces
      // visible stacking without relying on async/await in the click handler.
      const handle = setTimeout(() => {
        toast(`Rapid fire #${i}`, { variant: i % 2 === 0 ? 'success' : 'info', duration: 8000 })
      }, i * 80)
      rapidTimersRef.current.push(handle)
    }
  }

  return (
    <section className="demo-section">
      <h2 className="demo-section__title">Toast</h2>
      <p className="demo-section__note">
        ToastProvider + ToastViewport are mounted at App root — toasts render globally above all
        overlays.
      </p>

      {/* Individual variant buttons */}
      <div className="demo-row">
        <h3 className="demo-row__label">Single toasts by variant</h3>
        <div className="demo-button-row">
          <button
            className="demo-button"
            type="button"
            onClick={() => {
              toast.info('Info notification')
            }}
          >
            <Icon name="info" size={14} />
            Info
          </button>
          <button
            className="demo-button"
            type="button"
            onClick={() => {
              toast.success('Success — operation completed')
            }}
          >
            <Icon name="check" size={14} />
            Success
          </button>
          <button
            className="demo-button"
            type="button"
            onClick={() => {
              toast.warning('Warning — check your input')
            }}
          >
            <Icon name="alert" size={14} />
            Warning
          </button>
          <button
            className="demo-button"
            type="button"
            onClick={() => {
              toast.error('Error — request failed')
            }}
          >
            <Icon name="x" size={14} />
            Error
          </button>
        </div>
      </div>

      {/* Stacked / rapid-fire */}
      <div className="demo-row">
        <h3 className="demo-row__label">Stacked + rapid-fire (queue QA)</h3>
        <div className="demo-button-row">
          <button className="demo-button" type="button" onClick={fireStack}>
            Fire 4 at once (stacked)
          </button>
          <button className="demo-button" type="button" onClick={fireRapid}>
            Rapid-fire 5 (80 ms apart)
          </button>
        </div>
      </div>

      {/* Long message */}
      <div className="demo-row">
        <h3 className="demo-row__label">Long message (truncation / wrapping QA)</h3>
        <button
          className="demo-button"
          type="button"
          onClick={() => {
            toast.warning(
              'This is a very long toast message intended to exercise how the toast component handles text that extends beyond a comfortable single-line width.'
            )
          }}
        >
          Fire long message
        </button>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Tabs section
// ---------------------------------------------------------------------------

/** Tab descriptors for the request-pane set (6 tabs). */
const REQUEST_TABS: TabDescriptor[] = [
  { id: 'params', label: 'Params' },
  { id: 'auth', label: 'Auth' },
  { id: 'headers', label: 'Headers' },
  { id: 'body', label: 'Body' },
  { id: 'tests', label: 'Tests' },
  { id: 'code', label: 'Code' }
]

/** Tab descriptors for the response-pane set (4 tabs). */
const RESPONSE_TABS: TabDescriptor[] = [
  { id: 'resp-body', label: 'Body' },
  { id: 'resp-headers', label: 'Headers' },
  { id: 'resp-cookies', label: 'Cookies' },
  { id: 'resp-test-results', label: 'Test Results' }
]

/** Initial tab descriptors for the closable demo row. */
const INITIAL_CLOSABLE_TABS: TabDescriptor[] = [
  { id: 'cl-get', label: 'GET /users', badge: '●' },
  { id: 'cl-post', label: 'POST /auth' },
  { id: 'cl-put', label: 'PUT /profile' },
  { id: 'cl-delete', label: 'DELETE /item' }
]

/** Counter used to generate unique ids when adding new demo tabs. */
let closableDemoCounter = INITIAL_CLOSABLE_TABS.length + 1

/** Renders the Tabs molecule in several states for visual QA. */
function TabsSection(): React.JSX.Element {
  const [requestActiveId, setRequestActiveId] = useState('params')
  const [responseActiveId, setResponseActiveId] = useState('resp-body')

  // Closable demo state: the caller owns both the tab list and the active id.
  const [closableTabs, setClosableTabs] = useState<TabDescriptor[]>(INITIAL_CLOSABLE_TABS)
  const [closableActiveId, setClosableActiveId] = useState('cl-get')

  /** Remove the closed tab; if it was active, move focus to a neighbor. */
  const handleClose = useCallback(
    (id: string) => {
      // Guard: never remove the last remaining tab.
      setClosableTabs((prev) => {
        if (prev.length <= 1) return prev
        return prev.filter((t) => t.id !== id)
      })
      // If the closed tab was active, move focus to a neighbor.
      // This setState call is intentionally OUTSIDE the updater above so that
      // the updater stays pure (React may invoke pure updaters twice in StrictMode).
      setClosableActiveId((currentActiveId) => {
        if (currentActiveId !== id) return currentActiveId
        // closableTabs here is the latest committed list (useCallback re-runs when it
        // changes); selectNeighborId needs the pre-removal list + index.
        const prev = closableTabs
        if (prev.length <= 1) return currentActiveId
        const idx = prev.findIndex((t) => t.id === id)
        return selectNeighborId(prev, idx)
      })
    },
    [closableTabs]
  )

  /** Append a new demo tab to the end of the list. */
  function handleAddTab(): void {
    const newId = `cl-new-${closableDemoCounter}`
    closableDemoCounter += 1
    const newTab: TabDescriptor = { id: newId, label: `New tab ${closableDemoCounter - 1}` }
    setClosableTabs((prev) => [...prev, newTab])
    setClosableActiveId(newId)
  }

  return (
    <section className="demo-section">
      <h2 className="demo-section__title">Tabs</h2>

      {/* Request-pane tab set (6 tabs) */}
      <div className="demo-row">
        <h3 className="demo-row__label">Request pane (6 tabs)</h3>
        <Tabs
          aria-label="Request sections"
          tabs={REQUEST_TABS}
          activeId={requestActiveId}
          onChange={setRequestActiveId}
        />
      </div>

      {/* Response-pane tab set (4 tabs) */}
      <div className="demo-row">
        <h3 className="demo-row__label">Response pane (4 tabs)</h3>
        <Tabs
          aria-label="Response sections"
          tabs={RESPONSE_TABS}
          activeId={responseActiveId}
          onChange={setResponseActiveId}
        />
      </div>

      {/* Closable tabs demo (✕ button + dirty-dot badge + add action) */}
      <div className="demo-row">
        <h3 className="demo-row__label">Closable tabs (✕ + dirty marker)</h3>
        <Tabs
          aria-label="Closable request tabs demo"
          tabs={closableTabs}
          activeId={closableActiveId}
          onChange={setClosableActiveId}
          closable
          onClose={handleClose}
          actions={
            <button className="demo-button" type="button" onClick={handleAddTab}>
              +
            </button>
          }
        />
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Root export
// ---------------------------------------------------------------------------

/**
 * Dev-only primitives gallery.
 *
 * Returns `null` in production builds so Vite can tree-shake this module
 * and all its transitive imports from the production bundle (see module
 * doc-comment for the full guard explanation).
 *
 * Mount inside App.tsx behind the same guard:
 *   `{import.meta.env.DEV && <PrimitivesDemo />}`
 */
export function PrimitivesDemo(): React.JSX.Element | null {
  // Production guard — Vite replaces import.meta.env.DEV with `false` at
  // build time, making this branch statically unreachable. esbuild / Rollup
  // then tree-shakes the entire module out of the production bundle.
  if (!import.meta.env.DEV) {
    return null
  }

  return (
    <main className="demo-root" aria-label="Primitives demo gallery">
      <header className="demo-header">
        <h1 className="demo-header__title">Primitives Gallery</h1>
        <p className="demo-header__subtitle">
          Dev-only visual QA surface — not shipped to production
        </p>
      </header>
      <IconSection />
      <DropdownSection />
      <ModalSection />
      <ToastSection />
      <TabsSection />
    </main>
  )
}

export default PrimitivesDemo
