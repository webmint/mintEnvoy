/**
 * RequestBar.test.tsx
 *
 * Behavioral tests for the RequestBar organism — the `[method ▾][URL][Send/Save/Share]`
 * bar that binds to the active tab's RequestSpec via tabsStore.
 *
 * Runs under Vitest + jsdom + @testing-library/react.
 *
 * ## Test coverage
 *
 * (a) Trim guard — empty / whitespace url → Send disabled; `onSend` NOT called.
 * (b) Typing a url enables Send; clicking Send calls `onSend` with { tabId, method, url }.
 * (c) Selecting a method via the dropdown calls `updateActiveSpec` → method is written.
 * (d) Save calls `markClean` when dirty; no-op when already clean.
 * (e) Method switch does NOT change the url value.
 * (f) Switching `activeTabId` swaps the rendered method + url (per-tab isolation).
 *
 * ## Keyboard shortcuts
 *
 * (g) ⌘↵ triggers the Send path (same canSend guard; document-level listener).
 * (h) ⌘S triggers the Save path; dirty flag is cleared.
 *
 * ## Store reset strategy
 *
 * RequestBar subscribes to the module-level `tabsStore` singleton. In `beforeEach`
 * we call `tabsStore.setState({ tabs: [...], activeTabId })` to replace the data
 * fields while leaving the zustand action closures intact — the same pattern used
 * in TabBar.test.tsx and tabsStore.test.ts.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { tabsStore } from '@renderer/lib/tabsStore'
import { RequestBar } from '@renderer/components/organisms/RequestBar'
import { makeTab } from '@renderer/__tests__/fixtures/requestSpec'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** Stable id for the primary tab used across most test cases. */
const TAB_A_ID = 'req-tab-a'
/** Stable id for a second tab used in per-tab isolation tests. */
const TAB_B_ID = 'req-tab-b'

/**
 * Reset the store to a single clean GET tab before each test.
 * Keeps tests isolated — no state leaks between cases.
 */
function resetStore(): void {
  tabsStore.setState({
    tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
    activeTabId: TAB_A_ID
  })
}

beforeEach(() => {
  resetStore()
})

// ---------------------------------------------------------------------------
// (a) Trim guard — empty / whitespace url → Send disabled; onSend not called
// ---------------------------------------------------------------------------

