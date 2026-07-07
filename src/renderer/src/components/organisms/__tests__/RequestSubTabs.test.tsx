/**
 * RequestSubTabs.test.tsx
 *
 * Interaction and contract tests for the RequestSubTabs organism.
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## AC coverage
 *
 * - AC-6  / AC-9:  Clicking a sub-tab calls setActiveSubTab; clicked panel
 *                  becomes visible and all others are hidden.
 * - AC-10:         An external setActiveSubTab write (not triggered by a click)
 *                  updates the visible panel identically to a click.
 * - AC-12:         Params/Headers slot props render in their panels; the other 4
 *                  panels show the shared "Panel not yet available" empty-state.
 * - AC-14:         Each tabpanel carries role="tabpanel", id="panel-<key>",
 *                  aria-labelledby="tab-<key>", and aria-selected reflecting
 *                  the active sub-tab.
 * - AC-15:         Badge: params/headers counts; 99+ above 99; auth '•' when
 *                  auth.type !== 'none'; nothing for Body/Tests/Code.
 * - AC-16:         A persisted-garbage activeSubTab value normalizes to 'params'.
 * - AC-17:         No active tab renders a neutral empty region without throwing.
 *
 * ## Store reset strategy
 *
 * RequestSubTabs subscribes to the module-level tabsStore singleton. Each test
 * resets the store via `tabsStore.setState(...)` — the same pattern used in
 * TabBar.test.tsx and tabsStore.test.ts.
 */

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from 'react'
import { tabsStore, VALID_KEYS } from '@renderer/lib/tabsStore'
import type { SubTabKey } from '@renderer/lib/tabsStore'
import { RequestSubTabs } from '@renderer/components/organisms/RequestSubTabs'
import { makeSpec, makeTab } from '@renderer/__tests__/fixtures/requestSpec'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const TAB_ID = 'test-tab-id'

/** Reset the store to a predictable single-tab state. */
function resetStore(overrides: Partial<Parameters<typeof makeTab>[1]> = {}): void {
  tabsStore.setState({
    tabs: [makeTab(TAB_ID, overrides)],
    activeTabId: TAB_ID
  })
}

