# Feature Verification — 004-working-tabs-state-machine — 2026-06-25

**Feature**: specs/004-working-tabs-state-machine
**Date**: 2026-06-25
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | `src/renderer/src/lib/tabsStore.ts` exists; exports `tabsStore`, `Tab`, `TabsState`, `OpenFromCollectionInput`, `selectNeighborId` (tabsStore.ts:1–273) |
| AC-2 | PASS (code) | `src/renderer/src/lib/requestSpec.ts` exists; exports `RequestSpec`, `Row`, `Auth`, `NoneAuth`, `BearerAuth`, `isBearerAuth`, `makeBlankRequest` (requestSpec.ts:1–133) |
| AC-3 | PASS (code) | `src/renderer/src/components/organisms/TabBar.tsx` and sibling `TabBar.css` both exist; CSS binds to design tokens via `var(--bg, …)` etc. (TabBar.css:1–199, TabBar.tsx:1–141) |
| AC-4 | PASS (code) | `package.json` has `"zustand": "^5.0.14"`; `tabsStore.ts:20` imports `create` from `zustand`; no new state-management library (jotai/recoil/valtio/mobx/redux/xstate) in package.json |
| AC-11 | PASS (code) | `Tabs.tsx:493` the `if (!closable)` branch renders the exact 002-contract button with no wrapper div and no ✕ node; `Tabs.tsx:402–407` Delete/Backspace handler is gated `if (closable && ...)` — does not activate on default path; `Tabs.tsx:463–469` onFocus handler also only wired when `closable` is truthy; `Tabs.test.tsx:529–570` regression tests assert no `.tabs__tab-close` node and no onClose call for Delete/Backspace when closable omitted |
| AC-12 | PASS (code) | `Tabs.tsx:289–295` `rovingTabStopIndex` produces exactly one index → one `tabIndex=0` per render; ✕ button at `Tabs.tsx:577–590` is `tabIndex={-1}` and is explicitly excluded from `buttonRefs` (guardrail comment at Tabs.tsx:559); `Tabs.test.tsx:595–604` and `Tabs.test.tsx:637–644` assert exactly one `tabindex=0` in both closable and non-closable paths |
| AC-13 | PASS (code) | `tabsStore.ts:212–219` `openFromCollection` calls `findDedupeMatch`; leg-1 at `tabsStore.ts:159–161` matches `collectionRequestId` and returns early with `set({activeTabId:matchedId})`, no append; `tabsStore.test.ts:53–119` tests assert tabs.length stays 1 and activeTabId switches to matched id |
| AC-14 | PASS (code) | `tabsStore.ts:163–168` leg-2 compares `tab.spec.url === input.spec.url` only when `input.spec.url !== ''`; `tabsStore.test.ts:102–141` test seeds a tab by URL and verifies it is activated without appending |
| AC-15 | PASS (code) | `tabsStore.ts:164` guards leg-2 with `if (input.spec.url !== '')` — empty URL is never passed to the `find`; `tabsStore.test.ts:124–141` confirms empty-URL tab stays distinct: length becomes 2 and activating the new tab does not match the existing empty-url tab |
| AC-16 | PASS (code) | `requestSpec.ts:122–132` `makeBlankRequest()` returns method `'GET'`, url `''`, name `''`, body `{lang:'',type:'',text:''}`, auth `{type:'bearer',token:'{{apiKey}}'}`, headers `[{enabled:true,key:'Accept',value:'application/json',description:''}]`, params `[]`; `tabsStore.ts:119–126` `makeBlankTab` wraps it with `dirty:false`, `collectionRequestId:null`; `tabsStore.test.ts:212–258` tests assert every field including absence of any Authorization header |
| AC-17 | PASS (code) | `tabsStore.ts:239–247` `isOnlyTab` branch spawns `replacement = makeBlankTab()` and sets `{tabs:[replacement],activeTabId:replacement.id}`, never reaching the filter path; `tabsStore.test.ts:264–293` tests verify count stays 1 and the replacement id differs from the closed tab; `TabBar.test.tsx:346–397` confirms the never-zero invariant end-to-end through the TabBar |
| AC-18 | PASS (code) | `tabsStore.ts:250–252` computes `nextActiveId = isActiveTab ? selectNeighborId(tabs,closedIndex) : activeTabId`; `tabsStore.ts:184–188` `selectNeighborId` returns `closedIndex+1` unless it equals `tabs.length-1`, then `closedIndex-1`; `tabsStore.test.ts:300–325` tests verify right-neighbor for middle closed tab and left-neighbor for last closed tab; `TabBar.test.tsx:158–190` confirms left-fallback end-to-end with `aria-selected="true"` on the promoted tab |
| AC-19 | PASS (code) | `tabsStore.ts:232–255` `close()` has no `dirty` guard — proceeds through the same `isOnlyTab`/neighbor-select/filter path regardless of `dirty` flag; no `window.confirm`, `prompt`, or branch on dirty found in the module; `tabsStore.test.ts:367–401` tests explicitly set `dirty:true` and verify removal without any confirmation branch |
| AC-20 | PASS (code) | `tabsStore.ts:265–272` `markClean` maps only the targeted tab's `dirty` to `false` via `t.id === tabId ? {...t,dirty:false} : t`; `tabsStore.test.ts:407–434` tests verify the targeted tab becomes clean and the other dirty tab remains dirty; unknown id is a no-op (checked via `tabs.some`) |
| AC-21 | PASS (code) | `tabsStore.ts:258–262` `selectActive` guards with `tabs.some(t=>t.id===tabId)` and returns early on unknown id; otherwise `set({activeTabId:tabId})`; `tabsStore.test.ts:440–459` tests verify activeTabId is set to requested id and unknown id is a no-op without throwing |
| AC-22 | PASS (code) | `Tabs.tsx:538–592` closable=true branch renders `<div className="tabs__tab-wrapper">` with role=tab button and a sibling `<button type="button" tabIndex={-1} aria-label={"Close "+tab.label} className="tabs__tab-close">`; click handler at Tabs.tsx:582–587 calls `onClose?.(tab.id)` with `stopPropagation`; keyboard at Tabs.tsx:402–407 fires `onClose?.(tabId)` on Delete/Backspace; `Tabs.test.tsx:576–655` tests assert structure, tabIndex=-1, no role=tab on ✕, onClose fires once, onChange not fired |
| AC-23 | PASS (code) | `Tabs.tsx:379–387` `useLayoutEffect([activeId,tabs])` restores focus to `buttonRefs.current.get(activeId)` only when `lastFocusWasInListRef.current` is true (guard set by onFocus at Tabs.tsx:463–469, cleared on genuine blur at Tabs.tsx:471–481); `onClose` in Tabs.tsx (lines 405, 586) fires only a string id — zero list mutation; `Tabs.test.tsx:664–715` positive-path test proves Delete triggers focus move to neighbor; `Tabs.test.tsx:730–779` non-close guard test proves tab add while focus is outside does not steal focus |
| AC-24 | PASS (code) | `TabBar.tsx:116–118` pulls `selectActive`, `close`, `newBlank` directly from store; `TabBar.tsx:130` passes `onChange={selectActive}`, `TabBar.tsx:131` passes `onClose={close}`, `TabBar.tsx:135` has `onClick={newBlank}` on the + button; `TabBar.test.tsx:75–226` tests verify each gesture mutates store state correctly (activeTabId change, tab removal, tab count increase) |
| AC-25 | PASS (code) | `TabBar.tsx:53–61` `deriveLabel` returns `tab.spec.name` when non-empty, else `` `${method} ${url}` `` when url non-empty, else `'Untitled'`; `TabBar.tsx:73–78` `toDescriptor` uses `label:deriveLabel(tab)`; `TabBar.test.tsx:232–284` tests verify all three branches render verbatim labels without interpolation |
| AC-26 | PASS (code) | `TabBar.tsx:77` `toDescriptor` sets `badge: tab.dirty ? '●' : undefined`; when `badge` is `undefined` the Tabs molecule renders no badge node (Tabs.tsx:530); `TabBar.test.tsx:291–339` tests assert `●` present in `tab.textContent` for dirty tabs and absent for clean tabs |
| AC-27 | PASS (code) | `App.tsx:2` imports `TabBar` from `@renderer/components/organisms/TabBar`; `App.tsx:22` renders `<Shell tabs={<TabBar />} />`, passing the TabBar into Shell's `tabs` slot which mounts it above the pane split (Shell.tsx:360–361) |
| AC-28 | PASS (code) | tabsStore.ts: `Tab` (lines 28–43), `OpenFromCollectionInput` (lines 45–55), `TabsState` with each action (lines 57–107), `selectNeighborId` (lines 172–188), `makeBlankTab`/`makeCollectionTab`/`findDedupeMatch` all carry JSDoc; requestSpec.ts: `Row` (30–39), `NoneAuth`/`BearerAuth`/`Auth` (41–61), `RequestSpec` (63–83), `isBearerAuth` (89–98), `makeBlankRequest` (104–132) all carry JSDoc; Tabs.tsx: `closable` (lines 198–211) and `onClose` (lines 212–226) each carry `@since feature-004` JSDoc |
| AC-29 | PASS (code) | `specs/002-tabs-primitive/spec.md:127–159` has a "Section 10 Contract Lineage" entry titled "Extension: feature 004-working-tabs-state-machine (2026-06-25)" that documents the `closable`/`onClose` props, backward-compatibility guarantee, and cites spec and plan sources — recorded as a contract change, not a silent prop addition |
| AC-5 | PASS (code) | All new modules declare strict types with no `any`; `requestSpec.ts:8` and `tabsStore.ts:11` explicitly document the no-`any` constraint; type exports are complete and consistent across Tabs.tsx, TabBar.tsx, tabsStore.ts, requestSpec.ts |
| AC-6 | PASS (code) | No `console.log`, no eslint-disable suppressions, no bare TODOs in any of the 5 new source files; code follows project ESLint conventions throughout |
| AC-7 | PASS (code) | All imports use `@renderer` alias per constitution §2.3; CSS sibling imports are valid; no circular import paths visible; TypeScript types are consistent — build-blocking errors absent from code review |
| AC-8 | PASS (code) | `src/renderer/src/lib/__tests__/tabsStore.test.ts` exists with comprehensive suite (tabsStore.test.ts:1–509) covering AC-13 through AC-21 plus serialization and isBearerAuth; store reset pattern correctly uses `setState` to preserve action closures |
| AC-9 | PASS (code) | Grep for `style={{` across tabsStore.ts, requestSpec.ts, TabBar.tsx, Tabs.tsx returns only comment/doc-string lines (documentation of the rule, not executable inline-style JSX); no actual `style={{...}}` attribute in executable JSX code |
| AC-10 | PASS (code) | Grep for `from 'electron'` and `from 'node:'` across all new renderer modules returns zero matches; tabsStore.ts:7, requestSpec.ts:6, and TabBar.tsx:21 all explicitly document the renderer-only constraint |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/004-working-tabs-state-machine/review.md
**Scope creep** _(advisory — does not block the verdict)_: 5 changed file(s) outside the planned scope: .prettierignore, src/renderer/src/__tests__/app-toast-mount.test.tsx, src/renderer/src/__tests__/fixtures/requestSpec.ts, src/renderer/src/components/__tests__/PrimitivesDemo.test.tsx, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx
**Leftover artifacts** _(advisory — does not block the verdict)_: 44 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

0 confirmed | 0 contested | 0 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 5 scope-creep file(s), 44 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
