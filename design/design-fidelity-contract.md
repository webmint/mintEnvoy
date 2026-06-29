# MintEnvoy — Design-Fidelity Contract

> **Source of truth:** `design/styles.css` (Claude Design export, 34 tokens / 273 rules), read directly — NOT reconstructed. These are the reference's *resolved* values. The export app does not run (it is an export, not a project); it does not need to — every value lives in `styles.css`.
>
> **How to use:** feed these numbers into `/specify` AC-13 as explicit computed-style targets, and into CT `getComputedStyle` assertions. **Copy the VALUES, never the CODE.** `var(--token)` references mean: assert *resolves-to-token* (e.g. `assertResolvesToToken(el,'borderColor','--border')`), not a literal hex. `color-mix(...)` values are token-derived — assert at token level, not literal rgb.
>
> **Selector mapping is the one thing to get right:** the left column is YOUR component element; the middle is the reference selector whose values it MUST match. Drift enters when an element is mapped to the wrong reference selector — verify the mapping, don't just transcribe values.

---

## 1 · Design tokens (`:root`)

| Token | Value |
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
| `--text-muted` | `#71717a` |
| `--text-faint` | `#a1a1aa` |
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

---

## 2 · Request bar

Reference container `.reqbar`. The method trigger is `.method-select` (bordered box, mono 700). Action buttons share `.btn` base; Save/Share add `.btn-ghost`, Send adds `.btn-primary`. The `⌘↵` keycap is `.kbd`.

| element | reference selector | key resolved values |
|---|---|---|
| Bar container | `.reqbar` | `display: flex`<br>`padding: 12px 16px`<br>`gap: 8px`<br>`border-bottom: 1px solid var(--border-faint)` |
| Method trigger | `.method-select` | `display: flex`<br>`padding: 7px 10px 7px 12px`<br>`gap: 6px`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius)`<br>`background: var(--bg-elev)`<br>`font-family: var(--font-mono)`<br>`font-size: 11.5px`<br>`font-weight: 700`<br>`letter-spacing: 0.04em`<br>`min-width: 88px` |
| Method label (in trigger) | `.method-select .method` | `font-size: 11.5px`<br>`flex: 1` |
| Method text base | `.method` | `font-family: var(--font-mono)`<br>`font-size: 10px`<br>`font-weight: 700`<br>`letter-spacing: 0.04em`<br>`text-transform: uppercase`<br>`min-width: 38px` |
| URL field | `.url-bar` | `display: flex`<br>`height: 32px`<br>`padding: 0 12px`<br>`gap: 6px`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius)`<br>`background: var(--bg-elev)`<br>`font-family: var(--font-mono)`<br>`flex: 1`<br>`transition: border-color 0.1s` |
| URL input | `.url-bar input` | `flex: 1`<br>`font-size: 12.5px` |
| URL variable token | `.url-bar .url-var` | `color: var(--accent)` |
| Button base (all 3) | `.btn` | `display: inline-flex`<br>`height: 32px`<br>`padding: 0 14px`<br>`gap: 6px`<br>`border: 1px solid transparent`<br>`border-radius: var(--radius)`<br>`font-size: 12.5px`<br>`font-weight: 500`<br>`transition: all 0.1s` |
| Save / Share (ghost) | `.btn-ghost` | `color: var(--text-muted)`<br>`border-color: var(--border)`<br>`background: var(--bg-elev)` |
| Send (primary) | `.btn-primary` | `background: var(--accent)`<br>`color: #fff`<br>`font-weight: 600`<br>`box-shadow: 0 1px 0 rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.15)` |
| Keycap ⌘↵ | `.kbd` | `padding: 1px 5px`<br>`border: 1px solid var(--border)`<br>`border-radius: 3px`<br>`background: var(--bg-elev)`<br>`color: var(--text-faint)`<br>`font-family: var(--font-sans)`<br>`font-size: 11px`<br>`font-weight: 500`<br>`letter-spacing: 0.02em` |

## 3 · Send split-dropdown

The Send split button = `.btn-primary` with squared right corners + a `.split-toggle` chevron cell.

| element | reference selector | key resolved values |
|---|---|---|
| Send (left half) | `.send-split .btn-primary` | `border-top-right-radius: 0`<br>`border-bottom-right-radius: 0`<br>`padding-right: 18px` |
| Split toggle (chevron) | `.send-split .split-toggle` | `background: var(--accent)`<br>`color: #fff`<br>`width: 28px`<br>`border-top-right-radius: var(--radius)`<br>`border-left: 1px solid rgba(255, 255, 255, 0.18)` |
| Split toggle hover | `.send-split .split-toggle:hover` | `background: var(--accent-hover)` |

