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
 */

import { useState } from 'react'
import { Tabs } from '@renderer/components/molecules/Tabs'
import type { TabDescriptor } from '@renderer/components/molecules/Tabs'

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
