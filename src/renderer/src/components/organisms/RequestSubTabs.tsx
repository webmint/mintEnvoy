/**
 * RequestSubTabs — the per-request sub-tab switcher organism.
 *
 * Composes the `Tabs` molecule for a fixed 6-sub-tab strip (Params, Auth, Headers,
 * Body, Tests, Code) and owns 6 always-mounted tabpanels toggled via the `hidden`
 * attribute (D6). Panel state (panel scrollTop, input focus/value) survives sub-tab
 * switches because nothing is ever unmounted. scrollTop is captured
 * synchronously at switch time (outgoing panel read before the state update
 * hides it) and also via an onScroll handler; both feed the useLayoutEffect
 * restore on re-show (AC-9).
 *
 * Params and Headers panels arrive as named slot props from the App composition
 * root and are never imported directly here — §2.2 (organism may not import a
 * sibling organism). The remaining 4 tabs share one muted empty-state element
 * until those panels are built (AC-12, D7).
 *
 * Badge derivation is read-only — this component never calls `updateActiveSpec`
 * (AC-24). Badges update reactively via three independent scalar selectors
 * (paramsLength, headersLength, authType) that return primitives — Zustand
 * compares by value so a value-cell keystroke that leaves row counts and auth
 * type unchanged triggers no re-render (AC-26, Finding 1 perf fix).
 *
 * ## Defensive reads (D9)
 * - `activeSubTab` is normalized: `VALID_KEYS.includes(v) ? v : 'params'` (AC-16).
 * - When `activeTabId` resolves to no tab, a neutral empty region is rendered
 *   without throwing (AC-17).
 *
 * ## Constraints
 * - No `electron` or `node:` imports (AC-23).
 * - No `updateActiveSpec` call (AC-24).
 * - No `AuthPanel`, `BodyEditor`, `TestsPanel`, or `CodePanel` import (AC-25).
 * - No sibling organism import (§2.2).
 * - No inline `style={{...}}` (AC-22) — all styling via `RequestSubTabs.css`.
 * - No `any` types (§3.1).
 *
 * @module RequestSubTabs
 */

import './RequestSubTabs.css'

