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
 * | Delete     | Close focused tab (only when `closable` is true — AC-22) |
 * | Backspace  | Close focused tab (only when `closable` is true — AC-22) |
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
 * ## Opt-in close affordance (AC-11, AC-12, AC-22, AC-23 — feature-004 extension)
 *
 * When `closable` is true, a sibling ✕ `<button tabIndex={-1}>` is rendered next
 * to each tab's `role="tab"` button. The ✕ is a pointer target only — it is
 * NEVER added to `buttonRefs`, NEVER given `role="tab"`, and NEVER a roving tab
 * stop (AC-12). Clicking it calls `onClose?.(tab.id)` without also triggering
 * `onChange`. Delete/Backspace on the focused tab also fires `onClose`.
 *
 * `onClose` is signal-only: it emits the tab id and mutates no list — the store
 * owns the lifecycle. The primitive's only post-close job is roving-focus
 * integrity on the next render (AC-23), handled by `useLayoutEffect`.
 *
 * When `closable` is falsy (the default), the component is byte-identical to
 * the feature-002 selection-only contract — no Delete/Backspace handler active,
 * no extra close DOM node, no extra roving tab stop (AC-11).
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
 * - ✕ close button (when `closable`) is `tabIndex={-1}`, not `role="tab"` (AC-12).
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

import { useLayoutEffect, useRef } from 'react'
import { cx } from '@renderer/lib/cx'
import { Icon } from '@renderer/components/atoms/Icon'
import { METHODS } from '@renderer/lib/httpMethods'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Returns the CSS class string for a method chip.
 * When the uppercased `method` is in METHODS (the SSOT from httpMethods.ts)
 * the color modifier class is appended; otherwise only the base `method` class
 * is returned (AC-10).
 *
 * @param method - The raw method string from the TabDescriptor.
 */
function methodChipClassName(method: string): string {
  const upper = method.toUpperCase()
  return (METHODS as readonly string[]).includes(upper) ? cx('method', upper) : cx('method')
}

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

  /**
   * Optional HTTP method string displayed as a colored chip before the label.
   * When provided, a `<span class="method {METHOD}">` chip is rendered in both
   * the closable and non-closable branches. The method string is uppercased and
   * matched against METHODS (the SSOT from httpMethods.ts) to assign a color
   * modifier class; unknown methods render with the base `method` class only
   * (uncolored — AC-10).
   * When absent, no chip is rendered (byte-identical to the pre-005 contract).
   *
   * **Accessibility tradeoff**: the rendered chip carries `aria-hidden="true"`
   * (it is a decorative visual affordance that prevents double-announcement on
   * URL-only tabs where `deriveLabel` already prepends the method to the label).
   * For **named tabs** (where `label` is a human-readable request name and the
   * method string is NOT embedded in `label`), this makes the method invisible
   * to assistive technology. Callers who need AT users to hear the method should
   * include it in `label` — as `deriveLabel` does for URL-only tabs. For named
   * tabs the chip is intentionally a visual-only affordance.
   */
  method?: string

  /**
   * When `true`, the tab has unsaved changes (dirty state).
   * In the closable branch: replaces the close `<button>` with a non-focusable
   * `<span class="tabs__tab-dirty">` dot. Clicking the dot still calls
   * `onClose?.(id)` so the store can decide the close behaviour.
   * Delete/Backspace still fires `onClose` regardless of dirty state (AC-6).
   * Has no effect in the non-closable branch.
   */
  dirty?: boolean
}