describe('(a) trim guard — empty / whitespace url disables Send', () => {
  it('Send button is disabled when url is empty', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('Send button is disabled when url is whitespace only', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '   ' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('clicking Send when url is empty does NOT call onSend', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar onSend={onSend} />)

    // A disabled button is not clickable via userEvent — assert via fireEvent
    const sendBtn = screen.getByRole('button', { name: 'Send' })
    // Attempt a click directly (disabled buttons suppress click in userEvent)
    await user.click(sendBtn)

    expect(onSend).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// (b) Typing a url enables Send; clicking calls onSend
// ---------------------------------------------------------------------------

describe('(b) typing a url enables Send and clicking calls onSend', () => {
  it('Send button is enabled after typing a non-empty url', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    await user.type(urlInput, 'https://api.example.com')

    expect(screen.getByRole('button', { name: 'Send' })).not.toBeDisabled()
  })

  it('clicking Send calls onSend with { tabId, method, url }', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'POST', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar onSend={onSend} />)

    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    await user.type(urlInput, 'https://api.example.com/v2')

    const sendBtn = screen.getByRole('button', { name: 'Send' })
    await user.click(sendBtn)

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(onSend).toHaveBeenCalledWith({
      tabId: TAB_A_ID,
      method: 'POST',
      url: 'https://api.example.com/v2'
    })
  })

  it('clicking Send does not call onSend a second time when url becomes empty again', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar onSend={onSend} />)

    // Clear the url field
    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    await user.clear(urlInput)

    // Send button must now be disabled
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(onSend).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// (c) Selecting a method via the dropdown calls updateActiveSpec
// ---------------------------------------------------------------------------

describe('(c) selecting a method from the dropdown writes via updateActiveSpec', () => {
  it('clicking a method item updates the store method for the active tab', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    // Open the method dropdown — trigger's accessible name is the current method text
    const methodBtn = screen.getByRole('button', { name: 'GET' })
    await user.click(methodBtn)

    // Wait for Radix portal to render the menu items
    const postItem = await screen.findByRole('menuitem', { name: 'POST' })
    await user.click(postItem)

    // Store should reflect the method change
    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.spec.method).toBe('POST')
  })

  it('the method button label updates to reflect the new method after selection', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    // Open dropdown and select DELETE
    const methodBtn = screen.getByRole('button', { name: 'GET' })
    await user.click(methodBtn)

    const deleteItem = await screen.findByRole('menuitem', { name: 'DELETE' })
    await user.click(deleteItem)

    // The trigger button now shows DELETE as its accessible name
    expect(screen.getByRole('button', { name: 'DELETE' })).toBeInTheDocument()
  })

  // Finding 2 — method-selection sets dirty through the assembled UI path
  it('selecting a DIFFERENT method sets both method and dirty=true via the dropdown path', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    const methodBtn = screen.getByRole('button', { name: 'GET' })
    await user.click(methodBtn)

    const postItem = await screen.findByRole('menuitem', { name: 'POST' })
    await user.click(postItem)

    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.spec.method).toBe('POST')
    expect(tab?.dirty).toBe(true)
  })

  // Finding 4 — no-op guard through the UI: re-selecting the same method must NOT set dirty
  it('re-selecting the SAME current method does not set dirty (no-op guard)', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    const methodBtn = screen.getByRole('button', { name: 'GET' })
    await user.click(methodBtn)

    const getItem = await screen.findByRole('menuitem', { name: 'GET' })
    await user.click(getItem)

    const { tabs } = tabsStore.getState()
    expect(tabs.find((t) => t.id === TAB_A_ID)?.dirty).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// (d) Save — calls markClean when dirty; no-op when already clean
// ---------------------------------------------------------------------------

describe('(d) Save — calls markClean when dirty, no-op when clean', () => {
  it('clicking Save on a dirty tab clears the dirty flag in the store', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: true })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    const saveBtn = screen.getByRole('button', { name: 'Save' })
    await user.click(saveBtn)

    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.dirty).toBe(false)
  })

  it('clicking Save on a clean tab leaves dirty as false (no-op)', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: false })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    const saveBtn = screen.getByRole('button', { name: 'Save' })
    await user.click(saveBtn)

    // Dirty must still be false — no spurious state mutation
    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.dirty).toBe(false)
  })

  it('Save has request-bar__save--dirty modifier class when tab is dirty', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: true })],
      activeTabId: TAB_A_ID
    })

    const { container } = render(<RequestBar />)

    expect(container.querySelector('.request-bar__save--dirty')).not.toBeNull()
  })

  it('Save does NOT have request-bar__save--dirty modifier class when tab is clean', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: false })],
      activeTabId: TAB_A_ID
    })

    const { container } = render(<RequestBar />)

    expect(container.querySelector('.request-bar__save--dirty')).toBeNull()
  })

  // Finding 3 — full dirty round-trip via the Save BUTTON after typing (not pre-seeded, not ⌘S)
  it('typing a url then clicking the Save button clears the dirty flag', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    // Typing fires updateActiveSpec({ url }) → dirty becomes true
    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    await user.type(urlInput, 'https://example.com/typed')

    const { tabs: tabsAfterType } = tabsStore.getState()
    expect(tabsAfterType.find((t) => t.id === TAB_A_ID)?.dirty).toBe(true)

    // Click the Save button (not ⌘S) → markClean runs
    const saveBtn = screen.getByRole('button', { name: 'Save' })
    await user.click(saveBtn)

    const { tabs } = tabsStore.getState()
    expect(tabs.find((t) => t.id === TAB_A_ID)?.dirty).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// (e) Method switch does NOT change the url value
// ---------------------------------------------------------------------------

describe('(e) method switch does not change the url value', () => {
  it('selecting a new method leaves the url input value unchanged', async () => {
    const user = userEvent.setup()
    const INITIAL_URL = 'https://api.example.com/users'

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: INITIAL_URL })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    // Verify url is shown in the input
    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    expect(urlInput).toHaveValue(INITIAL_URL)

    // Switch method from GET to PUT
    const methodBtn = screen.getByRole('button', { name: 'GET' })
    await user.click(methodBtn)

    const putItem = await screen.findByRole('menuitem', { name: 'PUT' })
    await user.click(putItem)

    // Url must remain the same
    expect(urlInput).toHaveValue(INITIAL_URL)

    // Verify store url is also unchanged
    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.spec.url).toBe(INITIAL_URL)
  })
})

