/**
 * Icon.test.tsx
 *
 * Interaction tests for the Icon atom component.
 * Covers:
 *   - AC-23: a known name renders an <svg> with the expected viewBox / stroke-width
 *   - AC-13: an unknown name renders the fallback diamond without throwing
 *   - a11y: aria-hidden by default; role=img + aria-label when label is provided
 *   - Security (XSS): title prop is React-escaped, not raw-injected into HTML
 *   - Boundary: label="" → decorative; title="" → no <title> element
 */
import { render, screen } from '@testing-library/react'
import { Icon } from '@renderer/components/atoms/Icon'
import type { IconName } from '@renderer/components/atoms/icons'

/** Fallback diamond path injected by resolveIcon for unknown names. */
const FALLBACK_DIAMOND_PATH = 'M8 2l6 6-6 6-6-6 6-6z'

describe('Icon', () => {
  describe('AC-23 — known icon name renders correct SVG attributes', () => {
    it('renders an <svg> element for a known icon name', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('sets viewBox="0 0 16 16" on the svg', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('viewBox', '0 0 16 16')
    })

    it('sets stroke-width="1.5" on the svg', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('stroke-width', '1.5')
    })

    it('defaults width and height to 16', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('width', '16')
      expect(svg).toHaveAttribute('height', '16')
    })

    it('respects a custom size prop via width/height attributes (not inline style)', () => {
      const { container } = render(<Icon name="send" size={24} />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('width', '24')
      expect(svg).toHaveAttribute('height', '24')
      // Must not apply inline style for sizing
      expect(svg?.getAttribute('style')).toBeNull()
    })

    it('sets fill="none" and stroke="currentColor"', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('fill', 'none')
      expect(svg).toHaveAttribute('stroke', 'currentColor')
    })

    it('applies the semantic "icon" class', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveClass('icon')
    })

    it('merges extra className alongside the base "icon" class', () => {
      const { container } = render(<Icon name="send" className="icon--spin" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveClass('icon')
      expect(svg).toHaveClass('icon--spin')
    })

    it('injects inner SVG markup (non-empty innerHTML)', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg?.innerHTML).not.toBe('')
    })
  })

  describe('AC-13 — unknown icon name renders fallback without throwing', () => {
    it('does not throw when given an unknown icon name', () => {
      // Cast is intentional for testing the unvalidated-input path.
      expect(() => render(<Icon name={'__unknown__' as IconName} />)).not.toThrow()
    })

    it('renders an <svg> (the fallback diamond) for an unknown icon name', () => {
      const { container } = render(<Icon name={'__unknown__' as IconName} />)
      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('fallback svg still has correct viewBox and stroke-width', () => {
      const { container } = render(<Icon name={'__no_such_icon__' as IconName} />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('viewBox', '0 0 16 16')
      expect(svg).toHaveAttribute('stroke-width', '1.5')
    })

    it('fallback renders the diamond path in its geometry markup', () => {
      const { container } = render(<Icon name={'__nope__' as IconName} />)
      // The geometry <g> must contain the known fallback diamond path data.
      const geometryGroup = container.querySelector('svg > g')
      expect(geometryGroup).toBeInTheDocument()
      expect(geometryGroup?.innerHTML).toContain(FALLBACK_DIAMOND_PATH)
    })
  })

  describe('a11y — aria attributes', () => {
    it('is aria-hidden by default (decorative icon)', () => {
      const { container } = render(<Icon name="send" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('aria-hidden', 'true')
      expect(svg).not.toHaveAttribute('role')
    })

    it('sets role="img" and aria-label when label prop is provided', () => {
      render(<Icon name="send" label="Send request" />)
      const svg = screen.getByRole('img', { name: 'Send request' })
      expect(svg).toBeInTheDocument()
      expect(svg).toHaveAttribute('aria-label', 'Send request')
    })

    it('does not set aria-hidden when label is provided', () => {
      const { container } = render(<Icon name="send" label="Send" />)
      const svg = container.querySelector('svg')
      expect(svg).not.toHaveAttribute('aria-hidden')
    })

    it('injects a <title> element inside the svg when title prop is provided', () => {
      const { container } = render(<Icon name="send" title="Send icon" />)
      const titleEl = container.querySelector('svg > title')
      expect(titleEl).toBeInTheDocument()
      expect(titleEl?.textContent).toBe('Send icon')
    })
  })

  describe('boundary — empty string props', () => {
    it('label="" is treated as decorative (aria-hidden, no role)', () => {
      const { container } = render(<Icon name="send" label="" />)
      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('aria-hidden', 'true')
      expect(svg).not.toHaveAttribute('role')
    })

    it('title="" does not inject a <title> element into the svg', () => {
      const { container } = render(<Icon name="send" title="" />)
      const titleEl = container.querySelector('svg > title')
      expect(titleEl).not.toBeInTheDocument()
    })
  })

  describe('security — XSS: title prop is React-escaped, not raw-injected', () => {
    it('renders the XSS payload as escaped text, not injected markup', () => {
      const xssPayload = '</title><img src="x" onerror="alert(1)">'
      const { container } = render(<Icon name="send" title={xssPayload} />)

      // No <img> element should exist — the payload must not have been parsed as markup.
      expect(container.querySelector('img')).not.toBeInTheDocument()

      // The <title> element's text content must be the literal payload string
      // (React-escaped), not interpreted HTML.
      const titleEl = container.querySelector('svg > title')
      expect(titleEl).toBeInTheDocument()
      expect(titleEl?.textContent).toBe(xssPayload)
    })
  })
})
