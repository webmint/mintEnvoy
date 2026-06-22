import { defineConfig, devices } from '@playwright/experimental-ct-react'
import { resolve } from 'path'

export default defineConfig({
  testDir: './src/renderer/src',
  testMatch: '**/*.ct.{ts,tsx}',
  snapshotDir: './__snapshots__',
  timeout: 10 * 1000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'html',
  use: {
    ctPort: 3100,
    ctViteConfig: {
      resolve: {
        alias: {
          '@renderer': resolve(__dirname, 'src/renderer/src')
        }
      }
    }
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
})
