/**
 * tabsStore.test.ts
 *
 * Unit tests for the tabsStore zustand slice + the serialization contract of
 * requestSpec utilities (makeBlankRequest, isBearerAuth).
 *
 * AC coverage:
 *   AC-13 — openFromCollection leg-1 deduplication (collectionRequestId match)
 *   AC-14 — openFromCollection leg-2 deduplication (verbatim non-empty url match)
 *   AC-15 — empty url stays distinct (never matches leg 2)
 *   AC-16 — newBlank seeds a tab with canonical blank defaults
 *   AC-17 — close never-zero: last tab closes → fresh blank spawned
 *   AC-18 — close active → right neighbor activated; close active last → left neighbor
 *   AC-19 — dirty tabs close silently (no confirmation guard)
 *   AC-20 — markClean clears dirty flag; no-op on unknown id
 *   AC-21 — selectActive sets activeTabId; no-op on unknown id
 *   Risk-3 — RequestSpec round-trips through JSON.parse(JSON.stringify(...))
 */
import { tabsStore } from '@renderer/lib/tabsStore'
import { makeBlankRequest, isBearerAuth } from '@renderer/lib/requestSpec'
import { makeSpec, makeTab } from '@renderer/__tests__/fixtures/requestSpec'

// ---------------------------------------------------------------------------
// Store reset
// ---------------------------------------------------------------------------

/**
 * Reset the store to a predictable single-blank-tab state before each test.
 * We use setState to replace only the data fields; the action functions
 * created in the create() closure persist naturally (same pattern as toastStore
 * using clearAll() to drain items).
 *
 * We construct a fresh blank tab using makeBlankRequest() directly so the test
 * controls the id. We use a stable known id to make assertions easy.
 */
const INITIAL_ID = 'initial-tab-id'

function resetStore(): void {
  tabsStore.setState({
    tabs: [makeTab(INITIAL_ID)],
    activeTabId: INITIAL_ID
  })
}

beforeEach(() => {
  resetStore()
})

// ---------------------------------------------------------------------------
// openFromCollection — leg-1 dedupe (AC-13)
// ---------------------------------------------------------------------------

describe('openFromCollection — leg-1 dedupe (AC-13)', () => {
  it('activates the existing tab when collectionRequestId matches; does not append', () => {
    // Pre-condition: seed a tab with a known collectionRequestId
    tabsStore.setState({
      tabs: [
        makeTab(
          'tab-a',
          { url: 'https://api.example.com/users' },
          { collectionRequestId: 'coll-1' }
        )
      ],
      activeTabId: 'tab-a'
    })

    // Open with the same collectionRequestId
    tabsStore.getState().openFromCollection({
      collectionRequestId: 'coll-1',
      spec: makeSpec({ url: 'https://api.example.com/other' })
    })

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(1)
    expect(activeTabId).toBe('tab-a')
  })

  it('switches from a different active tab to the matched leg-1 tab', () => {
    tabsStore.setState({
      tabs: [
        makeTab('tab-active'),
        makeTab('tab-coll', { url: 'https://x.com' }, { collectionRequestId: 'coll-x' })
      ],
      activeTabId: 'tab-active'
    })

    tabsStore.getState().openFromCollection({
      collectionRequestId: 'coll-x',
      spec: makeSpec({ url: 'https://x.com' })
    })

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(2)
    expect(activeTabId).toBe('tab-coll')
  })
})

// ---------------------------------------------------------------------------
// openFromCollection — leg-2 dedupe (AC-14)
// ---------------------------------------------------------------------------

describe('openFromCollection — leg-2 dedupe (AC-14)', () => {
  it('activates an existing tab by verbatim non-empty url when no id match', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-url', { url: 'https://api.example.com/items' })],
      activeTabId: 'tab-url'
    })

    tabsStore.getState().openFromCollection({
      collectionRequestId: 'new-coll-id',
      spec: makeSpec({ url: 'https://api.example.com/items' })
    })

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(1)
    expect(activeTabId).toBe('tab-url')
  })
})

// ---------------------------------------------------------------------------
// empty url stays distinct (AC-15)
// ---------------------------------------------------------------------------

