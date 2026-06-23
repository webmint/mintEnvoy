/**
 * Tabs.test.tsx
 *
 * Interaction and contract tests for the Tabs molecule component.
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## Test surface
 *
 * - AC-5:  Clicking an enabled tab calls onChange exactly once with that tab's id.
 *          Clicking the already-active tab also fires onChange once.
 * - AC-6:  ArrowLeft/ArrowRight move to the adjacent enabled tab with wrap-around;
 *          Home/End jump to the first/last enabled tab; each fires onChange once
 *          with the correct id. Disabled tabs in the middle and at boundaries are
 *          skipped.
 * - AC-7:  Container has role="tablist"; each button has role="tab"; aria-selected
 *          reflects activeId; no tab has aria-controls (intentional omission);
 *          roving tabindex — exactly one tab has tabIndex=0.
 * - AC-8:  A supplied actions slot renders outside the role="tablist" element.
 * - AC-9:  Clicking a disabled tab does NOT call onChange; a key that targets a
 *          disabled tab lands on the next enabled one, never fires with the
 *          disabled id.
 * - AC-10: Empty tabs array, activeId matching no tab, activeId matching a disabled
 *          tab — no tab has aria-selected="true"; first enabled tab still has
 *          tabIndex=0 (intentional WAI-ARIA fallback for keyboard reachability).
 * - badge: Badge rendered for string and number values; absent when undefined.
 */

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tabs } from '@renderer/components/molecules/Tabs'
import type { TabDescriptor } from '@renderer/components/molecules/Tabs'

// ---------------------------------------------------------------------------
// Shared tab fixtures
// ---------------------------------------------------------------------------

/** A standard mixed tab set: params (active), headers, body (disabled), auth. */
const MIXED_TABS: TabDescriptor[] = [
  { id: 'params', label: 'Params' },
  { id: 'headers', label: 'Headers' },
  { id: 'body', label: 'Body', disabled: true },
  { id: 'auth', label: 'Auth' }
]

/** Helper: render Tabs with sensible defaults and a spy onChange. */
function renderTabs(
  overrides: Partial<{
    tabs: TabDescriptor[]
    activeId: string
    actions: React.ReactNode
    ariaLabel: string
  }> = {}
): { onChange: ReturnType<typeof vi.fn> } {
  const onChange = vi.fn()

  render(
    <Tabs
      tabs={overrides.tabs ?? MIXED_TABS}
      activeId={overrides.activeId ?? 'params'}
      onChange={onChange}
      actions={overrides.actions}
      aria-label={overrides.ariaLabel ?? 'Test tabs'}
    />
  )

  return { onChange }
}

// ---------------------------------------------------------------------------
// AC-5 — click fires onChange exactly once with the tab id
// ---------------------------------------------------------------------------

describe('AC-5 — click on enabled tab', () => {
  it('clicking an enabled tab calls onChange exactly once with that tab id', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs()

    const headersTab = screen.getByRole('tab', { name: 'Headers' })
    await user.click(headersTab)

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('headers')
  })

  it('clicking the already-active tab still fires onChange exactly once', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'params' })

    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    await user.click(paramsTab)

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('params')
  })
})

// ---------------------------------------------------------------------------
// AC-6 — keyboard navigation: ArrowRight / ArrowLeft / Home / End
// ---------------------------------------------------------------------------

