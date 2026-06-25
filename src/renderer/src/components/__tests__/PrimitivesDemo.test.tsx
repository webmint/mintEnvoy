/**
 * PrimitivesDemo.test.tsx
 *
 * Guards for the dev-only PrimitivesDemo component:
 *
 *   1. Production-safety guard — when import.meta.env.DEV is false the
 *      component renders nothing (returns null). This is the key assertion
 *      that proves the component-internal belt-and-suspenders guard works.
 *
 *   2. DEV smoke render — with DEV true (the vitest default) all four gallery
 *      sections mount without throwing and their section headings are present.
 *
 * PrimitivesDemo is a dev-only component rendered directly by this test file.
 * It is NOT mounted by App.tsx (App.tsx mounts only ToastProvider + Shell +
 * ToastViewport). There is no App.tsx mount-gate or lazy/Suspense wrapper for
 * this component; the component-internal DEV guard is the sole production-safety
 * mechanism tested here.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
import { PrimitivesDemo } from '@renderer/components/PrimitivesDemo'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Render PrimitivesDemo inside a ToastProvider so toast calls don't throw. */
function renderDemo(): ReturnType<typeof render> {
  return render(
    <ToastProvider>
      <PrimitivesDemo />
      <ToastViewport />
    </ToastProvider>
  )
}

// ---------------------------------------------------------------------------
// 1. Production-safety guard (DEV = false)
// ---------------------------------------------------------------------------

describe('PrimitivesDemo — production-safety guard (DEV = false)', () => {
  beforeEach(() => {
    vi.stubEnv('DEV', false)
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('renders nothing when import.meta.env.DEV is false', () => {
    renderDemo()
    // The component must return null — no demo-root landmark should exist.
    // (The container is not empty because ToastViewport is also rendered,
    // so we assert on the absence of the demo landmark specifically.)
    expect(screen.queryByRole('main', { name: /Primitives demo gallery/i })).not.toBeInTheDocument()
  })

  it('does not render any demo section headings in production mode', () => {
    renderDemo()
    expect(screen.queryByRole('heading', { name: /Icon/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Dropdown/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Modal/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Toast/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /Tabs/i })).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// 2. DEV smoke render (DEV = true, the vitest default)
// ---------------------------------------------------------------------------

describe('PrimitivesDemo — DEV smoke render', () => {
  it('renders without throwing', () => {
    expect(() => renderDemo()).not.toThrow()
  })

  it('renders the "Primitives Gallery" landmark with an accessible label', () => {
    renderDemo()
    expect(screen.getByRole('main', { name: /Primitives demo gallery/i })).toBeInTheDocument()
  })

  it('renders the Icon section heading', () => {
    renderDemo()
    expect(screen.getByRole('heading', { name: 'Icon', level: 2 })).toBeInTheDocument()
  })

  it('renders the Dropdown section heading', () => {
    renderDemo()
    expect(screen.getByRole('heading', { name: 'Dropdown', level: 2 })).toBeInTheDocument()
  })

  it('renders the Modal section heading', () => {
    renderDemo()
    expect(screen.getByRole('heading', { name: 'Modal', level: 2 })).toBeInTheDocument()
  })

  it('renders the Toast section heading', () => {
    renderDemo()
    expect(screen.getByRole('heading', { name: 'Toast', level: 2 })).toBeInTheDocument()
  })

  it('renders the Tabs section heading', () => {
    renderDemo()
    expect(screen.getByRole('heading', { name: 'Tabs', level: 2 })).toBeInTheDocument()
  })

  it('renders Tabs component instances through the gallery registration', () => {
    renderDemo()
    // Both REQUEST_TABS and RESPONSE_TABS instances must produce a tablist —
    // this proves the <Tabs> component wired into TabsSection actually rendered,
    // not just that the section heading mounted.
    expect(screen.getAllByRole('tablist').length).toBeGreaterThanOrEqual(2)
    // Spot-check a known tab label from REQUEST_TABS to confirm tab elements render.
    expect(screen.getByRole('tab', { name: 'Params' })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// 3. Closable-tabs handleClose interaction (DEV = true, the vitest default)
// ---------------------------------------------------------------------------

describe('PrimitivesDemo — closable-tabs handleClose (DEV mode)', () => {
  it('closing the ACTIVE tab selects the right neighbor (prefer-right selectNeighborId)', async () => {
    // The closable demo starts with 'GET /users' active (id: cl-get).
    // The second tab is 'POST /auth'. Closing the active first tab must
    // move focus to that right neighbor — matching selectNeighborId semantics.
    const user = userEvent.setup()
    renderDemo()

    const closeActiveBtn = screen.getByRole('button', { name: 'Close GET /users' })
    await user.click(closeActiveBtn)

    // The 'GET /users' tab must no longer be in the tablist.
    expect(screen.queryByRole('tab', { name: 'GET /users' })).not.toBeInTheDocument()

    // The right neighbor 'POST /auth' must now be the active tab (aria-selected).
    const postAuthTab = screen.getByRole('tab', { name: 'POST /auth' })
    expect(postAuthTab).toHaveAttribute('aria-selected', 'true')
  })

  it('closing the ONLY tab in the closable demo does NOT remove it (never-close-last guard)', async () => {
    // Render and close all tabs except the last one, then verify the final tab
    // cannot be removed — it stays in the tablist.
    const user = userEvent.setup()
    renderDemo()

    // Close three of the four initial tabs to get down to one.
    await user.click(screen.getByRole('button', { name: 'Close GET /users' }))
    await user.click(screen.getByRole('button', { name: 'Close POST /auth' }))
    await user.click(screen.getByRole('button', { name: 'Close PUT /profile' }))

    // Now only 'DELETE /item' remains. Attempt to close it.
    const closableTablist = screen.getByRole('tablist', { name: 'Closable request tabs demo' })
    const remainingTabs = Array.from(closableTablist.querySelectorAll('[role="tab"]'))
    expect(remainingTabs).toHaveLength(1)

    const closeLastBtn = screen.getByRole('button', { name: 'Close DELETE /item' })
    await user.click(closeLastBtn)

    // The tab must still be present — the guard prevents removing the last tab.
    const tabsAfter = Array.from(closableTablist.querySelectorAll('[role="tab"]'))
    expect(tabsAfter).toHaveLength(1)
    expect(screen.getByRole('tab', { name: 'DELETE /item' })).toBeInTheDocument()
  })
})