## 4 · Method colours (per verb)

`.method.<VERB>` sets the text colour to the method token. In chip context the token becomes the *background*; in soft context a 16% color-mix tint.

| element | reference selector | key resolved values |
|---|---|---|
| GET text | `.method.GET` | `color: var(--m-get)` |
| POST text | `.method.POST` | `color: var(--m-post)` |
| PUT text | `.method.PUT` | `color: var(--m-put)` |
| PATCH text | `.method.PATCH` | `color: var(--m-patch)` |
| DELETE text | `.method.DELETE` | `color: var(--m-delete)` |
| OPTIONS text | `.method.OPTIONS` | `color: var(--m-options)` |
| Chip GET (filled) | `[data-mstyle="chip"] .method.GET` | `background: var(--m-get)` |
| Chip base | `[data-mstyle="chip"] .method` | `font-size: 9.5px`<br>`padding: 0 5px`<br>`min-width: 42px`<br>`height: 17px`<br>`border-radius: 4px`<br>`color: #fff`<br>`box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14)` |
| Soft GET (tint) | `[data-mstyle="soft"] .method.GET` | `background: color-mix(in oklab, var(--m-get) 16%, transparent)`<br>`color: var(--m-get)` |

## 5 · Tab strip

**The tab width-cap target is explicit here:** `.tab { max-width: 220px }` + `.tab-label { ellipsis }`. The tab method chip uses `[data-mstyle="chip"]` (filled colour, white text) — NOT the bordered bar treatment.

| element | reference selector | key resolved values |
|---|---|---|
| Tab bar | `.tabbar` | `height: 36px`<br>`background: var(--bg-sunken)`<br>`border-bottom: 1px solid var(--border)` |
| Tab | `.tab` | `gap: 8px`<br>`padding: 0 10px 0 12px`<br>`max-width: 220px`<br>`font-size: 12.5px`<br>`color: var(--text-muted)`<br>`border-right: 1px solid var(--border)` |
| Tab label (B1) | `.tab .tab-label` | `white-space: nowrap`<br>`overflow: hidden`<br>`text-overflow: ellipsis`<br>`flex: 1` |
| Dirty dot | `.tab .tab-dirty` | `width: 7px`<br>`height: 7px`<br>`border-radius: 50%`<br>`background: var(--text-faint)` |
| Close button | `.tab .tab-close` | `width: 16px`<br>`height: 16px`<br>`border-radius: 3px`<br>`color: var(--text-faint)` |
| Close hover | `.tab .tab-close:hover` | `background: var(--bg-active)`<br>`color: var(--text)` |
| Rename input | `.tab .tab-rename` | `font-size: 12.5px`<br>`border: 1px solid var(--accent)`<br>`border-radius: 4px`<br>`box-shadow: 0 0 0 2px var(--accent-soft)`<br>`background: var(--bg-elev)` |
| New-tab (+) | `.tab-new` | `padding: 0 10px`<br>`color: var(--text-muted)` |

## 6 · Pane tabs (Params/Auth/Headers…)

| element | reference selector | key resolved values |
|---|---|---|
| Pane tab | `.pane-tab` | `height: 36px`<br>`gap: 6px`<br>`color: var(--text-muted)`<br>`font-size: 12.5px`<br>`font-weight: 500`<br>`margin-right: 14px` |
| Pane tab badge | `.pane-tab .badge` | `font-size: 10px`<br>`background: var(--bg-active)`<br>`color: var(--text-muted)`<br>`border-radius: 999px`<br>`padding: 1px 6px`<br>`font-weight: 600` |
| Active badge | `.pane-tab.active .badge` | `background: var(--accent-soft)`<br>`color: var(--accent)` |

## 7 · Key-Value editor

Grid columns `22px 1fr 1fr 1fr 24px`. Cells mono 12px. Row actions appear on hover.

