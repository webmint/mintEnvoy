/**
 * App.test.tsx
 *
 * Composed-request-pane smoke test (plan-additive, mitigates integration Risk 5).
 *
 * Asserts that rendering <App /> wires up the composed request pane correctly:
 * - RequestBar renders above RequestSubTabs (DOM order, AC-18 "above").
 * - RequestSubTabs mounts (the 6-tab sub-tab strip is present, AC-18).
 * - The Params slot renders a live KVTable (bound to field='params', AC-11).
 * - The Headers slot renders a live KVTable (bound to field='headers', AC-11).
 *
 * ## Store reset strategy
 *
 * The tabsStore seeds one blank tab at construction, so no explicit store
 * reset is needed for a fresh-render smoke test — the same approach used in
 * app-toast-mount.test.tsx. Each test gets its own render, so there is no
 * shared component state between cases.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import App from '@renderer/App'

describe('App — composed request pane (AC-11, AC-18)', () => {
  it('RequestBar renders above RequestSubTabs in the request pane (AC-18)', () => {
    render(<App />)

    const paneContainer = document.querySelector('.pane-split__pane--request')
    expect(paneContainer).not.toBeNull()

    const requestBar = paneContainer?.querySelector('.request-bar')
    const requestSubTabs = paneContainer?.querySelector('.request-sub-tabs')

    expect(requestBar).not.toBeNull()
    expect(requestSubTabs).not.toBeNull()

    // DOCUMENT_POSITION_FOLLOWING (bit 2) is set when requestSubTabs follows
    // requestBar in tree order. A transposition of the two App fragment children
    // would clear this bit and fail the assertion.
    const position = requestBar!.compareDocumentPosition(requestSubTabs!)
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeGreaterThan(0)
  })

  it('mounts RequestSubTabs in the request pane slot (AC-18)', () => {
    render(<App />)

    const paneContainer = document.querySelector('.pane-split__pane--request')
    expect(paneContainer).not.toBeNull()
    // RequestSubTabs renders a tablist with aria-label "Request sub-tabs"
    const tablist = paneContainer?.querySelector('[aria-label="Request sub-tabs"]')
    expect(tablist).not.toBeNull()
    // The Params tab must be present in the 6-tab strip
    expect(screen.getByRole('tab', { name: /Params/ })).toBeInTheDocument()
  })

  it('renders a live KVTable bound to field="params" in the Params tabpanel (AC-11)', () => {
    render(<App />)

    // KVTable is injected from the App root into the Params slot of RequestSubTabs.
    // RequestSubTabs always-mounts all panels (hidden-toggled, not conditional
    // unmount), so #panel-params is in the DOM from mount without tab interaction.
    const paramsPanel = document.getElementById('panel-params')
    expect(paramsPanel).not.toBeNull()
    // KVTable renders a .kv root div with a .kv-header inside
    expect(paramsPanel?.querySelector('.kv')).not.toBeNull()
    expect(paramsPanel?.querySelector('.kv-header')).not.toBeNull()
  })

  it('renders a live KVTable bound to field="headers" in the Headers tabpanel (AC-11)', () => {
    render(<App />)

    // RequestSubTabs always-mounts all panels, so #panel-headers is in the DOM
    // from mount. A dropped headers={...} prop in App.tsx would leave this empty.
    const headersPanel = document.getElementById('panel-headers')
    expect(headersPanel).not.toBeNull()
    // KVTable renders a .kv root div with a .kv-header inside
    expect(headersPanel?.querySelector('.kv')).not.toBeNull()
    expect(headersPanel?.querySelector('.kv-header')).not.toBeNull()
  })

  it('typing into the live Params KVTable updates the Params sub-tab badge (KVTable→badge integration)', () => {
    render(<App />)

    // The virtual trailing KVTable row's key input — the tab starts with no stored
    // params rows, so the first .kv-row is the virtual one (class .empty).
    const paramsPanel = document.getElementById('panel-params')
    expect(paramsPanel).not.toBeNull()
    const keyInputEl = paramsPanel!.querySelector('.kv-row.empty .kv-cell.key input')
    expect(keyInputEl).not.toBeNull()

    // Initially no badge on the Params tab.
    const paramsTab = screen.getByRole('tab', { name: /Params/ })
    expect(paramsTab.querySelector('.tabs__badge')).toBeNull()

    // Fire a change event on the KVTable virtual row's key input — this triggers
    // KVTable's onChange → handleVirtualKeyValue → writeRows → updateActiveSpec.
    // The store patch (params: [{key:'q',...}]) fires RequestSubTabs's paramsLength
    // scalar selector → re-render → badge shows "1" (end-to-end composed path).
    fireEvent.change(keyInputEl!, { target: { value: 'q' } })

    expect(paramsTab).toHaveTextContent('1')
  })
})