beforeEach(() => {
  resetStore()
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Human labels in the same order as VALID_KEYS. */
const LABELS: Record<SubTabKey, string> = {
  params: 'Params',
  auth: 'Auth',
  headers: 'Headers',
  body: 'Body',
  tests: 'Tests',
  code: 'Code'
}

/**
 * Render RequestSubTabs with sensible default slot props.
 * Params and Headers receive identifiable children for assertions.
 */
function renderComponent(opts: { params?: React.ReactNode; headers?: React.ReactNode } = {}): void {
  render(
    <RequestSubTabs
      params={opts.params ?? <div data-testid="params-content">Params panel</div>}
      headers={opts.headers ?? <div data-testid="headers-content">Headers panel</div>}
    />
  )
}

// ---------------------------------------------------------------------------
// AC-6 / AC-9 — Click switches the active panel
// ---------------------------------------------------------------------------

describe('AC-6 / AC-9 — clicking a sub-tab switches the active panel', () => {
  it('params panel is shown and all others are hidden on initial render (activeSubTab defaults to params)', () => {
    renderComponent()

    const paramsPanel = document.getElementById('panel-params')
    expect(paramsPanel).not.toBeNull()
    expect(paramsPanel!.hidden).toBe(false)

    for (const key of VALID_KEYS) {
      if (key === 'params') continue
      const panel = document.getElementById(`panel-${key}`)
      expect(panel).not.toBeNull()
      expect(panel!.hidden).toBe(true)
    }
  })

  it('clicking the Auth tab calls setActiveSubTab and shows the auth panel', async () => {
    const user = userEvent.setup()
    renderComponent()

    const authTab = screen.getByRole('tab', { name: /Auth/ })
    await user.click(authTab)

    expect(tabsStore.getState().tabs[0].activeSubTab).toBe('auth')
    expect(document.getElementById('panel-auth')!.hidden).toBe(false)
    expect(document.getElementById('panel-params')!.hidden).toBe(true)
  })

  it('clicking the Headers tab hides all other panels', async () => {
    const user = userEvent.setup()
    renderComponent()

    const headersTab = screen.getByRole('tab', { name: /Headers/ })
    await user.click(headersTab)

    expect(document.getElementById('panel-headers')!.hidden).toBe(false)
    for (const key of VALID_KEYS) {
      if (key === 'headers') continue
      expect(document.getElementById(`panel-${key}`)!.hidden).toBe(true)
    }
  })

  it('clicking Body tab stores body as activeSubTab', async () => {
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByRole('tab', { name: /Body/ }))

    expect(tabsStore.getState().tabs[0].activeSubTab).toBe('body')
  })

  it('all 6 tabpanels are mounted in the DOM at all times (never unmount)', () => {
    renderComponent()

    for (const key of VALID_KEYS) {
      expect(document.getElementById(`panel-${key}`)).not.toBeNull()
    }

    // Role count guard: exactly 6 tabpanels must exist (catches duplicate-panel regression).
    // hidden:true is required because inactive panels carry the HTML `hidden` attribute.
    const allPanels = screen.getAllByRole('tabpanel', { hidden: true })
    expect(allPanels).toHaveLength(6)
  })
})

// ---------------------------------------------------------------------------
// AC-14 — ARIA attributes on tabpanels
// ---------------------------------------------------------------------------

describe('AC-14 — tabpanel ARIA attributes', () => {
  it('each panel has role=tabpanel with the correct id and aria-labelledby', () => {
    renderComponent()

    for (const key of VALID_KEYS) {
      const panel = document.getElementById(`panel-${key}`)
      expect(panel).not.toBeNull()
      expect(panel!.getAttribute('role')).toBe('tabpanel')
      expect(panel!.getAttribute('aria-labelledby')).toBe(`tab-${key}`)
    }
  })

  it('aria-selected is true only for the active panel', () => {
    renderComponent()

    for (const key of VALID_KEYS) {
      const panel = document.getElementById(`panel-${key}`)!
      const expected = key === 'params' ? 'true' : 'false'
      expect(panel.getAttribute('aria-selected')).toBe(expected)
    }
  })

  it('aria-selected updates when sub-tab changes', async () => {
    const user = userEvent.setup()
    renderComponent()

    await user.click(screen.getByRole('tab', { name: /Headers/ }))

    for (const key of VALID_KEYS) {
      const panel = document.getElementById(`panel-${key}`)!
      const expected = key === 'headers' ? 'true' : 'false'
      expect(panel.getAttribute('aria-selected')).toBe(expected)
    }
  })

  it('tab buttons carry id=tab-<key> and aria-controls=panel-<key> (linkPanels)', () => {
    renderComponent()

    for (const key of VALID_KEYS) {
      const tab = document.getElementById(`tab-${key}`)
      expect(tab).not.toBeNull()
      expect(tab!.getAttribute('aria-controls')).toBe(`panel-${key}`)
    }
  })
})

// ---------------------------------------------------------------------------
// AC-12 — Slot props and shared empty-state
// ---------------------------------------------------------------------------

describe('AC-12 — slot props and shared empty-state', () => {
  it('renders the params prop inside the params panel', () => {
    renderComponent({ params: <span data-testid="my-params">My Params</span> })

    const paramsPanel = document.getElementById('panel-params')!
    expect(within(paramsPanel).getByTestId('my-params')).toBeInTheDocument()
  })

  it('renders the headers prop inside the headers panel', () => {
    renderComponent({ headers: <span data-testid="my-headers">My Headers</span> })

    const headersPanel = document.getElementById('panel-headers')!
    expect(within(headersPanel).getByTestId('my-headers')).toBeInTheDocument()
  })

  it('shows the shared empty-state for Auth, Body, Tests, and Code panels', () => {
    renderComponent()

    for (const key of ['auth', 'body', 'tests', 'code'] as SubTabKey[]) {
      const panel = document.getElementById(`panel-${key}`)!
      expect(within(panel).getByText('Panel not yet available')).toBeInTheDocument()
    }
  })

  it('shows the shared empty-state when params prop is omitted', () => {
    render(<RequestSubTabs headers={<div>Headers</div>} />)

    const paramsPanel = document.getElementById('panel-params')!
    expect(within(paramsPanel).getByText('Panel not yet available')).toBeInTheDocument()
  })

  it('shows the shared empty-state when headers prop is omitted', () => {
    render(<RequestSubTabs params={<div>Params</div>} />)

    const headersPanel = document.getElementById('panel-headers')!
    expect(within(headersPanel).getByText('Panel not yet available')).toBeInTheDocument()
  })

  it('the empty-state text does NOT appear inside the params or headers panels when props are supplied', () => {
    renderComponent()

    const paramsPanel = document.getElementById('panel-params')!
    const headersPanel = document.getElementById('panel-headers')!

    expect(within(paramsPanel).queryByText('Panel not yet available')).toBeNull()
    expect(within(headersPanel).queryByText('Panel not yet available')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// AC-15 — Badge derivation
// ---------------------------------------------------------------------------

describe('AC-15 — badge derivation', () => {
  it('params badge shows the count when params rows exist', () => {
    tabsStore.setState({
      tabs: [
        makeTab(TAB_ID, {
          params: [
            { enabled: true, key: 'foo', value: 'bar', description: '' },
            { enabled: true, key: 'baz', value: 'qux', description: '' }
          ]
        })
      ],
      activeTabId: TAB_ID
    })

    renderComponent()

    const paramsTab = screen.getByRole('tab', { name: /Params/ })
    expect(paramsTab).toHaveTextContent('2')
  })

  it('params badge is absent when params is empty', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { params: [] })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const paramsTab = screen.getByRole('tab', { name: /Params/ })
    // Badge span should not render — no badge class content
    expect(paramsTab.querySelector('.tabs__badge')).toBeNull()
  })

  it('params badge shows 99+ when count exceeds 99', () => {
    const manyRows = Array.from({ length: 100 }, (_, i) => ({
      enabled: true,
      key: `k${i}`,
      value: `v${i}`,
      description: ''
    }))

    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { params: manyRows })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const paramsTab = screen.getByRole('tab', { name: /Params/ })
    expect(paramsTab).toHaveTextContent('99+')
  })

  it('params badge shows 99 (not 99+) when count is exactly 99', () => {
    const rows = Array.from({ length: 99 }, (_, i) => ({
      enabled: true,
      key: `k${i}`,
      value: `v${i}`,
      description: ''
    }))

    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { params: rows })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const paramsTab = screen.getByRole('tab', { name: /Params/ })
    expect(paramsTab).toHaveTextContent('99')
    expect(paramsTab).not.toHaveTextContent('99+')
  })

  it('headers badge shows the count when headers rows exist', () => {
    tabsStore.setState({
      tabs: [
        makeTab(TAB_ID, {
          headers: [
            { enabled: true, key: 'Accept', value: 'application/json', description: '' },
            { enabled: true, key: 'X-Custom', value: 'value', description: '' },
            { enabled: true, key: 'X-Other', value: 'x', description: '' }
          ]
        })
      ],
      activeTabId: TAB_ID
    })

    renderComponent()

    const headersTab = screen.getByRole('tab', { name: /Headers/ })
    expect(headersTab).toHaveTextContent('3')
  })

  it('headers badge shows 99+ when count exceeds 99', () => {
    const manyRows = Array.from({ length: 101 }, (_, i) => ({
      enabled: true,
      key: `h${i}`,
      value: `v${i}`,
      description: ''
    }))

    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { headers: manyRows })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const headersTab = screen.getByRole('tab', { name: /Headers/ })
    expect(headersTab).toHaveTextContent('99+')
  })

  it('headers badge shows 99 (not 99+) when count is exactly 99', () => {
    const rows = Array.from({ length: 99 }, (_, i) => ({
      enabled: true,
      key: `h${i}`,
      value: `v${i}`,
      description: ''
    }))

    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { headers: rows })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const headersTab = screen.getByRole('tab', { name: /Headers/ })
    expect(headersTab).toHaveTextContent('99')
    expect(headersTab).not.toHaveTextContent('99+')
  })

  it('auth badge shows • when auth.type is bearer', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { auth: { type: 'bearer', token: 'tok' } })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const authTab = screen.getByRole('tab', { name: /Auth/ })
    expect(authTab).toHaveTextContent('•')
  })

  it('auth badge is absent when auth.type is none', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { auth: { type: 'none' } })],
      activeTabId: TAB_ID
    })

    renderComponent()

    const authTab = screen.getByRole('tab', { name: /Auth/ })
    expect(authTab.querySelector('.tabs__badge')).toBeNull()
  })

  it('Body, Tests, and Code tabs never carry a badge', () => {
    // Seed with lots of data to ensure nothing leaks into those tabs.
    const manyRows = Array.from({ length: 5 }, (_, i) => ({
      enabled: true,
      key: `k${i}`,
      value: `v${i}`,
      description: ''
    }))

    tabsStore.setState({
      tabs: [
        makeTab(TAB_ID, {
          params: manyRows,
          headers: manyRows,
          auth: { type: 'bearer', token: 'tok' }
        })
      ],
      activeTabId: TAB_ID
    })

    renderComponent()

    for (const key of ['body', 'tests', 'code'] as SubTabKey[]) {
      const tab = screen.getByRole('tab', { name: LABELS[key] })
      expect(tab.querySelector('.tabs__badge')).toBeNull()
    }
  })

  it('params badge updates reactively when spec changes', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { params: [] })],
      activeTabId: TAB_ID
    })

    renderComponent()

    // Initially no badge
    expect(screen.getByRole('tab', { name: /Params/ }).querySelector('.tabs__badge')).toBeNull()

    // Add a row via updateActiveSpec
    act(() => {
      tabsStore.getState().updateActiveSpec({
        params: [{ enabled: true, key: 'x', value: '1', description: '' }]
      })
    })

    expect(screen.getByRole('tab', { name: /Params/ })).toHaveTextContent('1')
  })

  it('headers badge updates reactively when spec changes (AC-26)', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { headers: [] })],
      activeTabId: TAB_ID
    })

    renderComponent()

    // Initially no badge — sub-tab is still params (no switch needed)
    expect(screen.getByRole('tab', { name: /Headers/ }).querySelector('.tabs__badge')).toBeNull()

    // Add a header row via updateActiveSpec without switching sub-tabs
    act(() => {
      tabsStore.getState().updateActiveSpec({
        headers: [{ enabled: true, key: 'Accept', value: 'application/json', description: '' }]
      })
    })

    expect(screen.getByRole('tab', { name: /Headers/ })).toHaveTextContent('1')
  })
})

