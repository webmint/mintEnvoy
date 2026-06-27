/**
 * Divider.stories.tsx — Playwright CT fixture components for Divider molecule.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers for Divider CT tests.
 *
 * These are NOT Storybook stories — the file is named ".stories.tsx" only
 * because that naming convention is idiomatic for "component fixtures used in
 * browser-rendered tests". The file has no Storybook dependency.
 */

import { useRef, useState } from 'react'
import { Divider } from '@renderer/components/molecules/Divider'
import { SIDEBAR_MIN, SIDEBAR_MAX, PANE_MIN, PANE_MAX } from '@renderer/lib/settingsStore'

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
