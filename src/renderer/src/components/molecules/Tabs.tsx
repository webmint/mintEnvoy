/**
 * Tabs — hand-rolled, controlled, horizontal-only, selection-only tab-strip.
 *
 * Renders a row of tab buttons from a flat {@link TabDescriptor} array, marks
 * the caller-supplied `activeId`, and emits `onChange(id)` on click or keyboard
 * selection. No panel content is rendered — the component is selection-only.
 *
 * ## WAI-ARIA engine
 *
 * The a11y engine is intentionally hand-rolled (`role="tablist"` containing
 * `role="tab"` buttons with manual roving tabindex) instead of wrapping Radix
 * Tabs. Radix `Tabs.Trigger` deterministically emits `aria-controls` pointing at
 * a sibling `Tabs.Content`; with no Content mounted (selection-only) that
 * attribute dangles and fails AC-7. Hand-rolling the small APG-specified pattern
 * is the only clean path that satisfies AC-7 while keeping the primitive
 * decoupled from its panel consumers.
 *
 * ## Keyboard navigation (automatic activation — AC-6)
 *
 * | Key        | Behaviour |
 * |------------|-----------|
 * | ArrowRight | Select next enabled tab (with wrap) |
 * | ArrowLeft  | Select previous enabled tab (with wrap) |
 * | Home       | Select first enabled tab |
 * | End        | Select last enabled tab |
 *
 * Disabled tabs are skipped by all keyboard navigation (AC-9).
 * Vertical arrow keys are intentionally ignored (horizontal-only).
 *
 * ## No-selection guard (AC-10)
 *
 * When `activeId` matches no enabled tab — empty array, no match, or all
 * disabled — the strip renders with no `aria-selected="true"` tab and
 * auto-selects nothing.
 *
 * ## Usage
 *
 * ```tsx
 * import { Tabs } from '@renderer/components/molecules/Tabs'
 *
 * function Example(): React.JSX.Element {
 *   const [activeId, setActiveId] = React.useState('params')
 *
 *   return (
 *     <Tabs
 *       aria-label="Request sections"
 *       tabs={[
 *         { id: 'params', label: 'Params', badge: 3 },
 *         { id: 'headers', label: 'Headers' },
 *         { id: 'body', label: 'Body' },
 *         { id: 'auth', label: 'Auth', disabled: true },
 *       ]}
 *       activeId={activeId}
 *       onChange={setActiveId}
 *       actions={<button>+ Add</button>}
 *     />
 *   )
 * }
 * ```
 *
 * ## Accessibility
 *
 * - `role="tablist"` on the list container with `aria-orientation="horizontal"`.
 * - Each button has `role="tab"` + `aria-selected` + `tabIndex` managed via
 *   roving tabindex (AC-7).
 * - `aria-controls` is deliberately NOT emitted — no panels are mounted (AC-7).
 * - Disabled tabs carry `disabled` + `aria-disabled="true"` (AC-9).
 *
 * ## Constraints
 *
 * - Controlled-only: the caller owns `activeId` and updates it via `onChange`.
 * - No inline `style={{...}}` anywhere — all styling via BEM CSS classes (AC-14).
 * - No `electron` or `node:` imports — renderer-only (AC-15).
 * - No Radix import — hand-rolled WAI-ARIA engine (per approved plan departure).
 *
 * @module Tabs
 */

import './Tabs.css'

import { useRef } from 'react'
import { cx } from '@renderer/lib/cx'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Descriptor for a single tab in the strip.
 *
 * All string values are rendered as JSX text nodes (React escapes them —
 * no HTML injection is possible, CWE-79).
 *
 * Satisfies AC-5, AC-6, AC-9, AC-10 (the descriptor carries id/disabled
 * which drive behavior).
 */
export interface TabDescriptor {
  /** Unique identifier for this tab. Passed to `onChange` when selected. */
  id: string

  /**
   * Visible label text.
   * Rendered as an escaped JSX text node — never treated as HTML.
   */
  label: string

  /**
   * Optional badge shown next to the label.
   * Typical use: unread count, item count, notification dot text.
   * Rendered as an escaped JSX text node (string | number — no ReactNode).
   */
  badge?: string | number

  /**
   * When `true`, the tab is rendered but not interactive.
   * Disabled tabs are skipped by all keyboard navigation (AC-9).
   */
  disabled?: boolean
}

