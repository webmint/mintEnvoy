/**
 * Project-owned icon set for mintenvoy.
 *
 * All icons target a 16×16 viewBox with 1.5px stroke, stroke="currentColor",
 * fill="none", stroke-linecap="round", and stroke-linejoin="round".
 * These are the stroke-based line-icon style (Lucide / Feather aesthetic).
 *
 * Source: extracted from design/mintenvoy.html (Claude Design export, icons.jsx section).
 * Each value is the raw inner SVG markup string — no component logic, no React imports.
 * The icon markup is intended to be rendered by the Icon component (task 003) via dangerouslySetInnerHTML.
 *
 * To add an icon: append a new key → inner-markup string entry to ICONS below.
 */
export const ICONS = {
  /** Right-pointing chevron (collapsed state, tree rows) */
  chevron: '<path d="M6 3.5l4 4.5-4 4.5"/>',

  /** Down-pointing chevron (open selects, accordions) */
  chevronDown: '<path d="M3.5 6l4.5 4 4.5-4"/>',

  /** Magnifying glass search icon */
  search: '<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L13.5 13.5"/>',

  /** Plus / add icon */
  plus: '<path d="M8 3v10"/><path d="M3 8h10"/>',

  /** Close / remove icon (×) */
  x: '<path d="M4 4l8 8"/><path d="M12 4l-8 8"/>',

  /** Horizontal ellipsis (more options) */
  more: '<circle cx="3.5" cy="8" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="8" r="1" fill="currentColor" stroke="none"/><circle cx="12.5" cy="8" r="1" fill="currentColor" stroke="none"/>',

  /** Closed folder */
  folder:
    '<path d="M2 5.5C2 4.67 2.67 4 3.5 4h2.38a1 1 0 0 1 .7.3l.71.71a1 1 0 0 0 .71.3H12.5c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5h-9C2.67 13.31 2 12.65 2 11.81V5.5z"/>',

  /** Open folder */
  folderOpen:
    '<path d="M2 5.5C2 4.67 2.67 4 3.5 4h2.38a1 1 0 0 1 .7.3l.71.71a1 1 0 0 0 .71.3H12.5c.83 0 1.5.67 1.5 1.5v.5H2V5.5zM2 6.5h12l-.95 5a1.5 1.5 0 0 1-1.48 1.31H3.43A1.5 1.5 0 0 1 1.95 11.5L2 6.5z"/>',

  /** Collection / document list icon */
  collection:
    '<rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/><path d="M5.5 5h5"/><path d="M5.5 8h5"/><path d="M5.5 11h3"/>',

  /** Stacked layers icon */
  layers:
    '<path d="M8 2l5.5 3L8 8 2.5 5 8 2z"/><path d="M2.5 8L8 11l5.5-3"/><path d="M2.5 11L8 14l5.5-3"/>',

  /** Clock / history icon */
  clock: '<circle cx="8" cy="8" r="5.5"/><path d="M8 5v3l2 1.5"/>',

  /** Globe / network icon */
  globe:
    '<circle cx="8" cy="8" r="5.5"/><path d="M2.5 8h11"/><path d="M8 2.5c1.7 2 2.5 4 2.5 5.5s-.8 3.5-2.5 5.5C6.3 11.5 5.5 9.5 5.5 8s.8-3.5 2.5-5.5z"/>',

  /** Send / submit icon */
  send: '<path d="M2.5 8L13.5 3 11 13 7.5 9 2.5 8z"/>',

  /** Lightning bolt icon */
  bolt: '<path d="M9 2L3 9h4l-1 5 6-7H8l1-5z"/>',

  /** Copy to clipboard icon */
  copy: '<rect x="5" y="5" width="8" height="8" rx="1.5"/><path d="M3 11V4a1 1 0 0 1 1-1h7"/>',

  /** Download icon */
  download: '<path d="M8 2v8"/><path d="M5 7l3 3 3-3"/><path d="M3 13h10"/>',

  /** Upload icon */
  upload: '<path d="M8 13V5"/><path d="M5 8l3-3 3 3"/><path d="M3 2h10"/>',

  /** Hyperlink icon */
  link: '<path d="M9 4.5l1.5-1.5a2.5 2.5 0 0 1 3.5 3.5L12.5 8"/><path d="M7 11.5L5.5 13a2.5 2.5 0 0 1-3.5-3.5L3.5 8"/><path d="M6 10l4-4"/>',

  /** Lock / auth icon */
  lock: '<rect x="3.5" y="7" width="9" height="6" rx="1.5"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"/>',

  /** Settings / gear icon */
  cog: '<circle cx="8" cy="8" r="2"/><path d="M8 1.5v1.7M8 12.8v1.7M3.4 3.4l1.2 1.2M11.4 11.4l1.2 1.2M1.5 8h1.7M12.8 8h1.7M3.4 12.6l1.2-1.2M11.4 4.6l1.2-1.2"/>',

  /** Notification bell icon */
  bell: '<path d="M4 11V7.5a4 4 0 0 1 8 0V11l1 1.5H3L4 11z"/><path d="M7 14a1 1 0 0 0 2 0"/>',

  /** Sun / light mode icon */
  sun: '<circle cx="8" cy="8" r="3"/><path d="M8 1.5v1.5M8 13v1.5M1.5 8h1.5M13 8h1.5M3.5 3.5l1 1M11.5 11.5l1 1M3.5 12.5l1-1M11.5 4.5l1-1"/>',

  /** Moon / dark mode icon */
  moon: '<path d="M13 9.5A5.5 5.5 0 1 1 6.5 3a4.5 4.5 0 0 0 6.5 6.5z"/>',

  /** Left panel layout icon */
  panel: '<rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/><path d="M6.5 2.5v11"/>',

  /** Right panel layout icon */
  panelRight: '<rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/><path d="M9.5 2.5v11"/>',

  /** Bottom panel layout icon */
  panelBottom: '<rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/><path d="M2.5 9.5h11"/>',

  /** Filter / funnel icon */
  filter: '<path d="M2.5 3.5h11l-4 5v4l-3 1V8.5l-4-5z"/>',

  /** Save / floppy disk icon */
  save: '<path d="M3 3h8l2 2v8H3V3z"/><path d="M5 3v3h6V3"/><rect x="5" y="9" width="6" height="4"/>',

  /** Share icon */
  share:
    '<circle cx="4" cy="8" r="1.5"/><circle cx="12" cy="4" r="1.5"/><circle cx="12" cy="12" r="1.5"/><path d="M5.5 7.2l5-2.4M5.5 8.8l5 2.4"/>',

  /** Star / favourite icon */
  star: '<path d="M8 2l1.7 3.6 3.8.5-2.8 2.7.7 3.9L8 10.9 4.6 12.7l.7-3.9L2.5 6.1l3.8-.5L8 2z"/>',

  /** Trash / delete icon */
  trash:
    '<path d="M3 4.5h10"/><path d="M5 4.5V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1.5"/><path d="M4.5 4.5l.7 8a1 1 0 0 0 1 .9h3.6a1 1 0 0 0 1-.9l.7-8"/>',

  /** Check / confirm icon */
  check: '<path d="M3 8.5l3 3 7-7"/>',

  /** Alert / warning triangle icon */
  alert:
    '<path d="M8 2.5l6 11H2l6-11z"/><path d="M8 6.5v3"/><circle cx="8" cy="11.5" r="0.5" fill="currentColor" stroke="none"/>',

  /** Info circle icon */
  info: '<circle cx="8" cy="8" r="5.5"/><path d="M8 7.5v3"/><circle cx="8" cy="5.5" r="0.5" fill="currentColor" stroke="none"/>',

  /** Code / angle-brackets icon */
  code: '<path d="M5 4L2 8l3 4"/><path d="M11 4l3 4-3 4"/><path d="M9.5 3L6.5 13"/>',

  /** Beaker / test tube icon */
  beaker:
    '<path d="M6 2v4L2.5 12a1 1 0 0 0 .9 1.5h9.2a1 1 0 0 0 .9-1.5L10 6V2"/><path d="M5 2h6"/><path d="M4.5 9.5h7"/>',

  /** Sidebar layout icon */
  sidebar: '<rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/><path d="M6 2.5v11"/>',

  /** Command / keyboard shortcut icon */
  command:
    '<path d="M5 5h6v6H5V5zM5 5V3.5A1.5 1.5 0 1 0 3.5 5H5zM5 11v1.5A1.5 1.5 0 1 1 3.5 11H5zM11 5V3.5A1.5 1.5 0 1 1 12.5 5H11zM11 11v1.5A1.5 1.5 0 1 0 12.5 11H11z"/>',

  /** Variable / template substitution icon */
  variable:
    '<path d="M4 3c-1.5 2-1.5 8 0 10"/><path d="M12 3c1.5 2 1.5 8 0 10"/><path d="M6 6.5l4 3M6 9.5l4-3"/>',

  /** Cloud icon */
  cloud: '<path d="M4 12a3 3 0 0 1-.5-6 4 4 0 0 1 7.7-1A3 3 0 0 1 12 12H4z"/>',

  /** Wi-Fi / connectivity icon */
  wifi: '<path d="M2 6.5a8 8 0 0 1 12 0"/><path d="M4 9a5 5 0 0 1 8 0"/><path d="M6 11.5a2 2 0 0 1 4 0"/><circle cx="8" cy="13.5" r="0.5" fill="currentColor" stroke="none"/>'
} as const

/**
 * Typed string-literal union of every valid icon name in the project icon set.
 * Use this type to constrain props that accept an icon name.
 *
 * @example
 *   function Icon({ name }: { name: IconName }) { ... }
 */
export type IconName = keyof typeof ICONS