describe('AC-6 — keyboard navigation', () => {
  it('ArrowRight from the active tab moves to the next enabled tab', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'params' })

    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    paramsTab.focus()
    await user.keyboard('{ArrowRight}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('headers')
  })

  it('ArrowLeft from the active tab moves to the previous enabled tab', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'headers' })

    const headersTab = screen.getByRole('tab', { name: 'Headers' })
    headersTab.focus()
    await user.keyboard('{ArrowLeft}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('params')
  })

  it('ArrowRight wraps from the last enabled tab to the first enabled tab', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'auth' })

    const authTab = screen.getByRole('tab', { name: 'Auth' })
    authTab.focus()
    await user.keyboard('{ArrowRight}')

    // auth is the last enabled tab; wrapping goes to params (first enabled)
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('params')
  })

  it('ArrowLeft wraps from the first enabled tab to the last enabled tab', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'params' })

    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    paramsTab.focus()
    await user.keyboard('{ArrowLeft}')

    // params is the first enabled tab; wrapping backward goes to auth (last enabled)
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('auth')
  })

  it('Home key jumps to the first enabled tab', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'auth' })

    const authTab = screen.getByRole('tab', { name: 'Auth' })
    authTab.focus()
    await user.keyboard('{Home}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('params')
  })

  it('End key jumps to the last enabled tab', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'params' })

    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    paramsTab.focus()
    await user.keyboard('{End}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('auth')
  })

  it('Home when already on the first enabled tab still fires onChange with that id (boundary)', async () => {
    // AC-6 boundary: pressing Home when already at the first enabled tab fires
    // onChange with the same id. This is documented controlled-component behaviour:
    // TabsProps.onChange JSDoc (Tabs.tsx) states "calling the active tab again
    // still fires once" — the caller decides whether to update activeId.
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'params' })

    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    paramsTab.focus()
    await user.keyboard('{Home}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('params')
  })

  it('End when already on the last enabled tab still fires onChange with that id (boundary)', async () => {
    // AC-6 boundary: pressing End when already at the last enabled tab fires
    // onChange with the same id. This is documented controlled-component behaviour:
    // TabsProps.onChange JSDoc (Tabs.tsx) states "calling the active tab again
    // still fires once" — the caller decides whether to update activeId.
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'auth' })

    const authTab = screen.getByRole('tab', { name: 'Auth' })
    authTab.focus()
    await user.keyboard('{End}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('auth')
  })

  it('ArrowRight skips a disabled tab in the middle', async () => {
    // MIXED_TABS: params → headers → [body disabled] → auth
    // ArrowRight from headers should skip body and land on auth
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'headers' })

    const headersTab = screen.getByRole('tab', { name: 'Headers' })
    headersTab.focus()
    await user.keyboard('{ArrowRight}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('auth')
  })

  it('ArrowLeft skips a disabled tab in the middle', async () => {
    // MIXED_TABS: params → headers → [body disabled] → auth
    // ArrowLeft from auth should skip body and land on headers
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'auth' })

    const authTab = screen.getByRole('tab', { name: 'Auth' })
    authTab.focus()
    await user.keyboard('{ArrowLeft}')

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('headers')
  })

  it('Home skips a disabled tab at the start to land on the first enabled tab', async () => {
    // Tabs where the first tab is disabled
    const tabs: TabDescriptor[] = [
      { id: 'disabled-first', label: 'Disabled First', disabled: true },
      { id: 'second', label: 'Second' },
      { id: 'third', label: 'Third' }
    ]
    const user = userEvent.setup()
    const { onChange } = renderTabs({ tabs, activeId: 'third' })

    const thirdTab = screen.getByRole('tab', { name: 'Third' })
    thirdTab.focus()
    await user.keyboard('{Home}')

    // Home must skip the first (disabled) tab and land on 'second'
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('second')
  })

  it('End skips a disabled tab at the end to land on the last enabled tab', async () => {
    // Tabs where the last tab is disabled
    const tabs: TabDescriptor[] = [
      { id: 'first', label: 'First' },
      { id: 'second', label: 'Second' },
      { id: 'disabled-last', label: 'Disabled Last', disabled: true }
    ]
    const user = userEvent.setup()
    const { onChange } = renderTabs({ tabs, activeId: 'first' })

    const firstTab = screen.getByRole('tab', { name: 'First' })
    firstTab.focus()
    await user.keyboard('{End}')

    // End must skip the last (disabled) tab and land on 'second'
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('second')
  })

  it('ArrowRight from last enabled wraps and skips a disabled boundary tab', async () => {
    // Tabs where the first tab is disabled; wrap from last should land on second
    const tabs: TabDescriptor[] = [
      { id: 'disabled-first', label: 'Disabled First', disabled: true },
      { id: 'second', label: 'Second' },
      { id: 'last', label: 'Last' }
    ]
    const user = userEvent.setup()
    const { onChange } = renderTabs({ tabs, activeId: 'last' })

    const lastTab = screen.getByRole('tab', { name: 'Last' })
    lastTab.focus()
    await user.keyboard('{ArrowRight}')

    // Wraps forward; first tab is disabled → lands on second
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('second')
  })
})

// ---------------------------------------------------------------------------
// AC-7 — WAI-ARIA roles, aria-selected, no aria-controls, roving tabindex
// ---------------------------------------------------------------------------

