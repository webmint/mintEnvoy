import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'
import { TabBar } from '@renderer/components/organisms/TabBar'
import { Shell } from '@renderer/components/organisms/Shell'

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
      <Shell tabs={<TabBar />} />
      {/* ToastViewport portals to document.body and renders above all overlays
          via z-index: 2147483647 (Toast.css). Placed after children so it is the
          last sibling inside the ToastProvider context — consistent with the
          mount contract documented in Toast.tsx. */}
      <ToastViewport />
    </ToastProvider>
  )
}

export default App
