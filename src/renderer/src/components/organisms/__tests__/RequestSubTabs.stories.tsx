/**
 * RequestSubTabs.stories.tsx — Playwright CT fixture components for RequestSubTabs.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers consumed by RequestSubTabs.ct.tsx.
 *
 * These are NOT Storybook stories — named ".stories.tsx" only for consistency
 * with the RequestBar.stories.tsx / KVTable.stories.tsx project convention.
 *
 * Styling context (memory: ct-fidelity-fixture-scoping):
 *   - tokens.css is loaded globally via playwright/index.tsx,
 *     making all design tokens available (no local import needed here).
 *   - The component under test (RequestSubTabs) naturally applies the
 *     .pane-tabs class to the Tabs molecule, so the §6-scoped CSS rules in
 *     RequestSubTabs.css are active in every fixture.
 *   - Theme (data-theme attribute) is set by individual CT tests on
 *     document.documentElement, not in beforeEach, so theme-parametrised
 *     fidelity tests can set it before mount.
 *
 * Fixtures exported:
 *   RequestSubTabsStoreResetFixture        — resets tabsStore; CT beforeEach
 *   RequestSubTabsBasicFixture             — single tab + focusable params input
 *   RequestSubTabsTwoRequestTabsFixture    — two tabs for A→B→A state test
 *   RequestSubTabsFidelityFixture          — one tab with param/header rows for badges
 *   RequestSubTabsScrollLeakFixture        — two tabs for scroll-leak regression
 *   RequestSubTabsWithKVTableFixture       — real KVTable in Params slot (AC-9 real-input gate)
 *   RequestSubTabsWithBodyFixture          — live BodyEditor in body slot, active='none'
 *   RequestSubTabsWithBodyRawFixture       — live BodyEditor in body slot, body.active='raw'
 */

import { useEffect, useRef, type JSX } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { makeTab } from '@renderer/__tests__/fixtures/requestSpec'
import { RequestSubTabs } from '@renderer/components/organisms/RequestSubTabs'
import { KVTable } from '@renderer/components/organisms/KVTable'
import { BodyEditor } from '@renderer/components/organisms/BodyEditor'

// ---------------------------------------------------------------------------
// Stable constants (module-internal — not exported to avoid mixing
// component and non-component imports in one CT import statement)
// ---------------------------------------------------------------------------

/** Tab A: initially active, activeSubTab = 'headers'. */
const CT_TAB_A_ID = 'ct-rst-tab-a'

/** Tab B: inactive initially, activeSubTab = 'body'. */
const CT_TAB_B_ID = 'ct-rst-tab-b'

/** Tab A for scroll-leak fixture: both tabs start on 'params'. */
const CT_SL_TAB_A_ID = 'ct-rst-sl-tab-a'

/** Tab B for scroll-leak fixture: both tabs start on 'params'. */
const CT_SL_TAB_B_ID = 'ct-rst-sl-tab-b'

// ---------------------------------------------------------------------------
// RequestSubTabsStoreResetFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: resets the zustand tabsStore to a single clean tab via `useEffect`,
 * then signals completion by attaching `data-testid="ct-rst-store-reset-done"`
 * to a span element.
 *
 * Mount in CT `beforeEach`, wait for the testid, then unmount:
 * ```ts
 * const reset = await mount(<RequestSubTabsStoreResetFixture />)
 * await page.waitForSelector('[data-testid="ct-rst-store-reset-done"]', { state: 'attached' })
 * await reset.unmount()
 * ```
 * The tabsStore state written by the useEffect persists after unmount.
 *
 * Mirrors the RequestBarStoreResetFixture pattern in RequestBar.stories.tsx.
 */
export function RequestSubTabsStoreResetFixture(): JSX.Element {
  const spanRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-rst-default')],
      activeTabId: 'ct-rst-default'
    })
    // Signal readiness via direct DOM mutation — avoids calling React setState
    // inside an effect body (react-hooks/set-state-in-effect rule).
    if (spanRef.current !== null) {
      spanRef.current.setAttribute('data-testid', 'ct-rst-store-reset-done')
    }
  }, [])

  return <span ref={spanRef} />
}

