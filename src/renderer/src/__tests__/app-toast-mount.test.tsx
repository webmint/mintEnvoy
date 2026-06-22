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
 * is needed: App mounts only ToastProvider + ToastViewport (+ the dev-only
 * PrimitivesDemo, which is null under the test build's import.meta.env.DEV).
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
