/**
 * Dropdown — molecule component wrapping Radix DropdownMenu.
 *
 * Provides a controlled dropdown menu with:
 * - Keyboard navigation: Arrow keys, Home, End, typeahead (Radix — AC-2)
 * - Click-outside + Escape dismiss dispatching `onOpenChange(false)` (AC-4)
 * - Focus return to trigger on close (Radix FocusScope — AC-3)
 * - Edge-aware flip/shift positioning so the menu stays in the viewport (AC-5)
 * - Animations gated behind `@media (prefers-reduced-motion: reduce)` (AC-14)
 * - Escaped JSX text rendering for item labels — never dangerouslySetInnerHTML (CWE-79)
 * - No inline styles (AC-18)
 * - No Node/Electron imports (AC-19)
 * - Strictly typed, no `any` (§3.1)
 *
 * ## Usage — items array API
 *
 * ```tsx
 * import { Dropdown } from '@renderer/components/molecules/Dropdown'
 *
 * function Example(): React.JSX.Element {
 *   const [open, setOpen] = React.useState(false)
 *
 *   return (
 *     <Dropdown
 *       open={open}
 *       onOpenChange={setOpen}
 *       trigger={<button>Options</button>}
 *       items={[
 *         { id: 'copy', label: 'Copy', onSelect: () => navigator.clipboard.writeText('') },
 *         { id: 'delete', label: 'Delete', onSelect: () => doDelete(), icon: 'trash' },
 *         { id: 'disabled', label: 'Unavailable', onSelect: () => {}, disabled: true },
 *       ]}
 *     />
 *   )
 * }
 * ```
 *
 * ## Usage — children API
 *
 * ```tsx
 * <Dropdown open={open} onOpenChange={setOpen} trigger={<button>More</button>}>
 *   <DropdownItem onSelect={() => doA()}>Action A</DropdownItem>
 *   <DropdownSeparator />
 *   <DropdownItem onSelect={() => doB()} disabled>Action B</DropdownItem>
 * </Dropdown>
 * ```
 *
 * ## Edge-aware positioning
 *
 * Radix `DropdownMenu.Content` is configured with:
 *   - `avoidCollisions={true}` (default) — flips the preferred side when space is
 *     insufficient and shifts along the cross-axis to keep the menu in the viewport.
 *   - `collisionPadding={8}` — keeps an 8 px gap from every viewport edge.
 *   - `sideOffset={4}` — gap between the trigger and the menu edge.
 * No extra JS is required; Radix's floating-ui-based positioning handles it.
 *
 * ## Accessibility
 *
 * Radix DropdownMenu provides:
 *   - `role="menu"` on the content element
 *   - `role="menuitem"` on each item (plus `aria-disabled` for disabled items)
 *   - Keyboard navigation: Arrow keys, Home, End, typeahead character search
 *   - Escape to close, focus return to trigger
 *
 * ## Security
 *
 * `item.label` values are rendered as JSX text children (React text nodes).
 * React escapes all text children — arbitrary strings including HTML injection
 * payloads are rendered as literal text, never parsed as markup (CWE-79).
 * `dangerouslySetInnerHTML` is NEVER used.
 *
 * @module Dropdown
 */

import './Dropdown.css'

import { DropdownMenu } from 'radix-ui'
import { cx } from '@renderer/lib/cx'
import { Icon } from '@renderer/components/atoms/Icon'
import type { IconName } from '@renderer/components/atoms/icons'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * A single item in the items-array API.
 * All string values are rendered as JSX text nodes (escaped — CWE-79).
 */
export interface DropdownItemDescriptor {
  /** Unique key for this item — used as the React list key. */
  id: string

  /**
   * Visible label text.
   * Rendered as an escaped JSX text node — never treated as HTML.
   */
  label: string

  /**
   * Callback invoked when the user selects this item.
   * Radix passes the `Event`; callers that do not need it can ignore it.
   */
  onSelect: (event: Event) => void

  /** When true, the item is rendered but not interactive. */
  disabled?: boolean

  /**
   * Optional leading icon name from the project icon set.
   * Rendered via the `Icon` atom with `aria-hidden` (decorative).
   */
  icon?: IconName
}