// ---------------------------------------------------------------------------
// AC-10 — External store write updates the visible panel
// ---------------------------------------------------------------------------

describe('AC-10 — external setActiveSubTab write updates visible panel', () => {
  it('directly calling setActiveSubTab on the store shows the correct panel', () => {
    renderComponent()

    // Initially params is visible
    expect(document.getElementById('panel-params')!.hidden).toBe(false)

    // Write to the store directly (not via click)
    act(() => {
      tabsStore.getState().setActiveSubTab(TAB_ID, 'tests')
    })

    expect(document.getElementById('panel-tests')!.hidden).toBe(false)
    expect(document.getElementById('panel-params')!.hidden).toBe(true)
  })

  it('direct store write and click produce identical panel visibility', async () => {
    const user = userEvent.setup()

    // Test via click
    const { unmount } = render(
      <RequestSubTabs
        params={<div data-testid="params-content">Params panel</div>}
        headers={<div data-testid="headers-content">Headers panel</div>}
      />
    )
    await user.click(screen.getByRole('tab', { name: /Code/ }))
    const expectedHiddenState = VALID_KEYS.map((k) => ({
      key: k,
      hidden: document.getElementById(`panel-${k}`)!.hidden
    }))
    // Unmount first render before mounting a second one to avoid cross-render state leaks.
    unmount()

    // Reset and test via direct write
    resetStore()
    render(
      <RequestSubTabs
        params={<div data-testid="params-content">Params panel</div>}
        headers={<div data-testid="headers-content">Headers panel</div>}
      />
    )
    act(() => {
      tabsStore.getState().setActiveSubTab(TAB_ID, 'code')
    })
    const visibilityAfterWrite = VALID_KEYS.map((k) => ({
      key: k,
      hidden: document.getElementById(`panel-${k}`)!.hidden
    }))

    expect(visibilityAfterWrite).toEqual(expectedHiddenState)
  })
})

