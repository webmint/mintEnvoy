/**
 * KVTable.stories.tsx — Playwright CT fixture components for KVTable.
 *
 * Playwright experimental-ct-react requires that mounted components be defined
 * in a SEPARATE file from the test file (not inside the test file itself).
 * This file exports reusable fixture wrappers consumed by KVTable.ct.tsx.
 *
 * These are NOT Storybook stories — named ".stories.tsx" only for consistency
 * with the RequestBar.stories.tsx project convention.
 *
 * Styling context (project memory ct-fidelity-fixture-scoping):
 *   - tokens.css is imported below for completeness; the global import in
 *     playwright/index.tsx already makes it available for every CT page.
 *   - Each fixture wraps its content in a <div data-theme="dark"> so the
 *     dark-theme token overrides resolve and colour assertions are deterministic.
 */

// NOTE: do NOT `import '@renderer/styles/tokens.css'` here — the `@renderer`
// alias resolves to `src/renderer/src`, so that path ENOENTs (the real file is
// `src/renderer/styles/tokens.css`) and silently breaks the whole CT build
// ("N did not run" under a misleading exit 0). The global `playwright/index.tsx`
// already imports the correct tokens path for every CT page. (ct-tokens-import-alias-trap)
import { useEffect, useRef, useState, type JSX } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { makeTab } from '@renderer/__tests__/fixtures/requestSpec'
import { KVTable } from '@renderer/components/organisms/KVTable'
import type { Row } from '@renderer/lib/tabsStore'

// ---------------------------------------------------------------------------
// Seed data — module-level constants shared between fixtures (not exported so
// the CT file never mixes component and non-component imports in one statement)
// ---------------------------------------------------------------------------

const ROW_ENABLED: Row = {
  enabled: true,
  key: 'api_key',
  value: 'secret',
  description: ''
}

const ROW_DISABLED: Row = {
  enabled: false,
  key: 'disabled_key',
  value: 'disabled_val',
  description: ''
}

const ROW_VAR_X: Row = { enabled: true, key: '{{x}}', value: '', description: '' }
const ROW_VAR_Y: Row = { enabled: true, key: '{{y}}', value: '', description: '' }

const ROW_PADDED_TOKEN: Row = { enabled: true, key: '{{ x }}', value: '', description: '' }
const ROW_VALUE_VAR: Row = { enabled: true, key: 'k', value: '{{v}}', description: '' }

const ROW_DESC_VAR: Row = {
  enabled: true,
  key: 'plain',
  value: 'plain',
  description: '{{x}} not tokenized'
}

const ROW_HEADER: Row = {
  enabled: true,
  key: 'Content-Type',
  value: 'application/json',
  description: ''
}

const REPLACED_ROW: Row = {
  enabled: true,
  key: 'imported_key',
  value: 'imported_value',
  description: ''
}

// ---------------------------------------------------------------------------
// Shared wrapper props
// ---------------------------------------------------------------------------

/** Fixed width so grid-track pixel values are deterministic in fidelity tests. */
const WRAPPER_STYLE: React.CSSProperties = { width: '700px' }

// ---------------------------------------------------------------------------
// KVTableStoreResetFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: resets the zustand `tabsStore` to a known empty state via
 * `useEffect`, then signals completion by setting `data-testid` on a ref span.
 *
 * Mounted in CT `beforeEach`, waited on, then unmounted — so every test starts
 * from the same clean store state (no stale params/headers from a prior test).
 *
 * data-testids:
 *   ct-kv-store-reset-done — appears after tabsStore.setState has been called
 */
export function KVTableStoreResetFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [], headers: [] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-store-reset-done')
    }
  }, [])

  return <span ref={ref} />
}

// ---------------------------------------------------------------------------
// KVTableEmptyParamsFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds an empty params array, renders KVTable(field="params").
 * Used for auto-promote tests and computed-style fidelity tests.
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableEmptyParamsFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable field="params" />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableOneRowParamsFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds one enabled real row in params, renders KVTable(field="params").
 * Used for delete-with-focus, checkbox toggle, and external-mutation tests.
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableOneRowParamsFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_ENABLED] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable field="params" />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableThreeRowsFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds three enabled rows in params, renders KVTable(field="params").
 * Used for delete-middle-with-focus-on-adjacent test.
 *
 * Row order: api_key / middle_key / last_key.
 * Deleting the middle row (index 1) should focus an adjacent row's cell.
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableThreeRowsFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab('ct-kv', {
          params: [
            ROW_ENABLED,
            { enabled: true, key: 'middle_key', value: 'middle_val', description: '' },
            { enabled: true, key: 'last_key', value: 'last_val', description: '' }
          ]
        })
      ],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable field="params" />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableVarNoValidVarsFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds a row with key `{{x}}`, renders KVTable with NO validVars prop.
 * Proves the AC-20 ∅-default path: tokens get .var but NEVER .var.missing when
 * validVars defaults to envVars() (empty set in v1).
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableVarNoValidVarsFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_VAR_X] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      {/* No validVars prop → defaults to envVars() which is empty in v1 */}
      <KVTable field="params" />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableVarWithValidVarsFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds two rows — `{{x}}` (in validVars) and `{{y}}` (absent) —
 * and renders KVTable with `validVars={new Set(['x'])}`.
 * Proves the AC-19 injected path: {{x}} → .var only; {{y}} → .var.missing.
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableVarWithValidVarsFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_VAR_X, ROW_VAR_Y] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable field="params" validVars={new Set(['x'])} />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableDescVarFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds a row whose DESCRIPTION contains `{{x}}`, renders KVTable
 * with validVars={new Set(['x'])} so var tokenisation is active on key/value.
 * Proves R10/AC-11: description is NOT tokenised — no .var span must appear.
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableDescVarFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_DESC_VAR] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      {/* validVars is non-empty so .missing would appear if description were tokenised */}
      <KVTable field="params" validVars={new Set(['x'])} />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableExternalMutationFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds one enabled row; exposes a control button that calls
 * `tabsStore.getState().updateActiveSpec` to replace all params rows —
 * simulating a cURL import that rewrites the grid without user interaction.
 * Used for AC-21 (external state mutation re-renders grid).
 *
 * data-testids:
 *   ct-kv-ready      — appears after the store is seeded
 *   ct-kv-replace    — button that replaces params with REPLACED_ROW
 */