// ---------------------------------------------------------------------------
// (f) Switching activeTabId swaps the rendered method + url (per-tab isolation)
// ---------------------------------------------------------------------------

describe('(f) switching activeTabId swaps the rendered method + url', () => {
  it('the url input shows the active tab url when switching tabs', () => {
    // Set up two tabs
    tabsStore.setState({
      tabs: [
        makeTab(TAB_A_ID, { method: 'GET', url: 'https://a.example.com' }),
        makeTab(TAB_B_ID, { method: 'POST', url: 'https://b.example.com' })
      ],
      activeTabId: TAB_A_ID
    })

    const { rerender } = render(<RequestBar />)

    // Initially shows Tab A's url
    expect(screen.getByRole('textbox', { name: 'Request URL' })).toHaveValue(
      'https://a.example.com'
    )

    // Switch active tab to Tab B via store
    tabsStore.setState({
      tabs: [
        makeTab(TAB_A_ID, { method: 'GET', url: 'https://a.example.com' }),
        makeTab(TAB_B_ID, { method: 'POST', url: 'https://b.example.com' })
      ],
      activeTabId: TAB_B_ID
    })
    rerender(<RequestBar />)

    // Now shows Tab B's url
    expect(screen.getByRole('textbox', { name: 'Request URL' })).toHaveValue(
      'https://b.example.com'
    )
  })

  it('the method button reflects the active tab method when switching tabs', () => {
    tabsStore.setState({
      tabs: [
        makeTab(TAB_A_ID, { method: 'GET', url: 'https://a.example.com' }),
        makeTab(TAB_B_ID, { method: 'PATCH', url: 'https://b.example.com' })
      ],
      activeTabId: TAB_A_ID
    })

    const { rerender } = render(<RequestBar />)

    // Tab A is active — method button shows GET
    expect(screen.getByRole('button', { name: 'GET' })).toBeInTheDocument()

    // Switch to Tab B
    tabsStore.setState({
      tabs: [
        makeTab(TAB_A_ID, { method: 'GET', url: 'https://a.example.com' }),
        makeTab(TAB_B_ID, { method: 'PATCH', url: 'https://b.example.com' })
      ],
      activeTabId: TAB_B_ID
    })
    rerender(<RequestBar />)

    // Method button now shows PATCH
    expect(screen.getByRole('button', { name: 'PATCH' })).toBeInTheDocument()
  })

  it('url edits on Tab A do not bleed into Tab B (per-tab isolation)', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [
        makeTab(TAB_A_ID, { method: 'GET', url: '' }),
        makeTab(TAB_B_ID, { method: 'POST', url: '' })
      ],
      activeTabId: TAB_A_ID
    })

    const { rerender } = render(<RequestBar />)

    // Type a url into Tab A
    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    await user.type(urlInput, 'https://a-only.example.com')

    // Switch to Tab B
    tabsStore.setState({
      tabs: tabsStore.getState().tabs,
      activeTabId: TAB_B_ID
    })
    rerender(<RequestBar />)

    // Tab B's url must still be empty
    expect(screen.getByRole('textbox', { name: 'Request URL' })).toHaveValue('')
  })
})

// ---------------------------------------------------------------------------
// (g) Keyboard — ⌘↵ triggers Send
// ---------------------------------------------------------------------------

describe('(g) ⌘↵ triggers the Send path', () => {
  it('⌘↵ calls onSend with active tab values when url is non-empty', () => {
    const onSend = vi.fn()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'DELETE', url: 'https://api.example.com/item/1' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar onSend={onSend} />)

    fireEvent.keyDown(document, { key: 'Enter', metaKey: true })

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(onSend).toHaveBeenCalledWith({
      tabId: TAB_A_ID,
      method: 'DELETE',
      url: 'https://api.example.com/item/1'
    })
  })

  it('⌘↵ does NOT call onSend when url is empty', () => {
    const onSend = vi.fn()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar onSend={onSend} />)

    fireEvent.keyDown(document, { key: 'Enter', metaKey: true })

    expect(onSend).not.toHaveBeenCalled()
  })

  it('⌘↵ does NOT call onSend when url is whitespace only', () => {
    const onSend = vi.fn()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '   ' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar onSend={onSend} />)

    fireEvent.keyDown(document, { key: 'Enter', metaKey: true })

    expect(onSend).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// (h) Keyboard — ⌘S triggers Save
// ---------------------------------------------------------------------------

describe('(h) ⌘S triggers the Save path', () => {
  it('⌘S calls markClean on a dirty tab', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: true })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    fireEvent.keyDown(document, { key: 's', metaKey: true })

    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.dirty).toBe(false)
  })

  it('⌘S is a no-op on a clean tab (dirty stays false)', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: false })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    fireEvent.keyDown(document, { key: 's', metaKey: true })

    const { tabs } = tabsStore.getState()
    const tab = tabs.find((t) => t.id === TAB_A_ID)
    expect(tab?.dirty).toBe(false)
  })

  it('⌘S prevents the default browser action', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://example.com' }, { dirty: false })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    const event = new KeyboardEvent('keydown', {
      key: 's',
      metaKey: true,
      bubbles: true,
      cancelable: true
    })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// (i) Share button is a disabled stub (AC-19)