describe('empty url stays distinct (AC-15)', () => {
  it('does NOT match an existing empty-url tab via leg 2 → appends instead', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-empty-url', { url: '' })],
      activeTabId: 'tab-empty-url'
    })

    tabsStore.getState().openFromCollection({
      collectionRequestId: 'some-new-id',
      spec: makeSpec({ url: '' })
    })

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(2)
    // The NEW tab (not the pre-existing empty-url tab) should be active
    expect(activeTabId).not.toBe('tab-empty-url')
  })
})

// ---------------------------------------------------------------------------
// leg PRECEDENCE: leg 1 beats leg 2
// ---------------------------------------------------------------------------

describe('openFromCollection — leg precedence', () => {
  it('prefers leg-1 (id match) over leg-2 (url match) when both apply', () => {
    const SHARED_URL = 'https://shared.example.com/resource'

    tabsStore.setState({
      tabs: [
        makeTab(
          'tab-a-id-match',
          { url: 'https://different.example.com/resource' },
          { collectionRequestId: 'coll-target' }
        ),
        makeTab('tab-b-url-match', { url: SHARED_URL })
      ],
      activeTabId: 'tab-b-url-match'
    })

    tabsStore.getState().openFromCollection({
      collectionRequestId: 'coll-target',
      spec: makeSpec({ url: SHARED_URL })
    })

    // leg 1 wins — tab-a is activated, NOT tab-b
    expect(tabsStore.getState().activeTabId).toBe('tab-a-id-match')
  })
})

// ---------------------------------------------------------------------------
// miss appends + stores collectionRequestId
// ---------------------------------------------------------------------------

describe('openFromCollection — miss appends and stores collectionRequestId', () => {
  it('appends a new tab on miss and subsequent call with same id hits leg 1', () => {
    // Start from a blank tab with no collectionRequestId
    const { tabs: initialTabs } = tabsStore.getState()
    expect(initialTabs).toHaveLength(1)

    const input = {
      collectionRequestId: 'fresh-coll',
      spec: makeSpec({ url: 'https://fresh.example.com' })
    }

    // First call: miss → appends
    tabsStore.getState().openFromCollection(input)

    const { tabs: afterFirst, activeTabId: afterFirstActiveId } = tabsStore.getState()
    expect(afterFirst).toHaveLength(2)

    // The new tab carries the collectionRequestId
    const newTab = afterFirst.find((t) => t.id === afterFirstActiveId)
    expect(newTab).toBeDefined()
    expect(newTab!.collectionRequestId).toBe('fresh-coll')

    // Second call with same collectionRequestId: leg-1 hit → no append
    tabsStore.getState().openFromCollection(input)

    const { tabs: afterSecond, activeTabId: afterSecondActiveId } = tabsStore.getState()
    expect(afterSecond).toHaveLength(2)
    expect(afterSecondActiveId).toBe(afterFirstActiveId)
  })
})

// ---------------------------------------------------------------------------
// newBlank (AC-16)
// ---------------------------------------------------------------------------

