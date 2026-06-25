/**
 * TabBar — working-tabs strip organism.
 *
 * Composes the closable {@link Tabs} molecule and binds it to the
 * {@link tabsStore} zustand store. Renders the full tab strip with:
 *
 * - Per-field store selectors (no full-store subscription) for `tabs` and
 *   `activeTabId`.
 * - Stable action references pulled directly from the store (`selectActive`,
 *   `close`, `newBlank` — zustand action identities are stable across renders).
 * - Label derivation with the AC-25 precedence:
 *   1. `tab.spec.name` when non-empty.
 *   2. `tab.spec.method + ' ' + tab.spec.url` when `tab.spec.url` is non-empty.
 *   3. The literal string `'Untitled'`.
 * - A dirty marker badge (`'●'`) shown only when `tab.dirty` is true (AC-26).
 *   When the tab is clean, `badge` is left `undefined` so no badge node renders.
 * - A `+` new-tab button in the actions slot.
 *
 * ## Constraints
 *
 * - Renderer-only: no `electron` or `node:` imports (AC-10, §2.1/§2.3).
 * - No inline `style={{...}}` (AC-9, constitution §3.1).
 * - No `any` types (§3.1).
 * - Does NOT import any sibling organism (§2.3, Risk 2).
 * - Imports via the `@renderer` alias (§2.3).
 *
 * @module TabBar
 */

import './TabBar.css'

import { useMemo, type JSX } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { Tabs, type TabDescriptor } from '@renderer/components/molecules/Tabs'
import type { Tab } from '@renderer/lib/tabsStore'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Derive the display label for a tab following the AC-25 precedence:
 * 1. `spec.name` when non-empty.
 * 2. `spec.method + ' ' + spec.url` when `spec.url` is non-empty.
 * 3. The literal `'Untitled'`.
 *
 * The returned string is passed as a plain text node — CSS handles ellipsis
 * truncation; no interpolation or HTML is involved.
 *
 * @param tab - The tab whose label should be derived.
 * @returns A plain string label.
 */
function deriveLabel(tab: Tab): string {
  if (tab.spec.name !== '') {
    return tab.spec.name
  }
  if (tab.spec.url !== '') {
    return `${tab.spec.method} ${tab.spec.url}`
  }
  return 'Untitled'
}

/**
 * Map a store {@link Tab} to a {@link TabDescriptor} for the Tabs primitive.
 *
 * - `label` follows the AC-25 precedence (see {@link deriveLabel}).
 * - `badge` is set to `'●'` (dirty marker) only when `tab.dirty` is true
 *   (AC-26). When clean, `badge` is `undefined` so no badge node is rendered.
 *
 * @param tab - The source tab from the store.
 * @returns A `TabDescriptor` ready for the Tabs molecule.
 */
function toDescriptor(tab: Tab): TabDescriptor {
  return {
    id: tab.id,
    label: deriveLabel(tab),
    badge: tab.dirty ? '●' : undefined
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Working-tabs strip organism.
 *
 * Binds the closable {@link Tabs} molecule to {@link tabsStore}. Consumes the
 * store via per-field selectors to avoid unnecessary re-renders:
 *
 * ```ts
 * const tabs        = tabsStore((s) => s.tabs)
 * const activeTabId = tabsStore((s) => s.activeTabId)
 * const selectActive = tabsStore((s) => s.selectActive)
 * const close        = tabsStore((s) => s.close)
 * const newBlank     = tabsStore((s) => s.newBlank)
 * ```
 *
 * Action references (`selectActive`, `close`, `newBlank`) are stable across
 * renders — zustand guarantees this for actions defined inside `create()`.
 *
 * AC-3:  organism exists.
 * AC-9:  no inline `style={{...}}`.
 * AC-10: no electron/node imports.
 * AC-24: tab activate → `selectActive`; ✕ → `close`; + → `newBlank`.
 * AC-25: label precedence: name → method+url → 'Untitled'.
 * AC-26: dirty marker via badge slot when `tab.dirty` is true.
 */
export function TabBar(): JSX.Element {
  // Per-field selectors — each subscribes independently to avoid re-renders
  // caused by unrelated state changes (constitution §4 / store pattern).
  const tabs = tabsStore((s) => s.tabs)
  const activeTabId = tabsStore((s) => s.activeTabId)

  // Stable action references — zustand action identities never change.
  const selectActive = tabsStore((s) => s.selectActive)
  const close = tabsStore((s) => s.close)
  const newBlank = tabsStore((s) => s.newBlank)

  // Map store tabs → TabDescriptors for the Tabs primitive.
  // Memoized so a change to activeTabId alone does not force Tabs to reconcile
  // all tab buttons — the array reference stays stable unless `tabs` changed.
  const descriptors = useMemo(() => tabs.map(toDescriptor), [tabs])

  return (
    <Tabs
      aria-label="Open request tabs"
      closable
      tabs={descriptors}
      activeId={activeTabId}
      onChange={selectActive}
      onClose={close}
      className="tabbar"
      actions={
        <button type="button" className="tabbar__new" aria-label="New tab" onClick={newBlank}>
          +
        </button>
      }
    />
  )
}