// ---------------------------------------------------------------------------

describe('(i) Share button is disabled (AC-19)', () => {
  it('Share button is always disabled', () => {
    render(<RequestBar />)

    expect(screen.getByRole('button', { name: /share/i })).toBeDisabled()
  })
})

// ---------------------------------------------------------------------------
// (j) Markup fidelity — keycap presence/absence, visible labels, aria-label
//     removal (AC-9, AC-10, AC-11)
// ---------------------------------------------------------------------------

describe('(j) keycap and visible labels (AC-9, AC-10, AC-11)', () => {
  it('request-bar__kbd is absent from the DOM when URL is empty (AC-10)', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '' })],
      activeTabId: TAB_A_ID
    })

    const { container } = render(<RequestBar />)

    expect(container.querySelector('.request-bar__kbd')).toBeNull()
  })

  it('request-bar__kbd is absent from the DOM when URL is whitespace only (AC-10)', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: '   ' })],
      activeTabId: TAB_A_ID
    })

    const { container } = render(<RequestBar />)

    expect(container.querySelector('.request-bar__kbd')).toBeNull()
  })

  it('request-bar__kbd is present in the DOM when URL is non-empty (AC-9)', () => {
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://api.example.com' })],
      activeTabId: TAB_A_ID
    })

    const { container } = render(<RequestBar />)

    expect(container.querySelector('.request-bar__kbd')).not.toBeNull()
  })

  it('request-bar__kbd is absent after URL is cleared (AC-10)', async () => {
    const user = userEvent.setup()

    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://api.example.com' })],
      activeTabId: TAB_A_ID
    })

    const { container } = render(<RequestBar />)

    // Keycap is present initially
    expect(container.querySelector('.request-bar__kbd')).not.toBeNull()

    // Clear the URL field
    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    await user.clear(urlInput)

    // Keycap must now be absent
    expect(container.querySelector('.request-bar__kbd')).toBeNull()
  })

  it('Send button accessible name is exactly "Send" even when keycap is rendered (AC-9)', () => {
    // Seed a non-empty URL so the kbd is rendered
    tabsStore.setState({
      tabs: [makeTab(TAB_A_ID, { method: 'GET', url: 'https://api.example.com' })],
      activeTabId: TAB_A_ID
    })

    render(<RequestBar />)

    // getByRole resolves by accessible name — the aria-hidden kbd must not pollute it
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })

  it('Save button resolves by visible label and carries no aria-label (AC-11)', () => {
    render(<RequestBar />)

    const saveBtn = screen.getByRole('button', { name: 'Save' })
    expect(saveBtn).toBeInTheDocument()
    // aria-label was removed; accessible name is supplied by the visible text
    expect(saveBtn).not.toHaveAttribute('aria-label')
  })

  it('Share button is icon-only: resolves by aria-label="Share" and has no visible text node (AC-3)', () => {
    render(<RequestBar />)

    const shareBtn = screen.getByRole('button', { name: 'Share' })
    expect(shareBtn).toBeInTheDocument()
    // Accessible name now comes from aria-label, not visible text (AC-3 icon-only)
    expect(shareBtn).toHaveAttribute('aria-label', 'Share')
    // No visible "Share" text — textContent is empty beyond the aria-hidden SVG
    expect(shareBtn.textContent?.trim()).toBe('')
  })

  it('URL input placeholder is exactly "Enter URL or paste cURL command…" (AC-2)', () => {
    render(<RequestBar />)

    const urlInput = screen.getByRole('textbox', { name: 'Request URL' })
    expect(urlInput).toHaveAttribute('placeholder', 'Enter URL or paste cURL command…')
  })
})