describe('newBlank (AC-16)', () => {
  it('appends a tab with canonical blank defaults', () => {
    tabsStore.getState().newBlank()

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(2)

    const newTab = tabs.find((t) => t.id === activeTabId)
    expect(newTab).toBeDefined()

    const { spec } = newTab!
    expect(spec.method).toBe('GET')
    expect(spec.url).toBe('')
    expect(spec.name).toBe('')
    expect(spec.body).toEqual({ lang: '', type: '', text: '' })
    expect(spec.auth).toEqual({ type: 'bearer', token: '{{apiKey}}' })
    expect(spec.headers).toEqual([
      { enabled: true, key: 'Accept', value: 'application/json', description: '' }
    ])
    expect(spec.params).toEqual([])
  })

  it('does NOT mirror auth into headers (no Authorization row)', () => {
    tabsStore.getState().newBlank()

    const { tabs, activeTabId } = tabsStore.getState()
    const newTab = tabs.find((t) => t.id === activeTabId)!
    const authorizationRow = newTab.spec.headers.find(
      (h) => h.key.toLowerCase() === 'authorization'
    )
    expect(authorizationRow).toBeUndefined()
  })

  it('new tab starts with dirty: false', () => {
    tabsStore.getState().newBlank()
    const { tabs, activeTabId } = tabsStore.getState()
    const newTab = tabs.find((t) => t.id === activeTabId)!
    expect(newTab.dirty).toBe(false)
  })

  it('new tab has null collectionRequestId', () => {
    tabsStore.getState().newBlank()
    const { tabs, activeTabId } = tabsStore.getState()
    const newTab = tabs.find((t) => t.id === activeTabId)!
    expect(newTab.collectionRequestId).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// close — never-zero (AC-17)
// ---------------------------------------------------------------------------

describe('close — never-zero (AC-17)', () => {
  it('closing the last tab spawns a fresh blank; tabs.length stays 1', () => {
    const { tabs } = tabsStore.getState()
    expect(tabs).toHaveLength(1)
    const lastTabId = tabs[0].id

    tabsStore.getState().close(lastTabId)

    const { tabs: afterClose, activeTabId } = tabsStore.getState()
    expect(afterClose).toHaveLength(1)
    // activeTabId must point at the replacement tab, not the closed tab
    expect(activeTabId).not.toBe(lastTabId)
    expect(activeTabId).toBe(afterClose[0].id)
  })

  it('the replacement tab after closing the last is a fresh blank seed', () => {
    const { tabs } = tabsStore.getState()
    const lastTabId = tabs[0].id

    tabsStore.getState().close(lastTabId)

    const { tabs: afterClose, activeTabId } = tabsStore.getState()
    const replacement = afterClose.find((t) => t.id === activeTabId)!

    expect(replacement).toBeDefined()
    expect(replacement.spec.method).toBe('GET')
    expect(replacement.spec.url).toBe('')
    expect(replacement.dirty).toBe(false)
    expect(replacement.collectionRequestId).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// close — active tab right neighbor (AC-18)
// ---------------------------------------------------------------------------

describe('close — active tab → right neighbor (AC-18)', () => {
  it('closing the active non-last tab activates the right neighbor', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-1'), makeTab('tab-2'), makeTab('tab-3')],
      activeTabId: 'tab-2'
    })

    tabsStore.getState().close('tab-2')

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(2)
    expect(activeTabId).toBe('tab-3')
  })

  it('closing the active last tab activates the left neighbor', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-1'), makeTab('tab-2'), makeTab('tab-3')],
      activeTabId: 'tab-3'
    })

    tabsStore.getState().close('tab-3')

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(2)
    expect(activeTabId).toBe('tab-2')
  })
})

// ---------------------------------------------------------------------------
// close — non-active tab leaves activeTabId unchanged
// ---------------------------------------------------------------------------

describe('close — non-active tab', () => {
  it('closing a non-active tab leaves activeTabId unchanged', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-1'), makeTab('tab-2')],
      activeTabId: 'tab-2'
    })

    tabsStore.getState().close('tab-1')

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(1)
    expect(activeTabId).toBe('tab-2')
  })
})

// ---------------------------------------------------------------------------
// close — unknown id no-op
// ---------------------------------------------------------------------------

describe('close — unknown id no-op', () => {
  it('does not throw and leaves tabs + activeTabId unchanged for an unknown id', () => {
    const before = tabsStore.getState()

    expect(() => tabsStore.getState().close('does-not-exist')).not.toThrow()

    const after = tabsStore.getState()
    expect(after.tabs).toHaveLength(before.tabs.length)
    expect(after.activeTabId).toBe(before.activeTabId)
  })
})

// ---------------------------------------------------------------------------
// close — dirty tab closes silently (AC-19)
// ---------------------------------------------------------------------------

describe('close — dirty tab closes silently (AC-19)', () => {
  it('a dirty tab is removed without confirmation', () => {
    tabsStore.setState({
      tabs: [
        makeTab('tab-dirty', { url: 'https://example.com' }, { dirty: true }),
        makeTab('tab-clean')
      ],
      activeTabId: 'tab-dirty'
    })

    tabsStore.getState().close('tab-dirty')

    const { tabs } = tabsStore.getState()
    expect(tabs).toHaveLength(1)
    expect(tabs.find((t) => t.id === 'tab-dirty')).toBeUndefined()
  })

  it('closing a dirty NON-ACTIVE tab removes it silently and leaves activeTabId unchanged', () => {
    tabsStore.setState({
      tabs: [
        makeTab('tab-active'),
        makeTab('tab-dirty-bg', { url: 'https://example.com/bg' }, { dirty: true })
      ],
      activeTabId: 'tab-active'
    })

    tabsStore.getState().close('tab-dirty-bg')

    const { tabs, activeTabId } = tabsStore.getState()
    expect(tabs).toHaveLength(1)
    expect(tabs.find((t) => t.id === 'tab-dirty-bg')).toBeUndefined()
    // Active tab must not have changed — this isolates AC-19 from AC-18's neighbor mechanics
    expect(activeTabId).toBe('tab-active')
  })
})