| element | reference selector | key resolved values |
|---|---|---|
| Table | `.kv` | `width: 100%`<br>`font-size: 12.5px` |
| Header row | `.kv-header, .kv-row` | `display: grid`<br>`grid-template-columns: 22px 1fr 1fr 1fr 24px`<br>`align-items: center` |
| Header label | `.kv-header` | `font-size: 10.5px`<br>`text-transform: uppercase`<br>`letter-spacing: 0.04em`<br>`color: var(--text-faint)`<br>`font-weight: 600` |
| Row | `.kv-row` | `border-bottom: 1px solid var(--border-faint)`<br>`min-height: 32px`<br>`color: var(--text)` |
| Row hover | `.kv-row:hover` | `background: var(--bg-hover)` |
| Cell | `.kv-row .kv-cell` | `padding: 6px 10px`<br>`gap: 6px`<br>`font-family: var(--font-mono)`<br>`font-size: 12px` |
| Cell input | `.kv-row .kv-cell input` | `font-family: var(--font-mono)`<br>`font-size: 12px`<br>`background: transparent` |
| Var token | `.kv-row .kv-cell .var` | `color: var(--accent)` |
| Checkbox | `.kv-row input[type="checkbox"]` | `accent-color: var(--accent)`<br>`width: 12px`<br>`height: 12px` |
| Disabled row | `.kv-row.disabled` | `opacity: 0.55` |

## 8 · Body editor

| element | reference selector | key resolved values |
|---|---|---|
| Toolbar | `.body-toolbar` | `gap: 4px`<br>`padding: 8px 16px`<br>`border-bottom: 1px solid var(--border-faint)`<br>`font-size: 12.5px` |
| Body radio | `.body-radio` | `gap: 5px`<br>`padding: 4px 10px`<br>`color: var(--text-muted)`<br>`border-radius: var(--radius-sm)` |
| Radio active | `.body-radio.active` | `background: var(--bg-active)`<br>`color: var(--text)` |
| Radio dot | `.body-radio .dot` | `width: 8px`<br>`height: 8px`<br>`border-radius: 50%`<br>`border: 1.5px solid var(--text-faint)` |
| Code editor | `.code-editor` | `display: grid`<br>`grid-template-columns: 36px 1fr`<br>`font-family: var(--font-mono)`<br>`font-size: 12.5px`<br>`line-height: 1.65`<br>`padding: 12px 0` |
| Gutter | `.code-editor .gutter` | `text-align: right`<br>`color: var(--text-faint)`<br>`padding-right: 12px`<br>`font-size: 11.5px` |
| Lang pill | `.lang-pill` | `gap: 5px`<br>`padding: 3px 8px`<br>`background: var(--bg-sunken)`<br>`border: 1px solid var(--border)` |

## 9 · Auth panel

Grid `140px 1fr`, gap `14px 24px`. Inputs `.input-field` (32px, focus-within accent border).

| element | reference selector | key resolved values |
|---|---|---|
| Panel | `.auth-panel` | `padding: 16px 20px`<br>`display: grid`<br>`grid-template-columns: 140px 1fr`<br>`gap: 14px 24px`<br>`max-width: 700px`<br>`font-size: 12.5px` |
| Label | `.auth-panel .label` | `color: var(--text-muted)`<br>`padding-top: 8px`<br>`font-weight: 500` |
| Input field | `.auth-panel .input-field` | `height: 32px`<br>`padding: 0 10px`<br>`border: 1px solid var(--border)`<br>`background: var(--bg-elev)` |
| Input focus | `.auth-panel .input-field:focus-within` | `border-color: var(--accent)` |
| Help text | `.auth-help` | `font-size: 12px`<br>`color: var(--text-muted)`<br>`gap: 8px`<br>`padding: 10px 12px` |
| Help icon | `.auth-help svg` | `color: var(--accent)` |

## 10 · Snippet generator

Mono code, syntax tokens map to method/status colours. Copy button top-right.

| element | reference selector | key resolved values |
|---|---|---|
| Snippet bar | `.snippet-bar` | `gap: 4px`<br>`padding: 6px 10px`<br>`border-bottom: 1px solid var(--border-faint)`<br>`background: var(--bg-sunken)` |
| Bar button | `.snippet-bar button` | `padding: 4px 10px`<br>`border-radius: var(--radius-sm)`<br>`font-size: 11.5px`<br>`color: var(--text-muted)` |
| Bar button active | `.snippet-bar button.active` | `background: var(--bg-active)`<br>`color: var(--text)` |
| Code | `.snippet-code` | `font-family: var(--font-mono)`<br>`font-size: 12.5px`<br>`line-height: 1.65`<br>`padding: 16px 20px`<br>`white-space: pre` |
| Copy button | `.snippet-copy` | `top: 12px`<br>`right: 18px`<br>`gap: 6px` |

## 11 · Response area

Empty/loading/meta states + status chip + JSON syntax tokens (`.tk-*`).

