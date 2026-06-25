/**
 * TabBar.test.tsx
 *
 * Behavioral tests for the TabBar organism — the working-tabs strip that binds
 * the Tabs molecule to the tabsStore singleton.
 *
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## AC coverage
 *
 * - AC-24: Gesture routing — click tab → selectActive; click ✕ → close;
 *          click + button → newBlank. Asserted against store state, not spies.
 * - AC-25: Label precedence:
 *          1. spec.name when non-empty.
 *          2. method + ' ' + url when url is non-empty.
 *          3. 'Untitled' when both name and url are empty.
 * - AC-26: Dirty marker — '●' badge renders alongside a dirty tab's label;
 *          no badge renders for a clean tab.
 *
 * ## Store reset strategy
 *
 * TabBar subscribes to the module-level tabsStore singleton. In beforeEach we
 * call tabsStore.setState({ tabs: [...], activeTabId }) to replace the data
 * fields while leaving the zustand actions intact — the same pattern used in
 * tabsStore.test.ts.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { tabsStore } from '@renderer/lib/tabsStore'
import { TabBar } from '@renderer/components/organisms/TabBar'
import { makeTab } from '@renderer/__tests__/fixtures/requestSpec'

// ---------------------------------------------------------------------------
// Store reset
// ---------------------------------------------------------------------------

/**
 * Stable ids for the two-tab fixture used in gesture tests (AC-24).
 * Using literal strings makes assertion callsites easy to read.
 */
const TAB_A_ID = 'tab-a'
const TAB_B_ID = 'tab-b'

/**
 * Stable ids for the three-tab fixture used in active-close routing tests.
 */
const TAB_LEFT_ID = 'tab-left'
const TAB_MID_ID = 'tab-mid'
const TAB_RIGHT_ID = 'tab-right'

/**
 * Reset the tabsStore singleton to a known two-tab state before each test.
 * We replace only the data fields (tabs, activeTabId); the action closures
 * persist naturally — matching the pattern in tabsStore.test.ts.
 */
function resetStore(): void {
  tabsStore.setState({
    tabs: [
      makeTab(TAB_A_ID, { name: 'Tab A', url: 'https://a.example.com', method: 'GET' }),
      makeTab(TAB_B_ID, { name: 'Tab B', url: 'https://b.example.com', method: 'POST' })
    ],
    activeTabId: TAB_A_ID
  })
}

beforeEach(() => {
  resetStore()
})

// ---------------------------------------------------------------------------
// AC-24 — Gesture routing
// ---------------------------------------------------------------------------