// ---------------------------------------------------------------------------
// markClean (AC-20)
// ---------------------------------------------------------------------------

describe('markClean (AC-20)', () => {
  it('clears the dirty flag on the targeted tab', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-dirty', {}, { dirty: true }), makeTab('tab-other', {}, { dirty: true })],
      activeTabId: 'tab-dirty'
    })

    tabsStore.getState().markClean('tab-dirty')

    const { tabs } = tabsStore.getState()
    const cleaned = tabs.find((t) => t.id === 'tab-dirty')!
    const other = tabs.find((t) => t.id === 'tab-other')!

    expect(cleaned.dirty).toBe(false)
    // Other tabs are unchanged
    expect(other.dirty).toBe(true)
  })

  it('is a no-op for an unknown id (no throw, entire state unchanged)', () => {
    const beforeTabs = tabsStore.getState().tabs
    const beforeActiveId = tabsStore.getState().activeTabId
    expect(() => tabsStore.getState().markClean('no-such-tab')).not.toThrow()

    const { tabs: afterTabs, activeTabId: afterActiveId } = tabsStore.getState()
    expect(afterTabs).toEqual(beforeTabs)
    expect(afterActiveId).toBe(beforeActiveId)
  })
})

// ---------------------------------------------------------------------------
// selectActive (AC-21)
// ---------------------------------------------------------------------------

describe('selectActive (AC-21)', () => {
  it('sets activeTabId to the requested id when it exists', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-1'), makeTab('tab-2')],
      activeTabId: 'tab-1'
    })

    tabsStore.getState().selectActive('tab-2')
    expect(tabsStore.getState().activeTabId).toBe('tab-2')
  })

  it('is a no-op for an unknown id (does not throw, activeTabId unchanged)', () => {
    tabsStore.setState({
      tabs: [makeTab('tab-1')],
      activeTabId: 'tab-1'
    })

    expect(() => tabsStore.getState().selectActive('no-such-tab')).not.toThrow()
    expect(tabsStore.getState().activeTabId).toBe('tab-1')
  })
})

// ---------------------------------------------------------------------------
// Serialization contract — Risk-3 (Q-2)
// ---------------------------------------------------------------------------

describe('serialization contract (Risk-3 / Q-2)', () => {
  it('RequestSpec is JSON round-trip safe: parse(stringify(x)) deep-equals x', () => {
    const spec = makeBlankRequest()
    expect(JSON.parse(JSON.stringify(spec))).toEqual(spec)
  })
})

// ---------------------------------------------------------------------------
// isBearerAuth — both branches
// ---------------------------------------------------------------------------

describe('isBearerAuth', () => {
  it('returns true for a BearerAuth value', () => {
    expect(isBearerAuth({ type: 'bearer', token: 't' })).toBe(true)
  })

  it('returns false for a NoneAuth value', () => {
    expect(isBearerAuth({ type: 'none' })).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// makeBlankRequest — reference independence
// ---------------------------------------------------------------------------

describe('makeBlankRequest — reference independence', () => {
  it('two calls return distinct headers array references', () => {
    const a = makeBlankRequest()
    const b = makeBlankRequest()
    expect(a.headers).not.toBe(b.headers)
  })

  it('two calls return distinct params array references', () => {
    const a = makeBlankRequest()
    const b = makeBlankRequest()
    expect(a.params).not.toBe(b.params)
  })

  it('two calls return distinct auth object references', () => {
    const a = makeBlankRequest()
    const b = makeBlankRequest()
    expect(a.auth).not.toBe(b.auth)
  })
})
