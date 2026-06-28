/**
 * app-toast-mount.test.tsx
 *
 * Single-viewport invariant: render(<App />) must produce EXACTLY ONE
 * .toast-viewport element in the document.  A second ToastProvider or
 * ToastViewport anywhere in the tree would break toast-store routing and
 * produce visual duplicates.
 *
 * The app shell no longer touches window.electron (the electron-vite starter
 * boilerplate — Versions badge + Send-IPC handler — was removed), so no stub
 * is needed: App mounts only ToastProvider + Shell (with a TabBar in the tabs
 * slot) + ToastViewport.
 */

import { render } from '@testing-library/react'
import App from '@renderer/App'

describe('App — single ToastViewport invariant', () => {
  it('renders exactly one .toast-viewport in the document', () => {
    render(<App />)

    const viewports = document.querySelectorAll('.toast-viewport')
    expect(viewports.length).toBe(1)
  })
})

describe('App — Shell tabs slot (AC-27)', () => {
  it('mounts the TabBar into the Shell tabs slot (AC-27)', () => {
    render(<App />)

    const tabsSlot = document.querySelector('.shell__tabs')
    expect(tabsSlot).not.toBeNull()
    // TabBar renders a WAI-ARIA tablist inside the slot; the tabsStore seeds
    // one blank tab at construction so no store setup is required.
    expect(tabsSlot?.querySelector('[role="tablist"]')).not.toBeNull()
  })
})

describe('App — Shell request-pane slot (AC-21)', () => {
  it('mounts the RequestBar into the Shell request-pane slot (AC-21)', () => {
    render(<App />)

    // PaneSplit renders the request slot inside .pane-split__pane--request
    const paneContainer = document.querySelector('.pane-split__pane--request')
    expect(paneContainer).not.toBeNull()
    // RequestBar renders a .request-bar root div; the tabsStore seeds one blank
    // tab at construction so no store setup is required.
    expect(paneContainer?.querySelector('.request-bar')).not.toBeNull()
    // Semantic-content check: RequestBar's URL input carries aria-label="Request URL".
    // An empty root div (broken child render) would pass the class check above but
    // fail here — mirrors the TabBar slot test's [role="tablist"] semantic anchor.
    expect(paneContainer?.querySelector('[aria-label="Request URL"]')).not.toBeNull()
  })
})
