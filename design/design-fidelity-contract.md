# MintEnvoy — Design-Fidelity Contract

> **Source of truth:** `design/styles.css` (Claude Design export), read directly — NOT reconstructed. Resolved values.
> **How to use:** feed into `/specify` AC-13 as computed-style targets + CT `getComputedStyle` assertions. **Copy the VALUES, never the CODE.** `var(--token)` ⇒ assert *resolves-to-token*; `color-mix(...)` ⇒ token level.
> **This file is the MENU, not the per-feature spec.** It describes the whole reference; a feature may ship a simpler element or none. Each feature carries its own MATCH/DEVIATE disposition in its own scope. **And the reference can be under-specified — where it lacks a needed constraint (e.g. no nowrap on a user-typed name), DEVIATE deliberately, don't copy the gap.**
> **Last full re-sync:** 2026-07-01 from the newest export — WCAG token darkening (B6/B7, light+dark), workspace-pill truncation (B4). Now **per-theme** (light + dark).

---

## 1 · Design tokens — LIGHT (`:root`)

| Token | Light value |
|---|---|
| `--accent` | `#10b981` |
| `--accent-soft` | `color-mix(in oklab, var(--accent) 14%, transparent)` |
| `--accent-hover` | `color-mix(in oklab, var(--accent) 88%, black)` |
| `--bg` | `#fbfaf9` |
| `--bg-sunken` | `#f4f3f1` |
| `--bg-elev` | `#ffffff` |
| `--bg-hover` | `#f0efed` |
| `--bg-active` | `#e8e6e3` |
| `--border` | `#e8e6e3` |
| `--border-strong` | `#d6d3d0` |
| `--border-faint` | `#f0efed` |
| `--text` | `#18181b` |
| `--text-muted` | `#6c6c75` |
| `--text-faint` | `#6e6e77` |
| `--text-inverse` | `#ffffff` |
| `--radius-sm` | `5px` |
| `--radius` | `7px` |
| `--radius-md` | `9px` |
| `--radius-lg` | `12px` |
| `--shadow-sm` | `0 1px 0 rgba(24, 24, 27, 0.04), 0 1px 2px rgba(24, 24, 27, 0.04)` |
| `--shadow-md` | `0 4px 16px -4px rgba(24, 24, 27, 0.08), 0 2px 4px rgba(24, 24, 27, 0.04)` |
| `--shadow-lg` | `0 16px 32px -8px rgba(24, 24, 27, 0.12), 0 4px 12px rgba(24, 24, 27, 0.06)` |
| `--font-sans` | `-apple-system, BlinkMacSystemFont, "Inter", "SF Pro Text", system-ui, sans-serif` |
| `--font-mono` | `"JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace` |
| `--m-get` | `#0ea5e9` |
| `--m-post` | `#22c55e` |
| `--m-put` | `#f59e0b` |
| `--m-patch` | `#a855f7` |
| `--m-delete` | `#ef4444` |
| `--m-options` | `#64748b` |
| `--status-2xx` | `#16a34a` |
| `--status-3xx` | `#2563eb` |
| `--status-4xx` | `#f59e0b` |
| `--status-5xx` | `#ef4444` |

## 1b · Design tokens — DARK (`[data-theme="dark"]` overrides)

Dark overrides only the tokens below; everything else inherits from light. Method colours are theme-aware; status colours are theme-invariant (light values apply). Assert against the active theme.

| Token | Dark value |
|---|---|
| `--bg` | `#0c0c0d` |
| `--bg-sunken` | `#08080a` |
| `--bg-elev` | `#141416` |
| `--bg-hover` | `#1c1c1f` |
| `--bg-active` | `#25252a` |
| `--border` | `#25252a` |
| `--border-strong` | `#34343a` |
| `--border-faint` | `#1c1c1f` |
| `--text` | `#f4f4f5` |
| `--text-muted` | `#a1a1aa` |
| `--text-faint` | `#787881` |
| `--text-inverse` | `#0c0c0d` |
| `--shadow-sm` | `0 1px 0 rgba(0, 0, 0, 0.4)` |
| `--shadow-md` | `0 4px 16px -4px rgba(0, 0, 0, 0.4)` |
| `--shadow-lg` | `0 16px 32px -8px rgba(0, 0, 0, 0.5)` |
| `--m-get` | `#38bdf8` |
| `--m-post` | `#4ade80` |
| `--m-put` | `#fbbf24` |
| `--m-patch` | `#c084fc` |
| `--m-delete` | `#f87171` |
| `--m-options` | `#94a3b8` |

