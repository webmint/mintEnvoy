import { lazy, Suspense } from 'react'
import { ToastProvider, ToastViewport } from '@renderer/components/molecules/Toast'

// Dev-only: PrimitivesDemo is loaded via a dynamic import gated on
// import.meta.env.DEV. In production Vite replaces DEV with `false`, so the
// import() expression is statically unreachable — Rollup excludes both the
// PrimitivesDemo JS module AND its `import './PrimitivesDemo.css'` side-effect
// from the production bundle. Setting the variable to null also prevents the
// lazy() call from being evaluated at all in production.
const PrimitivesDemo = import.meta.env.DEV
  ? lazy(() =>
      import('@renderer/components/PrimitivesDemo').then((m) => ({ default: m.PrimitivesDemo }))
    )
  : null

function App(): React.JSX.Element {
  return (
    /**
     * App shell. The product UI is not built yet — this feature ships the
     * reusable UI-primitives layer (Icon / Dropdown / Modal / Toast) plus the
     * overlay substrate it needs. The shell mounts that substrate:
     *
     * ToastProvider wraps the entire app tree exactly once so that any call to
     * toastStore.getState().enqueue() from anywhere in the tree renders into the
     * single ToastViewport below.
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
      {/* Dev-only primitives gallery — PrimitivesDemo is a lazy component
          assigned only when import.meta.env.DEV is true. In production the
          variable is null so this block is never rendered and the dynamic
          import() — along with PrimitivesDemo.css — is excluded from the
          production bundle. PrimitivesDemo also guards itself internally
          (returns null when !import.meta.env.DEV) as belt-and-suspenders. */}
      {PrimitivesDemo && (
        <Suspense fallback={null}>
          <PrimitivesDemo />
        </Suspense>
      )}
      {/* ToastViewport portals to document.body and renders above all overlays
          via z-index: 2147483647 (Toast.css). Placed after children so it is the
          last sibling inside the ToastProvider context — consistent with the
          mount contract documented in Toast.tsx. */}
      <ToastViewport />
    </ToastProvider>
  )
}

export default App
