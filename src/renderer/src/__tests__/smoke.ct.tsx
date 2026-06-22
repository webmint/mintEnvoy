import { test, expect } from '@playwright/experimental-ct-react'
import App from '@renderer/App'

// Importing App via the @renderer alias proves the CT Vite alias is wired correctly
// at compile/bundle time. We do NOT mount App (it calls window.electron which is
// unavailable in the CT browser sandbox), but asserting typeof App === 'function'
// proves the import resolved and the module evaluated without errors.
test('@renderer alias resolves: App is a function', async () => {
  expect(typeof App).toBe('function')
})

test('CT harness mounts a trivial component and asserts visibility', async ({ mount }) => {
  const component = await mount(<div data-testid="ct-smoke">hello from CT</div>)
  await expect(component).toBeVisible()
  await expect(component).toContainText('hello from CT')
})
