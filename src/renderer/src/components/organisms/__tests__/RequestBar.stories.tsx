/**
 * RequestBar.stories.tsx — Playwright CT fixture components for RequestBar.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers consumed by RequestBar.ct.tsx.
 *
 * These are NOT Storybook stories — named ".stories.tsx" only for consistency
 * with the Dropdown.stories.tsx project convention.
 */

import { useState, useEffect, useRef } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { makeTab } from '@renderer/__tests__/fixtures/requestSpec'
import { RequestBar, type SendIntent } from '@renderer/components/organisms/RequestBar'
import { METHODS, type HttpMethod } from '@renderer/lib/httpMethods'

// ---------------------------------------------------------------------------
// Stable constants — shared with RequestBar.ct.tsx for cross-file assertions
// ---------------------------------------------------------------------------

/** Stable Tab A id for the per-tab isolation fixture (GET, CT_TAB_A_URL). */
const CT_TAB_A_ID = 'ct-rb-tab-a'
/** Stable Tab B id for the per-tab isolation fixture (POST, CT_TAB_B_URL). */
const CT_TAB_B_ID = 'ct-rb-tab-b'

/** URL seeded into Tab A; asserted in the CT per-tab isolation test. */
export const CT_TAB_A_URL = 'https://tab-a.ct.example.com/api'
/** URL seeded into Tab B; asserted in the CT per-tab isolation test. */
export const CT_TAB_B_URL = 'https://tab-b.ct.example.com/data'

/**
 * URL seeded into the filled fixture; asserted in CT fidelity tests that
 * require a non-empty URL (enables Send, mounts the ⌘↵ keycap hint).
 */
export const CT_FILLED_URL = 'https://example.com/api/v1'

// ---------------------------------------------------------------------------
// Internal factory
// ---------------------------------------------------------------------------

/**
 * Builds a `Tab` fixture with a given id, HTTP method, and URL.
 * Delegates to the shared `makeTab` test-fixture helper so every required
 * `RequestSpec` field is present without duplicating defaults here.
 *
 * @param id      - Unique tab id.
 * @param method  - HTTP method — typed as `HttpMethod` so callers can pass
 *                  literal strings ('GET', 'POST', …) without a cast.
 * @param url     - Request URL to seed into the tab's spec.
 */
function makeCTTab(id: string, method: HttpMethod, url: string): ReturnType<typeof makeTab> {
  return makeTab(id, { method, url })
}

// ---------------------------------------------------------------------------
// RequestBarStoreResetFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: resets the zustand `tabsStore` to a single clean GET tab (empty URL)
 * via `useEffect`, then signals completion by rendering a known `data-testid`.
 *
 * This is mounted in the CT `beforeEach` so every test starts from the same
 * known store state, preventing order-dependent failures when a prior test
 * leaves a non-empty URL or a changed method in the store.
 *
 * The reset follows the established pattern used in TabBar.test.tsx and
 * tabsStore.test.ts (tabsStore.setState in beforeEach), adapted for the
 * browser context via mount-time seeding.
 *
 * data-testids:
 *   ct-store-reset-done  — appears after tabsStore.setState has been called;
 *                          the CT beforeEach waits for this before proceeding.
 */
export function RequestBarStoreResetFixture(): React.JSX.Element {
  const spanRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-default', { method: 'GET', url: '' })],
      activeTabId: 'ct-default'
    })
    // Signal readiness via direct DOM mutation — avoids calling React setState
    // inside an effect body (react-hooks/set-state-in-effect rule).
    // The CT beforeEach waits for `[data-testid="ct-store-reset-done"]` to be
    // attached before proceeding.
    if (spanRef.current !== null) {
      spanRef.current.setAttribute('data-testid', 'ct-store-reset-done')
    }
  }, [])

  return <span ref={spanRef} />
}

// ---------------------------------------------------------------------------
// RequestBarSendSpyFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: wraps `RequestBar` and exposes `onSend` call results as a
 * DOM-observable element so Playwright assertions can verify the send path
 * without relying on Node.js spy functions (which cannot bridge the browser
 * context in Playwright CT).
 *
 * The store is NOT pre-seeded here; tests type a URL into the input (which
 * calls `updateActiveSpec`) so `canSend` becomes true before pressing ⌘↵.
 *
 * data-testids:
 *   ct-rb-last-sent  — last formatted "METHOD::url" (empty until first send)
 */