> **WCAG note:** light `--text-muted #6c6c75` (4.69:1 on sunken), `--text-faint #6e6e77` (4.55:1). Dark `--text-faint #787881` (4.57:1 on `#08080a`). All pass AA. Dark JSON syntax tokens also differ: `.tk-key #7dd3fc`, `.tk-str #86efac`, `.tk-num #fcd34d`, `.tk-bool #f0abfc`.

---

## 2 · Request bar

Method trigger `.method-select` (mono 700). Buttons share `.btn`; Save adds `.btn-ghost`, Send adds `.btn-primary`. Keycap `.kbd`. (Share button removed — local-only model.)

| element | reference selector | key resolved values |
|---|---|---|
| Bar container | `.reqbar` | `display: flex`<br>`padding: 12px 16px`<br>`gap: 8px`<br>`border-bottom: 1px solid var(--border-faint)`<br>`align-items: center` |
| Method trigger | `.method-select` | `display: flex`<br>`padding: 7px 10px 7px 12px`<br>`gap: 6px`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius)`<br>`background: var(--bg-elev)`<br>`font-family: var(--font-mono)`<br>`font-size: 11.5px`<br>`font-weight: 700`<br>`letter-spacing: 0.04em`<br>`min-width: 88px`<br>`align-items: center` |
| Method label | `.method-select .method` | `font-size: 11.5px`<br>`flex: 1` |
| Method text base | `.method` | `font-family: var(--font-mono)`<br>`font-size: 10px`<br>`font-weight: 700`<br>`letter-spacing: 0.04em`<br>`text-transform: uppercase`<br>`min-width: 38px` |
| URL field | `.url-bar` | `display: flex`<br>`height: 32px`<br>`padding: 0 12px`<br>`gap: 6px`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius)`<br>`background: var(--bg-elev)`<br>`font-family: var(--font-mono)`<br>`flex: 1`<br>`transition: border-color 0.1s`<br>`align-items: center` |
| URL input | `.url-bar input` | `flex: 1`<br>`font-size: 12.5px` |
| URL var token | `.url-bar .url-var` | `color: var(--accent)` |
| Button base | `.btn` | `display: inline-flex`<br>`height: 32px`<br>`padding: 0 14px`<br>`gap: 6px`<br>`border: 1px solid transparent`<br>`border-radius: var(--radius)`<br>`font-size: 12.5px`<br>`font-weight: 500`<br>`transition: all 0.1s`<br>`align-items: center` |
| Save (ghost) | `.btn-ghost` | `color: var(--text-muted)`<br>`border-color: var(--border)`<br>`background: var(--bg-elev)` |
| Send (primary) | `.btn-primary` | `background: var(--accent)`<br>`color: #fff`<br>`font-weight: 600`<br>`box-shadow: 0 1px 0 rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.15)` |
| Keycap ⌘↵ | `.kbd` | `padding: 1px 5px`<br>`border: 1px solid var(--border)`<br>`border-radius: 3px`<br>`background: var(--bg-elev)`<br>`color: var(--text-faint)`<br>`font-family: var(--font-sans)`<br>`font-size: 11px`<br>`font-weight: 500`<br>`letter-spacing: 0.02em` |

## 3 · Send split-dropdown

| element | reference selector | key resolved values |
|---|---|---|
| Send left | `.send-split .btn-primary` | `border-top-right-radius: 0`<br>`border-bottom-right-radius: 0`<br>`padding-right: 18px` |
| Split toggle | `.send-split .split-toggle` | `background: var(--accent)`<br>`color: #fff`<br>`width: 28px`<br>`border-top-right-radius: var(--radius)`<br>`border-left: 1px solid rgba(255, 255, 255, 0.18)` |
| Toggle hover | `.send-split .split-toggle:hover` | `background: var(--accent-hover)` |

## 4 · Method colours (per verb)

Chip context = token as background; soft = 16% tint.