/** Public props for the Dropdown component. */
export interface DropdownProps {
  /**
   * Controls whether the menu is open.
   * The caller owns this state (controlled component — AC-11).
   */
  open: boolean

  /**
   * Called when Radix requests an open-state change (trigger click, Escape,
   * click-outside, or any internal Radix close trigger).
   * The new requested state is passed as the argument; the caller decides
   * whether to honor it. AC-11.
   */
  onOpenChange: (open: boolean) => void

  /**
   * The trigger element.  Rendered inside `DropdownMenu.Trigger asChild` so
   * Radix tracks it for:
   *   - Open/close toggling on click
   *   - Focus return on close (AC-3)
   * The trigger must be a single focusable element (button, anchor, etc.).
   */
  trigger: React.ReactNode

  /**
   * Items to render as `DropdownMenu.Item` entries (items-array API).
   *
   * **Precedence**: when both `items` and `children` are supplied, `items`
   * takes precedence and `children` is silently ignored.  Pass only one.
   * A DEV-mode console warning fires when both are present so callers notice
   * the conflict during development.
   */
  items?: DropdownItemDescriptor[]

  /**
   * Menu content as JSX children (children API).
   * Used when `items` is not provided.
   * Intended for `DropdownItem`, `DropdownSeparator`, and `DropdownLabel`
   * primitives exported below.
   *
   * **Precedence**: ignored when `items` is also supplied (see `items` above).
   */
  children?: React.ReactNode

  /**
   * The preferred side of the trigger to display the menu.
   * Radix will flip to the opposite side if there is insufficient space (AC-5).
   * @default "bottom"
   */
  side?: React.ComponentPropsWithoutRef<typeof DropdownMenu.Content>['side']

  /**
   * Alignment of the menu relative to the trigger along the main axis.
   * @default "start"
   */
  align?: React.ComponentPropsWithoutRef<typeof DropdownMenu.Content>['align']

  /**
   * Gap in pixels between the trigger edge and the menu (sideOffset).
   * @default 4
   */
  sideOffset?: number

  /**
   * Minimum distance in pixels from the viewport edges before collision
   * avoidance kicks in.
   * @default 8
   */
  collisionPadding?: number

  /** Additional CSS class name applied to `DropdownMenu.Content`. */
  className?: string
}

// ---------------------------------------------------------------------------
// Dropdown component
// ---------------------------------------------------------------------------

/**
 * Controlled dropdown menu built on Radix DropdownMenu primitives.
 *
 * Edge-aware positioning is handled by Radix via `avoidCollisions` (flip),
 * `collisionPadding` (viewport gap), and `sideOffset` (trigger gap) — no
 * JavaScript collision logic is needed in this component.
 *
 * @param props - See {@link DropdownProps}.
 */
