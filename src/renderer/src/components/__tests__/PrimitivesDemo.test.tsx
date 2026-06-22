/**
 * PrimitivesDemo.test.tsx
 *
 * Guards for the dev-only PrimitivesDemo component:
 *
 *   1. Production-safety guard — when import.meta.env.DEV is false the
 *      component renders nothing (returns null). This is the key assertion
 *      that proves the belt-and-suspenders guard works even if the caller
 *      forgets to gate the lazy import.
 *
 *   2. DEV smoke render — with DEV true (the vitest default) all four gallery
 *      sections mount without throwing and their section headings are present.
 *
 * The App.tsx mount-gate (lazy + Suspense, PrimitivesDemo === null in prod)
 * relies on a dynamic import which is hard to intercept in vitest without
 * module mocking; the component-internal guard test below is the primary
 * production-safety assertion.
 */

import { render, screen } from '@testing-library/react'
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
})