describe('AC-7 — WAI-ARIA semantics', () => {
  it('renders a container with role="tablist"', () => {
    renderTabs()
    expect(screen.getByRole('tablist')).toBeInTheDocument()
  })

  it('the role="tablist" element carries aria-orientation="horizontal"', () => {
    renderTabs()
    expect(screen.getByRole('tablist')).toHaveAttribute('aria-orientation', 'horizontal')
  })

  it('the aria-label prop is wired to the role="tablist" element', () => {
    renderTabs({ ariaLabel: 'Request sections' })
    expect(screen.getByRole('tablist')).toHaveAttribute('aria-label', 'Request sections')
  })

  it('each tab has role="tab"', () => {
    renderTabs()
    const tabs = screen.getAllByRole('tab')
    expect(tabs.length).toBe(MIXED_TABS.length)
  })

  it('the active tab has aria-selected="true"', () => {
    renderTabs({ activeId: 'params' })
    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    expect(paramsTab).toHaveAttribute('aria-selected', 'true')
  })

  it('non-active enabled tabs have aria-selected="false"', () => {
    renderTabs({ activeId: 'params' })
    const headersTab = screen.getByRole('tab', { name: 'Headers' })
    expect(headersTab).toHaveAttribute('aria-selected', 'false')
  })

  it('no tab has an aria-controls attribute (intentional omission — no panels)', () => {
    renderTabs()
    const tabs = screen.getAllByRole('tab')
    for (const tab of tabs) {
      expect(tab).not.toHaveAttribute('aria-controls')
    }
  })

  it('exactly one tab has tabIndex=0 (roving tabindex)', () => {
    renderTabs({ activeId: 'params' })
    const tabs = screen.getAllByRole('tab')
    const tabStops = tabs.filter((t) => t.getAttribute('tabindex') === '0')
    expect(tabStops).toHaveLength(1)
  })

  it('the tab with tabIndex=0 is the active tab when activeId matches an enabled tab', () => {
    renderTabs({ activeId: 'headers' })
    const headersTab = screen.getByRole('tab', { name: 'Headers' })
    expect(headersTab).toHaveAttribute('tabindex', '0')
  })
})

// ---------------------------------------------------------------------------
// AC-8 — actions slot is rendered outside the tablist element
// ---------------------------------------------------------------------------

