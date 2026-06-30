/**
 * Tabs.stories.tsx — Playwright CT fixture components for Tabs.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers for Tabs CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 *
 * Fixtures exported here:
 *   TabsFixture                    — standard 4-tab strip (AC-7/6/8/9/10)
 *   TabsActionsFixture             — strip with actions slot (AC-8)
 *   TabsNoMatchFixture             — no-match activeId (AC-10)
 *   TabsAllDisabledFixture         — all-disabled (AC-10)
 *   TabsClosableFixture            — signal-only closable (AC-22/23)
 *   TabsClosableRemoveFixture      — closable + removal + focus restoration (AC-23)
 *   TabsNonCloseReRenderFixture    — non-close re-render with focus inside list (AC-23 guard)
 *   TabsClosableRemoveTwoPhase     — two-phase close: close non-active tab then close active (AC-23 guard)
 *   TabbarFidelityFixture          — .tabbar-scoped closable strip for feature-005 fidelity (Task 009)
 *   TabbarLongTitleFidelityFixture — two long-title tabs + one short for [011] AC-7/AC-8 width cap assertions (Task 002)
 *   TabbarInShellTabsFixture       — TabbarFidelityFixture inside .shell__tabs wrapper for AC-17 Shell-context assertion
 */

import { useEffect, useState } from 'react'
import { Tabs } from '@renderer/components/molecules/Tabs'
import type { TabDescriptor } from '@renderer/components/molecules/Tabs'
import { selectNeighborId } from '@renderer/lib/tabsStore'
import { Icon } from '@renderer/components/atoms/Icon'

// Fidelity harness composition: load TabBar.css so the .tabbar organism-level
// rules (background, height, padding-right) resolve on the mounted
// <div class="tabs tabbar"> element — reproducing the same CSS cascade that the
// production element receives when TabBar.tsx renders (TabBar.tsx imports
// TabBar.css; Tabs.tsx imports Tabs.css; the real element gets both).
// Without this import the CT harness only loads Tabs.css, so .tabbar strip
// geometry would remain unset and AC-14 computed-style assertions would fail.
// This is a documented test-harness composition, mirroring task 006's
// tokens.css import in playwright/index.tsx.
import '@renderer/components/organisms/TabBar.css'
// Import Shell.css so the .shell__tabs rule resolves in the Shell-context AC-17
// fixture (TabbarInShellTabsFixture). Same test-harness composition pattern as the
// TabBar.css import above — mirrors the CSS cascade the production element receives
// when TabBar mounts inside Shell's workspace column.
import '@renderer/components/organisms/shell/Shell.css'

// Re-export TabDescriptor so fixtures below can use it without
// introducing a separate import in Tabs.ct.tsx.
export type { TabDescriptor }

// ---------------------------------------------------------------------------
// TabsFixture — a self-contained controlled tab strip for CT mounting
// ---------------------------------------------------------------------------

/** Props for the TabsFixture component. */
export interface TabsFixtureProps {
  /** The tab id that is active when the fixture first mounts. */
  initialActiveId?: string
}

/**
 * Fixture component: renders a controlled Tabs strip with a mixed set of
 * enabled and disabled tabs so CT tests have a full interactive strip to probe.
 *
 * Tab layout (index order):
 *   0 — "params"   enabled   (initial active)
 *   1 — "headers"  enabled
 *   2 — "body"     DISABLED
 *   3 — "auth"     enabled
 *
 * data-testids:
 *   ct-tabs-last-change  — shows the last id passed to onChange (empty on mount)
 */
