---
concern: renderer
files: 39
last_indexed: 2026-06-22
package: .
source_stamp: b44087ca58806208
---


# renderer

## Purpose

React 19 renderer process — the user-facing UI. Houses the reusable UI-primitive library (Icon atom; Dropdown, Modal, Toast, and Tabs molecules — Dropdown/Modal/Toast wrap Radix UI, Tabs hand-rolls its WAI-ARIA engine), a module-level zustand toast queue, className-merge and safe icon-resolution helpers, design tokens as CSS variables, and a dev-only primitives gallery gated on import.meta.env.DEV. main.tsx mounts App into index.html; the layer carries no Node/Electron imports per the renderer-isolation rule.

## Structure

```text
src/renderer/
├── src
│   ├── __tests__
│   │   ├── app-toast-mount.test.tsx  # Test: App mounts toast provider + viewport
│   │   ├── setup.ts  # Vitest setup; jsdom + testing-library wiring
│   │   ├── smoke.ct.tsx  # Playwright CT smoke render
│   │   └── smoke.test.tsx  # Vitest smoke render test
│   ├── components
│   │   ├── __tests__
│   │   │   └── PrimitivesDemo.test.tsx  # Test: PrimitivesDemo renders all primitives
│   │   ├── atoms
│   │   │   ├── __tests__
│   │   │   │   ├── Icon.ct.tsx  # Playwright CT: Icon rendering
│   │   │   │   └── Icon.test.tsx  # Vitest: Icon a11y + variants
│   │   │   ├── Icon.css  # Icon atom styles incl. spin modifier
│   │   │   ├── Icon.tsx  # Inline SVG icon atom; aria-hidden unless labeled
│   │   │   └── icons.ts  # Project icon set; raw inner-SVG markup keyed by name
│   │   ├── molecules
│   │   │   ├── __tests__
│   │   │   │   ├── Dropdown.ct.tsx  # Playwright CT: Dropdown interaction
│   │   │   │   ├── Dropdown.stories.tsx  # Storybook stories for Dropdown
│   │   │   │   ├── Dropdown.test.tsx  # Vitest: Dropdown behavior + a11y
│   │   │   │   ├── Modal.ct.tsx  # Playwright CT: Modal focus trap
│   │   │   │   ├── Modal.stories.tsx  # Storybook stories for Modal
│   │   │   │   ├── Modal.test.tsx  # Vitest: Modal behavior + a11y
│   │   │   │   ├── Tabs.ct.tsx  # Playwright CT: Tabs keyboard/focus + axe a11y
│   │   │   │   ├── Tabs.stories.tsx  # Storybook stories for Tabs
│   │   │   │   ├── Tabs.test.tsx  # Vitest: Tabs behavior + a11y
│   │   │   │   ├── Toast.ct.tsx  # Playwright CT: Toast queue
│   │   │   │   ├── Toast.stories.tsx  # Storybook stories for Toast
│   │   │   │   ├── Toast.test.tsx  # Vitest: Toast queue behavior
│   │   │   │   ├── nested-overlays.ct.tsx  # Playwright CT: nested modal + dropdown
│   │   │   │   └── nested-overlays.stories.tsx  # Storybook: nested overlay scenarios
│   │   │   ├── Dropdown.css  # Dropdown styles; reduced-motion-gated animation
│   │   │   ├── Dropdown.tsx  # Controlled dropdown menu over Radix DropdownMenu
│   │   │   ├── Modal.css  # Modal styles; overlay scrim + gated animation
│   │   │   ├── Modal.tsx  # Controlled modal dialog over Radix Dialog
│   │   │   ├── Tabs.css  # Tabs styles; token-bound BEM classes; reduced-motion guard
│   │   │   ├── Tabs.tsx  # Controlled tab-strip; hand-rolled WAI-ARIA tablist (no Radix)
│   │   │   ├── Toast.css  # Toast queue styles per variant
│   │   │   └── Toast.tsx  # Toast queue UI; ToastProvider + ToastViewport
│   │   ├── PrimitivesDemo.css  # Styles for the dev-only primitives gallery
│   │   └── PrimitivesDemo.tsx  # Dev-only visual QA gallery for all UI primitives
│   ├── lib
│   │   ├── __tests__
│   │   │   ├── icons-glue.test.ts  # Vitest: icon resolver fallback path
│   │   │   └── toastStore.test.ts  # Vitest: toast store actions
│   │   ├── cx.ts  # className merge util; drops falsy tokens
│   │   ├── icons-glue.ts  # Safe icon-name resolver; never throws on unknown
│   │   └── toastStore.ts  # Module-level zustand store for the toast queue
│   ├── App.tsx  # Root component; wraps ToastProvider, dev-gated demo
│   ├── env.d.ts  # Vite/renderer ambient type declarations
│   └── main.tsx  # React entry; mounts App into #root under StrictMode
├── styles
│   └── tokens.css  # Design tokens (color, spacing) as CSS variables
└── index.html  # Renderer HTML shell; mount point for the React root
```
