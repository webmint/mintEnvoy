/**
 * Icon — inline SVG icon atom.
 *
 * Renders a project-owned icon from the mintenvoy icon set as an accessible,
 * inline SVG element. Icons are purely decorative by default (aria-hidden) and
 * become meaningful when a `label` prop is provided, at which point the element
 * carries role="img" + aria-label so screen readers can announce it.
 *
 * Usage:
 *   // Decorative (hidden from assistive technology):
 *   <Icon name="send" size={20} />
 *
 *   // Meaningful / standalone (announced by screen readers):
 *   <Icon name="send" label="Send request" />
 *
 *   // With a spin modifier (loading state):
 *   <Icon name="cog" className="icon--spin" />
 *
 * @module Icon
 */
import './Icon.css'

import { cx } from '@renderer/lib/cx'
import { resolveIcon } from '@renderer/lib/icons-glue'
import type { IconName } from '@renderer/components/atoms/icons'

/** Props accepted by the Icon component. */
export interface IconProps {
  /**
   * The name of the icon to render, constrained to the project icon set.
   * Unknown names (e.g. when cast from an unvalidated string in tests) render
   * the fallback diamond placeholder — they never throw.
   */
  name: IconName

  /**
   * Square dimension of the rendered SVG in pixels.
   * Applied to the svg width and height attributes (not inline style).
   * @default 16
   */
  size?: number

  /**
   * Additional CSS class names to merge onto the svg element.
   * Use "icon--spin" for a continuously rotating variant.
   */
  className?: string

  /**
   * Accessible label for the icon.
   * When provided, the svg renders with role="img" and aria-label equal to
   * this value, making the icon meaningful to assistive technology.
   * Omit (or leave undefined) for decorative icons — they will be
   * aria-hidden="true" so screen readers skip them.
   */
  label?: string

  /**
   * Optional SVG title for tooltip / title semantics.
   * Rendered as a real JSX child (React-escaped) when provided, so the value
   * is safe for caller-supplied strings — it is NOT concatenated into raw HTML.
   * Prefer `label` for screen-reader announcements; use `title` only when a
   * native SVG tooltip is also desired.
   */
  title?: string
}

/**
 * Inline SVG icon component.
 *
 * Renders a 16×16 stroke-based SVG from the project icon set. Size is
 * controlled via the `size` prop, which maps to the svg width/height
 * attributes — no inline `style` is ever written. Visual styling (layout,
 * flex behaviour, animation) lives in Icon.css using semantic class names
 * bound to design tokens.
 *
 * Security: the `title` prop is rendered as a JSX child so React escapes it.
 * Only the static geometry markup from the project icon registry is injected
 * via dangerouslySetInnerHTML (into a <g> wrapper) — never caller-supplied text.
 *
 * @param props - See {@link IconProps} for the full prop reference.
 */
export function Icon({ name, size = 16, className, label, title }: IconProps): React.JSX.Element {
  const { markup } = resolveIcon(name)

  // Belt-and-suspenders guard: markup is always a string per resolveIcon's
  // contract, but we verify at runtime to satisfy the task requirement (AC-13).
  const safeMarkup = typeof markup === 'string' ? markup : ''

  const isAccessible = label !== undefined && label !== ''

  // Build the class string: always includes the semantic "icon" base class.
  const classNames = cx('icon', className)

  // Static SVG attributes shared by both accessible and decorative variants.
  const svgBaseAttrs = {
    viewBox: '0 0 16 16',
    width: size,
    height: size,
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className: classNames
  }

  // Accessibility attributes — mutually exclusive: role+aria-label (meaningful)
  // vs aria-hidden (decorative).
  const a11yAttrs = isAccessible
    ? ({ role: 'img', 'aria-label': label } as const)
    : ({ 'aria-hidden': 'true' } as const)

  return (
    <svg {...svgBaseAttrs} {...a11yAttrs}>
      {title !== undefined && title !== '' ? <title>{title}</title> : null}
      <g dangerouslySetInnerHTML={{ __html: safeMarkup }} />
    </svg>
  )
}

export default Icon
