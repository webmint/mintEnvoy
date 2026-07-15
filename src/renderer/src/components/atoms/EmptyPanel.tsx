import './EmptyPanel.css'
import type { JSX } from 'react'

/**
 * EmptyPanel — shared placeholder atom for panels that are not yet available.
 *
 * Renders a muted "Panel not yet available" paragraph. Used by organisms
 * (BodyEditor, RequestSubTabs) for deferred-mode slots so the text and
 * styling live in one place (§3.6 DRY). No props — the text is fixed.
 */
export function EmptyPanel(): JSX.Element {
  return <p className="empty-panel">Panel not yet available</p>
}