import { useLayoutEffect, useEffect, useRef, useMemo, type ReactNode, type JSX } from 'react'
import { tabsStore, VALID_KEYS } from '@renderer/lib/tabsStore'
import type { SubTabKey } from '@renderer/lib/tabsStore'
import { Tabs } from '@renderer/components/molecules/Tabs'
import type { TabDescriptor } from '@renderer/components/molecules/Tabs'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Human-readable label for each sub-tab key. */
const SUB_TAB_LABELS: Record<SubTabKey, string> = {
  params: 'Params',
  auth: 'Auth',
  headers: 'Headers',
  body: 'Body',
  tests: 'Tests',
  code: 'Code'
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Per-request sub-tab switcher organism.
 *
 * Renders a 6-tab strip via the `Tabs` molecule and owns 6 always-mounted,
 * `hidden`-toggled tabpanels. Params and Headers content arrives as slot props;
 * the other 4 show a shared muted empty-state placeholder (AC-12).
 *
 * @param props.params   - Optional slot content for the Params tabpanel.
 * @param props.headers  - Optional slot content for the Headers tabpanel.
 */
export function RequestSubTabs({
  params,
  headers
}: {
  /** Optional slot content for the Params tabpanel. */
  params?: ReactNode
  /** Optional slot content for the Headers tabpanel. */
  headers?: ReactNode
}): JSX.Element {
  // Per-field store selectors — each subscribes independently (constitution §4).
  const activeTabId = tabsStore((s) => s.activeTabId)

  // activeSubTab — normalized at read time (D9, AC-16).
  // rawSubTab is `SubTabKey | undefined`; guards against absent tab (no active tab).
  const rawSubTab = tabsStore((s) => {
    const tab = s.tabs.find((t) => t.id === s.activeTabId)
    return tab?.activeSubTab
  })
  const activeSubTab: SubTabKey =
    rawSubTab !== undefined && VALID_KEYS.includes(rawSubTab) ? rawSubTab : 'params'

  // Badge-relevant scalar selectors — subscribe independently and return primitives
  // so Zustand compares by value. A value-cell keystroke that leaves row count +
  // auth type unchanged produces NO re-render (Finding 1 perf fix, constitution §4).
  const paramsLength = tabsStore(
    (s) => s.tabs.find((t) => t.id === s.activeTabId)?.spec.params.length
  )
  const headersLength = tabsStore(
    (s) => s.tabs.find((t) => t.id === s.activeTabId)?.spec.headers.length
  )
  const authType = tabsStore((s) => s.tabs.find((t) => t.id === s.activeTabId)?.spec.auth.type)

  // AC-17: explicit active-tab guard — true when activeTabId references an open tab.
  const hasActiveTab = tabsStore((s) => s.tabs.some((t) => t.id === s.activeTabId))

  // Stable action reference — zustand action identities never change across renders.
  const setActiveSubTab = tabsStore((s) => s.setActiveSubTab)

  // Badge derivation — recomputes only when badge-relevant scalar values change (AC-26, AC-15).
  // Values read inside the memo are exactly the three scalars above; no spec ref captured.
  const badges = useMemo((): Partial<Record<SubTabKey, string | number>> => {
    const result: Partial<Record<SubTabKey, string | number>> = {}
    // params: row count, omitted when 0, clamped to '99+' above 99 (AC-15).
    if (paramsLength !== undefined && paramsLength > 0) {
      result.params = paramsLength > 99 ? '99+' : paramsLength
    }
    // headers: same rules as params.
    if (headersLength !== undefined && headersLength > 0) {
      result.headers = headersLength > 99 ? '99+' : headersLength
    }
    // auth: bullet '•' (U+2022) when auth.type !== 'none'; omitted otherwise.
    if (authType !== undefined && authType !== 'none') {
      result.auth = '•'
    }
    // body, tests, code — never badged (D3).
    return result
  }, [paramsLength, headersLength, authType])

  // Tab descriptors — stable reference unless badges change (D1, AC-13).
  const descriptors = useMemo((): TabDescriptor[] => {
    return VALID_KEYS.map((key) => ({
      id: key,
      label: SUB_TAB_LABELS[key],
      badge: badges[key]
    }))
  }, [badges])

  // D6 — focus and scroll preservation across hidden-attribute toggles (R6, AC-9).
  //
  // When a panel is hidden (`display:none`), the browser blurs any focused element
  // within it AND discards its scrollTop (reads as 0 while hidden; Chromium does
  // not restore scrollTop on un-hide). To preserve both on re-show:
  //   1. `onFocus` (bubbling) on each panel div records the last focused element.
  //   2. `handleSubTabChange` captures the OUTGOING panel's `scrollTop`
  //      synchronously the instant a switch is requested — while that panel is
  //      still visible — making scroll capture race-free. Reading a hidden
  //      panel's scrollTop always returns 0 (D6). `onScroll` backs this up for
  //      external `setActiveSubTab` calls and keeps the map fresh during
  //      continuous scrolling.
  //   3. `useLayoutEffect` on `activeSubTab` change:
  //      a. Restores the newly-shown panel's scrollTop from `scrollTops` (AC-9),
  //         synchronously before the browser paints — no flash at scrollTop 0.
  //      b. Refocuses the last-focused element in the newly-shown panel (D6/R6),
  //         synchronously before the browser paints.
  //
  // Both maps are scoped to the CURRENT REQUEST TAB: a `useEffect` on `activeTabId`
  // clears them whenever the active request tab switches, preventing scroll/focus
  // state from one request tab from leaking onto another (cross-request-tab leak fix).
  // Within-tab sub-tab-switch preservation (AC-9) is unaffected — the maps only
  // clear on request-tab change, not on sub-tab change.
  //
  // Mirrors the focus-restore pattern in Tabs.tsx lines 428-436, adapted for
  // a panel-keyed rather than buttonRef-keyed target.
  const lastFocusedInPanel = useRef<Map<SubTabKey, Element>>(new Map())
  const scrollTops = useRef<Map<SubTabKey, number>>(new Map())
  const panelRefs = useRef<Map<SubTabKey, HTMLDivElement>>(new Map())

  // Clear scroll and focus maps when the active REQUEST tab changes — prevents
  // SubTabKey-keyed state from tab A leaking onto tab B (D6, cross-request-tab leak fix).
  // Also resets every panel's DOM scrollTop to 0: when two request tabs share the same
  // activeSubTab (e.g. both on 'params'), the shared panel div is never toggled hidden,
  // so the browser physically retains tab A's scrollTop in the DOM. Clearing the maps
  // alone is not enough — the DOM node must also be reset. panelRefs is a ref (always
  // current), so it is safe to read here without adding it as a dep.
  useEffect(() => {
    scrollTops.current.clear()
    lastFocusedInPanel.current.clear()
    panelRefs.current.forEach((panel) => {
      panel.scrollTop = 0
    })
  }, [activeTabId])

  /**
   * Wraps `setActiveSubTab` to capture the OUTGOING panel's scrollTop
   * synchronously before the state update hides it. A hidden panel's
   * scrollTop always reads as 0, so capture must happen while the panel is
   * still visible (D6, AC-9). The `onScroll` handler remains as a secondary
   * source for external `setActiveSubTab` writes and during continuous scrolling.
   *
   * Receives the raw `onChange` string from `Tabs` and casts to `SubTabKey`
   * at the Tabs boundary (the only `as SubTabKey` cast in this component).
   */
  const handleSubTabChange = (k: string): void => {
    // Capture the currently-active (outgoing) panel's scroll position
    // synchronously, before setActiveSubTab hides it.
    const outgoing = panelRefs.current.get(activeSubTab)
    if (outgoing !== undefined) {
      scrollTops.current.set(activeSubTab, outgoing.scrollTop)
    }
    setActiveSubTab(activeTabId, k as SubTabKey)
  }

  useLayoutEffect(() => {
    const panel = panelRefs.current.get(activeSubTab)

    // Restore scroll position (AC-9) — unconditional; runs even when no element
    // was previously focused. Setting scrollTop before focus means the refocused
    // element is already in the correct scroll position when focus fires.
    if (panel !== undefined) {
      const savedScrollTop = scrollTops.current.get(activeSubTab)
      if (savedScrollTop !== undefined) {
        panel.scrollTop = savedScrollTop
      }
    }

    // Restore focus (D6, R6).
    const savedEl = lastFocusedInPanel.current.get(activeSubTab)
    if (!(savedEl instanceof HTMLElement)) return

    if (panel === undefined || !panel.contains(savedEl)) return

    // Guard: do not steal focus if the element is already focused.
    if (document.activeElement === savedEl) return

    // preventScroll: a bare focus() would scroll the panel to bring the element
    // into view, overriding the scrollTop restored above and defeating AC-9.
    savedEl.focus({ preventScroll: true })
  }, [activeSubTab])

  // AC-17: No-active-tab guard — render a neutral empty region when activeTabId
  // resolves to no tab (e.g. during a transient store state or a future restore).
  if (!hasActiveTab) {
    return <div className="request-sub-tabs request-sub-tabs--no-active" />
  }

  // ONE shared muted empty-state for unbuilt panels and absent slot props (AC-12, D7).
  const emptyState = <p className="request-sub-tabs__empty">Panel not yet available</p>

  return (
    <div className="request-sub-tabs">
      {/* 6-sub-tab strip: closable=false (selection-only), linkPanels emits
          id="tab-<key>" + aria-controls="panel-<key>" on each button (D8, AC-5, AC-6, D10). */}
      <Tabs
        closable={false}
        linkPanels
        activeId={activeSubTab}
        onChange={handleSubTabChange}
        className="pane-tabs"
        tabs={descriptors}
        aria-label="Request sub-tabs"
      />

      {/* 6 always-mounted tabpanels toggled by the hidden attribute (D6, AC-9).
          Each panel is linked back to its tab via aria-labelledby (D8, AC-14). */}
      {VALID_KEYS.map((key) => {
        let content: ReactNode
        if (key === 'params') {
          content = params ?? emptyState
        } else if (key === 'headers') {
          content = headers ?? emptyState
        } else {
          content = emptyState
        }

        return (
          <div
            key={key}
            role="tabpanel"
            id={`panel-${key}`}
            aria-labelledby={`tab-${key}`}
            aria-selected={key === activeSubTab}
            hidden={key !== activeSubTab}
            className="request-sub-tabs__panel"
            ref={(el) => {
              if (el !== null) {
                panelRefs.current.set(key, el)
              } else {
                panelRefs.current.delete(key)
              }
            }}
            onFocus={(e) => {
              // Bubble-phase capture: record the last focused descendant of this panel.
              if (e.target instanceof Element) {
                lastFocusedInPanel.current.set(key, e.target)
              }
            }}
            onScroll={(e) => {
              // Continuously record the panel's live scrollTop so it can be
              // restored when the panel is re-shown (AC-9). Reading scrollTop
              // after the panel is hidden always returns 0, so we must capture
              // it while the panel is still visible.
              scrollTops.current.set(key, e.currentTarget.scrollTop)
            }}
          >
            {content}
          </div>
        )
      })}
    </div>
  )
}