// ---------------------------------------------------------------------------
// RequestSubTabsBasicFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: renders RequestSubTabs with the store state left by the CT
 * beforeEach reset (one clean 'ct-rst-default' tab, activeSubTab='params').
 *
 * The Params slot receives a scrollable container with a focusable text input
 * (`data-testid="ct-rst-params-input"`, defaultValue="hello") so focus and
 * scroll preservation can be asserted in CT.
 *
 * No own useEffect — relies on the clean state from beforeEach.
 *
 * data-testids:
 *   ct-rst-params-input  — focusable text input in the Params panel.
 */
export function RequestSubTabsBasicFixture(): JSX.Element {
  // The outer div gives the flex-column root a BOUNDED height (250px) so that
  // .request-sub-tabs (flex:1) fills exactly 250px, the 36px strip consumes its
  // share, and the remaining ~214px panel becomes scroll-constrained.
  // Without this wrapper the panel grows unboundedly to fit its content, making
  // overflow:auto a no-op (scrollHeight ≤ clientHeight → scrollTop clamps to 0).
  // With it, the 600px spacer overflows the ~214px panel → scrollTop = 50 sticks
  // (AC-9 scroll-preservation CT).
  return (
    <div style={{ height: '250px', display: 'flex', flexDirection: 'column' }}>
      <RequestSubTabs
        params={
          <div style={{ padding: '8px' }}>
            <input
              data-testid="ct-rst-params-input"
              type="text"
              defaultValue="hello"
              style={{ display: 'block', width: '100%', marginBottom: '8px' }}
            />
            {/* Tall spacer so the panel (#panel-params, overflow: auto) has
                scrollable content — allows panel.scrollTop to be set and
                asserted non-vacuously in the AC-9 scroll-preservation CT. */}
            <div style={{ height: '600px' }} />
          </div>
        }
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestSubTabsTwoRequestTabsFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds tabsStore with two request tabs (via useEffect) then renders
 * RequestSubTabs alongside buttons to switch the active request tab.
 *
 * Tabs seeded:
 *   Tab A — activeSubTab = 'headers'  (initial active request tab)
 *   Tab B — activeSubTab = 'body'
 *
 * Wait for the store to seed before asserting, e.g.:
 * ```ts
 * await expect(page.getByRole('tab', { name: 'Headers' })).toHaveAttribute('aria-selected', 'true')
 * ```
 *
 * data-testids:
 *   ct-rst-select-tab-a  — switches the active request tab to Tab A
 *   ct-rst-select-tab-b  — switches the active request tab to Tab B
 */
export function RequestSubTabsTwoRequestTabsFixture(): JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab(CT_TAB_A_ID, {}, { activeSubTab: 'headers' }),
        makeTab(CT_TAB_B_ID, {}, { activeSubTab: 'body' })
      ],
      activeTabId: CT_TAB_A_ID
    })
  }, [])

  function handleSelectTabA(): void {
    tabsStore.getState().selectActive(CT_TAB_A_ID)
  }

  function handleSelectTabB(): void {
    tabsStore.getState().selectActive(CT_TAB_B_ID)
  }

  return (
    <div>
      <RequestSubTabs />
      <button type="button" data-testid="ct-rst-select-tab-a" onClick={handleSelectTabA}>
        Select Tab A
      </button>
      <button type="button" data-testid="ct-rst-select-tab-b" onClick={handleSelectTabB}>
        Select Tab B
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestSubTabsScrollLeakFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds tabsStore with two request tabs, both with activeSubTab='params'
 * (the default), so the Params panel is visible on both tabs without a sub-tab switch.
 * Renders RequestSubTabs with a scrollable Params slot and buttons to switch between
 * the two request tabs.
 *
 * Used for the scroll-leak regression test (Finding 1): scroll tab A's Params to a
 * non-zero value, switch to tab B, assert B's Params scrollTop is 0 (not leaked).
 *
 * data-testids:
 *   ct-rst-sl-select-tab-a  — switches the active request tab to Tab A
 *   ct-rst-sl-select-tab-b  — switches the active request tab to Tab B
 */
export function RequestSubTabsScrollLeakFixture(): JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab(CT_SL_TAB_A_ID, {}, { activeSubTab: 'params' }),
        makeTab(CT_SL_TAB_B_ID, {}, { activeSubTab: 'params' })
      ],
      activeTabId: CT_SL_TAB_A_ID
    })
  }, [])

  function handleSelectTabA(): void {
    tabsStore.getState().selectActive(CT_SL_TAB_A_ID)
  }

  function handleSelectTabB(): void {
    tabsStore.getState().selectActive(CT_SL_TAB_B_ID)
  }

  return (
    <div className="rst-ct-scroll-host">
      <RequestSubTabs
        params={
          <div>
            {/* Tall spacer ensures the Params panel has scrollable overflow,
                making a non-zero scrollTop assertion non-vacuous. */}
            <div className="rst-ct-scroll-spacer" />
          </div>
        }
      />
      <button type="button" data-testid="ct-rst-sl-select-tab-a" onClick={handleSelectTabA}>
        Select Tab A
      </button>
      <button type="button" data-testid="ct-rst-sl-select-tab-b" onClick={handleSelectTabB}>
        Select Tab B
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestSubTabsFidelityFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds tabsStore with a single tab that has one Params row and one
 * Headers row (via useEffect), then renders RequestSubTabs without slot props.
 *
 * This causes:
 *   - Params tab (active by default): badge = 1 → active badge styling
 *     (--accent-soft background, --accent text)
 *   - Headers tab (inactive): badge = 1 → inactive badge styling
 *     (--bg-active background, --text-muted text)
 *
 * Used for per-theme computed-style fidelity assertions (AC-27 / R3 / R7).
 *
 * Wait for badges to appear before asserting styles:
 * ```ts
 * await expect(page.locator('.pane-tabs .tabs__badge').first()).toBeVisible()
 * ```
 */
export function RequestSubTabsFidelityFixture(): JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab('ct-rst-fidelity', {
          params: [{ enabled: true, key: 'q', value: '1', description: '' }],
          headers: [{ enabled: true, key: 'Accept', value: 'application/json', description: '' }]
        })
      ],
      activeTabId: 'ct-rst-fidelity'
    })
  }, [])

  return <RequestSubTabs />
}

