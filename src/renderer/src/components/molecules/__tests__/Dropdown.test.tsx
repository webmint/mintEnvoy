/**
 * Dropdown.test.tsx
 *
 * Interaction and contract tests for the Dropdown molecule component.
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## Test surface
 *
 * - AC-11: controlled open prop reflects open/closed state; onOpenChange fires
 *          on user-driven open (trigger click) and user-driven close (Escape).
 * - AC-4:  Escape key dismiss → onOpenChange(false).
 *          Click-outside dismiss is deferred to CT (jsdom has unreliable pointer
 *          event support for Radix DismissableLayer — see Dropdown.ct.tsx).
 * - AC-3:  Focus returns to trigger on close (best-effort in jsdom; authoritative
 *          coverage in Dropdown.ct.tsx with real Chromium).
 * - Item onSelect fires when an enabled item is selected.
 * - Disabled item's onSelect does NOT fire on click.
 * - Item label is rendered as escaped text (XSS safety / CWE-79).
 *
 * ## jsdom limitations
 *
 * Radix DismissableLayer's click-outside detection depends on the browser
 * pointer-event dispatch chain, which jsdom does not faithfully implement.
 * Assertions that require real pointer events (click-outside close) are
 * covered in Dropdown.ct.tsx instead, where a real Chromium engine is used.
 *
 * ## Portal behaviour
 *
 * Radix DropdownMenu renders content into a Portal (appended to document.body).
 * `screen.*` queries search the full document, so they find portal content
 * without additional setup.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  Dropdown,
  DropdownItem,
  DropdownLabel,
  DropdownSeparator
} from '@renderer/components/molecules/Dropdown'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface RenderDropdownOptions {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  withTrigger?: boolean
  items?: Array<{ id: string; label: string; onSelect: () => void; disabled?: boolean }>
  children?: React.ReactNode
}

/**
 * Render a Dropdown with sensible defaults.
 * Returns the render result and the onOpenChange mock.
 */
function renderDropdown(opts: RenderDropdownOptions = {}): {
  result: ReturnType<typeof render>
  onOpenChange: (open: boolean) => void
} {
  const {
    open = false,
    onOpenChange = vi.fn(),
    items = [
      { id: 'a', label: 'Action A', onSelect: vi.fn() },
      { id: 'b', label: 'Action B', onSelect: vi.fn() }
    ],
    children
  } = opts

  const trigger = <button data-testid="dropdown-trigger">Open</button>

  const result = render(
    <Dropdown
      open={open}
      onOpenChange={onOpenChange}
      trigger={trigger}
      items={children === undefined ? items : undefined}
    >
      {children}
    </Dropdown>
  )

  return { result, onOpenChange }
}

// ---------------------------------------------------------------------------
// AC-11 — controlled open prop and onOpenChange
// ---------------------------------------------------------------------------