describe('AC-24 — gesture routing', () => {
  it('clicking a non-active tab calls selectActive → activeTabId becomes that tab id', async () => {
    const user = userEvent.setup()
    render(<TabBar />)

    // Tab A is active; click Tab B (non-active)
    const tabBButton = screen.getByRole('tab', { name: 'Tab B' })
    await user.click(tabBButton)

    expect(tabsStore.getState().activeTabId).toBe(TAB_B_ID)
  })

  it('clicking a tab ✕ close control calls close → that tab is removed from tabs', async () => {
    const user = userEvent.setup()
    render(<TabBar />)

    // TabBar renders with closable=true; each tab gets a "Close <label>" button
    const closeTabB = screen.getByRole('button', { name: 'Close Tab B' })
    await user.click(closeTabB)

    const tabs = tabsStore.getState().tabs
    expect(tabs.find((t) => t.id === TAB_B_ID)).toBeUndefined()
  })

  it('clicking the + new-tab button calls newBlank → tabs length increases by 1', async () => {
    const user = userEvent.setup()
    render(<TabBar />)

    const lengthBefore = tabsStore.getState().tabs.length

    const newTabBtn = screen.getByRole('button', { name: 'New tab' })
    await user.click(newTabBtn)

    const lengthAfter = tabsStore.getState().tabs.length
    expect(lengthAfter).toBe(lengthBefore + 1)
  })

  it('clicking the + new-tab button: the new tab is a blank seed (empty name, empty url, method GET)', async () => {
    const user = userEvent.setup()
    render(<TabBar />)

    const newTabBtn = screen.getByRole('button', { name: 'New tab' })
    await user.click(newTabBtn)

    const { tabs, activeTabId } = tabsStore.getState()
    const newTab = tabs.find((t) => t.id === activeTabId)
    // The new (just-added) tab should be the active one and be a blank seed
    expect(newTab).toBeDefined()
    expect(newTab!.spec.name).toBe('')
    expect(newTab!.spec.url).toBe('')
    expect(newTab!.spec.method).toBe('GET')
    expect(newTab!.dirty).toBe(false)
  })

  it('✕ on the ACTIVE tab closes it and moves activeTabId to the right neighbor (AC-24 active-close path)', async () => {
    // Seed three tabs; the MIDDLE tab (TAB_MID_ID) is the active one.
    // Closing it should remove it from `tabs` and move activeTabId to the
    // right neighbor (TAB_RIGHT_ID) per selectNeighborId — right-then-left.
    tabsStore.setState({
      tabs: [
        makeTab(TAB_LEFT_ID, { name: 'Left Tab', url: '', method: 'GET' }),
        makeTab(TAB_MID_ID, { name: 'Active Tab', url: '', method: 'GET' }),
        makeTab(TAB_RIGHT_ID, { name: 'Right Tab', url: '', method: 'GET' })
      ],
      activeTabId: TAB_MID_ID
    })

    const user = userEvent.setup()
    render(<TabBar />)

    // The close control's aria-label matches "Close <label>" where label = tab's display label.
    const closeActive = screen.getByRole('button', { name: 'Close Active Tab' })
    await user.click(closeActive)

    const { tabs, activeTabId } = tabsStore.getState()

    // The closed tab must no longer be present.
    expect(tabs.find((t) => t.id === TAB_MID_ID)).toBeUndefined()

    // The right neighbor (TAB_RIGHT_ID) must now be active.
    expect(activeTabId).toBe(TAB_RIGHT_ID)
  })

  it('✕ on the LAST (rightmost) ACTIVE tab closes it and moves activeTabId to the LEFT neighbor (AC-18 left-fallback)', async () => {
    // Seed three tabs; the LAST tab (TAB_RIGHT_ID) is the active one.
    // Closing it should remove it from `tabs` and move activeTabId to the
    // left neighbor (TAB_MID_ID) per selectNeighborId — isLast branch picks left.
    tabsStore.setState({
      tabs: [
        makeTab(TAB_LEFT_ID, { name: 'Left Tab', url: '', method: 'GET' }),
        makeTab(TAB_MID_ID, { name: 'Mid Tab', url: '', method: 'GET' }),
        makeTab(TAB_RIGHT_ID, { name: 'Right Tab', url: '', method: 'GET' })
      ],
      activeTabId: TAB_RIGHT_ID
    })

    const user = userEvent.setup()
    render(<TabBar />)

    // The close control's aria-label matches "Close <label>" where label = tab's display label.
    const closeActive = screen.getByRole('button', { name: 'Close Right Tab' })
    await user.click(closeActive)

    const { tabs, activeTabId } = tabsStore.getState()

    // The closed tab must no longer be present.
    expect(tabs.find((t) => t.id === TAB_RIGHT_ID)).toBeUndefined()

    // The left neighbor (TAB_MID_ID) must now be active — isLast fallback branch.
    expect(activeTabId).toBe(TAB_MID_ID)

    // TabBar must re-render with the left neighbor carrying aria-selected="true"
    // (store → TabBar → Tabs activeId binding for the left-fallback branch).
    const midTab = screen.getByRole('tab', { name: 'Mid Tab' })
    expect(midTab).toHaveAttribute('aria-selected', 'true')
  })

  it('clicking the ALREADY-ACTIVE tab fires selectActive but leaves state unchanged (AC-24)', async () => {
    // Tab A is active. Clicking Tab A again must not crash and must keep
    // activeTabId as TAB_A_ID (selectActive is a no-op when the tab is
    // already active — it just re-sets the same value).
    const user = userEvent.setup()
    render(<TabBar />)

    const tabLengthBefore = tabsStore.getState().tabs.length

    // Click the already-active tab (Tab A).
    const tabAButton = screen.getByRole('tab', { name: 'Tab A' })
    await user.click(tabAButton)

    const { tabs, activeTabId } = tabsStore.getState()

    // activeTabId must still be Tab A — clicking an already-active tab is stable.
    expect(activeTabId).toBe(TAB_A_ID)
    // No tabs were added or removed.
    expect(tabs.length).toBe(tabLengthBefore)
  })

  it('clicking + new-tab: the new tab has collectionRequestId: null (matches makeBlankTab)', async () => {
    const user = userEvent.setup()
    render(<TabBar />)

    const newTabBtn = screen.getByRole('button', { name: 'New tab' })
    await user.click(newTabBtn)

    const { tabs, activeTabId } = tabsStore.getState()
    const newTab = tabs.find((t) => t.id === activeTabId)
    expect(newTab).toBeDefined()
    // A blank tab must carry no collection binding.
    expect(newTab!.collectionRequestId).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// AC-25 — Label precedence
// ---------------------------------------------------------------------------

describe('AC-25 — label precedence', () => {
  it('renders spec.name verbatim when name is non-empty', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-named', { name: 'My Request', url: 'https://x', method: 'GET' })],
      activeTabId: 'tab-named'
    })

    render(<TabBar />)

    // The tab label text must be exactly "My Request"
    expect(screen.getByRole('tab', { name: 'My Request' })).toBeInTheDocument()
  })

  it('renders "METHOD url" when name is empty and url is non-empty', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-url', { name: '', url: 'https://api.example.com/v1', method: 'POST' })],
      activeTabId: 'tab-url'
    })

    render(<TabBar />)

    // Label must be exactly "POST https://api.example.com/v1" — method + single space + url
    expect(screen.getByRole('tab', { name: 'POST https://api.example.com/v1' })).toBeInTheDocument()
  })

  it('renders "Untitled" when both name and url are empty', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-untitled', { name: '', url: '', method: 'GET' })],
      activeTabId: 'tab-untitled'
    })

    render(<TabBar />)

    // Label must be exactly "Untitled"
    expect(screen.getByRole('tab', { name: 'Untitled' })).toBeInTheDocument()
  })

  it('all three branches render in a single TabBar with the correct verbatim text', () => {
    tabsStore.setState({
      tabs: [
        makeTab('tab-1', { name: 'My Request', url: 'https://x', method: 'GET' }),
        makeTab('tab-2', { name: '', url: 'https://api.example.com/v1', method: 'POST' }),
        makeTab('tab-3', { name: '', url: '', method: 'GET' })
      ],
      activeTabId: 'tab-1'
    })

    render(<TabBar />)

    expect(screen.getByRole('tab', { name: 'My Request' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'POST https://api.example.com/v1' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Untitled' })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// AC-26 — Dirty marker
// ---------------------------------------------------------------------------

describe('AC-26 — dirty marker (● badge)', () => {
  it('a dirty tab renders the ● badge alongside its label (label text still present)', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-dirty', { name: 'Dirty Request' }, { dirty: true })],
      activeTabId: 'tab-dirty'
    })

    render(<TabBar />)

    // The label text must still be accessible
    const tab = screen.getByRole('tab', { name: /Dirty Request/ })
    expect(tab).toBeInTheDocument()

    // The dirty marker '●' must be rendered inside the tab
    expect(tab.textContent).toContain('●')
  })

  it('a clean tab renders NO ● badge', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-clean', { name: 'Clean Request' }, { dirty: false })],
      activeTabId: 'tab-clean'
    })

    render(<TabBar />)

    const tab = screen.getByRole('tab', { name: 'Clean Request' })
    expect(tab).toBeInTheDocument()

    // No dirty marker on a clean tab
    expect(tab.textContent).not.toContain('●')
  })

  it('only the dirty tab carries ● when both dirty and clean tabs are present', () => {
    tabsStore.setState({
      tabs: [
        makeTab('tab-clean', { name: 'Clean' }, { dirty: false }),
        makeTab('tab-dirty', { name: 'Dirty' }, { dirty: true })
      ],
      activeTabId: 'tab-clean'
    })

    render(<TabBar />)

    const cleanTab = screen.getByRole('tab', { name: 'Clean' })
    const dirtyTab = screen.getByRole('tab', { name: /Dirty/ })

    expect(cleanTab.textContent).not.toContain('●')
    expect(dirtyTab.textContent).toContain('●')
  })
})