/**
 * Props for the {@link Tabs} component.
 *
 * Satisfies AC-5 (onChange), AC-6 (keyboard via onChange), AC-7 (activeId →
 * aria-selected), AC-8 (actions slot), AC-10 (render-no-selection guard when
 * activeId matches no enabled tab), AC-11 (JSDoc), AC-14 (no inline styles),
 * AC-15 (no electron/node imports).
 */
export interface TabsProps {
  /**
   * Flat array of tab descriptors rendered in order.
   * Empty arrays and all-disabled arrays render a strip with no active tab
   * (AC-10).
   */
  tabs: TabDescriptor[]

  /**
   * The `id` of the currently selected tab.
   * The caller owns this value (controlled-only — no uncontrolled mode).
   * When `activeId` matches no enabled tab, no tab is marked selected (AC-10).
   */
  activeId: string

  /**
   * Called with the target tab's `id` when the user clicks an enabled tab or
   * selects one via keyboard (AC-5, AC-6).
   * The caller decides whether to update `activeId` (standard controlled
   * pattern — calling the active tab again still fires once).
   * Never called for disabled tabs (AC-9).
   */
  onChange: (id: string) => void

  /**
   * Optional right-aligned content rendered at the end of the strip, OUTSIDE
   * the `role="tablist"` element (AC-8).
   * Typical use: action buttons, icon controls, or menus.
   */
  actions?: React.ReactNode

  /** Additional CSS class applied to the outermost wrapper element. */
  className?: string

