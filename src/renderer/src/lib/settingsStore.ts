/**
 * settingsStore.ts
 *
 * Module-level zustand store for managing the shell's view state.
 *
 * This module:
 *   - has NO node / electron imports (renderer-only, constitution §2.1/§2.3, AC-15)
 *   - exports a single module-level store instance (avoid per-consumer instantiation)
 *   - mutates state only via store actions (constitution §4)
 *   - is in-memory only (persistence is out of scope for this task)
 *
 * Usage:
 *   // Reactive (inside a React component):
 *   const theme = settingsStore(state => state.theme)
 *
 *   // Imperative (from any module):
 *   settingsStore.getState().setTheme('dark')
 */
import { create } from 'zustand'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Colour-scheme preference for the application shell. */
export type Theme = 'light' | 'dark'

/**
 * Method-style visual treatment for the active-item marker in navigation
 * lists (e.g. sidebar request list, tab strip).
 */
export type Mstyle = 'soft' | 'chip' | 'outline' | 'dot' | 'bar'

/**
 * Accent-colour identifier.
 *
 * The value is persisted in the store but is visually inert in this task —
 * no `[data-accent]` CSS is applied yet. Do not add accent palette CSS here.
 */
export type Accent = string

// ---------------------------------------------------------------------------
// Bounds (exported so consumers can clamp or validate independently)
// ---------------------------------------------------------------------------

/** Minimum sidebar width in pixels. */
export const SIDEBAR_MIN = 200

/** Maximum sidebar width in pixels. */
export const SIDEBAR_MAX = 520

/** Minimum left-pane ratio (fraction of available horizontal space). */
export const PANE_MIN = 0.15

/** Maximum left-pane ratio (fraction of available horizontal space). */
export const PANE_MAX = 0.85

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const defaults = {
  theme: 'light' as Theme,
  accent: 'mint' as Accent,
  mstyle: 'soft' as Mstyle,
  sidebarWidth: 260,
  paneRatio: 0.5,
  sidebarCollapsed: false
}

/** Default sidebar width in pixels (equals defaults.sidebarWidth). */
const DEFAULT_SIDEBAR_WIDTH = defaults.sidebarWidth

/** Default left-pane ratio (equals defaults.paneRatio). */
const DEFAULT_PANE_RATIO = defaults.paneRatio

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/**
 * Clamp a sidebar-width value to the valid range [SIDEBAR_MIN, SIDEBAR_MAX].
 *
 * Non-finite inputs (NaN, ±Infinity) fall back to `DEFAULT_SIDEBAR_WIDTH`
 * instead of propagating NaN through Math.min/max into the store.
 *
 * @param px - Desired sidebar width in pixels.
 * @returns   The clamped pixel value, or the default when `px` is not finite.
 */
export function clampSidebarWidth(px: number): number {
  if (!Number.isFinite(px)) return DEFAULT_SIDEBAR_WIDTH
  return Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, px))
}

/**
 * Clamp a pane-ratio value to the valid range [PANE_MIN, PANE_MAX].
 *
 * Non-finite inputs (NaN, ±Infinity) fall back to `DEFAULT_PANE_RATIO`
 * instead of propagating NaN through Math.min/max into the store.
 *
 * @param r - Desired ratio as a fraction (0–1).
 * @returns  The clamped ratio value, or the default when `r` is not finite.
 */
export function clampPaneRatio(r: number): number {
  if (!Number.isFinite(r)) return DEFAULT_PANE_RATIO
  return Math.min(PANE_MAX, Math.max(PANE_MIN, r))
}

// ---------------------------------------------------------------------------
// Store state + actions
// ---------------------------------------------------------------------------

/**
 * Complete state shape for the settings store.
 *
 * Scalar view-preference fields are paired with their mutating actions.
 * State is never mutated directly — all writes go through the actions below.
 */
export interface SettingsState {
  /** Current colour-scheme preference. */
  theme: Theme

  /**
   * Active accent-colour identifier.
   * Visually inert this release — persisted but no `[data-accent]` CSS yet.
   */
  accent: Accent

  /** Active method-style marker variant for navigation lists. */
  mstyle: Mstyle

  /** Current sidebar width in pixels; always within [SIDEBAR_MIN, SIDEBAR_MAX]. */
  sidebarWidth: number

  /**
   * Fraction of the horizontal workspace assigned to the left pane.
   * Always within [PANE_MIN, PANE_MAX].
   */
  paneRatio: number

  /** Whether the sidebar is currently collapsed. */
  sidebarCollapsed: boolean

  /**
   * Set the colour-scheme preference.
   * @param theme - The new theme to apply.
   */
  setTheme: (theme: Theme) => void

  /**
   * Set the accent-colour identifier.
   * @param accent - An accent identifier string (visually inert this release).
   */
  setAccent: (accent: Accent) => void

  /**
   * Set the method-style marker variant.
   * @param mstyle - The new marker style to apply.
   */
  setMstyle: (mstyle: Mstyle) => void

  /**
   * Set the sidebar width, clamping the value to [SIDEBAR_MIN, SIDEBAR_MAX].
   * @param px - Desired sidebar width in pixels.
   */
  setSidebarWidth: (px: number) => void

  /**
   * Set the left-pane ratio, clamping the value to [PANE_MIN, PANE_MAX].
   * @param r - Desired ratio as a fraction (0–1).
   */
  setPaneRatio: (r: number) => void

  /**
   * Toggle the sidebar between collapsed and expanded states.
   * Does NOT zero or modify `sidebarWidth` — the stored width is preserved
   * so the sidebar restores its previous size on expand.
   */
  toggleSidebar: () => void

  /**
   * Restore all fields to their documented default values.
   */
  reset: () => void
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

/**
 * The single, module-level zustand store for shell view settings.
 *
 * Consumers should prefer selectors over reading the full store:
 *   const theme = settingsStore(state => state.theme)
 *
 * Named `settingsStore` per project naming convention (Store suffix, §3.3).
 */
export const settingsStore = create<SettingsState>((set) => ({
  ...defaults,

  setTheme(theme) {
    set({ theme })
  },

  setAccent(accent) {
    set({ accent })
  },

  setMstyle(mstyle) {
    set({ mstyle })
  },

  setSidebarWidth(px) {
    set({ sidebarWidth: clampSidebarWidth(px) })
  },

  setPaneRatio(r) {
    set({ paneRatio: clampPaneRatio(r) })
  },

  toggleSidebar() {
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
  },

  reset() {
    set({ ...defaults })
  }
}))
