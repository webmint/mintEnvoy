/**
 * Sidebar — resizable left-sidebar region for the app shell.
 *
 * Consumes the `--sidebar-width` CSS custom property (set by Shell and updated
 * in real-time by the mounted `Divider`) for its width. Renders an arbitrary
 * `children` mount slot (sidebar content is out of scope for this component)
 * and mounts a vertical `Divider` wired to `setSidebarWidth`.
 *
 * ## Collapse behaviour
 *
 * When `sidebarCollapsed` is `true` in the settings store, the sidebar
 * container AND its `Divider` are conditionally unmounted — NOT hidden with
 * `width:0` or `display:none`. This removes the focusable separator from the
 * a11y tree cleanly (AC-5).
 *
 * ## Resize behaviour
 *
 * The `Divider` (vertical orientation) writes `--sidebar-width` onto
 * `document.documentElement` during a drag at native frame rate and calls
 * `setSidebarWidth(px)` on release. The CSS custom property resolves directly
 * in `.sidebar { width: var(--sidebar-width) }` — no React re-renders occur
 * during the drag (AC-4).
 *
 * ## Constraints
 *
 * - No inline `style={{...}}` JSX attributes — all sizing via CSS custom
 *   properties and BEM class rules (§ constitution §3.1 / AC-14).
 * - No `electron` or `node:` imports — renderer-only (§2.1 / §2.3).
 * - Imports via `@renderer` alias (§2.3).
 *
 * @module Sidebar
 */

import './Sidebar.css'

import { type ReactNode, type JSX } from 'react'
import { cx } from '@renderer/lib/cx'
import { settingsStore, SIDEBAR_MIN, SIDEBAR_MAX } from '@renderer/lib/settingsStore'
import { Divider } from '@renderer/components/molecules/Divider'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Props for the {@link Sidebar} component.
 */
export interface SidebarProps {
  /**
   * The sidebar mount slot — arbitrary content rendered inside the sidebar
   * region. Contents are not inspected or modified by this component.
   * When the sidebar is collapsed this subtree is fully unmounted.
   */
  children?: ReactNode

  /** Additional CSS class applied to the outermost sidebar element. */
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Resizable left-sidebar region.
 *
 * Reads `sidebarCollapsed` and `sidebarWidth` from the settings store via
 * per-field selectors. When collapsed, renders `null` (both the sidebar
 * container and its `Divider` are absent from the React tree). When expanded,
 * renders the sidebar container followed by a vertical `Divider` that lets
 * the user resize it by dragging.
 *
 * The sidebar's width is driven entirely by `var(--sidebar-width)` — no
 * inline styles are used. The `Divider` sets that CSS custom property directly
 * on `document.documentElement` during drag and calls `setSidebarWidth` on
 * release.
 *
 * @param props - See {@link SidebarProps}.
 *
 * AC-4: sidebar drag clamp — via the mounted Divider + setSidebarWidth.
 * AC-5: sidebarCollapsed unmounts sidebar + divider (conditional render).
 */
export function Sidebar({ children, className }: SidebarProps): JSX.Element | null {
  /** Whether the sidebar is currently collapsed. Per-field selector. */
  const sidebarCollapsed = settingsStore((s) => s.sidebarCollapsed)

  /** Current sidebar width in pixels. Per-field selector. */
  const sidebarWidth = settingsStore((s) => s.sidebarWidth)

  // When collapsed, both the sidebar region and its Divider are fully absent
  // from the React tree — no hidden DOM, no focusable separator (AC-5).
  if (sidebarCollapsed) {
    return null
  }

  return (
    <>
      {/* Sidebar content container — width resolves from var(--sidebar-width). */}
      <aside className={cx('sidebar', className)}>{children}</aside>

      {/*
       * Vertical drag handle — separates the sidebar from the workspace.
       * The Divider writes --sidebar-width to document.documentElement during
       * drag and calls setSidebarWidth on release (AC-4).
       * Do NOT re-clamp here — the Divider already clamps to [min, max].
       */}
      <Divider
        orientation="vertical"
        value={sidebarWidth}
        min={SIDEBAR_MIN}
        max={SIDEBAR_MAX}
        cssVar="--sidebar-width"
        ariaLabel="Resize sidebar"
        onCommit={(px) => settingsStore.getState().setSidebarWidth(px)}
      />
    </>
  )
}