describe('AC-11 — controlled open prop and onOpenChange', () => {
  it('does not render menu content when open=false', () => {
    renderDropdown({ open: false })
    // Radix DropdownMenu.Content is not in the DOM when closed
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('renders menu content when open=true', () => {
    renderDropdown({ open: true })
    expect(screen.getByRole('menu')).toBeInTheDocument()
  })

  it('renders item labels when open=true', () => {
    renderDropdown({ open: true })
    expect(screen.getByText('Action A')).toBeInTheDocument()
    expect(screen.getByText('Action B')).toBeInTheDocument()
  })

  it('calls onOpenChange(true) when the trigger is clicked while closed', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderDropdown({ open: false, onOpenChange })

    const trigger = screen.getByTestId('dropdown-trigger')
    await user.click(trigger)

    expect(onOpenChange).toHaveBeenCalledWith(true)
  })

  it('menu content disappears when open prop switches from true to false', () => {
    const onOpenChange = vi.fn()
    const { result } = renderDropdown({ open: true, onOpenChange })

    expect(screen.getByRole('menu')).toBeInTheDocument()

    // Re-render with open=false to simulate the caller honoring onOpenChange(false)
    result.rerender(
      <Dropdown
        open={false}
        onOpenChange={onOpenChange}
        trigger={<button data-testid="dropdown-trigger">Open</button>}
        items={[{ id: 'a', label: 'Action A', onSelect: vi.fn() }]}
      />
    )

    // The menu content must leave the DOM when open becomes false (AC-11)
    // Note: Radix applies an exit animation; in jsdom the element is removed synchronously.
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// AC-4 — Escape key fires onOpenChange(false)
// ---------------------------------------------------------------------------

describe('AC-4 — Escape key calls onOpenChange(false)', () => {
  it('pressing Escape while the menu is open dispatches onOpenChange(false)', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderDropdown({ open: true, onOpenChange })

    // Focus a menu item so Escape reaches Radix DismissableLayer
    const menuItems = screen.getAllByRole('menuitem')
    menuItems[0].focus()

    await user.keyboard('{Escape}')

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})

// ---------------------------------------------------------------------------
// AC-3 — focus returns to trigger on close (best-effort jsdom)
// ---------------------------------------------------------------------------

describe('AC-3 — focus returns to trigger on close (jsdom best-effort)', () => {
  it('trigger remains in the DOM after the menu closes', async () => {
    const onOpenChange = vi.fn()

    const { result } = renderDropdown({ open: true, onOpenChange })

    // Close by re-rendering with open=false
    result.rerender(
      <Dropdown
        open={false}
        onOpenChange={onOpenChange}
        trigger={<button data-testid="dropdown-trigger">Open</button>}
        items={[{ id: 'a', label: 'Action A', onSelect: vi.fn() }]}
      />
    )

    // Trigger must still be in the DOM — Radix has not destroyed it
    await waitFor(() => {
      expect(screen.getByTestId('dropdown-trigger')).toBeInTheDocument()
    })
    // Authoritative focus-return assertion is in Dropdown.ct.tsx (real Chromium)
  })
})

// ---------------------------------------------------------------------------
// Item onSelect
// ---------------------------------------------------------------------------

describe('item onSelect', () => {
  it('fires the item onSelect callback when an enabled item is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    renderDropdown({
      open: true,
      items: [{ id: 'click-me', label: 'Click Me', onSelect }]
    })

    const item = screen.getByText('Click Me')
    await user.click(item)

    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  it('does NOT fire onSelect when a disabled item is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    renderDropdown({
      open: true,
      items: [{ id: 'noop', label: 'Disabled Item', onSelect, disabled: true }]
    })

    const item = screen.getByText('Disabled Item')
    await user.click(item)

    expect(onSelect).not.toHaveBeenCalled()
  })

  it('disabled item has aria-disabled attribute', () => {
    renderDropdown({
      open: true,
      items: [{ id: 'dis', label: 'Disabled', onSelect: vi.fn(), disabled: true }]
    })

    const item = screen.getByText('Disabled').closest('[role="menuitem"]')
    expect(item).toHaveAttribute('aria-disabled', 'true')
  })
})

// ---------------------------------------------------------------------------
// XSS / CWE-79 — item labels escaped as text, never HTML
// ---------------------------------------------------------------------------

describe('security — XSS: item labels are rendered as escaped text', () => {
  it('renders an XSS img payload in a label as literal text — no <img> created', () => {
    const payload = '<img src=x onerror=alert(1)>'
    renderDropdown({
      open: true,
      items: [{ id: 'xss', label: payload, onSelect: vi.fn() }]
    })

    // The literal string must appear as text
    expect(screen.getByText(payload)).toBeInTheDocument()

    // No <img> must have been parsed from the payload
    expect(document.querySelectorAll('img')).toHaveLength(0)
  })

  it('renders a script-injection payload in a label as literal text', () => {
    const payload = '</li><script>alert(1)</script>'
    renderDropdown({
      open: true,
      items: [{ id: 'xss2', label: payload, onSelect: vi.fn() }]
    })

    expect(screen.getByText(payload)).toBeInTheDocument()
    expect(document.querySelectorAll('script')).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// Children API — DropdownItem / DropdownSeparator primitives
// ---------------------------------------------------------------------------

describe('children API', () => {
  it('renders items passed as children', () => {
    const onSelect = vi.fn()

    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownItem onSelect={onSelect}>Child Item</DropdownItem>
      </Dropdown>
    )

    expect(screen.getByText('Child Item')).toBeInTheDocument()
  })

  it('DropdownSeparator renders with the correct role', () => {
    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownItem onSelect={vi.fn()}>Before</DropdownItem>
        <DropdownSeparator />
        <DropdownItem onSelect={vi.fn()}>After</DropdownItem>
      </Dropdown>
    )

    // Radix renders DropdownMenu.Separator as role="separator"
    expect(screen.getByRole('separator')).toBeInTheDocument()
  })

  it('disabled DropdownItem child does not fire onSelect on click', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownItem onSelect={onSelect} disabled>
          Disabled Child
        </DropdownItem>
      </Dropdown>
    )

    const item = screen.getByText('Disabled Child')
    await user.click(item)

    expect(onSelect).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// DropdownLabel — non-interactive group label
// ---------------------------------------------------------------------------

describe('DropdownLabel', () => {
  it('renders the label text inside the menu', () => {
    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownLabel>File actions</DropdownLabel>
        <DropdownItem onSelect={vi.fn()}>Save</DropdownItem>
      </Dropdown>
    )

    expect(screen.getByText('File actions')).toBeInTheDocument()
  })

  it('does NOT carry role="menuitem" — it is a label, not interactive', () => {
    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownLabel>Section Header</DropdownLabel>
      </Dropdown>
    )

    const label = screen.getByText('Section Header')
    // The label element must not be a menuitem — it is purely presentational
    expect(label.closest('[role="menuitem"]')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// items-array API — icon field rendering
// ---------------------------------------------------------------------------

describe('items-array icon', () => {
  it('renders an svg icon for an item in the items array when the icon field is set', () => {
    render(
      <Dropdown
        open={true}
        onOpenChange={vi.fn()}
        trigger={<button>Open</button>}
        items={[{ id: 'copy', label: 'Copy URL', onSelect: vi.fn(), icon: 'copy' }]}
      />
    )

    const item = screen.getByRole('menuitem', { name: /copy url/i })
    // The Icon atom renders an aria-hidden <svg> inside the item
    const svg = item.querySelector('svg')
    expect(svg).not.toBeNull()

    // Prove the correct icon reached the Icon atom — not the fallback diamond.
    // The copy icon's path contains 'M3 11V4'; the fallback diamond contains 'M8 2l6 6-6 6-6-6 6-6z'.
    // Icon places geometry inside a <g> child (mirroring Icon.test.tsx geometry assertions).
    const geometryGroup = svg!.querySelector('g')
    expect(geometryGroup).not.toBeNull()
    expect(geometryGroup!.innerHTML).toContain('M3 11V4')
    expect(geometryGroup!.innerHTML).not.toContain('M8 2l6 6-6 6-6-6 6-6z')

    // Prove the Dropdown passes size={14} to <Icon> — a regression changing this size is caught here.
    expect(svg).toHaveAttribute('width', '14')
    expect(svg).toHaveAttribute('height', '14')
  })

  it('renders no svg for an items-array item without an icon field', () => {
    render(
      <Dropdown
        open={true}
        onOpenChange={vi.fn()}
        trigger={<button>Open</button>}
        items={[{ id: 'save', label: 'Save', onSelect: vi.fn() }]}
      />
    )

    const item = screen.getByRole('menuitem', { name: /save/i })
    expect(item.querySelector('svg')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// DropdownItem icon rendering
// ---------------------------------------------------------------------------

describe('DropdownItem icon', () => {
  it('renders an svg icon when the icon prop is supplied', () => {
    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownItem onSelect={vi.fn()} icon="copy">
          Copy URL
        </DropdownItem>
      </Dropdown>
    )

    const item = screen.getByRole('menuitem', { name: /copy url/i })
    // The Icon atom renders an aria-hidden <svg> inside the item
    const svg = item.querySelector('svg')
    expect(svg).not.toBeNull()
  })

  it('item with an icon is still selectable — onSelect fires on click', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <Dropdown open={true} onOpenChange={vi.fn()} trigger={<button>Open</button>}>
        <DropdownItem onSelect={onSelect} icon="copy">
          Copy URL
        </DropdownItem>
      </Dropdown>
    )

    const item = screen.getByRole('menuitem', { name: /copy url/i })
    await user.click(item)

    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})
