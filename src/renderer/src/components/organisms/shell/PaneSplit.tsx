/**
 * PaneSplit — request/response vertical split for the main workspace area.
 *
 * Renders two vertically-stacked panes (request on top, response on bottom)
 * separated by a horizontal `Divider`. The split ratio is driven by
 * `var(--pane-ratio)`, a unitless fraction (0.15–0.85) set on
 * `document.documentElement` by the Shell on mount and updated in real-time
 * by the `Divider` during drag.
 *
 * ## Layout
 *
 * The container is a `flex-direction: column` flex parent. The request pane
 * gets `flex: var(--pane-ratio)` and the response pane gets
 * `flex: calc(1 - var(--pane-ratio))`. Because CSS `flex` accepts a unitless
 * number as the `flex-grow` factor, this cleanly splits the available height
 * in the desired ratio without pixel arithmetic.
 *
 * ## Resize behaviour
 *
 * The mounted `Divider` (horizontal orientation) writes `--pane-ratio` onto
 * `document.documentElement` during drag at native frame rate and calls
 * `setPaneRatio(clamped)` on release. No React re-renders occur during the
 * drag — the CSS custom property drives layout directly (AC-16).
 *
 * ## Constraints
 *
 * - No inline `style={{...}}` JSX attributes — all sizing via CSS custom
 *   properties and BEM class rules (constitution §3.1 / AC-14).
 * - No `electron` or `node:` imports — renderer-only (§2.1 / §2.3).
 * - Imports via `@renderer` alias (§2.3).
 *
 * @module PaneSplit
 */

import './PaneSplit.css'

import { useRef, type ReactNode, type JSX } from 'react'
import { cx } from '@renderer/lib/cx'
import { settingsStore, PANE_MIN, PANE_MAX } from '@renderer/lib/settingsStore'
import { Divider } from '@renderer/components/molecules/Divider'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Props for the {@link PaneSplit} component.
 */
export interface PaneSplitProps {
  /**
   * Content for the top (request) pane.
   * Rendered inside the request mount slot without inspection or modification.
   */
  request?: ReactNode

  /**
   * Content for the bottom (response) pane.
   * Rendered inside the response mount slot without inspection or modification.
   */
  response?: ReactNode

  /** Additional CSS class applied to the outermost container element. */
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Vertically-stacked request / response split for the main workspace area.
 *
 * Reads `paneRatio` from the settings store via a per-field selector.
 * Renders the request pane, a horizontal `Divider`, and the response pane.
 * Pane heights are driven entirely by `var(--pane-ratio)` — no inline styles
 * are used. The `Divider` sets that CSS custom property directly on
 * `document.documentElement` during drag and calls `setPaneRatio` on release.
 *
 * @param props - See {@link PaneSplitProps}.
 *
 * AC-16: pane divider clamp — via the mounted Divider + setPaneRatio.
 */
export function PaneSplit({ request, response, className }: PaneSplitProps): JSX.Element {
  /** Current left-pane ratio (fraction). Per-field selector avoids full store re-renders. */
  const paneRatio = settingsStore((s) => s.paneRatio)

  /**
   * Ref to the flex container so the Divider can measure its pixel height at
   * drag time, enabling correct pixel→ratio conversion via `getDragExtent`.
   */
  const containerRef = useRef<HTMLDivElement>(null)

  return (
    <div ref={containerRef} className={cx('pane-split', className)}>
      {/* Top (request) pane — height resolves from var(--pane-ratio) via flex. */}
      <div className="pane-split__pane pane-split__pane--request">{request}</div>

      {/*
       * Horizontal drag handle — separates the request pane from the response pane.
       * The Divider writes --pane-ratio to document.documentElement during drag
       * and calls setPaneRatio on release (AC-16).
       * Do NOT re-clamp here — the Divider already clamps to [PANE_MIN, PANE_MAX].
       */}
      <Divider
        orientation="horizontal"
        value={paneRatio}
        min={PANE_MIN}
        max={PANE_MAX}
        cssVar="--pane-ratio"
        unit=""
        ariaLabel="Resize request and response panes"
        onCommit={(r) => settingsStore.getState().setPaneRatio(r)}
        getDragExtent={() => containerRef.current?.getBoundingClientRect().height ?? null}
        keyboardStep={0.02}
      />

      {/* Bottom (response) pane — height resolves from calc(1 - var(--pane-ratio)) via flex. */}
      <div className="pane-split__pane pane-split__pane--response">{response}</div>
    </div>
  )
}
