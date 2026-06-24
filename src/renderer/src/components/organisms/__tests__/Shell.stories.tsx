/**
 * Shell.stories.tsx — Playwright CT fixture components for Shell organisms.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers for Shell CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 */

import { useEffect, useRef, useState } from 'react'
import { Divider } from '@renderer/components/organisms/Divider'
import { Shell } from '@renderer/components/organisms/Shell'
import { Sidebar } from '@renderer/components/organisms/Sidebar'
import { Titlebar } from '@renderer/components/organisms/Titlebar'
import { Statusbar } from '@renderer/components/organisms/Statusbar'
import { PaneSplit } from '@renderer/components/organisms/PaneSplit'
import {
  settingsStore,
  SIDEBAR_MIN,
  SIDEBAR_MAX,
  PANE_MIN,
  PANE_MAX
} from '@renderer/lib/settingsStore'
import { Tabs } from '@renderer/components/molecules/Tabs'
import type { TabDescriptor } from '@renderer/components/molecules/Tabs'

// ---------------------------------------------------------------------------
// DividerFixture — vertical/sidebar divider for CT drag/keyboard tests
// ---------------------------------------------------------------------------

export interface DividerFixtureProps {
  orientation?: 'vertical' | 'horizontal'
  initialValue?: number
  min?: number
  max?: number
  cssVar?: string
  unit?: string
  keyboardStep?: number
  getDragExtent?: (() => number | null) | undefined
}

/**
 * A self-contained controlled Divider fixture.
 * Tracks the committed value via state so CT tests can read aria-valuenow.
 *
 * data-testids:
 *   ct-divider-committed — displays the last committed value as text
 */
