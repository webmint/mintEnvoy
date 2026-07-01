# MintEnvoy — Design-Fidelity Contract

> **Source of truth:** `design/styles.css` (Claude Design export), read directly — NOT reconstructed. These are the reference's _resolved_ values.
>
> **How to use:** feed these numbers into `/specify` AC-13 as explicit computed-style targets, and into CT `getComputedStyle` assertions. **Copy the VALUES, never the CODE.** `var(--token)` ⇒ assert _resolves-to-token_; `color-mix(...)` ⇒ assert at token level.
>
> **Last re-sync:** 2026-06-30 — `--text-muted` and `--text-faint` darkened in Claude Design for WCAG AA (bugs B6/B7).

---

## 1 · Design tokens (`:root`)

| Token             | Value                                                                              |
| ----------------- | ---------------------------------------------------------------------------------- |
| `--accent`        | `#10b981`                                                                          |
| `--accent-soft`   | `color-mix(in oklab, var(--accent) 14%, transparent)`                              |
| `--accent-hover`  | `color-mix(in oklab, var(--accent) 88%, black)`                                    |
| `--bg`            | `#fbfaf9`                                                                          |
| `--bg-sunken`     | `#f4f3f1`                                                                          |
| `--bg-elev`       | `#ffffff`                                                                          |
| `--bg-hover`      | `#f0efed`                                                                          |
| `--bg-active`     | `#e8e6e3`                                                                          |
| `--border`        | `#e8e6e3`                                                                          |
| `--border-strong` | `#d6d3d0`                                                                          |
| `--border-faint`  | `#f0efed`                                                                          |
| `--text`          | `#18181b`                                                                          |
| `--text-muted`    | `#6c6c75`                                                                          |
| `--text-faint`    | `#6e6e77`                                                                          |
| `--text-inverse`  | `#ffffff`                                                                          |
| `--radius-sm`     | `5px`                                                                              |
| `--radius`        | `7px`                                                                              |
| `--radius-md`     | `9px`                                                                              |
| `--radius-lg`     | `12px`                                                                             |
| `--shadow-sm`     | `0 1px 0 rgba(24, 24, 27, 0.04), 0 1px 2px rgba(24, 24, 27, 0.04)`                 |
| `--shadow-md`     | `0 4px 16px -4px rgba(24, 24, 27, 0.08), 0 2px 4px rgba(24, 24, 27, 0.04)`         |
| `--shadow-lg`     | `0 16px 32px -8px rgba(24, 24, 27, 0.12), 0 4px 12px rgba(24, 24, 27, 0.06)`       |
| `--font-sans`     | `-apple-system, BlinkMacSystemFont, "Inter", "SF Pro Text", system-ui, sans-serif` |
| `--font-mono`     | `"JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace`            |
| `--m-get`         | `#0ea5e9`                                                                          |
| `--m-post`        | `#22c55e`                                                                          |
| `--m-put`         | `#f59e0b`                                                                          |
| `--m-patch`       | `#a855f7`                                                                          |
| `--m-delete`      | `#ef4444`                                                                          |
| `--m-options`     | `#64748b`                                                                          |
| `--status-2xx`    | `#16a34a`                                                                          |
| `--status-3xx`    | `#2563eb`                                                                          |
| `--status-4xx`    | `#f59e0b`                                                                          |
| `--status-5xx`    | `#ef4444`                                                                          |

> **Token change log:** `--text-muted` `#71717a`→`#6c6c75` (4.69:1 on `--bg-sunken`); `--text-faint` `#a1a1aa`→`#6e6e77` (4.55:1 on `--bg-sunken`, 5.05:1 on `--bg-elev`). Both now pass WCAG AA. Re-exported from Claude Design 2026-06-30.

---

> **NOTE:** §2–§15 (component value tables: Request bar, Send split, Method colours, Tab strip, Pane tabs, KV editor, Body editor, Auth panel, Snippet, Response, Sidebar, Status bar, Command palette, Modal) + "How to consume" are unchanged from the canonical export in `/mnt/user-data/outputs/mintenvoy-design-fidelity-contract.md` — only the two token values above changed. Re-paste those sections here on next code-exec pass for a single in-vault source, OR keep the outputs file as canonical and this as the token-truth head.

related: [[_index]]