// ---------------------------------------------------------------------------
// RequestSubTabsWithKVTableFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds tabsStore with a single tab that has one pre-seeded params row
 * (so KVTable renders a real cell input, not just the virtual trailing row), then
 * renders RequestSubTabs with a live KVTable in the Params slot.
 *
 * Used for the AC-9 CT that exercises focus + value survival across a sub-tab
 * switch when the real KVTable organism (not a plain input) occupies the Params
 * slot — mirroring the App composition root exactly (Finding 3).
 *
 * Uses the .rst-ct-scroll-host bounded-height wrapper (mirrors ScrollLeak fixture)
 * so the Params panel is height-constrained and overflow works correctly.
 *
 * data-testids: none — locators use KVTable's DOM class structure.
 *   Real-row key input: `.kv-row:not(.empty) .kv-cell.key input`
 */
// ---------------------------------------------------------------------------
// RequestSubTabsWithBodyFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds tabsStore with a single tab whose `activeSubTab` is 'body'
 * (via useEffect), then renders RequestSubTabs with a live BodyEditor in the
 * body slot.
 *
 * Used for the body-slot + BodyEditor seam CT (Finding 11): asserting that when
 * the Body sub-tab is active, `[data-testid="body-toolbar"]` is present inside
 * `#panel-body`.
 *
 * NOTE: The corresponding CT lives in RequestSubTabs.ct.tsx. The fixture is
 * placed here following the project convention (all CT fixtures in .stories.tsx).
 *
 * data-testids:
 *   ct-rst-body-ready  — signals the store seed completed; wait for it in CT.
 */
export function RequestSubTabsWithBodyFixture(): JSX.Element {
  const spanRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-rst-body', {}, { activeSubTab: 'body' })],
      activeTabId: 'ct-rst-body'
    })
    if (spanRef.current !== null) {
      spanRef.current.setAttribute('data-testid', 'ct-rst-body-ready')
    }
  }, [])

  return (
    <div className="rst-ct-scroll-host">
      <RequestSubTabs
        body={
          <BodyEditor
            renderUrlencoded={(rows, onRowsChange) => (
              <KVTable rows={rows} onRowsChange={onRowsChange} />
            )}
          />
        }
      />
      <span ref={spanRef} />
    </div>
  )
}