export function Dropdown({
  open,
  onOpenChange,
  trigger,
  items,
  children,
  side = 'bottom',
  align = 'start',
  sideOffset = 4,
  collisionPadding = 8,
  className
}: DropdownProps): React.JSX.Element {
  // DEV-only: warn when both `items` and `children` are provided — items wins
  // but the children slot will be silently ignored, which is easy to miss.
  if (import.meta.env.DEV && items !== undefined && children !== undefined) {
    console.warn(
      '[Dropdown] Both `items` and `children` props were supplied. ' +
        '`items` takes precedence and `children` will be ignored. ' +
        'Use one or the other, not both.'
    )
  }

  return (
    <DropdownMenu.Root open={open} onOpenChange={onOpenChange}>
      {/* DropdownMenu.Trigger asChild — Radix tracks this element for:
          - click-to-toggle open state
          - focus return on close (AC-3)
          The trigger element is passed through as-is; Radix does not wrap it
          in an extra DOM node when asChild is set. */}
      <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>

      {/* DropdownMenu.Portal — renders content outside the current DOM tree
          (appended to document.body), ensuring correct stacking without
          z-index conflicts with ancestor elements. */}
      <DropdownMenu.Portal>
        {/* DropdownMenu.Content — the menu panel.
            Radix provides:
              - role="menu" + aria-orientation="vertical"
              - Arrow / Home / End / typeahead keyboard navigation (AC-2)
              - Escape → onOpenChange(false) (AC-4)
              - Click-outside → onOpenChange(false) (AC-4)
              - Focus return to trigger on close (AC-3)
              - avoidCollisions + collisionPadding → edge-aware flip/shift (AC-5) */}
        <DropdownMenu.Content
          className={cx('dropdown-content', className)}
          side={side}
          align={align}
          sideOffset={sideOffset}
          collisionPadding={collisionPadding}
          avoidCollisions={true}
        >
          {items !== undefined
            ? items.map((item) => (
                <DropdownMenu.Item
                  key={item.id}
                  className={cx(
                    'dropdown-item',
                    item.disabled === true ? 'dropdown-item--disabled' : undefined
                  )}
                  disabled={item.disabled}
                  onSelect={item.onSelect}
                >
                  {item.icon !== undefined && (
                    <span className="dropdown-item__icon">
                      {/* Icon is decorative here — the label text carries the meaning */}
                      <Icon name={item.icon} size={14} />
                    </span>
                  )}
                  {/* Rendered as a JSX text node — React escapes the string
                      so HTML injection payloads are safe (CWE-79). */}
                  <span className="dropdown-item__label">{item.label}</span>
                </DropdownMenu.Item>
              ))
            : children}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}

// ---------------------------------------------------------------------------
// Primitive re-exports — for the children API
// ---------------------------------------------------------------------------

/**
 * Props for DropdownItem.
 * Mirrors `DropdownMenu.Item` props with two additions:
 *   - `icon`: optional leading icon from the project icon set.
 *   - `className`: intentional escape-hatch for one-off style overrides.
 *     The component appends any supplied class alongside its own BEM classes,
 *     so callers can layer extra styles without forking the component.
 */
export type DropdownItemProps = Omit<
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Item>,
  'className'
> & {
  /** Optional leading icon from the project icon set. */
  icon?: IconName
  /**
   * Additional CSS class name appended to the item's own BEM classes.
   * Intentional escape-hatch — use sparingly for one-off overrides.
   */
  className?: string
}

/**
 * A single interactive menu item for use in the children API.
 *
 * Label text is passed as `children` and rendered as an escaped JSX text node
 * — never treated as HTML (CWE-79).
 *
 * @example
 * ```tsx
 * <Dropdown open={open} onOpenChange={setOpen} trigger={<button>Options</button>}>
 *   <DropdownItem onSelect={() => doAction()} icon="copy">Copy URL</DropdownItem>
 * </Dropdown>
 * ```
 */
export function DropdownItem({
  children,
  icon,
  disabled,
  className,
  ...rest
}: DropdownItemProps): React.JSX.Element {
  return (
    <DropdownMenu.Item
      className={cx(
        'dropdown-item',
        disabled === true ? 'dropdown-item--disabled' : undefined,
        className
      )}
      disabled={disabled}
      {...rest}
    >
      {icon !== undefined && (
        <span className="dropdown-item__icon">
          <Icon name={icon} size={14} />
        </span>
      )}
      <span className="dropdown-item__label">{children}</span>
    </DropdownMenu.Item>
  )
}

/**
 * A visual separator between groups of menu items.
 * Renders as `DropdownMenu.Separator` with a semantic class.
 */
export function DropdownSeparator(): React.JSX.Element {
  return <DropdownMenu.Separator className="dropdown-separator" />
}

/**
 * Props for DropdownLabel.
 * Mirrors `DropdownMenu.Label` props, excluding `className`.
 */
export type DropdownLabelProps = Omit<
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Label>,
  'className'
>

/**
 * A non-interactive group label inside the menu.
 *
 * @example
 * ```tsx
 * <Dropdown open={open} onOpenChange={setOpen} trigger={<button>More</button>}>
 *   <DropdownLabel>File actions</DropdownLabel>
 *   <DropdownItem onSelect={() => {}}>Save</DropdownItem>
 * </Dropdown>
 * ```
 */
export function DropdownLabel({ children, ...rest }: DropdownLabelProps): React.JSX.Element {
  return (
    <DropdownMenu.Label className="dropdown-label" {...rest}>
      {children}
    </DropdownMenu.Label>
  )
}