export function TabsFixture({ initialActiveId = 'params' }: TabsFixtureProps): React.JSX.Element {
  const [activeId, setActiveId] = useState(initialActiveId)
  const [lastChange, setLastChange] = useState('')

  const tabs: TabDescriptor[] = [
    { id: 'params', label: 'Params' },
    { id: 'headers', label: 'Headers' },
    { id: 'body', label: 'Body', disabled: true },
    { id: 'auth', label: 'Auth' }
  ]

  function handleChange(id: string): void {
    setActiveId(id)
    setLastChange(id)
  }

  return (
    <div>
      <Tabs aria-label="Request sections" tabs={tabs} activeId={activeId} onChange={handleChange} />
      <div data-testid="ct-tabs-last-change">{lastChange}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabsActionsFixture — fixture exercising the actions slot
// ---------------------------------------------------------------------------

/**
 * Fixture that exercises the optional `actions` slot.
 *
 * Renders a three-tab strip (all enabled) plus an "Add tab" button in the
 * actions slot. CT tests verify focus movement and that actions are not
 * inside the tablist.
 *
 * data-testids:
 *   ct-tabs-actions-last-change  — shows the last id passed to onChange
 *   ct-tabs-add-btn              — the actions-slot button
 */
export function TabsActionsFixture(): React.JSX.Element {
  const [activeId, setActiveId] = useState('one')
  const [lastChange, setLastChange] = useState('')

  const tabs: TabDescriptor[] = [
    { id: 'one', label: 'One' },
    { id: 'two', label: 'Two' },
    { id: 'three', label: 'Three' }
  ]

  function handleChange(id: string): void {
    setActiveId(id)
    setLastChange(id)
  }

  return (
    <div>
      <Tabs
        aria-label="Sections"
        tabs={tabs}
        activeId={activeId}
        onChange={handleChange}
        actions={<button data-testid="ct-tabs-add-btn">+ Add</button>}
      />
      <div data-testid="ct-tabs-actions-last-change">{lastChange}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabsNoMatchFixture — activeId matches no tab (AC-10 no-selection guard)
// ---------------------------------------------------------------------------

/**
 * Fixture for the no-selection guard test (AC-10).
 *
 * Renders a strip where `activeId` deliberately matches no tab descriptor,
 * so no tab should receive `aria-selected="true"`.
 *
 * data-testids:
 *   ct-tabs-nomatch-change  — shows the last id passed to onChange
 */
export function TabsNoMatchFixture(): React.JSX.Element {
  const [lastChange, setLastChange] = useState('')

  const tabs: TabDescriptor[] = [
    { id: 'alpha', label: 'Alpha' },
    { id: 'beta', label: 'Beta' }
  ]

  return (
    <div>
      <Tabs
        aria-label="No-match tabs"
        tabs={tabs}
        activeId="nonexistent-id"
        onChange={setLastChange}
      />
      <div data-testid="ct-tabs-nomatch-change">{lastChange}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabsAllDisabledFixture — all tabs are disabled (AC-10 no-selection guard)
// ---------------------------------------------------------------------------

/**
 * Fixture for the all-disabled no-selection guard test (AC-10).
 *
 * Every tab in the strip is disabled so neither aria-selected nor tabIndex=0
 * should be assigned to any tab button.
 */
export function TabsAllDisabledFixture(): React.JSX.Element {
  const tabs: TabDescriptor[] = [
    { id: 'a', label: 'Alpha', disabled: true },
    { id: 'b', label: 'Beta', disabled: true }
  ]

  return <Tabs aria-label="All-disabled tabs" tabs={tabs} activeId="a" onChange={() => {}} />
}

// ---------------------------------------------------------------------------
// TabsClosableFixture — closable=true strip for AC-22/AC-23 CT tests
// ---------------------------------------------------------------------------

/** Props for the TabsClosableFixture component. */
export interface TabsClosableFixtureProps {
  /** The tab id that is active when the fixture first mounts. */
  initialActiveId?: string
}

/**
 * Fixture for closable=true tests (AC-22, AC-23, AC-12).
 *
 * Tab layout (index order):
 *   0 — "params"   enabled   (initial active)
 *   1 — "headers"  enabled
 *   2 — "auth"     enabled
 *
 * The fixture records the last onClose id and the last onChange id via
 * data-testid elements so CT tests can inspect them.
 *
 * data-testids:
 *   ct-closable-last-change  — last id passed to onChange (empty on mount)
 *   ct-closable-last-close   — last id passed to onClose (empty on mount)
 */
export function TabsClosableFixture({
  initialActiveId = 'params'
}: TabsClosableFixtureProps): React.JSX.Element {
  const [activeId, setActiveId] = useState(initialActiveId)
  const [lastChange, setLastChange] = useState('')
  const [lastClose, setLastClose] = useState('')

  const tabs: TabDescriptor[] = [
    { id: 'params', label: 'Params' },
    { id: 'headers', label: 'Headers' },
    { id: 'auth', label: 'Auth' }
  ]

  function handleChange(id: string): void {
    setActiveId(id)
    setLastChange(id)
  }

  function handleClose(id: string): void {
    setLastClose(id)
    // Signal-only fixture: does not remove the tab from the list.
    // Use TabsClosableRemoveFixture for removal/focus-restoration tests.
  }

  return (
    <div>
      <Tabs
        aria-label="Closable sections"
        tabs={tabs}
        activeId={activeId}
        onChange={handleChange}
        closable
        onClose={handleClose}
      />
      <div data-testid="ct-closable-last-change">{lastChange}</div>
      <div data-testid="ct-closable-last-close">{lastClose}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabsClosableRemoveFixture — removes a tab and updates activeId to simulate
// the store's post-close state, exercising AC-23 focus restoration.
// ---------------------------------------------------------------------------

/**
 * Fixture for focus restoration after a tab is closed (AC-23).
 *
 * Initial tab layout:
 *   0 — "params"   enabled   (initial active)
 *   1 — "headers"  enabled
 *   2 — "auth"     enabled
 *
 * When onClose fires for the active tab ("params"), the fixture removes it
 * from the list and sets activeId to "headers" — exactly what the store would
 * do. The useLayoutEffect inside Tabs should then restore focus to the new
 * active tab button.
 *
 * data-testids:
 *   ct-remove-last-change   — last id passed to onChange
 *   ct-remove-last-close    — last id passed to onClose
 */
export function TabsClosableRemoveFixture(): React.JSX.Element {
  const INITIAL_TABS: TabDescriptor[] = [
    { id: 'params', label: 'Params' },
    { id: 'headers', label: 'Headers' },
    { id: 'auth', label: 'Auth' }
  ]

  const [tabs, setTabs] = useState<TabDescriptor[]>(INITIAL_TABS)
  const [activeId, setActiveId] = useState('params')
  const [lastChange, setLastChange] = useState('')
  const [lastClose, setLastClose] = useState('')

  function handleChange(id: string): void {
    setActiveId(id)
    setLastChange(id)
  }

  function handleClose(id: string): void {
    setLastClose(id)
    // Simulate store: remove the closed tab and pick a neighbor as the new active
    // using the canonical selectNeighborId helper from tabsStore.
    setTabs((prev) => {
      const idx = prev.findIndex((t) => t.id === id)
      const next = prev.filter((t) => t.id !== id)
      if (next.length > 0) {
        setActiveId(selectNeighborId(prev, idx))
      }
      return next
    })
  }

  return (
    <div>
      <Tabs
        aria-label="Removable sections"
        tabs={tabs}
        activeId={activeId}
        onChange={handleChange}
        closable
        onClose={handleClose}
      />
      <div data-testid="ct-remove-last-change">{lastChange}</div>
      <div data-testid="ct-remove-last-close">{lastClose}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabsNonCloseReRenderFixture — changed tabs[] but SAME activeId, for AC-23
// non-close guard test (focus INSIDE the list must NOT steal focus).
// ---------------------------------------------------------------------------

/**
 * Fixture for the AC-23 non-close re-render guard test.
 *
 * Renders a closable strip. Exposes `window.__tabsNonCloseAddTab` so the CT
 * test can trigger a re-render WITHOUT clicking an external button (which would
 * steal focus out of the tablist, clearing lastFocusWasInListRef and making the
 * test exercise the wrong branch).
 *
 * The CT test sequence:
 *   1. Tab into the strip → focus lands on Params (lastFocusWasInListRef = true).
 *   2. Call page.evaluate(() => window.__tabsNonCloseAddTab?.()) to append Auth
 *      without moving focus out of the strip.
 *   3. useLayoutEffect fires: guard=true, activeEl=Params button,
 *      document.activeElement === activeEl → returns early (no focus theft).
 *   4. Assert Params tab is still focused.
 *
 * The key difference from TabsClosableRemoveFixture: the re-render is NOT a
 * close (activeId is unchanged, only the tabs array grows).
 *
 * data-testids:
 *   ct-nonclose-last-change   — last id passed to onChange
 */
export function TabsNonCloseReRenderFixture(): React.JSX.Element {
  const BASE_TABS: TabDescriptor[] = [
    { id: 'params', label: 'Params' },
    { id: 'headers', label: 'Headers' }
  ]

  const [tabs, setTabs] = useState<TabDescriptor[]>(BASE_TABS)
  const [activeId, setActiveId] = useState('params')
  const [lastChange, setLastChange] = useState('')

  function handleChange(id: string): void {
    setActiveId(id)
    setLastChange(id)
  }

  function addTab(): void {
    // Appends a new tab; activeId stays 'params' — non-close re-render.
    setTabs((prev) => [...prev, { id: 'auth', label: 'Auth' }])
  }

  // Expose the addTab function as a global so CT tests can trigger the
  // re-render via page.evaluate without moving browser focus.
  useEffect(() => {
    ;(window as Window & { __tabsNonCloseAddTab?: () => void }).__tabsNonCloseAddTab = addTab
    return () => {
      delete (window as Window & { __tabsNonCloseAddTab?: () => void }).__tabsNonCloseAddTab
    }
    // addTab is stable (defined once per render cycle); deps intentionally empty.
  }, [])

  return (
    <div>
      <Tabs
        aria-label="Non-close re-render sections"
        tabs={tabs}
        activeId={activeId}
        onChange={handleChange}
        closable
        onClose={() => {}}
      />
      <div data-testid="ct-nonclose-last-change">{lastChange}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabsClosableRemoveTwoPhase — two-phase close test fixture (AC-23 guard).
//
// Phase 1: Focus tab Params. Click ✕ of Headers (a DIFFERENT tab).
//           → Internal blur: Params-button → Headers-✕ → guard stays set.
//           → Headers removed; fixture keeps Params as active (it picks the
//             neighbor that results in Params remaining, i.e. Auth at idx 1
//             becomes new active when headers at idx 1 closes... but we
//             customize the logic so that closing a NON-ACTIVE tab keeps
//             the current activeId unchanged if that tab still exists).
// Phase 2: Press Delete on now-focused Params (focus was restored by
//           useLayoutEffect after phase-1 re-render) → Params closes →
//           focus must land on the neighbor.
//
// data-testids:
//   ct-twophase-last-change  — last id passed to onChange
//   ct-twophase-last-close   — last id passed to onClose
// ---------------------------------------------------------------------------

/**
 * Fixture for the two-phase internal-transfer guard test.
 *
 * Initial tab layout:
 *   0 — "params"   enabled   (initial active)
 *   1 — "headers"  enabled
 *   2 — "auth"     enabled
 *
 * handleClose logic:
 *   - If the closed tab is NOT the active tab, remove it and keep the current
 *     activeId (the active tab is still present).
 *   - If the closed tab IS the active tab, remove it and pick the neighbor.
 *
 * This lets the test do: focus Params → close Headers (guard stays, Params
 * still active, useLayoutEffect focuses Params) → press Delete on Params
 * (closes Params) → focus lands on Auth (neighbor).
 */
export function TabsClosableRemoveTwoPhase(): React.JSX.Element {
  const INITIAL_TABS: TabDescriptor[] = [
    { id: 'params', label: 'Params' },
    { id: 'headers', label: 'Headers' },
    { id: 'auth', label: 'Auth' }
  ]

  const [tabs, setTabs] = useState<TabDescriptor[]>(INITIAL_TABS)
  const [activeId, setActiveId] = useState('params')
  const [lastChange, setLastChange] = useState('')
  const [lastClose, setLastClose] = useState('')

  function handleChange(id: string): void {
    setActiveId(id)
    setLastChange(id)
  }

  function handleClose(id: string): void {
    setLastClose(id)
    setTabs((prev) => {
      const idx = prev.findIndex((t) => t.id === id)
      const next = prev.filter((t) => t.id !== id)
      if (id === activeId) {
        // Active tab closed: pick neighbor.
        const newActive = next[Math.min(idx, next.length - 1)]
        if (newActive !== undefined) {
          setActiveId(newActive.id)
        }
      }
      // Non-active tab closed: keep current activeId (it still exists).
      return next
    })
  }

  return (
    <div>
      <Tabs
        aria-label="Two-phase sections"
        tabs={tabs}
        activeId={activeId}
        onChange={handleChange}
        closable
        onClose={handleClose}
      />
      <div data-testid="ct-twophase-last-change">{lastChange}</div>
      <div data-testid="ct-twophase-last-close">{lastClose}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabbarFidelityFixture — .tabbar-scoped fidelity fixture (feature-005, Task 009)
// ---------------------------------------------------------------------------

/**
 * Fidelity fixture for feature-005 tabbar computed-style assertions (Task 009).
 *
 * Mounts <Tabs className="tabbar" closable> so the .tabbar-scoped CSS rules
 * engage (they require the compound .tabbar selector on the outer container).
 * The active tab carries method="HEAD" so the HEAD chip color can be asserted
 * under [data-mstyle="soft"]. A dirty tab and a clean tab complete the set.
 *
 * F1 grill binding: every fidelity assertion is .tabbar-compound-scoped and the
 * active ::before/::after only render on the wrapper in the closable branch.
 * Mounting a bare <Tabs> would measure unscoped, inert rules.
 *
 * Tab layout:
 *   0 — "head-tab"   active, method="HEAD"  (asserts AC-19 HEAD chip color)
 *   1 — "dirty-tab"  dirty=true             (dirty-state dot path)
 *   2 — "clean-tab"  default                (close-button path)
 *
 * The CT test sets [data-mstyle="soft"] in beforeEach so the HEAD chip color
 * rule ([data-mstyle="soft"] .method.HEAD { color: var(--m-head) }) applies.
 */
export function TabbarFidelityFixture(): React.JSX.Element {
  const [activeId, setActiveId] = useState('head-tab')

  const tabs: TabDescriptor[] = [
    { id: 'head-tab', label: 'GET /users', method: 'HEAD' },
    { id: 'dirty-tab', label: 'POST /data', dirty: true },
    { id: 'clean-tab', label: 'PUT /item' }
  ]

  return (
    <Tabs
      aria-label="Tabbar fidelity"
      tabs={tabs}
      activeId={activeId}
      onChange={setActiveId}
      className="tabbar"
      closable
      onClose={() => {}}
      actions={
        <>
          {/* Mirror TabBar.tsx's actions row so CT tests can assert the + button
              geometry (Fix D: no border-radius, flush height). The spacer pushes
              the chevron to the right within the actions area. */}
          <button type="button" className="tabbar__new" aria-label="New tab">
            <Icon name="plus" size={13} />
          </button>
          <span className="tabbar__spacer" />
          <button type="button" className="tabbar__overflow" aria-label="More tabs">
            <Icon name="chevronDown" size={13} />
          </button>
        </>
      }
    />
  )
}

// ---------------------------------------------------------------------------
// TabbarLongTitleFidelityFixture — long-title variant for AC-7/AC-8 cap assertion
// ---------------------------------------------------------------------------

/**
 * Fidelity fixture for the tab width cap assertions ([011] AC-7, AC-8, Task 002).
 *
 * Mounts <Tabs className="tabbar" closable> with MULTIPLE long-titled tabs so
 * the "multiple long-titled tabs are open" condition from spec AC-8 is exercised.
 * Each long label overflows 220px if the cap is absent, giving width and tablist
 * measurements real content to compare against the 220px boundary.
 *
 * Baseline lesson (ct-layout-baseline-keycap-confound): never baseline against
 * empty→filled, which conflates unrelated layout effects. Labels are pre-set.
 *
 * Cascade: tokens.css via playwright/index.tsx, TabBar.css + Shell.css
 * (imported at top of this file), .tabbar className scope, and
 * [data-mstyle="soft"] set in beforeEach by the consuming test suite.
 * Unlike TabbarFidelityFixture, this fixture supplies its own border-box reset
 * via the scoped `.ct-borderbox-scope` <style> so cap geometry matches
 * production (playwright/index.tsx imports only tokens.css — base.css is NOT
 * in the global harness; a global import would shift unrelated baselines).
 * TabbarFidelityFixture has no border-box reset and is unaffected.
 *
 * Tab layout:
 *   0 — "long-tab-1"  active, label ~65 chars → overflows at 12.5px font-size
 *   1 — "long-tab-2"  second long tab → exercises "multiple long tabs" condition
 *   2 — "short-tab"   short label for contrast
 *
 * Includes the standard actions row (.tabbar__new, .tabbar__spacer,
 * .tabbar__overflow) so [011] AC-8 can assert the tablist width cap bound.
 */
export function TabbarLongTitleFidelityFixture(): React.JSX.Element {
  const [activeId, setActiveId] = useState('long-tab-1')

  // Labels long enough to clearly overflow 220px: at 12.5px, ~60 ASCII chars
  // render at approximately 450px — well beyond the 220px cap.
  const tabs: TabDescriptor[] = [
    {
      id: 'long-tab-1',
      label: 'GET /api/v2/users/profile/settings/preferences/notifications/enabled'
    },
    {
      id: 'long-tab-2',
      label: 'POST /api/v2/organizations/members/permissions/roles/assignments'
    },
    { id: 'short-tab', label: 'POST /data' }
  ]

  // Reproduce production base.css `* { box-sizing: border-box }` for this
  // fixture only, so the [011] AC-7 cap-geometry assertion (≤221px) measures
  // border-box width (220px max-width caps the full border box) rather than
  // content-box width (220 content + 22 padding + 1 border = 243px).
  // A global base.css import in playwright/index.tsx would shift unrelated
  // screenshot baselines (TabbarFidelityFixture, RequestBar) — so the reset is
  // scoped to this fixture via the `ct-borderbox-scope` wrapper class.
  // Reference: repo memory "CT fidelity fixture scoping".
  return (
    <div className="ct-borderbox-scope">
      <style>{`.ct-borderbox-scope, .ct-borderbox-scope *, .ct-borderbox-scope *::before, .ct-borderbox-scope *::after { box-sizing: border-box; }`}</style>
      <Tabs
        aria-label="Long-title fidelity"
        tabs={tabs}
        activeId={activeId}
        onChange={setActiveId}
        className="tabbar"
        closable
        onClose={() => {}}
        actions={
          <>
            {/* Mirror TabBar.tsx's actions row so CT tests can assert the + button
                geometry and its anchored position after the capped tablist.
                Same pattern as TabbarFidelityFixture (Task 009). */}
            <button type="button" className="tabbar__new" aria-label="New tab">
              <Icon name="plus" size={13} />
            </button>
            <span className="tabbar__spacer" />
            <button type="button" className="tabbar__overflow" aria-label="More tabs">
              <Icon name="chevronDown" size={13} />
            </button>
          </>
        }
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// TabbarInShellTabsFixture — .tabbar inside .shell__tabs wrapper (AC-17)
// ---------------------------------------------------------------------------

/**
 * Fixture for the AC-17 Shell-context assertion.
 *
 * Wraps the same <Tabs className="tabbar" closable> setup inside a
 * <div className="shell__tabs"> element so Shell.css's .shell__tabs rule
 * applies. The CT test asserts that .shell__tabs has NO bottom border
 * (border-bottom-width: 0px), proving the single-border de-dup guarantee:
 * the strip border lives exclusively on .tabbar, not doubled by the Shell
 * wrapper. If Shell.css ever re-introduces a .shell__tabs border-bottom,
 * this test fails.
 *
 * A SEPARATE mount from TabbarFidelityFixture — the screenshot baseline for
 * TabbarFidelityFixture is unchanged by this fixture.
 */
export function TabbarInShellTabsFixture(): React.JSX.Element {
  const [activeId, setActiveId] = useState('head-tab')

  const tabs: TabDescriptor[] = [
    { id: 'head-tab', label: 'GET /users', method: 'HEAD' },
    { id: 'dirty-tab', label: 'POST /data', dirty: true },
    { id: 'clean-tab', label: 'PUT /item' }
  ]

  return (
    <div className="shell__tabs">
      <Tabs
        aria-label="Tabbar fidelity in shell"
        tabs={tabs}
        activeId={activeId}
        onChange={setActiveId}
        className="tabbar"
        closable
        onClose={() => {}}
      />
    </div>
  )
}