| element | reference selector | key resolved values |
|---|---|---|
| GET | `.method.GET` | `color: var(--m-get)` |
| POST | `.method.POST` | `color: var(--m-post)` |
| PUT | `.method.PUT` | `color: var(--m-put)` |
| PATCH | `.method.PATCH` | `color: var(--m-patch)` |
| DELETE | `.method.DELETE` | `color: var(--m-delete)` |
| OPTIONS | `.method.OPTIONS` | `color: var(--m-options)` |
| Chip base | `[data-mstyle="chip"] .method` | `font-size: 9.5px`<br>`padding: 0 5px`<br>`min-width: 42px`<br>`height: 17px`<br>`border-radius: 4px`<br>`color: #fff`<br>`box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14)` |
| Chip GET | `[data-mstyle="chip"] .method.GET` | `background: var(--m-get)` |
| Soft GET | `[data-mstyle="soft"] .method.GET` | `background: color-mix(in oklab, var(--m-get) 16%, transparent)`<br>`color: var(--m-get)` |

## 5 · Tab strip

`.tab{max-width:220px}` + `.tab-label{ellipsis}`. Method chip uses `[data-mstyle="chip"]`.

| element | reference selector | key resolved values |
|---|---|---|
| Tab bar | `.tabbar` | `height: 36px`<br>`background: var(--bg-sunken)`<br>`border-bottom: 1px solid var(--border)` |
| Tab | `.tab` | `gap: 8px`<br>`padding: 0 10px 0 12px`<br>`max-width: 220px`<br>`font-size: 12.5px`<br>`color: var(--text-muted)`<br>`border-right: 1px solid var(--border)` |
| Tab label | `.tab .tab-label` | `white-space: nowrap`<br>`overflow: hidden`<br>`text-overflow: ellipsis`<br>`flex: 1` |
| Dirty dot | `.tab .tab-dirty` | `width: 7px`<br>`height: 7px`<br>`border-radius: 50%`<br>`background: var(--m-put)` |
| Close | `.tab .tab-close` | `width: 16px`<br>`height: 16px`<br>`border-radius: 3px`<br>`color: var(--text-faint)` |
| Close hover | `.tab .tab-close:hover` | `background: var(--bg-active)`<br>`color: var(--text)` |
| Rename | `.tab .tab-rename` | `font-size: 12.5px`<br>`border: 1px solid var(--accent)`<br>`border-radius: 4px`<br>`box-shadow: 0 0 0 2px var(--accent-soft)`<br>`background: var(--bg-elev)` |
| New (+) | `.tab-new` | `padding: 0 10px`<br>`color: var(--text-muted)` |

## 6 · Pane tabs

| element | reference selector | key resolved values |
|---|---|---|
| Pane tab | `.pane-tab` | `height: 36px`<br>`gap: 6px`<br>`color: var(--text-muted)`<br>`font-size: 12.5px`<br>`font-weight: 500`<br>`margin-right: 14px` |
| Badge | `.pane-tab .badge` | `font-size: 10px`<br>`background: var(--bg-active)`<br>`color: var(--text-muted)`<br>`border-radius: 999px`<br>`padding: 1px 6px`<br>`font-weight: 600` |
| Active badge | `.pane-tab.active .badge` | `background: var(--accent-soft)`<br>`color: var(--accent)` |

## 7 · Key-Value editor

Grid `22px 1fr 1fr 1fr 24px`, mono cells.

| element | reference selector | key resolved values |
|---|---|---|
| Table | `.kv` | `width: 100%`<br>`font-size: 12.5px` |
| Header/row grid | `.kv-header, .kv-row` | `display: grid`<br>`grid-template-columns: 22px 1fr 1fr 1fr 24px`<br>`align-items: center` |
| Header | `.kv-header` | `font-size: 10.5px`<br>`text-transform: uppercase`<br>`letter-spacing: 0.04em`<br>`color: var(--text-faint)`<br>`font-weight: 600` |
| Row | `.kv-row` | `border-bottom: 1px solid var(--border-faint)`<br>`min-height: 32px`<br>`color: var(--text)` |
| Row hover | `.kv-row:hover` | `background: var(--bg-hover)` |
| Cell | `.kv-row .kv-cell` | `padding: 6px 10px`<br>`gap: 6px`<br>`font-family: var(--font-mono)`<br>`font-size: 12px` |
| Cell input | `.kv-row .kv-cell input` | `font-family: var(--font-mono)`<br>`font-size: 12px`<br>`background: transparent` |
| Var | `.kv-row .kv-cell .var` | `color: var(--accent)` |
| Checkbox | `.kv-row input[type="checkbox"]` | `accent-color: var(--accent)`<br>`width: 12px`<br>`height: 12px` |
| Disabled | `.kv-row.disabled` | `opacity: 0.55` |

