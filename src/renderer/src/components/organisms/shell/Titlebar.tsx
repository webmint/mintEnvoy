/**
 * Titlebar — app shell titlebar with six presentational regions.
 *
 * Renders the top chrome of the application window: logo, workspace pill,
 * sidebar-toggle button (the focus-return target when the sidebar collapses),
 * command-palette trigger (button slot only — palette behavior is out of scope),
 * environment selector (static/presentational), and account pill.
 *
 * ## Focus-return contract (AC-5 / grill F3)
 *
 * The sidebar-toggle `<button>` is the designated focus-return target. When the
 * sidebar collapses via keyboard, the Shell (task 008) focuses this button.
 * Callers pass `toggleRef` and the ref is forwarded directly onto the sidebar-
 * toggle `<button>` — NOT onto any wrapper element.
 *
 * ## Constraints
 *
 * - No inline `style={{...}}` JSX attributes — all sizing via CSS class rules
 *   bound to tokens.css custom properties (§ constitution §3.1).
 * - No `electron` or `node:` imports — renderer-only (§2.1 / §2.3).
 * - Imports via `@renderer` alias (§2.3).
 *
 * @module Titlebar
 */

import './Titlebar.css'

import { type Ref, type JSX } from 'react'
import { cx } from '@renderer/lib/cx'
import { settingsStore } from '@renderer/lib/settingsStore'
import { Icon } from '@renderer/components/atoms/Icon'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Props for the {@link Titlebar} component.
 */
export interface TitlebarProps {
  /**
   * Ref forwarded onto the sidebar-toggle `<button>`.
   *
   * This is the focus-return target (grill F3 / AC-5): when the sidebar
   * collapses the Shell focuses this button so keyboard users land somewhere
   * meaningful. Attach via `ref={toggleRef}` on the toggle button only.
   */
  toggleRef?: Ref<HTMLButtonElement>

  /** Additional CSS class applied to the outermost titlebar element. */
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Presentational app shell titlebar.
 *
 * Renders six regions in a three-column grid (left / center / right):
 *
 * Left:
 *   1. Logo — app mark + wordmark.
 *   2. Workspace pill — static label (workspace switcher is out of scope).
 *   3. Sidebar-toggle button — calls `toggleSidebar()`; `ref={toggleRef}`.
 *
 * Center:
 *   4. Command-palette trigger — `<button>` slot; no palette behavior (out of scope).
 *
 * Right:
 *   5. Environment selector — static presentational button (no dropdown data).
 *   6. Account pill — static presentational button.
 *
 * @param props - See {@link TitlebarProps}.
 */
export function Titlebar({ toggleRef, className }: TitlebarProps): JSX.Element {
  /** Whether the sidebar is currently collapsed — used for the toggle active state. */
  const sidebarCollapsed = settingsStore((s) => s.sidebarCollapsed)

  return (
    <header className={cx('titlebar', className)}>
      {/* ---- Left section: logo, workspace pill, sidebar toggle ---- */}
      <div className="titlebar__left">
        {/* 1. Logo */}
        <div className="titlebar__logo">
          <span className="titlebar__logo-mark" aria-hidden="true">
            m
          </span>
          <span className="titlebar__logo-name">mintenvoy</span>
        </div>

        <span className="titlebar__divider" aria-hidden="true" />

        {/* 2. Workspace pill — static placeholder: workspace/env/account data is out of scope this task */}
        <button
          className="titlebar__workspace-pill"
          type="button"
          aria-label="Workspace: Friends &amp; Family — switch workspace"
        >
          <span className="titlebar__workspace-avatar" aria-hidden="true">
            {/* static placeholder — initials and gradient are hardcoded; real data is out of scope this task */}
            FF
          </span>
          <span className="titlebar__workspace-name">Friends &amp; Family</span>
          <Icon name="chevronDown" size={11} />
        </button>

        {/* 3. Sidebar-toggle — focus-return target (F3 / AC-5) */}
        <button
          ref={toggleRef}
          className={cx('titlebar__icon-btn', sidebarCollapsed && 'titlebar__icon-btn--active')}
          type="button"
          aria-label="Toggle sidebar"
          onClick={() => settingsStore.getState().toggleSidebar()}
        >
          <Icon name="sidebar" size={14} />
        </button>
      </div>

      {/* ---- Center section: command-palette trigger ---- */}
      {/* 4. Command-palette trigger (button slot only — palette behavior is out of scope) */}
      <button className="titlebar__cmdk" type="button" aria-label="Open command palette">
        <Icon name="search" size={13} className="titlebar__cmdk-icon" />
        <span className="titlebar__cmdk-text">Search requests, history, variables&hellip;</span>
        <span className="titlebar__kbd" aria-label="keyboard shortcut Command K">
          &#8984;K
        </span>
      </button>

      {/* ---- Right section: environment selector, account pill ---- */}
      <div className="titlebar__right">
        {/* 5. Environment selector — static placeholder: environment list and selection are out of scope this task */}
        <button
          className="titlebar__env-selector"
          type="button"
          aria-label="Environment: Development — switch environment"
        >
          <span className="titlebar__env-dot" aria-hidden="true" />
          <span className="titlebar__env-name">Development</span>
          <Icon name="chevronDown" size={11} />
        </button>

        {/* 6. Account pill — static placeholder: account identity and actions are out of scope this task */}
        <button className="titlebar__account-pill" type="button" aria-label="Account">
          <span className="titlebar__account-avatar" aria-hidden="true">
            {/* static placeholder — initials and gradient are hardcoded; real account data is out of scope this task */}
            YC
          </span>
        </button>
      </div>
    </header>
  )
}