export function RequestSubTabsWithKVTableFixture(): JSX.Element {
  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab('ct-rst-kvtable', {
          params: [{ enabled: true, key: 'ct-key', value: 'ct-value', description: '' }]
        })
      ],
      activeTabId: 'ct-rst-kvtable'
    })
  }, [])

  return (
    <div className="rst-ct-scroll-host">
      <RequestSubTabs params={<KVTable field="params" />} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestSubTabsWithAllSlotsFixture
// ---------------------------------------------------------------------------

/** Tab id for the all-slots concurrent-subscription fixture. */
const CT_RST_ALL_SLOTS_ID = 'ct-rst-all-slots'

/**
 * Fixture: seeds tabsStore with a single tab that has all three data slices
 * populated, then renders RequestSubTabs with ALL THREE slots simultaneously:
 *   - params  → KVTable (field-bound to spec.params)
 *   - headers → KVTable (field-bound to spec.headers)
 *   - body    → BodyEditor (with live KVTable render-prop for urlencoded mode)
 *
 * Mirrors the real App.tsx composition root where all three slot components
 * subscribe to the same tabsStore in the same React tree. Used for the
 * concurrent-subscription topology CT that asserts store-slice independence:
 * a write to one slice (e.g. body.raw.text) must not bleed into another
 * (e.g. spec.params).
 *
 * Seed:
 *   params:       [{ key:'p-key', value:'p-val' }]
 *   headers:      [{ key:'h-key', value:'h-val' }]
 *   body:         active='raw', raw.text='initial-body-text'
 *   activeSubTab: 'body'
 *
 * data-testids:
 *   ct-rst-all-slots-ready — signals the store seed completed; wait for it in CT.
 */
export function RequestSubTabsWithAllSlotsFixture(): JSX.Element {
  const spanRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab(
          CT_RST_ALL_SLOTS_ID,
          {
            params: [{ enabled: true, key: 'p-key', value: 'p-val', description: '' }],
            headers: [{ enabled: true, key: 'h-key', value: 'h-val', description: '' }],
            body: {
              active: 'raw',
              raw: { lang: 'json', text: 'initial-body-text' },
              urlencoded: { rows: [] }
            }
          },
          { activeSubTab: 'body' }
        )
      ],
      activeTabId: CT_RST_ALL_SLOTS_ID
    })
    if (spanRef.current !== null) {
      spanRef.current.setAttribute('data-testid', 'ct-rst-all-slots-ready')
    }
  }, [])

  return (
    <div className="rst-ct-scroll-host">
      <RequestSubTabs
        params={<KVTable field="params" />}
        headers={<KVTable field="headers" />}
        body={
          <BodyEditor
            renderUrlencoded={(rows, onRowsChange) => (
              <KVTable rows={rows} onRowsChange={onRowsChange} />
            )}
          />
        }
      />
      <span ref={spanRef} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// RequestSubTabsWithBodyRawFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds tabsStore with a single tab whose `activeSubTab` is 'body'
 * AND whose `body.active` is 'raw' (so the `<textarea aria-label="Request body">`
 * renders immediately), then renders RequestSubTabs with a live BodyEditor.
 *
 * Used for two Finding-2/3 CTs in RequestSubTabs.ct.tsx:
 *   - Finding 2 (textarea focus-restoration): focus the textarea, switch away
 *     from Body to Params, switch back — assert the textarea regains focus via
 *     RequestSubTabs' lastFocusedInPanel / useLayoutEffect restoration path.
 *   - Finding 3 (body-panel scroll seam): switch away and back — assert the
 *     textarea CONTENT is preserved (mount-all keeps the panel always mounted).
 *     NOTE: textarea internal scrollTop is NOT preserved across the hidden/shown
 *     toggle by design — accepted/known behavior; only content is asserted.
 *
 * data-testids:
 *   ct-rst-body-raw-ready  — signals the store seed completed; wait for it in CT.
 */
export function RequestSubTabsWithBodyRawFixture(): JSX.Element {
  const spanRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab(
          'ct-rst-body-raw',
          {
            body: {
              active: 'raw',
              raw: { lang: 'json', text: 'body-raw-content' },
              urlencoded: { rows: [] }
            }
          },
          { activeSubTab: 'body' }
        )
      ],
      activeTabId: 'ct-rst-body-raw'
    })
    if (spanRef.current !== null) {
      spanRef.current.setAttribute('data-testid', 'ct-rst-body-raw-ready')
    }
  }, [])

  return (
    <div className="rst-ct-scroll-host">
      <RequestSubTabs
        body={
          <BodyEditor
            renderUrlencoded={(rows, onRowsChange) => (
              <KVTable rows={rows} onRowsChange={onRowsChange} />
            )}
          />
        }
      />
      <span ref={spanRef} />
    </div>
  )
}
