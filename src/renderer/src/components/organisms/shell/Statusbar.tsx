/**
 * Statusbar — presentational bottom statusbar region for the app shell.
 *
 * Provides a thin bottom bar (`<footer>`) that serves as the shell's status
 * surface. Content is entirely controlled by downstream features via the
 * `children` slot — this component only provides the region and its styling.
 *
 * ## Content surface
 *
 * The Statusbar renders an arbitrary `children` mount slot. Contents are not
 * inspected or modified by this component; downstream features are responsible
 * for populating the region with status items.
 *
 * ## Constraints
 *
 * - No inline `style={{...}}` JSX attributes — all sizing via CSS class rules
 *   bound to tokens.css custom properties (§ constitution §3.1).
 * - No `electron` or `node:` imports — renderer-only (§2.1 / §2.3).
 * - Imports via `@renderer` alias (§2.3).
 *
 * @module Statusbar
 */

import './Statusbar.css'

import { type ReactNode, type JSX } from 'react'
import { cx } from '@renderer/lib/cx'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Props for the {@link Statusbar} component.
 */
export interface StatusbarProps {
  /**
   * The statusbar content slot — arbitrary children rendered inside the bar.
   * Contents are not inspected or modified by this component.
   * Downstream features populate this slot with status items.
   */
  children?: ReactNode

  /** Additional CSS class applied to the outermost statusbar element. */
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Presentational bottom statusbar region.
 *
 * Renders a `<footer>` element with the `statusbar` BEM class that anchors to
 * the bottom of the app shell. The region is an empty content surface this
 * task — downstream features (sync state, environment indicator, etc.) fill it
 * via `children`.
 *
 * @param props - See {@link StatusbarProps}.
 */
export function Statusbar({ children, className }: StatusbarProps): JSX.Element {
  return (
    <footer className={cx('statusbar', className)} role="status" aria-label="Status bar">
      {children}
    </footer>
  )
}