// ---------------------------------------------------------------------------
// AC-16 — Invalid activeSubTab normalizes to params
// ---------------------------------------------------------------------------

describe('AC-16 — invalid activeSubTab normalizes to params', () => {
  it('renders params panel as visible when activeSubTab is an invalid garbage value', () => {
    tabsStore.setState({
      tabs: [
        {
          id: TAB_ID,
          collectionRequestId: null,
          spec: makeSpec(),
          dirty: false,
          // Cast a garbage value to SubTabKey to simulate persisted corruption.
          activeSubTab: 'nonexistent-key' as SubTabKey
        }
      ],
      activeTabId: TAB_ID
    })

    renderComponent()

    // Should fall back to 'params' without throwing
    expect(document.getElementById('panel-params')!.hidden).toBe(false)
    for (const key of VALID_KEYS) {
      if (key === 'params') continue
      expect(document.getElementById(`panel-${key}`)!.hidden).toBe(true)
    }
  })
})

// ---------------------------------------------------------------------------
// AC-17 — No active tab renders a neutral empty region without throwing
// ---------------------------------------------------------------------------

describe('AC-17 — no active tab renders a neutral empty region', () => {
  it('does not throw when activeTabId resolves to no tab', () => {
    // Force a state where activeTabId references a missing tab (bypasses store invariant).
    tabsStore.setState({
      tabs: [],
      activeTabId: 'nonexistent-tab-id'
    })

    expect(() => {
      render(<RequestSubTabs />)
    }).not.toThrow()
  })

  it('renders a fallback container element when no tab is active', () => {
    tabsStore.setState({
      tabs: [],
      activeTabId: 'nonexistent-tab-id'
    })

    const { container } = render(<RequestSubTabs />)

    // Should render something (not null); the tablist should NOT be present
    expect(container.firstChild).not.toBeNull()
    expect(screen.queryByRole('tablist')).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Tab strip structure
// ---------------------------------------------------------------------------

describe('tab strip structure', () => {
  it('renders a tablist with aria-label "Request sub-tabs"', () => {
    renderComponent()

    const tablist = screen.getByRole('tablist', { name: 'Request sub-tabs' })
    expect(tablist).toBeInTheDocument()
  })

  it('renders exactly 6 tabs in the correct order', () => {
    // Seed with no params, no headers, no auth so badges don't appear.
    tabsStore.setState({
      tabs: [makeTab(TAB_ID, { params: [], headers: [], auth: { type: 'none' } })],
      activeTabId: TAB_ID
    })
    renderComponent()

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(6)
    // Read label text from the .tabs__tab-label span to exclude badge text.
    const labelTexts = tabs.map((t) => t.querySelector('.tabs__tab-label')?.textContent?.trim())
    expect(labelTexts).toEqual(['Params', 'Auth', 'Headers', 'Body', 'Tests', 'Code'])
  })

  it('the Params tab is aria-selected on initial render', () => {
    renderComponent()

    const paramsTab = screen.getByRole('tab', { name: /Params/ })
    expect(paramsTab).toHaveAttribute('aria-selected', 'true')
  })
})

// ---------------------------------------------------------------------------
// AC-13 — All 6 tabs are enabled (none carry disabled / aria-disabled)
// ---------------------------------------------------------------------------

describe('AC-13 — all 6 tabs are reachable (none disabled)', () => {
  it('no tab button carries aria-disabled or the disabled attribute', () => {
    renderComponent()

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(6)
    for (const tab of tabs) {
      expect(tab).not.toHaveAttribute('aria-disabled', 'true')
      expect(tab).not.toBeDisabled()
    }
  })
})