## 8 · Body editor

| element | reference selector | key resolved values |
|---|---|---|
| Toolbar | `.body-toolbar` | `gap: 4px`<br>`padding: 8px 16px`<br>`border-bottom: 1px solid var(--border-faint)`<br>`font-size: 12.5px` |
| Radio | `.body-radio` | `gap: 5px`<br>`padding: 4px 10px`<br>`color: var(--text-muted)`<br>`border-radius: var(--radius-sm)` |
| Radio active | `.body-radio.active` | `background: var(--bg-active)`<br>`color: var(--text)` |
| Radio dot | `.body-radio .dot` | `width: 8px`<br>`height: 8px`<br>`border-radius: 50%`<br>`border: 1.5px solid var(--text-faint)` |
| Code editor | `.code-editor` | `display: grid`<br>`grid-template-columns: 36px 1fr`<br>`font-family: var(--font-mono)`<br>`font-size: 12.5px`<br>`line-height: 1.65`<br>`padding: 12px 0` |
| Gutter | `.code-editor .gutter` | `text-align: right`<br>`color: var(--text-faint)`<br>`padding-right: 12px`<br>`font-size: 11.5px` |
| Lang pill | `.lang-pill` | `gap: 5px`<br>`padding: 3px 8px`<br>`background: var(--bg-sunken)`<br>`border: 1px solid var(--border)` |

## 9 · Auth panel

Grid `140px 1fr`, gap `14px 24px`.

| element | reference selector | key resolved values |
|---|---|---|
| Panel | `.auth-panel` | `padding: 16px 20px`<br>`display: grid`<br>`grid-template-columns: 140px 1fr`<br>`gap: 14px 24px`<br>`max-width: 700px`<br>`font-size: 12.5px` |
| Label | `.auth-panel .label` | `color: var(--text-muted)`<br>`padding-top: 8px`<br>`font-weight: 500` |
| Input | `.auth-panel .input-field` | `height: 32px`<br>`padding: 0 10px`<br>`border: 1px solid var(--border)`<br>`background: var(--bg-elev)` |
| Input focus | `.auth-panel .input-field:focus-within` | `border-color: var(--accent)` |
| Help | `.auth-help` | `font-size: 12px`<br>`color: var(--text-muted)`<br>`gap: 8px`<br>`padding: 10px 12px` |
| Help icon | `.auth-help svg` | `color: var(--accent)` |

## 10 · Snippet generator

| element | reference selector | key resolved values |
|---|---|---|
| Bar | `.snippet-bar` | `gap: 4px`<br>`padding: 6px 10px`<br>`border-bottom: 1px solid var(--border-faint)`<br>`background: var(--bg-sunken)` |
| Bar button | `.snippet-bar button` | `padding: 4px 10px`<br>`border-radius: var(--radius-sm)`<br>`font-size: 11.5px`<br>`color: var(--text-muted)` |
| Bar active | `.snippet-bar button.active` | `background: var(--bg-active)`<br>`color: var(--text)` |
| Code | `.snippet-code` | `font-family: var(--font-mono)`<br>`font-size: 12.5px`<br>`line-height: 1.65`<br>`padding: 16px 20px`<br>`white-space: pre` |
| Copy | `.snippet-copy` | `top: 12px`<br>`right: 18px`<br>`gap: 6px` |

## 11 · Response area

Dark JSON tokens differ (see §1b note).

