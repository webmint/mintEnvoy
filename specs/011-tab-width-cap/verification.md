# Feature Verification — 011-tab-width-cap — 2026-06-30

**Feature**: specs/011-tab-width-cap
**Date**: 2026-06-30
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | `Tabs.css:421-433`: `.tabbar .tabs__tab-wrapper { ... max-width: 220px; }` — the compound-selector rule on the wrapper element sets the cap. |
| AC-2 | PASS (code) | `TabBar.css` (all 229 lines read): no `max-width` declaration exists anywhere in the file. The file header at lines 22-27 explicitly documents "This file carries no label-scoped truncation override." |
| AC-3 | PASS (code) | CSS rule uses `.tabbar .tabs__tab-wrapper { max-width: 220px }` (compound selector requiring `.tabbar` — `Tabs.css:421`). CT test `Tabs.ct.tsx:1329-1345` (`[011] bare .tabs__tab-wrapper: max-width computes to none`) mounts `TabsClosableFixture` (no `.tabbar` className) and asserts `maxWidth === 'none'`. |
| AC-4 | PASS (code) | Changed files contain only CSS and CT test files. No production `.tsx` files modified. All existing `.tabbar`-scoped rules for active styling (`::before`, `::after`, `.tabs__tab-wrapper--active` — `Tabs.css:440-488`), dirty dot (`.tabs__tab-dirty` — `Tabs.css:382-391`), method chip (`.method` — unmodified), and close button (`.tabs__tab-close` — `Tabs.css:300-352`) are untouched. The `max-width` addition to `.tabbar .tabs__tab-wrapper` at `Tabs.css:432` is the only substantive change to that rule block. |
| AC-5 | PASS (code) | No production source file (`.tsx`) appears in the changed-files list. `deriveLabel` is not touched. The CSS change (`max-width: 220px` on the wrapper) affects rendered geometry only; the text fed to the label is unchanged. The comment in `Tabs.css:429-432` confirms this: "the base `.tabs__tab-label` ellipsis triple fires once this wrapper reaches its limit." |
| AC-6 | PASS (code) | CT test `Tabs.ct.tsx:830-844` (`AC-6/AC-9 — .tabbar .tabs__tab-wrapper: max-width computed value is exactly 220px`) mounts `TabbarFidelityFixture`, reads `window.getComputedStyle(el).maxWidth`, and asserts `expect(maxWidth).toBe('220px')`. The underlying CSS rule is at `Tabs.css:432`. |
| AC-7 | PASS (code) | CT test `Tabs.ct.tsx:1143-1179` (`[011] AC-7 — long-title tab cell: width cap ≤ 221px and label text-overflow ellipsis under cap`) mounts `TabbarLongTitleFidelityFixture` (two ~65-char labels at 12.5px, estimated ~450px uncapped). It asserts `getBoundingClientRect().width <= 221` (border-box cap under fixture's scoped `.ct-borderbox-scope` reset) AND `getComputedStyle(el).textOverflow === 'ellipsis'`. Fixture defined at `Tabs.stories.tsx:580-633`. |
| AC-8 | PASS (code) | CT test `Tabs.ct.tsx:1181-1221` (`[011] AC-8 — tablist total width stays within cap-derived bound`) mounts `TabbarLongTitleFidelityFixture` (3 tabs, 2 long), reads `.tabbar .tabs__list` `getBoundingClientRect().width`, and asserts `width <= 662` (= 3 × 220 + 2). Actions row (`tabbar__new`, `tabbar__spacer`, `tabbar__overflow`) is included in the fixture at `Tabs.stories.tsx:617-629`. Fix C (`Tabs.css:507-512`: `.tabbar .tabs__list { flex: 0 0 auto }`) makes the tablist content-width so the actions row is anchored after it. |
| AC-9 | PASS (code) | CT test `Tabs.ct.tsx:838-844`: `expect(maxWidth).toBe('220px')` — exact string equality, not a numeric comparison. This is a Playwright component test (running in real Chromium via `@playwright/experimental-ct-react`). |
| AC-10 | PASS (code) | `Tabs.css:428-432`: the comment immediately preceding `max-width: 220px` reads: `/* design-fidelity-contract §5: max-width cap belongs on the tab cell, not the label. Cap relocated here from .tabbar .tabs__tab-label (TabBar.css). ... */` — explicitly cites §5. |
| AC-11 | PASS (code) | Changed files are CSS files and CT test/fixture files. `Tabs.stories.tsx` uses correctly typed React JSX, imports only existing typed symbols (`Tabs`, `TabDescriptor`, `selectNeighborId`, `Icon`), and all new fixtures follow the same patterns as existing ones. No TypeScript in CSS files. No new type-unsafe constructs introduced. |
| AC-12 | PASS (code) | CSS files contain no lintable JavaScript. `Tabs.stories.tsx` additions follow the same import and JSX patterns as existing passing fixtures. `Tabs.ct.tsx` adds two new `test.describe` blocks (`[011]` prefix) with standard Playwright CT APIs. No `console.log`, no bare `any`, no suppressed linting directives in the changed lines. |
| AC-13 | PASS (code) | Changes are limited to CSS files (`Tabs.css`, `TabBar.css`) and CT test/fixture files (`Tabs.ct.tsx`, `Tabs.stories.tsx`). No production imports altered, no new npm dependencies, no build-affecting module graph changes. CT test files are not included in the Vite/electron-vite production bundle. |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/011-tab-width-cap/review.md
**Scope creep**: none detected
**Leftover artifacts** _(advisory — does not block the verdict)_: 33 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

0 confirmed | 0 contested | 0 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 33 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