| element | reference selector | key resolved values |
|---|---|---|
| Empty state | `.response-empty` | `display: grid`<br>`place-items: center`<br>`color: var(--text-muted)`<br>`padding: 40px` |
| Empty glyph | `.response-empty .glyph` | `width: 56px`<br>`height: 56px`<br>`border-radius: 14px`<br>`background: var(--bg-sunken)`<br>`border: 1px solid var(--border)` |
| Empty heading | `.response-empty h3` | `font-size: 14px`<br>`color: var(--text)` |
| Loading | `.response-loading` | `display: grid`<br>`place-items: center`<br>`padding: 40px` |
| Meta bar | `.response-meta` | `gap: 14px`<br>`padding: 0 16px`<br>`height: 32px`<br>`border-bottom: 1px solid var(--border-faint)` |
| Stat value | `.response-meta .stat-value` | `font-weight: 600`<br>`font-family: var(--font-mono)` |
| Status chip | `.status-chip` | `font-family: var(--font-mono)`<br>`font-weight: 700`<br>`font-size: 11.5px`<br>`gap: 6px` |
| Status chip OK | `.status-chip.ok` | `background: color-mix(in oklab, var(--status-2xx) 15%, transparent)`<br>`color: var(--status-2xx)` |
| JSON string | `.tk-str` | `color: #15803d` |
| JSON number | `.tk-num` | `color: #b45309` |
| JSON key | `.tk-key` | `color: #0369a1` |
| JSON var | `.tk-var` | `color: var(--accent)`<br>`font-weight: 600` |

## 12 · Sidebar

Tree rows, search, sub-tabs, env selector.

| element | reference selector | key resolved values |
|---|---|---|
| Sidebar | `.sidebar` | `border-right: 1px solid var(--border)`<br>`background: var(--bg-sunken)`<br>`display: flex` |
| Search | `.sb-search` | `gap: 7px`<br>`padding: 8px 12px`<br>`border-bottom: 1px solid var(--border)` |
| Sub-tabs | `.sb-tabs` | `gap: 2px`<br>`padding: 6px 6px 0`<br>`border-bottom: 1px solid var(--border)` |
| Sub-tab | `.sb-tab` | `gap: 5px`<br>`padding: 6px 9px`<br>`color: var(--text-muted)`<br>`border-radius: var(--radius-sm) var(--radius-sm) 0 0` |
| Sub-tab active | `.sb-tab.active` | `color: var(--text)`<br>`border-bottom-color: var(--accent)` |
| Tab count | `.sb-tab .count` | `font-size: 10.5px`<br>`color: var(--text-faint)`<br>`background: var(--bg-active)`<br>`border-radius: 999px`<br>`padding: 1px 5px`<br>`min-width: 18px` |
| Tree row | `.tree-row` | `gap: 6px`<br>`padding: 4px 12px`<br>`color: var(--text)` |
| Tree row hover | `.tree-row:hover` | `background: var(--bg-hover)` |
| Tree row selected | `.tree-row.selected` | `background: var(--bg-active)` |
| Row label | `.tree-row .row-label` | `flex: 1`<br>`white-space: nowrap`<br>`overflow: hidden`<br>`text-overflow: ellipsis` |
| Env selector | `.env-selector` | `gap: 6px`<br>`padding: 4px 8px 4px 10px`<br>`border-radius: var(--radius-sm)`<br>`color: var(--text)` |
| Env dot | `.env-selector .env-dot` | `width: 7px`<br>`height: 7px`<br>`border-radius: 50%`<br>`background: var(--accent)`<br>`box-shadow: 0 0 0 2px color-mix(in oklab, var(--accent) 25%, transparent)` |

## 13 · Status bar

| element | reference selector | key resolved values |
|---|---|---|
| Status bar | `.statusbar` | `height: 22px`<br>`padding: 0 12px`<br>`gap: 14px`<br>`border-top: 1px solid var(--border)` |
| Status dot | `.statusbar .dot` | `width: 6px`<br>`height: 6px`<br>`border-radius: 50%` |
| Item | `.statusbar .sb-item` | `gap: 5px` |

---

## 14 · Command palette (⌘K)

The top search bar is the trigger `.cmdk` (360px, sunken). The open overlay is `.cmdk-input` (search) + `.cmdk-list` of `.cmdk-item`s grouped by `.cmdk-group`, with `.cmdk-footer`.

