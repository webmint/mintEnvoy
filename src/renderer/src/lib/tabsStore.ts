/**
 * tabsStore.ts
 *
 * Module-level zustand store for managing the working-tabs lifecycle state machine.
 *
 * This module:
 *   - has NO node / electron imports (renderer-only, constitution §2.1/§2.3, AC-10)
 *   - exports a single module-level store instance (avoid per-consumer instantiation)
 *   - mutates state only via store actions (constitution §4)
 *   - uses `crypto.randomUUID()` (browser global — NOT node:crypto, §2.1)
 *   - imports domain types from requestSpec.ts via the @renderer alias (§2.3)
 *
 * Usage:
 *   // Reactive (inside a React component):
 *   const tabs = tabsStore(state => state.tabs)
 *
 *   // Imperative (from any module):
 *   tabsStore.getState().newBlank()
 */
import { create } from 'zustand'
import { RequestSpec, makeBlankRequest } from '@renderer/lib/requestSpec'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A single open tab pairing a RequestSpec with tab-local state.
 * `id` is a per-tab surrogate key — NOT the collection identity.
 */
export interface Tab {
  /** Unique tab identifier generated via `crypto.randomUUID()`. */
  id: string
  /**
   * Source collection-request identity when the tab was opened from a
   * collection; `null` for new blank tabs (AC-13 dedupe key, not `id`).
   */
  collectionRequestId: string | null
  /** The request this tab currently holds. */
  spec: RequestSpec
  /** True when the tab has unsaved edits not yet persisted/synced. */
  dirty: boolean
}

/**
 * Input shape accepted by `openFromCollection`.
 * The slice does NOT derive the collection identity — it stores the one supplied
 * by the caller (the collection-list trigger site is out of scope for this slice).
 */
export interface OpenFromCollectionInput {
  /** Stable identity of the collection request being opened (matched by dedupe leg 1). */
  collectionRequestId: string
  /** The request payload to seed the new (or matched) tab with. */
  spec: RequestSpec
}

/**
 * Complete state shape for the tabs store.
 *
 * `tabs` array order IS tab-strip order; `activeTabId` always references
 * a tab present in `tabs` (never-zero + active-validity invariants).
 */
export interface TabsState {
  /** Ordered list of open tabs; array index === visual position. */
  tabs: Tab[]
  /** Id of the currently selected tab; always present in `tabs`. */
  activeTabId: string

  /**
   * Open a request from the collection, deduplicating against open tabs:
   *   - Leg 1: existing tab with matching `collectionRequestId` → activate it.
   *   - Leg 2: existing tab with identical non-empty `url` → activate it.
   *   - Miss: append a new tab carrying the supplied spec and activate it.
   * @param input - The collection request identity + spec to open.
   */
  openFromCollection: (input: OpenFromCollectionInput) => void

  /**
   * Append a new blank tab (wrapping `makeBlankRequest()`) and activate it.
   */
  newBlank: () => void

  /**
   * Close the tab identified by `tabId`.
   * - If closing the LAST tab, a fresh seeded blank is spawned first (never-zero).
   * - If closing the ACTIVE tab, the right neighbor is activated (or left when last).
   * - If closing a NON-active tab, `activeTabId` is left unchanged.
   * - Dirty tabs close silently (no confirmation).
   * - Unknown id is a no-op.
   * @param tabId - The id of the tab to close.
   */
  close: (tabId: string) => void

  /**
   * Set the active tab to `tabId`.
   * No-op when `tabId` does not reference an open tab.
   * @param tabId - The id of the tab to activate.
   */
  selectActive: (tabId: string) => void