export function RequestBarSendSpyFixture(): React.JSX.Element {
  const [lastSent, setLastSent] = useState<string>('')

  function handleSend(intent: SendIntent): void {
    setLastSent(`${intent.method}::${intent.url}`)
  }

  return (
    <div>
      <RequestBar onSend={handleSend} />
      <div data-testid="ct-rb-last-sent">{lastSent}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestBarTwoTabFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds the zustand `tabsStore` (in the browser context via
 * `useEffect`) with two known tabs, then renders `RequestBar` alongside a
 * control button to switch the active tab to Tab B.
 *
 * Tabs seeded:
 *   Tab A — GET  CT_TAB_A_URL  (initial active tab)
 *   Tab B — POST CT_TAB_B_URL
 *
 * Because the seed fires in `useEffect` (after the initial render), tests
 * must wait for the URL input to show `CT_TAB_A_URL` before asserting the
 * per-tab state.
 *
 * data-testids:
 *   ct-rb-select-tab-b  — button that switches the active tab to Tab B
 */
export function RequestBarTwoTabFixture(): React.JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeCTTab(CT_TAB_A_ID, 'GET', CT_TAB_A_URL),
        makeCTTab(CT_TAB_B_ID, 'POST', CT_TAB_B_URL)
      ],
      activeTabId: CT_TAB_A_ID
    })
  }, [])

  function handleSelectTabB(): void {
    tabsStore.getState().selectActive(CT_TAB_B_ID)
  }

  return (
    <div>
      <RequestBar />
      <button type="button" data-testid="ct-rb-select-tab-b" onClick={handleSelectTabB}>
        Switch to Tab B
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestBarFilledFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds the zustand `tabsStore` (via `useEffect`) with a single GET
 * tab whose URL is `CT_FILLED_URL`, then renders `RequestBar`.
 *
 * Used in CT fidelity tests that require a non-empty URL so that:
 *   - `canSend` is true → the Send button is enabled with its inset shadow
 *   - the `request-bar__kbd` keycap hint is mounted (aria-hidden ⌘↵ badge)
 *
 * The store update fires in `useEffect` (after first render).  Tests must wait
 * for the URL input to show `CT_FILLED_URL` before asserting enabled-state
 * styles or taking screenshots:
 *   ```ts
 *   await expect(page.getByRole('textbox', { name: 'Request URL' })).toHaveValue(CT_FILLED_URL)
 *   ```
 */
export function RequestBarFilledFixture(): React.JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-filled', { method: 'GET', url: CT_FILLED_URL })],
      activeTabId: 'ct-filled'
    })
  }, [])

  return <RequestBar />
}

// ---------------------------------------------------------------------------
// RequestBarMethodSwitchFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds the zustand `tabsStore` with a single GET tab, then renders
 * `RequestBar` alongside one switch button per HTTP method.
 *
 * Each button calls `tabsStore.getState().updateActiveSpec({ method })` from the
 * React context, avoiding the Radix method-dropdown click-outside arm-race
 * (memory: ct-radix-dismiss-arm-race).
 *
 * METHODS is imported from httpMethods.ts (the single source of truth), so
 * adding a new method there automatically adds its button here — the CT loop
 * will catch any missing chip counter-rule on the first run after the METHODS
 * extension.
 *
 * data-testids:
 *   ct-rb-set-method-GET     — switches the active tab's method to GET
 *   ct-rb-set-method-POST    — switches the active tab's method to POST
 *   ct-rb-set-method-PUT     — switches the active tab's method to PUT
 *   ct-rb-set-method-PATCH   — switches the active tab's method to PATCH
 *   ct-rb-set-method-DELETE  — switches the active tab's method to DELETE
 *   ct-rb-set-method-OPTIONS — switches the active tab's method to OPTIONS
 *   ct-rb-set-method-HEAD    — switches the active tab's method to HEAD
 */
export function RequestBarMethodSwitchFixture(): React.JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-method-switch', { method: 'GET', url: '' })],
      activeTabId: 'ct-method-switch'
    })
  }, [])

  return (
    <div>
      <RequestBar />
      {METHODS.map((method) => (
        <button
          key={method}
          type="button"
          data-testid={`ct-rb-set-method-${method}`}
          onClick={() => tabsStore.getState().updateActiveSpec({ method })}
        >
          {method}
        </button>
      ))}
    </div>
  )
}