export function DividerFixture({
  orientation = 'vertical',
  initialValue = 300,
  min = SIDEBAR_MIN,
  max = SIDEBAR_MAX,
  cssVar = '--sidebar-width',
  unit = 'px',
  keyboardStep = 8,
  getDragExtent
}: DividerFixtureProps): React.JSX.Element {
  const [value, setValue] = useState(initialValue)

  return (
    <div style={{ width: '600px', height: '600px', display: 'flex', flexDirection: 'column' }}>
      <Divider
        orientation={orientation}
        value={value}
        min={min}
        max={max}
        cssVar={cssVar}
        ariaLabel={orientation === 'vertical' ? 'Resize sidebar' : 'Resize panes'}
        onCommit={(v) => setValue(v)}
        unit={unit}
        keyboardStep={keyboardStep}
        getDragExtent={getDragExtent}
      />
      <div data-testid="ct-divider-committed">{value}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// PaneDividerFixture — horizontal/pane divider with extent-providing container
// ---------------------------------------------------------------------------

/**
 * Pane divider fixture with a container that has real pixel height for the
 * px→ratio conversion. The container is given a fixed height so that the
 * getBoundingClientRect().height returns a real value in Chromium.
 *
 * data-testids:
 *   ct-pane-divider-committed — displays the last committed ratio
 */
export function PaneDividerFixture(): React.JSX.Element {
  const [value, setValue] = useState(0.5)
  // useRef so React tracks the ref and the immutability rule is satisfied
  const containerRef = useRef<HTMLDivElement | null>(null)

  return (
    <div
      ref={containerRef}
      style={{ width: '400px', height: '400px', display: 'flex', flexDirection: 'column' }}
      data-testid="ct-pane-container"
    >
      <Divider
        orientation="horizontal"
        value={value}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        ariaLabel="Resize panes"
        onCommit={(v) => setValue(v)}
        unit=""
        keyboardStep={0.02}
        getDragExtent={() => containerRef.current?.getBoundingClientRect().height ?? null}
      />
      <div data-testid="ct-pane-divider-committed">{value}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ShellWithTabsFixture — Shell with Tabs molecule in the tabs slot
// ---------------------------------------------------------------------------

const REQUEST_TABS: TabDescriptor[] = [
  { id: 'params', label: 'Params' },
  { id: 'headers', label: 'Headers' },
  { id: 'body', label: 'Body' }
]

/**
 * Shell fixture with the Tabs molecule mounted into the tabs slot.
 * Proves content-decoupling: Shell renders the Tabs without inspecting contents.
 *
 * data-testids:
 *   ct-shell-tabs-last-change — shows the last tab id passed to onChange
 */
export function ShellWithTabsFixture(): React.JSX.Element {
  const [activeTab, setActiveTab] = useState('params')
  const [lastChange, setLastChange] = useState('')

  useEffect(() => {
    settingsStore.getState().reset()
    return () => {
      settingsStore.getState().reset()
    }
  }, [])

  function handleTabChange(id: string): void {
    setActiveTab(id)
    setLastChange(id)
  }

  return (
    <div>
      <Shell
        tabs={
          <Tabs
            aria-label="Request sections"
            tabs={REQUEST_TABS}
            activeId={activeTab}
            onChange={handleTabChange}
          />
        }
        sidebar={<div data-testid="ct-shell-sidebar-content">Sidebar content</div>}
        panes={{
          request: <div data-testid="ct-shell-request-content">Request content</div>,
          response: <div data-testid="ct-shell-response-content">Response content</div>
        }}
      />
      <div data-testid="ct-shell-tabs-last-change">{lastChange}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ShellCollapsedFixture — Shell with sidebar initially collapsed
// ---------------------------------------------------------------------------

/**
 * Shell fixture for collapse/expand tests.
 * Resets settingsStore on mount so CT tests are isolated.
 */
export function ShellCollapsedFixture(): React.JSX.Element {
  useEffect(() => {
    settingsStore.getState().reset()
    return () => {
      settingsStore.getState().reset()
    }
  }, [])

  return <Shell sidebar={<div data-testid="ct-shell-sidebar">Sidebar</div>} />
}

// ---------------------------------------------------------------------------
// TitlebarFixture — standalone Titlebar for CT focus tests
// ---------------------------------------------------------------------------

/**
 * Fixture for Titlebar CT tests.
 *
 * data-testids:
 *   ct-titlebar-collapsed — shows current sidebarCollapsed state
 */
export function TitlebarFixture(): React.JSX.Element {
  const collapsed = settingsStore((s) => s.sidebarCollapsed)

  useEffect(() => {
    settingsStore.getState().reset()
    return () => {
      settingsStore.getState().reset()
    }
  }, [])

  return (
    <div>
      <Titlebar />
      <div data-testid="ct-titlebar-collapsed">{String(collapsed)}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// StatusbarFixture — standalone Statusbar with children
// ---------------------------------------------------------------------------

/**
 * Fixture for Statusbar CT tests.
 */
export function StatusbarFixture(): React.JSX.Element {
  return (
    <Statusbar>
      <span data-testid="ct-statusbar-child">Status content</span>
    </Statusbar>
  )
}

// ---------------------------------------------------------------------------
// SidebarFixture — standalone Sidebar for CT tests
// ---------------------------------------------------------------------------

/**
 * Fixture for Sidebar CT drag tests.
 *
 * data-testids:
 *   ct-sidebar-width — shows current sidebarWidth from store
 */
export function SidebarFixture(): React.JSX.Element {
  const sidebarWidth = settingsStore((s) => s.sidebarWidth)

  useEffect(() => {
    settingsStore.getState().reset()
    return () => {
      settingsStore.getState().reset()
    }
  }, [])

  return (
    <div style={{ display: 'flex', height: '400px' }}>
      <Sidebar>
        <div data-testid="ct-sidebar-content">Sidebar content</div>
      </Sidebar>
      <div data-testid="ct-sidebar-width">{sidebarWidth}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// PaneSplitFixture — standalone PaneSplit for CT drag tests
// ---------------------------------------------------------------------------

/**
 * Fixture for PaneSplit CT drag tests.
 *
 * data-testids:
 *   ct-pane-ratio — shows current paneRatio from store
 */
export function PaneSplitFixture(): React.JSX.Element {
  const paneRatio = settingsStore((s) => s.paneRatio)

  useEffect(() => {
    settingsStore.getState().reset()
    return () => {
      settingsStore.getState().reset()
    }
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '600px', width: '400px' }}>
      <PaneSplit
        request={<div data-testid="ct-pane-request">Request</div>}
        response={<div data-testid="ct-pane-response">Response</div>}
      />
      <div data-testid="ct-pane-ratio">{paneRatio}</div>
    </div>
  )
}