  /**
   * Clear the dirty flag on the tab identified by `tabId`.
   * All other tabs remain unchanged. No-op on unknown id.
   * @param tabId - The id of the tab to mark clean.
   */
  markClean: (tabId: string) => void
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/**
 * Build a fresh Tab wrapping `makeBlankRequest()` with no collection binding.
 * Every call generates a new UUID so two blank tabs never share an id.
 *
 * @returns A new blank Tab with `dirty: false` and `collectionRequestId: null`.
 */
function makeBlankTab(): Tab {
  return {
    id: crypto.randomUUID(),
    collectionRequestId: null,
    spec: makeBlankRequest(),
    dirty: false
  }
}

/**
 * Build a new Tab from a collection-open input.
 *
 * @param input - The collection request identity + spec.
 * @returns A Tab carrying the supplied spec and collection identity, `dirty: false`.
 */
function makeCollectionTab(input: OpenFromCollectionInput): Tab {
  return {
    id: crypto.randomUUID(),
    collectionRequestId: input.collectionRequestId,
    spec: input.spec,
    dirty: false
  }
}

/**
 * Two-leg dedupe: find an existing tab that matches the collection input.
 *
 * Leg 1 — collection-request id match (both non-null):
 *   `tab.collectionRequestId === input.collectionRequestId`
 *
 * Leg 2 — verbatim non-empty URL match (fall-through when leg 1 misses):
 *   `tab.spec.url === input.spec.url && input.spec.url !== ''`
 *
 * An empty URL never satisfies leg 2, so blank tabs always stay distinct (AC-15).
 *
 * @param tabs  - The current open tabs.
 * @param input - The incoming collection-open payload.
 * @returns The matched tab's id, or `undefined` on a miss.
 */
function findDedupeMatch(tabs: Tab[], input: OpenFromCollectionInput): string | undefined {
  // Leg 1: id match
  const byId = tabs.find((t) => t.collectionRequestId === input.collectionRequestId)
  if (byId !== undefined) return byId.id

  // Leg 2: non-empty URL match
  if (input.spec.url !== '') {
    const byUrl = tabs.find((t) => t.spec.url === input.spec.url)
    if (byUrl !== undefined) return byUrl.id
  }

  return undefined
}

/**
 * Determine the next active tab id after the tab at `closedIndex` is removed.
 * Prefers the right neighbor; falls back to the left when closing the last slot.
 *
 * Exported so callers that maintain their own tab-like arrays (e.g. demo
 * fixtures, stories) can share the canonical neighbor-selection logic instead
 * of open-coding it.
 *
 * @param tabs        - The tabs array BEFORE removal; elements only need an `id` field.
 * @param closedIndex - Index of the tab being closed.
 * @returns The id of the tab that should become active.
 */
export function selectNeighborId(tabs: readonly { id: string }[], closedIndex: number): string {
  const isLast = closedIndex === tabs.length - 1
  const neighborIndex = isLast ? closedIndex - 1 : closedIndex + 1
  return tabs[neighborIndex].id
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

/** Seeded initial blank tab (constructed once at module load). */
const initialTab = makeBlankTab()

/**
 * The single, module-level zustand store for the working-tabs state machine.
 *
 * Initial state: one seeded blank tab is always present so the store never
 * starts in an empty state (never-zero invariant from construction, AC-17).
 *
 * Consumers should prefer selectors over reading the full store:
 *   const tabs = tabsStore(state => state.tabs)
 *
 * Named `tabsStore` per project naming convention (Store suffix, §3.3).
 */
export const tabsStore = create<TabsState>((set, get) => ({
  tabs: [initialTab],
  activeTabId: initialTab.id,

  openFromCollection(input) {
    const { tabs } = get()
    const matchedId = findDedupeMatch(tabs, input)

    if (matchedId !== undefined) {
      // Leg 1 or leg 2 hit — activate the existing tab, append nothing (AC-13, AC-14)
      set({ activeTabId: matchedId })
      return
    }

    // Miss — append a new tab and activate it
    const newTab = makeCollectionTab(input)
    set((state) => ({ tabs: [...state.tabs, newTab], activeTabId: newTab.id }))
  },

  newBlank() {
    const newTab = makeBlankTab()
    set((state) => ({ tabs: [...state.tabs, newTab], activeTabId: newTab.id }))
  },

  close(tabId) {
    const { tabs, activeTabId } = get()
    const closedIndex = tabs.findIndex((t) => t.id === tabId)

    // Unknown id → no-op (defensive)
    if (closedIndex === -1) return

    const isOnlyTab = tabs.length === 1
    const isActiveTab = tabId === activeTabId

    if (isOnlyTab) {
      // Never-zero: spawn a fresh blank before removing the last tab (AC-17)
      const replacement = makeBlankTab()
      set({ tabs: [replacement], activeTabId: replacement.id })
      return
    }

    // Determine next activeTabId BEFORE filtering (indices still valid)
    const nextActiveId = isActiveTab
      ? selectNeighborId(tabs, closedIndex) // active-tab closed → pick neighbor (AC-18)
      : activeTabId // non-active closed → leave activeTabId unchanged (invariant)

    const nextTabs = tabs.filter((t) => t.id !== tabId)
    set({ tabs: nextTabs, activeTabId: nextActiveId })
  },

  selectActive(tabId) {
    const { tabs } = get()
    const exists = tabs.some((t) => t.id === tabId)
    if (!exists) return // no-op on unknown id (AC-21)
    set({ activeTabId: tabId })
  },

  markClean(tabId) {
    const { tabs } = get()
    const exists = tabs.some((t) => t.id === tabId)
    if (!exists) return // no-op on unknown id (AC-20)
    set((state) => ({
      tabs: state.tabs.map((t) => (t.id === tabId ? { ...t, dirty: false } : t))
    }))
  }
}))
