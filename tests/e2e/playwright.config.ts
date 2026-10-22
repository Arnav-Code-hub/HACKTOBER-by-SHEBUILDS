import { defineConfig, devices } from "@playwright/test";

/**
 * Cross-service E2E. Runs against a real stack (`make dev`), not mocks — the
 * point is to catch the seams between mobile-shaped API calls, the web app and
 * the AI service, which unit tests by construction cannot see.
 */
export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["html"], ["github"]] : [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