| element | reference selector | key resolved values |
|---|---|---|
| Empty | `.response-empty` | `display: grid`<br>`place-items: center`<br>`color: var(--text-muted)`<br>`padding: 40px` |
| Empty glyph | `.response-empty .glyph` | `width: 56px`<br>`height: 56px`<br>`border-radius: 14px`<br>`background: var(--bg-sunken)`<br>`border: 1px solid var(--border)` |
| Empty heading | `.response-empty h3` | `font-size: 14px`<br>`color: var(--text)` |
| Loading | `.response-loading` | `display: grid`<br>`place-items: center`<br>`padding: 40px` |
| Meta bar | `.response-meta` | `gap: 14px`<br>`padding: 0 16px`<br>`height: 32px`<br>`border-bottom: 1px solid var(--border-faint)` |
| Stat value | `.response-meta .stat-value` | `font-weight: 600`<br>`font-family: var(--font-mono)` |
| Status chip | `.status-chip` | `font-family: var(--font-mono)`<br>`font-weight: 700`<br>`font-size: 11.5px`<br>`gap: 6px` |
| Status OK | `.status-chip.ok` | `background: color-mix(in oklab, var(--status-2xx) 15%, transparent)`<br>`color: var(--status-2xx)` |
| JSON string | `.tk-str` | `color: #15803d` |
| JSON number | `.tk-num` | `color: #b45309` |
| JSON key | `.tk-key` | `color: #0369a1` |
| JSON var | `.tk-var` | `color: var(--accent)`<br>`font-weight: 600` |

## 12 · Sidebar

Collections tree, search, sub-tabs, env selector. (No sharing UI — local-only.)

| element | reference selector | key resolved values |
|---|---|---|
| Sidebar | `.sidebar` | `border-right: 1px solid var(--border)`<br>`background: var(--bg-sunken)`<br>`display: flex` |
| Search | `.sb-search` | `gap: 7px`<br>`padding: 8px 12px`<br>`border-bottom: 1px solid var(--border)` |
| Sub-tabs | `.sb-tabs` | `gap: 2px`<br>`padding: 6px 6px 0`<br>`border-bottom: 1px solid var(--border)` |
| Sub-tab | `.sb-tab` | `gap: 5px`<br>`padding: 6px 9px`<br>`color: var(--text-muted)`<br>`border-radius: var(--radius-sm) var(--radius-sm) 0 0` |
| Sub-tab active | `.sb-tab.active` | `color: var(--text)`<br>`border-bottom-color: var(--accent)` |
| Count | `.sb-tab .count` | `font-size: 10.5px`<br>`color: var(--text-faint)`<br>`background: var(--bg-active)`<br>`border-radius: 999px`<br>`padding: 1px 5px`<br>`min-width: 18px` |
| Tree row | `.tree-row` | `gap: 6px`<br>`padding: 4px 12px`<br>`color: var(--text)` |
| Row hover | `.tree-row:hover` | `background: var(--bg-hover)` |
| Row selected | `.tree-row.selected` | `background: var(--bg-active)` |
| Row label | `.tree-row .row-label` | `flex: 1`<br>`white-space: nowrap`<br>`overflow: hidden`<br>`text-overflow: ellipsis` |
| Env selector | `.env-selector` | `gap: 6px`<br>`padding: 4px 8px 4px 10px`<br>`border-radius: var(--radius-sm)`<br>`color: var(--text)` |
| Env dot | `.env-selector .env-dot` | `width: 7px`<br>`height: 7px`<br>`border-radius: 50%`<br>`background: var(--accent)`<br>`box-shadow: 0 0 0 2px color-mix(in oklab, var(--accent) 25%, transparent)` |

## 13 · Status bar

| element | reference selector | key resolved values |
|---|---|---|
| Status bar | `.statusbar` | `height: 22px`<br>`padding: 0 12px`<br>`gap: 14px`<br>`border-top: 1px solid var(--border)` |
| Dot | `.statusbar .dot` | `width: 6px`<br>`height: 6px`<br>`border-radius: 50%` |
| Item | `.statusbar .sb-item` | `gap: 5px` |

## 14 · Command palette (⌘K)

Trigger `.cmdk`; open overlay `.cmdk-input`/`.cmdk-list`/`.cmdk-item`.

