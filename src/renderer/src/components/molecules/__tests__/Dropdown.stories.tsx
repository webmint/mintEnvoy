/**
 * Dropdown.stories.tsx — Playwright CT fixture components for Dropdown.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers for Dropdown CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 */

import { useState } from 'react'
import { Dropdown } from '@renderer/components/molecules/Dropdown'

// ---------------------------------------------------------------------------
// DropdownFixture — a self-contained controlled dropdown for CT mounting
// ---------------------------------------------------------------------------

/** Props for the DropdownFixture component. */
export interface DropdownFixtureProps {
  /** Whether the dropdown starts open. */
  initialOpen?: boolean
}

/**
 * Fixture component: renders a controlled Dropdown with a trigger button and
 * three items (including one disabled) so CT tests have a full interactive
 * widget to probe.
 *
 * data-testids:
 *   ct-dropdown-trigger   — the trigger button (Dialog.Trigger-tracked for focus-return)
 *   ct-dropdown-item-a    — first enabled item
 *   ct-dropdown-item-b    — second enabled item
 *   ct-dropdown-item-dis  — disabled item
 */
export function DropdownFixture({ initialOpen = false }: DropdownFixtureProps): React.JSX.Element {
  const [open, setOpen] = useState(initialOpen)

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      trigger={<button data-testid="ct-dropdown-trigger">Open menu</button>}
      items={[
        {
          id: 'a',
          label: 'Item A',
          onSelect: () => {
            setOpen(false)
          }
        },
        {
          id: 'b',
          label: 'Item B',
          onSelect: () => {
            setOpen(false)
          }
        },
        {
          id: 'dis',
          label: 'Disabled',
          onSelect: () => {},
          disabled: true
        }
      ]}
    />
  )
}

// ---------------------------------------------------------------------------
// DropdownEdgeFixture — trigger near a viewport edge for AC-5 (edge-aware)
// ---------------------------------------------------------------------------

/**
 * Fixture for edge-aware positioning test (AC-5).
 *
 * The trigger is positioned near the bottom-right corner of the viewport using
 * a fixed position wrapper — the worst-case for a menu that defaults to
 * `side="bottom"` + `align="start"`.  With `avoidCollisions=true` (the
 * Dropdown default) and `collisionPadding={8}`, Radix should flip / shift the
 * content so it stays fully within the viewport bounds.
 *
 * The content panel is expected to have its bounding rect entirely inside the
 * window dimensions when this fixture is mounted at 600×400 viewport size.
 */
export function DropdownEdgeFixture(): React.JSX.Element {
  const [open, setOpen] = useState(false)

  return (
    /* Position the trigger near the bottom-right viewport edge */
    <div
      style={{
        position: 'fixed',
        bottom: 8,
        right: 8
      }}
    >
      <Dropdown
        open={open}
        onOpenChange={setOpen}
        trigger={
          <button data-testid="ct-edge-trigger" onClick={() => setOpen(true)}>
            Edge
          </button>
        }
        items={[
          { id: '1', label: 'Option 1', onSelect: () => {} },
          { id: '2', label: 'Option 2', onSelect: () => {} },
          { id: '3', label: 'Option 3', onSelect: () => {} }
        ]}
        side="bottom"
        align="start"
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// DropdownKeyboardFixture — for keyboard item activation (AC-2 / AC-3)
// ---------------------------------------------------------------------------

/**
 * Fixture for keyboard item-activation tests (Enter / Space select an item).
 *
 * Renders with a visible "last selected" output element so CT tests can assert
 * which item was activated without relying on side-effects outside the component.
 * Starts CLOSED so tests open the menu via keyboard (focus trigger → Enter/Space),
 * which causes Radix to register keyboard-manager mode and auto-focus the first item.
 *
 * data-testids:
 *   ct-kb-trigger        — trigger button
 *   ct-kb-last-selected  — text node showing the id of the last activated item
 *                          (empty string when nothing has been selected yet)
 */
export function DropdownKeyboardFixture(): React.JSX.Element {
  const [open, setOpen] = useState(false)
  const [lastSelected, setLastSelected] = useState('')

  return (
    <div>
      <Dropdown
        open={open}
        onOpenChange={setOpen}
        trigger={<button data-testid="ct-kb-trigger">Keyboard test</button>}
        items={[
          {
            id: 'first',
            label: 'First',
            onSelect: () => {
              setLastSelected('first')
              setOpen(false)
            }
          },
          {
            id: 'second',
            label: 'Second',
            onSelect: () => {
              setLastSelected('second')
              setOpen(false)
            }
          },
          {
            id: 'third',
            label: 'Third',
            onSelect: () => {
              setLastSelected('third')
              setOpen(false)
            }
          }
        ]}
      />
      <div data-testid="ct-kb-last-selected">{lastSelected}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// DropdownEdgeTopFixture — trigger near the TOP-LEFT edge (AC-5 second corner)
// ---------------------------------------------------------------------------

/**
 * Fixture for the top-left edge-aware positioning test (AC-5).
 *
 * The trigger is positioned near the top-left corner of the viewport using a
 * fixed-position wrapper — the complement to DropdownEdgeFixture which tests
 * the bottom-right corner.  With `side="bottom"` + `align="start"` and
 * `avoidCollisions=true`, the menu should shift / flip to remain fully within
 * the viewport without clipping the top or left edges.
 *
 * The test sets a small viewport (600×400) to make collision avoidance kick in.
 */
export function DropdownEdgeTopFixture(): React.JSX.Element {
  const [open, setOpen] = useState(false)

  return (
    /* Position the trigger near the top-left viewport edge */
    <div
      style={{
        position: 'fixed',
        top: 8,
        left: 8
      }}
    >
      <Dropdown
        open={open}
        onOpenChange={setOpen}
        trigger={
          <button data-testid="ct-edge-top-trigger" onClick={() => setOpen(true)}>
            Top Edge
          </button>
        }
        items={[
          { id: '1', label: 'Option 1', onSelect: () => {} },
          { id: '2', label: 'Option 2', onSelect: () => {} },
          { id: '3', label: 'Option 3', onSelect: () => {} }
        ]}
        side="top"
        align="start"
      />
    </div>
  )
}
