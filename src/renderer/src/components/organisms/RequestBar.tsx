/**
 * RequestBar — request submission bar organism.
 *
 * Renders a flat `[method ▾][URL input][Send][Save][Share]` row bound to the
 * active tab's RequestSpec fields via per-field tabsStore selectors.
 *
 * ## Store bindings
 *
 * - `tabs` + `activeTabId` → derive the active tab's `method`, `url`, `dirty`.
 * - `updateActiveSpec` → patches `method` or `url` on the active tab's spec.
 * - `markClean` → clears the `dirty` flag on Save.
 *
 * ## Keyboard shortcuts (global, mirrors Shell Effect 4)
 *
 * A single `document`-level `keydown` listener with empty dep array:
 * - `⌘↵` (metaKey+Enter) — Send path; same `canSend` guard; reads live state
 *   via `tabsStore.getState()` to avoid stale closures; calls `onSend` via ref.
 * - `⌘S` (metaKey+'s') — calls `e.preventDefault()` then the Save path.
 * Cleanup removes the listener on unmount.
 *
 * ## Constraints
 *
 * - Does NOT import `requestSpec` (constitution §5.2).
 * - No inline `style={{...}}` (constitution §4).
 * - No `electron` or `node:` imports (§2.1/§2.3).
 * - Imports via `@renderer` alias (§2.3).
 * - No sibling-organism import (§2.2).
 * - Strictly typed, no `any` (§3.1).
 *
 * @module RequestBar
 */

import './RequestBar.css'

import { useState, useEffect, useRef, type JSX } from 'react'
import { tabsStore } from '@renderer/lib/tabsStore'
import { METHODS, type HttpMethod } from '@renderer/lib/httpMethods'
import { Dropdown } from '@renderer/components/molecules/Dropdown'
import { Icon } from '@renderer/components/atoms/Icon'
import { cx } from '@renderer/lib/cx'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * The payload emitted by the Send action.
 *
 * Uses only primitive types — no `RequestSpec` reference (constitution §5.2).
 * Callers that need to initiate HTTP can read additional spec fields from the
 * store using `tabId`.
 */
export interface SendIntent {
  /** The id of the active tab at the time of the send. */
  tabId: string
  /** The HTTP method selected in the method dropdown. */
  method: HttpMethod
  /** The URL from the URL input field. */
  url: string
}

/**
 * Props for the {@link RequestBar} organism.
 */
