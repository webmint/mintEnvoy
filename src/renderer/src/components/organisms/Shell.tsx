/**
 * Shell — root composition layer for the app shell.
 *
 * Composes the full application chrome from its constituent organisms:
 * `Titlebar` on top, a main row of `Sidebar` + workspace area in the middle,
 * and `Statusbar` at the bottom. The workspace area hosts the `tabs` slot
 * (a tab-strip region above the panes) and `PaneSplit` (the request/response
 * split workspace).
 *
 * ## Named slots
 *
 * Shell accepts four named slots as props and renders each into its designated
 * mount point without inspecting the slot's contents:
 *
 * - `sidebar` — rendered inside `<Sidebar>` as its `children`.
 * - `tabs` — rendered above `<PaneSplit>` in the workspace column.
 * - `panes.request` / `panes.response` — forwarded to `<PaneSplit>`.
 * - `modals` — rendered at the Shell root level as a portal-less mount point;
 *   modal behavior (overlay, focus-trap, backdrop) is each modal's own concern.
 *
 * ## store→<html> effect
 *
 * A single `useEffect` keyed on `theme`, `accent`, and `mstyle` writes those
 * values into `document.documentElement.dataset`. This is the ONLY writer for
 * these attributes; callers must not set them directly.
 *
 * ## CSS-var effect
 *
 * A second `useEffect` keyed on `sidebarWidth` and `paneRatio` writes:
 * - `--sidebar-width: ${sidebarWidth}px` (with `px` unit, matching Divider output)
 * - `--pane-ratio: ${paneRatio}` (unitless, matching Divider output)
 *
 * Both are written onto `document.documentElement` so the Sidebar and PaneSplit
 * CSS custom properties resolve from the same element the Divider writes to
 * during live drag.
 *
 * ## Window-resize re-clamp effect (AC-17)
 *
 * A third `useEffect` registers a `window` `resize` listener. On each resize
 * event the handler reads the current raw values imperatively via
 * `settingsStore.getState()` (not through reactive selectors — the listener is
 * registered once) and commits clamped values back through `setSidebarWidth`
 * and `setPaneRatio`. This is the renderer-side guarantee that no pane goes
 * negative or overflows after the OS window is resized.
 *
 * ## Global Cmd-B / Ctrl-B toggle (AC-5)
 *
 * A fourth `useEffect` registers a `document`-level `keydown` listener.
 * When `(e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b'` is true,
 * it calls `e.preventDefault()` then `toggleSidebar()` imperatively. The
 * listener is registered on `document` (not a focusable element) so it fires
 * regardless of which element currently has focus.
 *
 * ## Focus-return on collapse (AC-5 / grill F3)
 *
 * A fifth `useEffect` detects the `sidebarCollapsed` false→true edge. When
 * the sidebar collapses (and its DOM subtree unmounts), focus would otherwise
 * fall to `<body>`. The effect moves focus to the Titlebar sidebar-toggle via
 * the `toggleRef` passed to `<Titlebar>`. A `prevCollapsedRef` holds the
 * previous value across renders so the effect fires only on the expand→collapse
 * direction; it does NOT steal focus on mount or on the collapse→expand edge.
 *
 * ## Constraints
 *
 * - No inline `style={{...}}` JSX attributes — all sizing via CSS custom
 *   properties and BEM class rules (constitution §3.1 / AC-14).
 * - No `electron` or `node:` imports — renderer-only (§2.1 / §2.3).
 * - Imports via `@renderer` alias (§2.3).
 *
 * @module Shell
 */

import './Shell.css'

import { useEffect, useRef, type ReactNode, type JSX } from 'react'
import { cx } from '@renderer/lib/cx'
import { settingsStore } from '@renderer/lib/settingsStore'
import { Titlebar } from '@renderer/components/organisms/Titlebar'
import { Sidebar } from '@renderer/components/organisms/Sidebar'
import { PaneSplit } from '@renderer/components/organisms/PaneSplit'
import { Statusbar } from '@renderer/components/organisms/Statusbar'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Named pane slot contents forwarded to {@link PaneSplit}.
 */
export interface ShellPanes {
  /**
   * Content for the top (request) pane.
   * Forwarded to `PaneSplit` without inspection.
   */
  request?: ReactNode

  /**
   * Content for the bottom (response) pane.
   * Forwarded to `PaneSplit` without inspection.
   */
  response?: ReactNode
}

/**
 * Props for the {@link Shell} component.
 *
 * All slot props are optional — absent slots render nothing in their mount
 * point. Shell never inspects the contents of any slot.
 */
export interface ShellProps {
  /**
   * Content for the sidebar slot.
   * Rendered inside `<Sidebar>` as its `children`.
   * When the sidebar is collapsed by the store, `Sidebar` unmounts this subtree.
   */
  sidebar?: ReactNode