| element | reference selector | key resolved values |
|---|---|---|
| Trigger | `.cmdk` | `display: flex`<br>`width: 360px`<br>`padding: 5px 10px 5px 10px`<br>`gap: 10px`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius)`<br>`background: var(--bg-sunken)`<br>`color: var(--text-muted)` |
| Trigger text | `.cmdk-text` | `flex: 1`<br>`font-size: 12.5px` |
| Search row | `.cmdk-input` | `gap: 12px`<br>`padding: 14px 18px`<br>`border-bottom: 1px solid var(--border)`<br>`color: var(--text-muted)` |
| Search input | `.cmdk-input input` | `flex: 1`<br>`font-size: 14px`<br>`color: var(--text)` |
| List | `.cmdk-list` | `max-height: 380px`<br>`overflow-y: auto`<br>`padding: 6px 6px 8px` |
| Group | `.cmdk-group` | `font-size: 10.5px`<br>`text-transform: uppercase`<br>`letter-spacing: 0.04em`<br>`color: var(--text-faint)`<br>`font-weight: 600`<br>`padding: 8px 10px 4px` |
| Item | `.cmdk-item` | `gap: 10px`<br>`padding: 8px 10px`<br>`border-radius: var(--radius-sm)`<br>`font-size: 13px`<br>`text-align: left` |
| Item hover | `.cmdk-item:hover` | `background: var(--bg-hover)` |
| Item meta | `.cmdk-item-meta` | `font-size: 11.5px`<br>`color: var(--text-faint)`<br>`white-space: nowrap` |
| Action icon | `.cmdk-action-icon` | `width: 22px`<br>`height: 22px`<br>`border-radius: 5px`<br>`background: var(--bg-sunken)`<br>`color: var(--text-muted)` |
| Empty | `.cmdk-empty` | `text-align: center`<br>`padding: 30px 20px`<br>`color: var(--text-faint)`<br>`font-size: 12.5px` |
| Footer | `.cmdk-footer` | `gap: 14px`<br>`padding: 8px 16px`<br>`border-top: 1px solid var(--border)`<br>`background: var(--bg-sunken)`<br>`font-size: 11px`<br>`color: var(--text-muted)` |

## 15 · Modal

Shell + scrim; content uses other sections.

| element | reference selector | key resolved values |
|---|---|---|
| Container | `.modal` | `background: var(--bg-elev)`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius-lg)`<br>`box-shadow: var(--shadow-lg)`<br>`overflow: hidden`<br>`animation: modalIn 0.15s ease-out` |
| Scrim | `.modal-scrim` | `inset: 0`<br>`background: color-mix(in oklab, var(--bg-sunken) 60%, rgba(0, 0, 0, 0.4))`<br>`backdrop-filter: blur(6px)`<br>`z-index: 200`<br>`animation: scrimIn 0.12s ease-out` |

## 16 · Workspace switcher (top bar)

Switches the open local vault (local-only model). **The name truncates — reference now defends against long user-typed names (added 2026-07-01, was the B4 gap).** Truncate the NAME only; avatar + chevron stay (`flex-shrink:0`).

| element | reference selector | key resolved values |
|---|---|---|
| Pill | `.workspace-pill` | `display: flex`<br>`align-items: center`<br>`gap: 6px`<br>`padding: 4px 8px`<br>`border-radius: var(--radius-sm)`<br>`color: var(--text-muted)`<br>`font-weight: 500` |
| Pill hover | `.workspace-pill:hover` | `background: var(--bg-hover)`<br>`color: var(--text)` |
| Name (truncates) | `.workspace-pill .ws-name` | `max-width: 160px`<br>`white-space: nowrap`<br>`overflow: hidden`<br>`text-overflow: ellipsis` |
| Avatar | `.workspace-pill .avatar` | `width: 14px`<br>`height: 14px`<br>`flex-shrink: 0` |
| Chevron | `.workspace-pill > svg` | `flex-shrink: 0` |

---

## How to consume this contract

Find the surface by component name; use its resolved values as `getComputedStyle` AC targets. `var(--token)` ⇒ resolves-to-token (assert against the ACTIVE theme — light §1 or dark §1b). `color-mix(...)` ⇒ token level. **Copy the VALUES, never the CODE.**

Two limits: (1) **menu, not spec** — each feature needs its own MATCH/DEVIATE disposition; don't assert elements a feature doesn't ship. (2) **reference can be wrong** — where it omits a needed constraint (long user text without nowrap, etc.), DEVIATE on purpose. B1 (tab cap) and the original B4 (workspace name) are both this pattern; B4 is now folded INTO the reference (§16), so it's a plain MATCH again.

> **Staleness:** snapshot of `styles.css`. Re-run extraction + diff on any re-export. This file was regenerated 2026-07-01 from the newest export (light+dark tokens, workspace truncation).