export interface RequestBarProps {
  /**
   * Called when the user triggers a Send action (button click or ⌘↵/⌃↵).
   *
   * Receives only the active tab id, method, and url — no `RequestSpec`
   * reference (constitution §5.2). Defaults to a no-op when omitted, so the
   * bar renders correctly in isolation without a send handler wired.
   *
   * @param intent - `{ tabId, method, url }` for the active request.
   */
  onSend?: (intent: SendIntent) => void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Request submission bar organism.
 *
 * Binds the `[method ▾][URL input][Send][Save][Share]` row to the active tab's
 * fields via per-field {@link tabsStore} selectors. Does NOT perform HTTP;
 * the caller's `onSend` callback owns the network layer.
 *
 * AC-7:  Method selector is a controlled Dropdown with a color-coded trigger.
 * AC-8:  URL field is a controlled single-line input.
 * AC-11: URL value is bound to the active tab's spec — no remount key.
 * AC-12: `canSend` is the single predicate for enabling/disabling Send.
 * AC-13: Send click calls `onSend` when `canSend`; disabled otherwise.
 * AC-14: Save calls `markClean` when dirty; no-op when clean.
 * AC-15: Save is a no-op when the tab is already clean.
 * AC-16: ⌘↵ triggers the Send path (global, any focused element).
 * AC-17: ⌘S triggers the Save path (global, any focused element).
 * AC-18: Method change does not remount the URL input.
 * AC-19: Share button is a disabled stub.
 * AC-20: Method pill and action buttons do not reflow with URL length.
 * AC-28: Zero inline styles — all layout and color via CSS.
 *
 * @param props - See {@link RequestBarProps}.
 */
export function RequestBar({ onSend = () => {} }: RequestBarProps): JSX.Element {
  // --------------------------------------------------------------------------
  // Store reads — per-field selectors (avoid full-store subscription)
  // --------------------------------------------------------------------------

  /** Id of the currently active tab. */
  const activeTabId = tabsStore((s) => s.activeTabId)

  /**
   * Active tab's HTTP method — per-field primitive selector.
   * Re-renders only when the active tab's method actually changes;
   * background-tab mutations produce identical primitive values and are skipped.
   */
  const method = tabsStore(
    (s): HttpMethod => s.tabs.find((t) => t.id === s.activeTabId)?.spec.method ?? 'GET'
  )

  /**
   * Active tab's URL — per-field primitive selector.
   * Re-renders only when the active tab's url actually changes.
   */
  const url = tabsStore((s): string => s.tabs.find((t) => t.id === s.activeTabId)?.spec.url ?? '')

  /**
   * Active tab's dirty flag — per-field primitive selector.
   * Re-renders only when the active tab's dirty flag actually changes.
   */
  const dirty = tabsStore(
    (s): boolean => s.tabs.find((t) => t.id === s.activeTabId)?.dirty ?? false
  )

  /**
   * Shallow-merges a partial spec patch into the active tab's spec.
   * Stable action reference — zustand guarantees identity across renders.
   */
  const updateActiveSpec = tabsStore((s) => s.updateActiveSpec)

  /**
   * Clears the dirty flag on a tab identified by id.
   * Stable action reference.
   */
  const markClean = tabsStore((s) => s.markClean)

  // --------------------------------------------------------------------------
  // Local state
  // --------------------------------------------------------------------------

  /** Controlled open state for the method Dropdown. */
  const [methodOpen, setMethodOpen] = useState(false)

  // --------------------------------------------------------------------------
  // Ref — keeps onSend current inside the keydown handler without listing it
  // in the effect dep array. Updated synchronously on every render so the
  // handler always calls the latest callback regardless of caller memoization.
  // --------------------------------------------------------------------------

  /** Always points to the current `onSend` prop — updated on every render. */
  const onSendRef = useRef(onSend)
  useEffect(() => {
    onSendRef.current = onSend
  })

  // --------------------------------------------------------------------------
  // Derived predicate — single source of truth used by button, click, ⌘↵
  // --------------------------------------------------------------------------

  /** True when the URL field contains at least one non-whitespace character. */
  const canSend = url.trim() !== ''

  // --------------------------------------------------------------------------
  // Handlers for button interactions (read reactive store state via closure)
  // --------------------------------------------------------------------------

  /** Invoke onSend with the active tab's current values — guarded by canSend. */
  function handleSend(): void {
    if (canSend) {
      onSend({ tabId: activeTabId, method, url })
    }
  }

  /** Clear the dirty flag on the active tab — no-op when already clean. */
  function handleSave(): void {
    if (dirty) {
      markClean(activeTabId)
    }
  }

  // --------------------------------------------------------------------------
  // Effect — global keyboard shortcuts (mirrors Shell Effect 4)
  //
  // Registers a single `document` keydown listener.
  // - ⌘↵: Send path — reads live state via getState() (not reactive selectors)
  //   so store reads inside the handler are always current. `onSend` is called
  //   via `onSendRef` (kept current by the sync ref effect above) so the handler
  //   never captures a stale callback.
  // - ⌘S: Save path — calls e.preventDefault() then markClean via getState().
  //
  // Dep array is [] — registers once on mount, removed on unmount.
  // `onSendRef.current` is always up to date, so no re-registration is needed
  // when the caller changes the callback identity.
  // Acts on the active tab regardless of which element currently has focus
  // (document-level listener, not tied to a specific focused element).
  // --------------------------------------------------------------------------

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent): void {
      if (e.metaKey || e.ctrlKey) {
        if (e.key === 'Enter') {
          // ⌘↵ → Send path; read live state via getState() to avoid stale closures
          const state = tabsStore.getState()
          const liveTab = state.tabs.find((t) => t.id === state.activeTabId)
          const liveUrl = liveTab?.spec.url ?? ''
          const liveMethod: HttpMethod = liveTab?.spec.method ?? 'GET'
          if (liveUrl.trim() !== '') {
            onSendRef.current({ tabId: state.activeTabId, method: liveMethod, url: liveUrl })
          }
        } else if (e.key === 's') {
          // ⌘S → Save path
          e.preventDefault()
          const state = tabsStore.getState()
          const liveTab = state.tabs.find((t) => t.id === state.activeTabId)
          if (liveTab?.dirty === true) {
            state.markClean(state.activeTabId)
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  // --------------------------------------------------------------------------
  // Method dropdown items — one entry per method in METHODS display order
  // --------------------------------------------------------------------------

  const methodItems = METHODS.map((m) => ({
    id: m,
    label: m,
    onSelect: (): void => {
      updateActiveSpec({ method: m })
    }
  }))

  // --------------------------------------------------------------------------
  // Render
  // --------------------------------------------------------------------------

  return (
    <div className="request-bar">
      {/* ---- Method selector ---- */}
      {/*
       * Controlled Dropdown; trigger is a <button> with the method color classes.
       * className={cx('method', method)} applies tokens.css method-color styles
       * (e.g. GET → --m-get, resolved by [data-mstyle] written by Shell).
       * The accessible name of the trigger is the visible method text — no
       * redundant aria-label (AC-7).
       */}
      <Dropdown
        open={methodOpen}
        onOpenChange={setMethodOpen}
        trigger={
          <button type="button" className={cx('request-bar__method', 'method', method)}>
            {method}
            <Icon name="chevronDown" size={10} />
          </button>
        }
        items={methodItems}
        align="start"
      />

      {/* ---- URL input ---- */}
      {/*
       * Controlled single-line input bound to the active tab's url.
       * No `key` prop — the input is never remounted on method change (AC-11, AC-18).
       * overflow-x scrolling on content wider than the input is native browser
       * behaviour for type="text" — no CSS or JS needed.
       */}
      <input
        type="text"
        className="request-bar__url"
        value={url}
        onChange={(e) => updateActiveSpec({ url: e.target.value })}
        placeholder="Enter URL"
        aria-label="Request URL"
      />

      {/* ---- Action buttons ---- */}
      <div className="request-bar__actions">
        {/* Send — disabled when !canSend (AC-12, AC-13) */}
        {/*
         * The <kbd> keycap is aria-hidden so it is purely decorative — the
         * Send button's accessible name remains exactly "Send" (AC-9, AC-10).
         * It is only mounted when canSend is true, so it is absent from the
         * DOM when the URL field is empty or whitespace-only.
         */}
        <button
          type="button"
          className="request-bar__send"
          disabled={!canSend}
          aria-disabled={!canSend}
          onClick={handleSend}
        >
          <Icon name="send" size={13} />
          Send
          {canSend && (
            <kbd aria-hidden="true" className="request-bar__kbd">
              ⌘↵
            </kbd>
          )}
        </button>

        {/* Save — calls markClean when dirty, no-op when clean (AC-14, AC-15) */}
        {/*
         * Visible text "Save" supplies the accessible name — aria-label is not
         * needed and has been removed to avoid the redundancy (AC-11).
         */}
        <button
          type="button"
          className={cx('request-bar__save', dirty ? 'request-bar__save--dirty' : undefined)}
          onClick={handleSave}
        >
          <Icon name="save" size={13} />
          Save
        </button>

        {/* Share — disabled stub, rendered in its final slot (AC-19) */}
        {/*
         * Visible text "Share" supplies the accessible name — aria-label is not
         * needed and has been removed to avoid the redundancy (AC-11).
         * Remains disabled (009 AC-19 stub — still a no-op).
         */}
        <button type="button" className="request-bar__share" disabled aria-disabled="true">
          <Icon name="share" size={13} />
          Share
        </button>
      </div>
    </div>
  )
}