// ---------------------------------------------------------------------------
// AC-17 — never-zero end-to-end through TabBar (Finding 4)
// ---------------------------------------------------------------------------

describe('AC-17 — never-zero through TabBar: close last tab spawns replacement', () => {
  it('clicking ✕ on the only tab: tabs.length stays 1, replacement id differs, tablist still visible', async () => {
    // Seed EXACTLY ONE tab so the never-zero path is exercised end-to-end.
    const ONLY_ID = 'only-tab'
    tabsStore.setState({
      tabs: [makeTab(ONLY_ID, { name: 'Only Tab', url: '', method: 'GET' })],
      activeTabId: ONLY_ID
    })

    const user = userEvent.setup()
    render(<TabBar />)

    const closeOnlyTab = screen.getByRole('button', { name: 'Close Only Tab' })
    await user.click(closeOnlyTab)

    const { tabs } = tabsStore.getState()

    // (1) Never-zero: exactly one tab must remain (the replacement blank).
    expect(tabs).toHaveLength(1)

    // (2) The replacement tab must have a different id than the closed tab.
    expect(tabs[0].id).not.toBe(ONLY_ID)

    // (3) The TabBar must still render a visible tab button after the interaction.
    expect(screen.getAllByRole('tab').length).toBeGreaterThanOrEqual(1)
  })

  it('clicking ✕ on the only tab: the replacement tab renders with aria-selected="true" (store→TabBar→Tabs activeId binding)', async () => {
    // Exercises the cross-task seam: tabsStore.close sets the replacement's id as
    // activeTabId (Task 2) → TabBar threads it as `activeId` into Tabs (Task 7) →
    // Tabs marks that tab with aria-selected="true". A selector/binding bug would
    // leave the replacement with aria-selected="false" and the tests above would
    // still pass.
    const ONLY_ID = 'only-tab'
    tabsStore.setState({
      tabs: [makeTab(ONLY_ID, { name: 'Only Tab', url: '', method: 'GET' })],
      activeTabId: ONLY_ID
    })

    const user = userEvent.setup()
    render(<TabBar />)

    const closeOnlyTab = screen.getByRole('button', { name: 'Close Only Tab' })
    await user.click(closeOnlyTab)

    // The single remaining tab button must carry aria-selected="true" —
    // proving the replacement id flows correctly from the store through TabBar into
    // the Tabs molecule's aria-selected binding.
    const remainingTabs = screen.getAllByRole('tab')
    expect(remainingTabs).toHaveLength(1)
    expect(remainingTabs[0]).toHaveAttribute('aria-selected', 'true')
  })
})

// ---------------------------------------------------------------------------
// AC-24 (extended) — ✕ close-button aria-label branches (Finding 5)
// ---------------------------------------------------------------------------

describe('AC-24 — ✕ close-button aria-label: method+url and Untitled branches', () => {
  it('close button is "Close <METHOD> <url>" when name is empty and url is non-empty', () => {
    tabsStore.setState({
      tabs: [
        makeTab('tab-method-url', { name: '', url: 'https://api.example.com', method: 'GET' })
      ],
      activeTabId: 'tab-method-url'
    })

    render(<TabBar />)

    // The ✕ button aria-label must be "Close <derived label>" where label = "GET https://api.example.com"
    expect(
      screen.getByRole('button', { name: 'Close GET https://api.example.com' })
    ).toBeInTheDocument()
  })

  it('close button is "Close Untitled" when both name and url are empty', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-untitled', { name: '', url: '', method: 'GET' })],
      activeTabId: 'tab-untitled'
    })

    render(<TabBar />)

    // The ✕ button aria-label must be "Close Untitled"
    expect(screen.getByRole('button', { name: 'Close Untitled' })).toBeInTheDocument()
  })
})