  /**
   * Content for the tab-strip region above the pane split.
   * Rendered as the first child of the workspace column.
   */
  tabs?: ReactNode

  /**
   * Content for the request and response panes.
   * Forwarded to `<PaneSplit request={...} response={...} />`.
   */
  panes?: ShellPanes

  /**
   * Portal-less mount point for modals and overlays.
   * Rendered at the Shell root level so modals can escape the grid stacking
   * context. Each modal is responsible for its own overlay, focus-trap, and
   * backdrop behavior.
   */
  modals?: ReactNode

  /** Additional CSS class applied to the outermost shell element. */
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Root composition layer for the application shell.
 *
 * Reads `theme`, `accent`, `mstyle`, `sidebarWidth`, `paneRatio`, and
 * `sidebarCollapsed` from the settings store via per-field selectors.
 * Maintains five imperative effects:
 *
 * 1. `theme`/`accent`/`mstyle` → `document.documentElement.dataset.*`
 * 2. `sidebarWidth`/`paneRatio` → CSS custom properties on `document.documentElement`
 * 3. `window` `resize` → re-clamps sidebar width and pane ratio via store
 *    actions (AC-17: no pane goes negative/overflows after OS-window resize).
 * 4. `document` `keydown` Cmd-B/Ctrl-B → `toggleSidebar()` (AC-5: global
 *    keyboard shortcut fires regardless of focused element).
 * 5. `sidebarCollapsed` false→true edge → `toggleRef.current?.focus()` so
 *    focus returns to the Titlebar toggle button on collapse (AC-5 / grill F3).
 *
 * @param props - See {@link ShellProps}.
 *
 * AC-2: Shell module present.
 * AC-3: No reference cruft (data-om-*, __OmT, tweaks-panel).
 * AC-5: Cmd-B toggles sidebar regardless of focus; focus returns to toggle on collapse.
 * AC-6: store→html data-attrs + CSS vars reflect for the session.
 * AC-7: Named slots render arbitrary children.
 * AC-10: data-accent set (visually inert this release — no [data-accent] CSS yet).
 * AC-11: JSDoc on component + slot prop types.
 * AC-14: No inline styles.
 * AC-15: No electron/node imports.
 * AC-17: Window resize re-clamps pane values so no pane overflows.
 */
export function Shell({ sidebar, tabs, panes, modals, className }: ShellProps): JSX.Element {
  // -------------------------------------------------------------------------
  // Store reads — per-field selectors to avoid full-store re-renders
  // -------------------------------------------------------------------------

  /** Current colour-scheme preference. Per-field selector. */
  const theme = settingsStore((s) => s.theme)

  /**
   * Active accent-colour identifier.
   * Visually inert this release — persisted and applied to data-accent but no
   * [data-accent] CSS selectors exist yet (AC-10).
   */
  const accent = settingsStore((s) => s.accent)

  /** Active method-style marker variant. Per-field selector. */
  const mstyle = settingsStore((s) => s.mstyle)

  /** Current sidebar width in pixels. Per-field selector. */
  const sidebarWidth = settingsStore((s) => s.sidebarWidth)

  /** Current left-pane ratio (fraction). Per-field selector. */
  const paneRatio = settingsStore((s) => s.paneRatio)

  /**
   * Whether the sidebar is currently collapsed.
   * Reactive selector — used to detect the false→true collapse edge for
   * focus-return (Effect 5).
   */
  const sidebarCollapsed = settingsStore((s) => s.sidebarCollapsed)

  // -------------------------------------------------------------------------
  // Refs
  // -------------------------------------------------------------------------

  /**
   * Ref forwarded to the sidebar-toggle `<button>` inside Titlebar.
   * Used by Effect 5 (focus-return on collapse) to move focus back to the
   * toggle button when the sidebar collapses via keyboard (AC-5).
   */
  const toggleRef = useRef<HTMLButtonElement>(null)

  /**
   * Tracks the previous `sidebarCollapsed` value across renders.
   * Used in Effect 5 to detect the false→true edge without re-registering
   * the listener on every collapse state change.
   */
  const prevCollapsedRef = useRef<boolean>(sidebarCollapsed)

  // -------------------------------------------------------------------------
  // Effect 1 — store→<html> data attribute effect
  //
  // Writes theme, accent, and mstyle into document.documentElement.dataset.
  // This is the sole writer for these data attributes; they are overwritten
  // (never stacked) on every change.
  //
  // data-accent is set but visually inert this release (AC-10).
  // -------------------------------------------------------------------------
  useEffect(() => {
    const { documentElement } = document
    documentElement.dataset.theme = theme
    documentElement.dataset.accent = accent
    documentElement.dataset.mstyle = mstyle
  }, [theme, accent, mstyle])

  // -------------------------------------------------------------------------
  // Effect 2 — CSS custom property effect
  //
  // Writes --sidebar-width (with px unit) and --pane-ratio (unitless) onto
  // document.documentElement so both the Sidebar and PaneSplit CSS rules
  // resolve from the same element the Divider writes to during live drag.
  //
  // The initial/committed values are written here; the Divider handles
  // real-time updates during a drag gesture.
  // -------------------------------------------------------------------------
  useEffect(() => {
    const { style } = document.documentElement
    const nextWidth = `${sidebarWidth}px`
    if (style.getPropertyValue('--sidebar-width') !== nextWidth) {
      style.setProperty('--sidebar-width', nextWidth)
    }
    const nextRatio = `${paneRatio}`
    if (style.getPropertyValue('--pane-ratio') !== nextRatio) {
      style.setProperty('--pane-ratio', nextRatio)
    }
  }, [sidebarWidth, paneRatio])

  // -------------------------------------------------------------------------
  // Effect 3 — window-resize re-clamp (AC-17)
  //
  // Registers a `resize` listener on `window`. On each resize event the
  // handler reads the current raw values imperatively (via `getState()` —
  // NOT the reactive selectors) so the listener is never re-registered on
  // value changes, then re-clamps and commits them via store actions.
  //
  // This is the renderer-side guarantee that no pane goes negative or
  // overflows after the OS window is resized. The complementary OS-window
  // minWidth floor lives in task 010.
  //
  // Empty dep array — the handler closes over nothing; `getState()` always
  // reads the latest store state at call time.
  // -------------------------------------------------------------------------
  useEffect(() => {
    function handleResize(): void {
      const state = settingsStore.getState()
      state.setSidebarWidth(state.sidebarWidth)
      state.setPaneRatio(state.paneRatio)
    }

    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  // -------------------------------------------------------------------------
  // Effect 4 — global Cmd-B / Ctrl-B toggle (AC-5)
  //
  // Registers a `keydown` listener on `document` (not on a focused element)
  // so Cmd-B fires regardless of which element has focus. On match:
  //   1. `e.preventDefault()` — suppresses browser / OS default (bold text
  //      in editable fields, browser bookmark shortcut, etc.).
  //   2. `toggleSidebar()` — called imperatively via `getState()` so the
  //      listener is never re-registered on sidebar state changes.
  //
  // Empty dep array — register once, remove on unmount.
  // -------------------------------------------------------------------------
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent): void {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault()
        settingsStore.getState().toggleSidebar()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  // -------------------------------------------------------------------------
  // Effect 5 — focus-return on collapse (AC-5 / grill F3)
  //
  // Detects the false→true edge of `sidebarCollapsed`: when the sidebar
  // transitions from expanded to collapsed, focus would fall to `<body>`
  // because the sidebar (and its Divider) unmount. This effect moves focus
  // to the sidebar-toggle button in the Titlebar via `toggleRef`.
  //
  // Mechanism:
  //   - `prevCollapsedRef` holds the value of `sidebarCollapsed` from the
  //     previous render. On each render where `sidebarCollapsed` has changed,
  //     the effect runs, compares the previous and current values, and fires
  //     `toggleRef.current?.focus()` only on the false→true edge.
  //   - The ref update (`prevCollapsedRef.current = sidebarCollapsed`) is
  //     performed inside the effect (after the comparison) to capture the
  //     transition correctly.
  //   - On mount `prevCollapsedRef` is initialised to the current value so
  //     the initial render never steals focus.
  // -------------------------------------------------------------------------
  useEffect(() => {
    const wasCollapsed = prevCollapsedRef.current
    prevCollapsedRef.current = sidebarCollapsed

    if (!wasCollapsed && sidebarCollapsed) {
      toggleRef.current?.focus()
    }
  }, [sidebarCollapsed])

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className={cx('shell', className)}>
      {/* ---- Titlebar row ---- */}
      <Titlebar toggleRef={toggleRef} />

      {/* ---- Main row: sidebar + workspace ---- */}
      <div className="shell__main">
        {/* Left column: resizable sidebar (conditionally unmounted when collapsed) */}
        <Sidebar>{sidebar}</Sidebar>

        {/* Right column: workspace — tabs strip above, pane split below */}
        <div className="shell__workspace">
          {/* Tabs slot: tab-strip region; absent when no tabs content is provided */}
          {tabs != null && <div className="shell__tabs">{tabs}</div>}

          {/* Pane split: request / response workspace */}
          <PaneSplit request={panes?.request} response={panes?.response} />
        </div>
      </div>

      {/* ---- Statusbar row ---- */}
      <Statusbar />

      {/*
       * Modals slot — portal-less mount point at the Shell root level.
       * Modal overlay, focus-trap, and backdrop behavior are each modal's own
       * concern; Shell only provides the mount surface.
       */}
      {modals}
    </div>
  )
}