| element | reference selector | key resolved values |
|---|---|---|
| Trigger bar | `.cmdk` | `display: flex`<br>`width: 360px`<br>`padding: 5px 10px 5px 10px`<br>`gap: 10px`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius)`<br>`background: var(--bg-sunken)`<br>`color: var(--text-muted)` |
| Trigger text | `.cmdk-text` | `flex: 1`<br>`font-size: 12.5px` |
| Open: search row | `.cmdk-input` | `gap: 12px`<br>`padding: 14px 18px`<br>`border-bottom: 1px solid var(--border)`<br>`color: var(--text-muted)` |
| Search input | `.cmdk-input input` | `flex: 1`<br>`font-size: 14px`<br>`color: var(--text)` |
| List | `.cmdk-list` | `max-height: 380px`<br>`overflow-y: auto`<br>`padding: 6px 6px 8px` |
| Group heading | `.cmdk-group` | `font-size: 10.5px`<br>`text-transform: uppercase`<br>`letter-spacing: 0.04em`<br>`color: var(--text-faint)`<br>`font-weight: 600`<br>`padding: 8px 10px 4px` |
| Item | `.cmdk-item` | `gap: 10px`<br>`padding: 8px 10px`<br>`border-radius: var(--radius-sm)`<br>`font-size: 13px`<br>`text-align: left` |
| Item hover | `.cmdk-item:hover` | `background: var(--bg-hover)` |
| Item meta | `.cmdk-item-meta` | `font-size: 11.5px`<br>`color: var(--text-faint)`<br>`white-space: nowrap` |
| Action icon | `.cmdk-action-icon` | `width: 22px`<br>`height: 22px`<br>`border-radius: 5px`<br>`background: var(--bg-sunken)`<br>`color: var(--text-muted)` |
| Empty state | `.cmdk-empty` | `text-align: center`<br>`padding: 30px 20px`<br>`color: var(--text-faint)`<br>`font-size: 12.5px` |
| Footer | `.cmdk-footer` | `gap: 14px`<br>`padding: 8px 16px`<br>`border-top: 1px solid var(--border)`<br>`background: var(--bg-sunken)`<br>`font-size: 11px`<br>`color: var(--text-muted)` |

## 15 · Modal (overlay container)

Generic modal shell + scrim (used by the environment manager and other dialogs). The modal's *content* uses the component sections above (e.g. env-selector in §12, key-value rows in §7).

| element | reference selector | key resolved values |
|---|---|---|
| Modal container | `.modal` | `background: var(--bg-elev)`<br>`border: 1px solid var(--border)`<br>`border-radius: var(--radius-lg)`<br>`box-shadow: var(--shadow-lg)`<br>`overflow: hidden`<br>`animation: modalIn 0.15s ease-out` |
| Scrim | `.modal-scrim` | `inset: 0`<br>`background: color-mix(in oklab, var(--bg-sunken) 60%, rgba(0, 0, 0, 0.4))`<br>`backdrop-filter: blur(6px)`<br>`z-index: 200`<br>`animation: scrimIn 0.12s ease-out` |

## How to consume this contract

For any UI surface being built, find its section above by **component name** (request bar, tab strip, key-value editor, auth panel, response area, sidebar, …). Each row gives the reference selector and its resolved values. Use those as explicit `getComputedStyle` AC targets. `var(--token)` ⇒ assert *resolves-to-token*; `color-mix(...)` ⇒ assert at token level, not literal rgb. **Copy the values, never the code.**

**This file is the MENU, not the per-feature spec.** It describes the *whole reference*, including elements a given feature intentionally omits or diverges from. Do **not** assert a whole section blindly — a feature may ship a simpler element than the reference, or none at all (e.g. a single Send button where the reference shows a split-dropdown; an icon-only action where the reference shows a labelled one). Each feature must carry its own thin **MATCH / DEVIATE disposition** — "this surface MATCHES section X, except element Y is DEVIATE/OUT because <product reason>". That disposition lives in the **feature's own scope/intake**, not here; this contract only supplies the resolved numbers the disposition then points at. Asserting reference values for elements the feature doesn't ship produces false failures.

> **Staleness:** this is a snapshot of `styles.css` as extracted. If the design is re-exported, re-run the extraction and diff against this file before trusting it — otherwise it silently rots.

> **Note — what static extraction cannot give:** contested cascade outcomes (which same-specificity rule wins, emergent inheritance) and computed `color-mix()` rgb. Those are rare in this clean token-CSS; resolve them with a one-shot `dev:audit` runtime read against the built app if a specific assertion proves contested. Everything above is direct from `styles.css`.