describe('AC-8 — actions slot', () => {
  it('renders the actions slot content in the DOM', () => {
    renderTabs({ actions: <button data-testid="add-btn">+ Add</button> })
    expect(screen.getByTestId('add-btn')).toBeInTheDocument()
  })

  it('actions slot content is NOT a descendant of role="tablist"', () => {
    renderTabs({ actions: <button data-testid="add-btn">+ Add</button> })
    const tablist = screen.getByRole('tablist')
    const insideTablist = within(tablist).queryByTestId('add-btn')
    expect(insideTablist).toBeNull()
  })

  it('renders no actions content when actions prop is undefined', () => {
    renderTabs({ actions: undefined })
    // When no actions prop is supplied, no actions-slot testid is in the DOM.
    // (The companion presence test uses data-testid="add-btn".)
    expect(screen.queryByTestId('add-btn')).toBeNull()
  })

  it('actions slot appears AFTER the tablist in DOM source order (right-aligned end)', () => {
    // AC-8: the actions wrapper must be a FOLLOWING sibling of the tablist, not
    // preceding it. Node.compareDocumentPosition bit 4 (DOCUMENT_POSITION_FOLLOWING)
    // is set when the argument node follows the reference node in document order.
    renderTabs({ actions: <button data-testid="add-btn">+ Add</button> })

    const tablist = screen.getByRole('tablist')
    const addBtn = screen.getByTestId('add-btn')

    // Walk up from the button to find the direct actions wrapper sibling
    const actionsWrapper = addBtn.parentElement!
    const position = tablist.compareDocumentPosition(actionsWrapper)
    // Bit 4 = DOCUMENT_POSITION_FOLLOWING: actionsWrapper comes after tablist
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// AC-9 — disabled tabs do not fire onChange and are skipped by keyboard
// ---------------------------------------------------------------------------

describe('AC-9 — disabled tab behaviour', () => {
  it('clicking a disabled tab does NOT call onChange', async () => {
    const user = userEvent.setup()
    const { onChange } = renderTabs()

    const bodyTab = screen.getByRole('tab', { name: 'Body' })
    // userEvent.click on a disabled button is a no-op (button is disabled attribute)
    await user.click(bodyTab)

    expect(onChange).not.toHaveBeenCalled()
  })

  it('a key that would target a disabled tab lands on the next enabled one', async () => {
    // From headers, ArrowRight targets body (disabled) — should skip to auth
    const user = userEvent.setup()
    const { onChange } = renderTabs({ activeId: 'headers' })

    const headersTab = screen.getByRole('tab', { name: 'Headers' })
    headersTab.focus()
    await user.keyboard('{ArrowRight}')

    // Should land on auth, never call onChange with 'body'
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).not.toHaveBeenCalledWith('body')
    expect(onChange).toHaveBeenCalledWith('auth')
  })

  it('disabled tab has aria-disabled attribute', () => {
    renderTabs()
    const bodyTab = screen.getByRole('tab', { name: 'Body' })
    expect(bodyTab).toHaveAttribute('aria-disabled', 'true')
  })

  it('enabled tab does NOT carry the aria-disabled attribute at all', () => {
    // The component emits aria-disabled={isDisabled || undefined}:
    // when false, undefined is emitted so the attribute is entirely absent.
    renderTabs()
    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    expect(paramsTab).not.toHaveAttribute('aria-disabled')
  })
})

// ---------------------------------------------------------------------------
// AC-10 — no-selection guard (empty array / no-match / active-is-disabled)
// ---------------------------------------------------------------------------

describe('AC-10 — no-selection guard', () => {
  it('empty tabs array: no tab has aria-selected="true"', () => {
    render(<Tabs tabs={[]} activeId="anything" onChange={vi.fn()} aria-label="Empty" />)
    // No tabs are rendered at all — also verify no aria-selected="true" just in case
    const allTabs = screen.queryAllByRole('tab')
    const selected = allTabs.filter((t) => t.getAttribute('aria-selected') === 'true')
    expect(selected).toHaveLength(0)
  })

  it('activeId matches no tab: no tab has aria-selected="true"', () => {
    renderTabs({ activeId: 'nonexistent-id' })
    const allTabs = screen.getAllByRole('tab')
    const selected = allTabs.filter((t) => t.getAttribute('aria-selected') === 'true')
    expect(selected).toHaveLength(0)
  })

  it('activeId matches a disabled tab: that tab does NOT get aria-selected="true"', () => {
    renderTabs({ activeId: 'body' }) // body is disabled in MIXED_TABS
    const bodyTab = screen.getByRole('tab', { name: 'Body' })
    expect(bodyTab).toHaveAttribute('aria-selected', 'false')
  })

  it('no-match case: first enabled tab still has tabIndex=0 (WAI-ARIA roving fallback)', () => {
    renderTabs({ activeId: 'nonexistent-id' })
    const paramsTab = screen.getByRole('tab', { name: 'Params' })
    // The first enabled tab keeps tabIndex=0 so the strip stays keyboard-reachable
    expect(paramsTab).toHaveAttribute('tabindex', '0')
  })

  it('all-disabled tabs: no tab has tabIndex=0 (no enabled tab to be the stop)', () => {
    const allDisabled: TabDescriptor[] = [
      { id: 'a', label: 'A', disabled: true },
      { id: 'b', label: 'B', disabled: true }
    ]
    render(<Tabs tabs={allDisabled} activeId="a" onChange={vi.fn()} aria-label="All disabled" />)
    const allTabs = screen.getAllByRole('tab')
    const tabStops = allTabs.filter((t) => t.getAttribute('tabindex') === '0')
    expect(tabStops).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// Badge rendering
// ---------------------------------------------------------------------------

describe('badge rendering', () => {
  it('renders a string badge when badge is set', () => {
    const tabs: TabDescriptor[] = [{ id: 'a', label: 'Alpha', badge: 'NEW' }]
    render(<Tabs tabs={tabs} activeId="a" onChange={vi.fn()} aria-label="Badge test" />)
    expect(screen.getByText('NEW')).toBeInTheDocument()
  })

  it('renders a number badge when badge is a number', () => {
    const tabs: TabDescriptor[] = [{ id: 'a', label: 'Alpha', badge: 5 }]
    render(<Tabs tabs={tabs} activeId="a" onChange={vi.fn()} aria-label="Badge test" />)
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders no badge element when badge is undefined', () => {
    const tabs: TabDescriptor[] = [{ id: 'a', label: 'Alpha' }]
    render(<Tabs tabs={tabs} activeId="a" onChange={vi.fn()} aria-label="Badge test" />)
    // The tab's text content equals just the label — no extra badge text appended
    const tab = screen.getByRole('tab', { name: 'Alpha' })
    expect(tab.textContent).toBe('Alpha')
  })
})