/**
 * Props for the {@link Tabs} component.
 *
 * Satisfies AC-5 (onChange), AC-6 (keyboard via onChange), AC-7 (activeId →
 * aria-selected), AC-8 (actions slot), AC-10 (render-no-selection guard when
 * activeId matches no enabled tab), AC-11 (JSDoc), AC-14 (no inline styles),
 * AC-15 (no electron/node imports).
 *
 * ## Backward-compatible contract extension (feature-004, AC-28/AC-29)
 *
 * `closable` and `onClose` are opt-in additions to the feature-002
 * selection-only contract. When both are omitted (or `closable` is falsy), the
 * component is byte-identical to the 002 contract: no ✕ DOM node is rendered,
 * no Delete/Backspace close path is active, and no extra roving tab stop is
 * introduced (AC-11/AC-12). Existing consumers need not update.
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

  /**
   * Opt-in per-tab close affordance (default `false`/`undefined` — off).
   *
   * When `true`, a sibling ✕ `<button tabIndex={-1}>` is rendered next to
   * each tab button. The ✕ is a pointer target only — it is NEVER added to
   * `buttonRefs`, NEVER given `role="tab"`, and NEVER a roving tab stop
   * (AC-12). Delete/Backspace while a tab is focused also fires `onClose`.
   *
   * When `false` or omitted, the component is byte-identical to the 002
   * selection-only contract (AC-11).
   *
   * @since feature-004 (backward-compatible opt-in extension — AC-28)
   */
  closable?: boolean

  /**
   * Called with the closed tab's `id` when the ✕ button is clicked or
   * Delete/Backspace is pressed while the tab is focused.
   *
   * Signal-only: this callback emits the id and mutates no list. The store
   * owns the tab lifecycle. The primitive's only post-close responsibility is
   * roving-focus integrity on the next render (AC-22, AC-23).
   *
   * Only fired when `closable` is `true`. Safe to omit even with `closable`:
   * calling it is a no-op when `onClose` is `undefined`.
   *
   * @since feature-004 (backward-compatible opt-in extension — AC-28)
   */
  onClose?: (id: string) => void
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
 * When `closable` is true, a sibling ✕ button (tabIndex={-1}, not role="tab")
 * is rendered per tab and `onClose` fires on click or Delete/Backspace (AC-22).
 * Focus is restored via `useLayoutEffect` when the active tab changes after a
 * close re-render, without hijacking mouse-user focus (AC-23).
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
 * AC-11: JSDoc on all exported symbols; closable=false path byte-identical to 002.
 * AC-12: exactly one roving tab stop per tab regardless of closable.
 * AC-14: no inline style={{...}}.
 * AC-15: no electron/node: imports.
 * AC-22: ✕ button + Delete/Backspace → onClose (signal-only, no list mutation).
 * AC-23: useLayoutEffect restores roving focus to neighbor after close re-render.
 * AC-28: closable/onClose JSDoc records the backward-compatible contract extension.
 */
