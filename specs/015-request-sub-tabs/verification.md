# Feature Verification — 015-request-sub-tabs — 2026-07-07

**Feature**: specs/015-request-sub-tabs
**Date**: 2026-07-07
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | `src/renderer/src/components/organisms/RequestSubTabs.tsx` confirmed by shell `test -f`. |
| AC-2 | PASS (code) | `RequestSubTabs.css` exists; uses `var(--border-faint)`, `var(--text-muted)`, `var(--text)`, `var(--accent)`, `var(--bg-active)`, `var(--accent-soft)` — all present in `src/renderer/styles/tokens.css` both `:root` and `[data-theme='dark']`. |
| AC-3 | PASS (code) | `grep -E 'react-tabs\|@radix-ui/react-tabs' package.json` returned 0 matches. |
| AC-4 | PASS (code) | `activeSubTab: SubTabKey` added to `Tab` interface at `tabsStore.ts:67`. `TabBar.tsx` reads only `tab.spec.name/method/url` and `tab.dirty`; never references `activeSubTab`. The new field is purely additive. |
| AC-5 | PASS (code) | `Tabs.tsx:580-582` emits `id`/`aria-controls` only when `linkPanels` is truthy; when absent/false the button is byte-identical to the selection-only contract. `RequestSubTabs.tsx:249` passes `linkPanels` opt-in. `Tabs.ct.tsx` has a `TabsLinkPanelsFixture` test for the on-path and asserts NO `aria-controls` on the off-path. |
| AC-6 | PASS (code) | `Tabs.tsx:475-521` handles `ArrowRight/Left/Home/End` via `handleKeyDown`, calls `onChange` with automatic activation. Click path: `onClick → onChange`. `RequestSubTabs.ct.tsx` CT tests (lines 92-177) cover all four keys in a real Chromium browser. |
| AC-7 | PASS (code) | `RequestSubTabs.tsx:204` is the sole write site: `setActiveSubTab(activeTabId, k as SubTabKey)` called from `handleSubTabChange`. The `setActiveSubTab` action in `tabsStore.ts:330-338` is the only mutation path. No other code in the component calls `tabsStore.setState` for `activeSubTab`. |
| AC-8 | PASS (code) | `Tab.activeSubTab` is a per-tab field (tabsStore.ts:67). `setActiveSubTab` action (tabsStore.ts:335) maps tabs and only updates the matching id, leaving all other tabs unchanged. `RequestSubTabs.ct.tsx:281-324` (A→B→A CT) and `tabsStore.test.ts:684-708` cover per-tab isolation and round-trip preservation. |
| AC-9 | PASS (code) | `RequestSubTabs.tsx:259-302` renders all 6 panels unconditionally via `VALID_KEYS.map`. Visibility toggled by `hidden={key !== activeSubTab}` (line 276). `useLayoutEffect` (lines 207-232) restores `scrollTop` and refocuses last-focused element on re-show. `RequestSubTabs.ct.tsx:183-267` covers focus+value+scrollTop preservation in Chromium. |
| AC-10 | PASS (code) | `RequestSubTabs.tsx:85-108` subscribes to the store reactively; both a click (`handleSubTabChange`) and a direct `tabsStore.getState().setActiveSubTab(...)` write trigger the same re-render path. `RequestSubTabs.test.tsx:489-541` directly asserts identical panel visibility for both paths. |
| AC-11 | PASS (code) | `App.tsx:31-34`: `<RequestSubTabs params={<KVTable field="params" />} headers={<KVTable field="headers" />} />`. `App.test.tsx:55-101` confirms KVTable renders in the correct panels and that a params badge updates reactively when a KVTable row is added. |
| AC-12 | PASS (code) | `RequestSubTabs.tsx:241`: `const emptyState = <p className="request-sub-tabs__empty">Panel not yet available</p>`. Auth/Body/Tests/Code always use `emptyState`; Params/Headers use `prop ?? emptyState`. CSS: `RequestSubTabs.css:179` applies `color: var(--text-muted)`. `RequestSubTabs.test.tsx:221-252` asserts the single shared text appears in all four unbuilt panels. |
| AC-13 | PASS (code) | `RequestSubTabs.tsx:134-140` builds descriptors from `VALID_KEYS.map` without any `disabled` field. Tabs.tsx only marks a tab disabled when `tab.disabled === true`. `RequestSubTabs.test.tsx:643-655` asserts no tab has `aria-disabled` or the `disabled` attribute. |
| AC-14 | PASS (code) | `RequestSubTabs.tsx:270-282`: `role="tabpanel"`, `id={\`panel-${key}\`}`, `aria-labelledby={\`tab-${key}\`}`, `aria-selected={key === activeSubTab}`. Tab buttons get `id={\`tab-${key}\`}` and `aria-controls={\`panel-${key}\`}` via `linkPanels`. `RequestSubTabs.test.tsx:156-199` and `RequestSubTabs.ct.tsx:771-813` assert the full bidirectional linkage. |
| AC-15 | PASS (code) | `RequestSubTabs.tsx:118-119`: `result.params = paramsLength > 99 ? '99+' : paramsLength`. Same logic for headers (line 122-124). `RequestSubTabs.test.tsx:292-310` tests 100 rows → '99+'; lines 311-329 tests exactly 99 rows → '99' (not '99+'). |
| AC-16 | PASS (code) | `RequestSubTabs.tsx:93-94`: `rawSubTab !== undefined && VALID_KEYS.includes(rawSubTab) ? rawSubTab : 'params'` — any value absent from `VALID_KEYS` falls back to `'params'`. `tabsStore.test.ts:725-738` confirms `setActiveSubTab` no-ops on invalid key. `RequestSubTabs.test.tsx:547-572` seeds a garbage `activeSubTab` and asserts `panel-params` becomes visible. |
| AC-17 | PASS (code) | `RequestSubTabs.tsx:108`: `const hasActiveTab = tabsStore((s) => s.tabs.some((t) => t.id === s.activeTabId))`. `lines 236-238`: `if (!hasActiveTab) return <div className="request-sub-tabs request-sub-tabs--no-active" />`. `RequestSubTabs.test.tsx:578-602` tests the empty-tabs scenario — no throw + no tablist rendered. |
| AC-18 | PASS (code) | `App.tsx:29-36`: `<RequestBar />` appears before `<RequestSubTabs .../>` inside the Fragment. `App.test.tsx:24-41` asserts `requestBar.compareDocumentPosition(requestSubTabs) & DOCUMENT_POSITION_FOLLOWING > 0`, confirming DOM order. |
| AC-26 | PASS (code) | `RequestSubTabs.tsx:99-105`: three independent per-field selectors (`paramsLength`, `headersLength`, `authType`) return primitives — Zustand value-compares them so only a count/type change triggers re-render. `RequestSubTabs.test.tsx:442-482` asserts both params and headers badges update reactively via `updateActiveSpec` without any sub-tab switch. |
| AC-27 | PASS (code) | `RequestSubTabs.css` implements every §6 value from `design/styles.css:877-925`: `height:36px`, `border-bottom: 1px solid var(--border-faint)`, `padding: 0 16px`, `overflow: visible`, tab `font-size:12.5px / font-weight:500 / color:var(--text-muted)`, active `color:var(--text) / box-shadow:none / background:transparent`, `::after {height:1.5px; bottom:-1px; background:var(--accent)}`, badge `font-size:10px / border-radius:999px / padding:1px 6px / font-weight:600`, active badge `background:var(--accent-soft) / color:var(--accent)`. `RequestSubTabs.ct.tsx:413-765` asserts each resolved `getComputedStyle` value under both light and dark themes against hardcoded token-resolved rgb() values. |
| AC-19 | PASS (code) | `RequestSubTabs.tsx:65-83`: JSDoc on the component export. `tabsStore.ts:27-31`: JSDoc on `SubTabKey`. `tabsStore.ts:133-142`: JSDoc on `setActiveSubTab` action documenting no-op contracts and VALID_KEYS guard. |
| AC-20 | PASS (code) | `npm run typecheck:web` (`tsc --noEmit -p tsconfig.web.json`) completed with no errors and no diagnostic output. |
| AC-21 | PASS (code) | `npm run lint` returned "ESLint: No issues found". |
| AC-22 | PASS (code) | Grep for `style={{` in `RequestSubTabs.tsx` returned one match at line 33, confined to JSDoc comment text `* - No inline \`style={{...}}\`` (documentation of the rule, not executable code). No inline styles in executable JSX. |
| AC-23 | PASS (code) | Grep for `import.*electron\\|import.*node:` in `RequestSubTabs.tsx` returned 0 matches. Imports are: `./RequestSubTabs.css`, `react`, `@renderer/lib/tabsStore`, `@renderer/components/molecules/Tabs`. |
| AC-24 | PASS (code) | Grep for `updateActiveSpec` in `RequestSubTabs.tsx` returned two matches at lines 17 and 30, both in JSDoc comments documenting the constraint. Zero calls in executable code. `RequestSubTabs.tsx` has no `updateActiveSpec` invocation. |
| AC-25 | PASS (code) | Grep for `AuthPanel\\|BodyEditor\\|TestsPanel\\|CodePanel` in `RequestSubTabs.tsx` returned one match at line 31, a JSDoc comment listing the prohibited imports. No such import exists in the executable import section (lines 39-45). |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/015-request-sub-tabs/review.md
**Scope creep** _(advisory — does not block the verdict)_: 3 changed file(s) outside the planned scope: src/renderer/src/__tests__/fixtures/requestSpec.ts, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx, src/renderer/src/components/organisms/__tests__/RequestSubTabs.stories.tsx
**Leftover artifacts** _(advisory — does not block the verdict)_: 70 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

0 confirmed | 0 contested | 1 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 3 scope-creep file(s), 70 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