export function KVTableExternalMutationFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_ENABLED] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  function handleReplace(): void {
    tabsStore.getState().updateActiveSpec({ params: [REPLACED_ROW] })
  }

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable field="params" />
      <button type="button" data-testid="ct-kv-replace" onClick={handleReplace}>
        Replace Rows
      </button>
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableDisabledRowFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds one DISABLED real row in params.
 * Used to assert that .kv-row.disabled opacity is 0.55 (fidelity test).
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableDisabledRowFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_DISABLED] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable field="params" />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTablePaddedTokenFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds a row whose KEY is `'{{ x }}'` (padded placeholder) and
 * renders KVTable with `validVars={new Set(['x'])}`.
 * Used to lock the display-length desync fix: the overlay must render the
 * verbatim `'{{ x }}'` (7 chars) not the reconstructed `'{{x}}'` (5 chars).
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTablePaddedTokenFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_PADDED_TOKEN] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      {/* validVars contains 'x' (trimmed name) so the token resolves — no .missing */}
      <KVTable field="params" validVars={new Set(['x'])} />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableValueCellFixture
// ---------------------------------------------------------------------------

/**
 * Fixture: seeds a row whose VALUE is `'{{v}}'` and renders KVTable with no
 * validVars prop (defaults to envVars() — empty set, so no .missing gate).
 * Used to assert that the value cell's `.kv-highlight` overlay tokenises the
 * value text (the `renderSegments(row.value)` path), previously untested.
 *
 * data-testids:
 *   ct-kv-ready — appears after the store is seeded
 */
export function KVTableValueCellFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [makeTab('ct-kv', { params: [ROW_VALUE_VAR] })],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      {/* No validVars prop → all tokens are .var only, never .var.missing */}
      <KVTable field="params" />
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableTwoFieldsFixture
// ---------------------------------------------------------------------------

export function KVTableTwoFieldsFixture(): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    tabsStore.setState({
      tabs: [
        makeTab('ct-kv', {
          params: [ROW_ENABLED],
          headers: [ROW_HEADER]
        })
      ],
      activeTabId: 'ct-kv'
    })
    if (ref.current !== null) {
      ref.current.setAttribute('data-testid', 'ct-kv-ready')
    }
  }, [])

  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <div data-testid="params-table">
        <KVTable field="params" />
      </div>
      <div data-testid="headers-table">
        <KVTable field="headers" />
      </div>
      <span ref={ref} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableControlledFixture (task 005 controlled arm)
// ---------------------------------------------------------------------------

/**
 * Fixture: renders KVTable in CONTROLLED mode — rows live in local component
 * state, `onRowsChange` replaces them. An edit therefore round-trips through
 * the callback (never the tabsStore).
 *
 * Also renders a live read-out of the ACTIVE tab's stored `params.length` so a
 * test can assert the store is NEVER written during a controlled-mode edit —
 * the AC-11 negative arm (carried from the task 005 review). `beforeEach` seeds
 * `params: []`, so the read-out is `0` and must stay `0` across a controlled edit.
 *
 * data-testids:
 *   ct-kv-ready              — always present (no async seed for local state)
 *   ct-kv-store-params-count — the live stored params.length (starts at 0)
 */
export function KVTableControlledFixture(): JSX.Element {
  const [rows, setRows] = useState<Row[]>([ROW_ENABLED])
  const storeParamsCount = tabsStore(
    (s) => s.tabs.find((t) => t.id === s.activeTabId)?.spec.params.length ?? -1
  )
  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable rows={rows} onRowsChange={setRows} />
      <span data-testid="ct-kv-store-params-count">{storeParamsCount}</span>
      <span data-testid="ct-kv-ready" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KVTableControlledVarFixture (controlled mode + .missing highlight retention)
// ---------------------------------------------------------------------------

/**
 * Fixture: controlled mode seeded with `{{x}}` (in validVars) and `{{y}}`
 * (absent), `validVars={new Set(['x'])}`. Proves the retained `.missing` gate
 * still fires in controlled mode: `{{x}}` → `.var` only; `{{y}}` → `.var.missing`.
 *
 * data-testids:
 *   ct-kv-ready — always present
 */
export function KVTableControlledVarFixture(): JSX.Element {
  const [rows, setRows] = useState<Row[]>([ROW_VAR_X, ROW_VAR_Y])
  return (
    <div data-theme="dark" style={WRAPPER_STYLE}>
      <KVTable rows={rows} onRowsChange={setRows} validVars={new Set(['x'])} />
      <span data-testid="ct-kv-ready" />
    </div>
  )
}