export function Tabs({
  tabs,
  activeId,
  onChange,
  actions,
  className,
  'aria-label': ariaLabel,
  closable,
  onClose
}: TabsProps): React.JSX.Element {
  // Ref map: keyed by tab id → the button DOM element.
  // Used to move DOM focus after keyboard navigation (AC-6).
  // GUARDRAIL: the ✕ close button is NEVER added to this map (AC-12, Risk-1).
  const buttonRefs = useRef<Map<string, HTMLButtonElement>>(new Map())

  // Tracks whether focus is currently inside the tablist (capture phase).
  // Used by useLayoutEffect to decide whether to restore focus after a close
  // re-render — prevents hijacking focus from a mouse user (AC-23).
  const lastFocusWasInListRef = useRef<boolean>(false)

  // Determine which tab (if any) is truly active for aria-selected.
  // When activeId matches no enabled tab → no tab is selected (AC-10).
  const activeEnabledId = tabs.find((t) => t.id === activeId && t.disabled !== true)?.id

  // Roving tab-stop: the index of the single focusable tab (AC-7).
  // Re-derived from (tabs, activeId) on EVERY render so tabIndex={0} can
  // never dangle after a tab is removed (AC-12, AC-23).
  const tabStopIndex = rovingTabStopIndex(tabs, activeId)

  // ---------------------------------------------------------------------------
  // Focus restoration after close re-render (AC-23 — useLayoutEffect, not useEffect)
  //
  // After a close fires, the store removes the tab and updates activeId to a
  // neighbor. On the very next synchronous paint, this effect checks whether:
  //   1. Focus was inside the tablist immediately before the re-render, AND
  //   2. The active tab's button is not already focused (covers non-close navigations).
  // When both conditions hold, it moves focus to the new active tab button.
  //
  // useLayoutEffect (not useEffect) fires before the browser paints, so the
  // focus move happens in the same frame as the DOM update — no flash of
  // focus falling to <body>.
  //
  // MUST NOT use a DOM selector to find the target — use buttonRefs (index-based
  // engine, Risk-1 guardrail 3). The effect reads buttonRefs.current.get(activeId)
  // which is always populated by the ref callback below before this fires.
  // ---------------------------------------------------------------------------
  useLayoutEffect(() => {
    if (!lastFocusWasInListRef.current) return

    const activeEl = buttonRefs.current.get(activeId)
    if (activeEl === undefined) return
    if (document.activeElement === activeEl) return

    activeEl.focus()
  }, [activeId, tabs])

  // ---------------------------------------------------------------------------
  // Keyboard handler (automatic activation — AC-6)
  //
  // GUARDRAIL 3 (Risk-1): this handler is index-based and MUST stay that way.
  // Do NOT switch to a DOM selector (querySelectorAll / closest / etc.).
  // ---------------------------------------------------------------------------

  function handleKeyDown(
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
    tabId: string
  ): void {
    // Delete/Backspace close path — only active when closable=true (AC-11/AC-22).
    // Keep this branch BEFORE the switch so early-return doesn't hide it.
    if (closable && (event.key === 'Delete' || event.key === 'Backspace')) {
      event.preventDefault()
      onClose?.(tabId)
      return
    }

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
    // GUARDRAIL 3: use buttonRefs (index-based), not a DOM selector.
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
        // Capture-phase focus/blur to track whether focus is inside the list.
        // Only wired when closable=true — the closable=false path adds no handlers
        // to preserve the 002 byte-identical contract (AC-11).
        // Used by useLayoutEffect to guard focus restoration (AC-23):
        // only restore if the user was navigating by keyboard inside the list,
        // never if they clicked elsewhere (mouse-user protection).
        onFocus={
          closable
            ? () => {
                lastFocusWasInListRef.current = true
              }
            : undefined
        }
        onBlur={
          closable
            ? (e) => {
                // Clear the guard only when focus truly leaves the tablist.
                // relatedTarget is the element receiving focus; when it is inside
                // this element, the blur is an internal transfer — keep the guard set.
                const next = e.relatedTarget
                if (!(next instanceof Node) || !e.currentTarget.contains(next)) {
                  lastFocusWasInListRef.current = false
                }
              }
            : undefined
        }
      >
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeEnabledId
          const isDisabled = tab.disabled === true
          const isTabStop = index === tabStopIndex

          // closable=false (default): render exactly the 002-contract tab button
          // with no wrapper div and no ✕ node — byte-identical DOM output (AC-11).
          // GUARDRAIL 1 (Risk-1): only this button enters buttonRefs.
          // GUARDRAIL 3 (Risk-1): onKeyDown uses index-based engine, not a DOM selector.
          if (!closable) {
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
                  if (isDisabled) return
                  onChange(tab.id)
                }}
                onKeyDown={(e) => handleKeyDown(e, index, tab.id)}
                ref={(el) => {
                  if (el !== null) {
                    buttonRefs.current.set(tab.id, el)
                  } else {
                    buttonRefs.current.delete(tab.id)
                  }
                }}
              >
                {/* Optional method chip — rendered only when method is defined (AC-9, AC-10).
                    aria-hidden: the chip is a decorative visual affordance; the label
                    span carries the full accessible text (Fix E — prevents double-announce
                    on URL-only tabs where deriveLabel already includes the method). */}
                {tab.method !== undefined && (
                  <span aria-hidden="true" className={methodChipClassName(tab.method)}>
                    {tab.method}
                  </span>
                )}

                {/* Label text — rendered as a JSX text node (React escapes it). */}
                <span className="tabs__tab-label">{tab.label}</span>

                {/* Optional badge — rendered only when badge is not undefined (AC-3 reuse). */}
                {tab.badge !== undefined && <span className="tabs__badge">{tab.badge}</span>}
              </button>
            )
          }

          // closable=true: wrap the tab button with a presentational div that
          // groups it with the sibling dirty-dot or close button.
          // The wrapper carries no ARIA role.
          // AC-12: the close button / dirty-dot is tabIndex={-1} — exactly one
          // roving stop per tab.
          return (
            <div
              key={tab.id}
              className={cx('tabs__tab-wrapper', isActive && 'tabs__tab-wrapper--active')}
            >
              {/* role="tab" button — same structure as the closable=false branch. */}
              <button
                role="tab"
                aria-selected={isActive}
                disabled={isDisabled}
                aria-disabled={isDisabled || undefined}
                // AC-12: this is the ONLY tabIndex={0} stop per tab — dirty-dot /
                // close button are both excluded from roving focus (AC-3).
                tabIndex={isTabStop ? 0 : -1}
                className={cx(
                  'tabs__tab',
                  isActive && 'tabs__tab--active',
                  isDisabled && 'tabs__tab--disabled'
                )}
                onClick={() => {
                  if (isDisabled) return
                  onChange(tab.id)
                }}
                onKeyDown={(e) => handleKeyDown(e, index, tab.id)}
                ref={(el) => {
                  // GUARDRAIL 1 (Risk-1): only role="tab" buttons enter buttonRefs.
                  // The dirty-dot span and close button are NEVER passed here.
                  if (el !== null) {
                    buttonRefs.current.set(tab.id, el)
                  } else {
                    buttonRefs.current.delete(tab.id)
                  }
                }}
              >
                {/* Optional method chip — rendered only when method is defined (AC-9).
                    aria-hidden: decorative visual affordance only (Fix E — same
                    rationale as the closable=false branch above). */}
                {tab.method !== undefined && (
                  <span aria-hidden="true" className={methodChipClassName(tab.method)}>
                    {tab.method}
                  </span>
                )}

                <span className="tabs__tab-label">{tab.label}</span>
                {tab.badge !== undefined && <span className="tabs__badge">{tab.badge}</span>}
              </button>

              {/* Dirty-XOR-close: exactly one of these renders per tab (AC-12).
                  GUARDRAIL 1: neither enters buttonRefs.
                  GUARDRAIL 2: neither carries role="tab".
                  The dirty span has no tabIndex (non-focusable) — AC-3 preserved.
                  The close button is tabIndex={-1} — not a roving stop (AC-12). */}
              {tab.dirty === true ? (
                /* Dirty state: non-focusable dot; clicking still signals close
                   so the store can apply its own save-then-close policy. */
                <span
                  className="tabs__tab-dirty"
                  onClick={(e) => {
                    e.stopPropagation()
                    onClose?.(tab.id)
                  }}
                />
              ) : (
                /* Clean state: close button with Icon SVG (AC-13). */
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label={`Close ${tab.label}`}
                  className="tabs__tab-close"
                  onClick={(e) => {
                    // stopPropagation prevents the click from bubbling up and
                    // accidentally triggering the tab button's onClick (AC-22).
                    e.stopPropagation()
                    onClose?.(tab.id)
                  }}
                >
                  <Icon name="x" size={11} />
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Right-aligned actions slot — outside the tablist element (AC-8). */}
      {actions !== undefined && <div className="tabs__actions">{actions}</div>}
    </div>
  )
}
