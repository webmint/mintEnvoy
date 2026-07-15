import { memo } from 'react'
import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
import { BodyEditor } from '@renderer/components/organisms/BodyEditor'
import { KVTable } from '@renderer/components/organisms/KVTable'
import { RequestBar } from '@renderer/components/organisms/RequestBar'
import { RequestSubTabs } from '@renderer/components/organisms/RequestSubTabs'
import { TabBar } from '@renderer/components/organisms/TabBar'
import { Shell } from '@renderer/components/organisms/shell/Shell'
import type { Row } from '@renderer/lib/tabsStore'

/**
 * Memo-wrapped KVTable for the urlencoded render-prop slot.
 *
 * BodyEditor calls renderUrlencoded(rows, stableCallback) on every render, which
 * would cause KVTable to re-render even when rows and onRowsChange are reference-
 * stable (e.g. while the user types in raw mode). Wrapping in memo ensures KVTable
 * skips re-renders when its props are unchanged (stableCallback comes from
 * BodyEditor's useCallback(handleUrlencodedRowsChange)).
 */
const UrlencodedKVTable = memo(function UrlencodedKVTable({
  rows,
  onRowsChange
}: {
  rows: readonly Row[]
  onRowsChange: (r: Row[]) => void
}): React.JSX.Element {
  return <KVTable rows={rows} onRowsChange={onRowsChange} />
})

/**
 * Module-level render-prop for BodyEditor's urlencoded slot.
 *
 * Defined at module scope so the function reference is stable across all App
 * renders. BodyEditor is memo-wrapped and uses shallow-equality on its props;
 * a stable reference here means memo never sees a changed renderUrlencoded
 * prop and does not trigger an unnecessary BodyEditor re-render.
 */
const renderUrlencodedKVTable = (
  rows: readonly Row[],
  onRowsChange: (r: Row[]) => void
): React.JSX.Element => <UrlencodedKVTable rows={rows} onRowsChange={onRowsChange} />

function App(): React.JSX.Element {
  return (
    /**
     * App shell. ToastProvider wraps the entire app tree exactly once so that
     * any call to toastStore.getState().enqueue() from anywhere in the tree
     * renders into the single ToastViewport below.
     *
     * Portal z-order (all body-portalled by Radix defaults):
     *   modal-overlay  → z-index: 900  (Modal.css)
     *   modal-content  → z-index: 901  (Modal.css)
     *   dropdown       → Radix default (DismissableLayer stacks so Escape closes
     *                    the topmost overlay first)
     *   toast-viewport → z-index: 2147483647 (Toast.css) — always above all overlays
     *
     * No dedicated portal container is needed; body-portal + CSS z-index handles it.
     */
    <ToastProvider>
      <Shell
        tabs={<TabBar />}
        panes={{
          request: (
            <>
              <RequestBar />
              <RequestSubTabs
                params={<KVTable field="params" />}
                headers={<KVTable field="headers" />}
                body={
                  <BodyEditor
                    renderUrlencoded={renderUrlencodedKVTable}
                  />
                }
              />
            </>
          )
        }}
      />
      {/* ToastViewport portals to document.body and renders above all overlays
          via z-index: 2147483647 (Toast.css). Placed after children so it is the
          last sibling inside the ToastProvider context — consistent with the
          mount contract documented in Toast.tsx. */}
      <ToastViewport />
    </ToastProvider>
  )
}

export default App