  /**
   * Accessible label for the tablist element.
   * Required when there is no visible heading that labels the set of tabs.
   * Maps directly to `aria-label` on the `role="tablist"` element (AC-7).
   */
  'aria-label'?: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns the index of the next enabled tab, wrapping around the array.
 * Direction: +1 for forward (ArrowRight), -1 for backward (ArrowLeft).
 * Skips disabled tabs. Returns -1 when no enabled tab exists.
 *
 * @param tabs - The full descriptor array.
 * @param fromIndex - Starting index (the currently focused tab).
 * @param direction - +1 (next) or -1 (previous).
 */
function nextEnabledIndex(tabs: TabDescriptor[], fromIndex: number, direction: 1 | -1): number {
  const len = tabs.length
  if (len === 0) return -1
  let i = fromIndex
  let steps = 0
  while (steps < len) {
    i = (i + direction + len) % len
    steps++
    if (tabs[i].disabled !== true) return i
  }
  return -1
}

/**
 * Returns the index of the first enabled tab, or -1 when none is enabled.
 *
 * @param tabs - The full descriptor array.
 */
function firstEnabledIndex(tabs: TabDescriptor[]): number {
  return tabs.findIndex((t) => t.disabled !== true)
}

/**
 * Returns the index of the last enabled tab, or -1 when none is enabled.
 *
 * @param tabs - The full descriptor array.
 */
function lastEnabledIndex(tabs: TabDescriptor[]): number {
  for (let i = tabs.length - 1; i >= 0; i--) {
    if (tabs[i].disabled !== true) return i
  }
  return -1
}

/**
 * Derives the roving-tabindex tab-stop index.
 *
 * Exactly one tab is the keyboard tab-stop (tabIndex=0):
 * - The active tab when `activeId` matches an enabled tab.
 * - The first enabled tab when `activeId` matches no enabled tab.
 * - -1 (no tab-stop) when no enabled tab exists.
 *
 * Satisfies AC-7 (roving tabindex), AC-10 (no-selection guard falls back to
 * the first enabled tab as tab-stop rather than auto-selecting).
 *
 * @param tabs - The full descriptor array.
 * @param activeId - The caller-supplied active tab id.
 */
function rovingTabStopIndex(tabs: TabDescriptor[], activeId: string): number {
  // Prefer the active tab if it's enabled.
  const activeIndex = tabs.findIndex((t) => t.id === activeId && t.disabled !== true)
  if (activeIndex !== -1) return activeIndex
  // Fall back to the first enabled tab as the tab-stop.
  return firstEnabledIndex(tabs)
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Controlled, horizontal-only, selection-only tab-strip.
 *
 * Emits `onChange(id)` when a tab is selected via click or keyboard. Renders
 * a WAI-ARIA tablist with roving tabindex and automatic activation. Disabled
 * tabs are rendered but skipped by all navigation and never invoke `onChange`.
 *
 * The `actions` slot renders right-aligned content outside the tablist —
 * useful for add/more buttons scoped to the current tab group.
 *
 * @param props - See {@link TabsProps}.
 *
 * AC-1: component exists in the molecules dir.
 * AC-5: click → onChange once per enabled tab.
 * AC-6: ArrowRight/Left/Home/End → onChange with wrap + disabled-skip.
 * AC-7: role=tablist/tab, aria-selected, roving tabindex, no aria-controls.
 * AC-8: actions slot rendered right-aligned outside the tablist.
 * AC-9: disabled tabs skip onChange on click and keyboard.
 * AC-10: no-selection guard when activeId matches no enabled tab.
 * AC-11: JSDoc on all exported symbols.
 * AC-14: no inline style={{...}}.
 * AC-15: no electron/node: imports.
 */
export function Tabs({
  tabs,
  activeId,
  onChange,
  actions,
  className,
  'aria-label': ariaLabel
}: TabsProps): React.JSX.Element {
  // Ref map: keyed by tab id → the button DOM element.
  // Used to move DOM focus after keyboard navigation (AC-6).
  const buttonRefs = useRef<Map<string, HTMLButtonElement>>(new Map())

  // Determine which tab (if any) is truly active for aria-selected.
  // When activeId matches no enabled tab → no tab is selected (AC-10).
  const activeEnabledId = tabs.find((t) => t.id === activeId && t.disabled !== true)?.id

  // Roving tab-stop: the index of the single focusable tab (AC-7).
  const tabStopIndex = rovingTabStopIndex(tabs, activeId)

  // ---------------------------------------------------------------------------
  // Keyboard handler (automatic activation — AC-6)
  // ---------------------------------------------------------------------------

  function handleKeyDown(
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentIndex: number
  ): void {
    let targetIndex = -1

    switch (event.key) {
      case 'ArrowRight':
        targetIndex = nextEnabledIndex(tabs, currentIndex, 1)
        break
      case 'ArrowLeft':
        targetIndex = nextEnabledIndex(tabs, currentIndex, -1)
        break
      case 'Home':
        targetIndex = firstEnabledIndex(tabs)
        break
      case 'End':
        targetIndex = lastEnabledIndex(tabs)
        break
      default:
        return // Do not call preventDefault for other keys.
    }

    if (targetIndex === -1) return

    event.preventDefault()

    const targetTab = tabs[targetIndex]
    if (targetTab === undefined) return

    // Automatic activation: fire onChange immediately (AC-6).
    onChange(targetTab.id)

    // Move DOM focus to the target button (AC-6).
    const targetEl = buttonRefs.current.get(targetTab.id)
    targetEl?.focus()
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={cx('tabs', className)}>
      {/* role="tablist" is on the inner element; the outer div holds the
          optional right-aligned actions slot (AC-8). */}
      <div
        role="tablist"
        aria-label={ariaLabel}
        aria-orientation="horizontal"
        className="tabs__list"
      >
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeEnabledId
          const isDisabled = tab.disabled === true
          const isTabStop = index === tabStopIndex

          return (
            <button
              key={tab.id}
              role="tab"
              // aria-selected reflects the active tab; false (not absent) for
              // inactive tabs (WAI-ARIA Tabs pattern requires explicit false).
              // When no tab is active (AC-10), every tab gets false.
              aria-selected={isActive}
              // Disabled: native `disabled` attribute prevents click/focus;
              // aria-disabled="true" is the explicit ARIA signal (AC-9).
              disabled={isDisabled}
              aria-disabled={isDisabled || undefined}
              // Roving tabindex: exactly one tab is the keyboard entry point (AC-7).
              tabIndex={isTabStop ? 0 : -1}
              className={cx(
                'tabs__tab',
                isActive && 'tabs__tab--active',
                isDisabled && 'tabs__tab--disabled'
              )}
              onClick={() => {
                // Guard: the `disabled` attribute already prevents browser
                // clicks, but also guard in JS to be safe (AC-9).
                if (isDisabled) return
                onChange(tab.id)
              }}
              onKeyDown={(e) => handleKeyDown(e, index)}
              ref={(el) => {
                if (el !== null) {
                  buttonRefs.current.set(tab.id, el)
                } else {
                  buttonRefs.current.delete(tab.id)
                }
              }}
            >
              {/* Label text — rendered as a JSX text node (React escapes it). */}
              <span className="tabs__tab-label">{tab.label}</span>

              {/* Optional badge — rendered only when badge is not undefined (AC-3 reuse). */}
              {tab.badge !== undefined && <span className="tabs__badge">{tab.badge}</span>}
            </button>
          )
        })}
      </div>

      {/* Right-aligned actions slot — outside the tablist element (AC-8). */}
      {actions !== undefined && <div className="tabs__actions">{actions}</div>}
    </div>
  )
}
