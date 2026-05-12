// Playwright configuration for E2E tests (technical flows, distinct from UAT).
//
// Run locally from repo root:
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/e2e/ --config frontend/playwright.e2e.config.js
//
// Run locally from frontend/:
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/e2e/ --config playwright.e2e.config.js

module.exports = {
  timeout: 45_000,
  retries: 1,

  reporter: [
    ['html', { outputFolder: 'playwright-e2e-report', open: 'never' }],
    ['junit', { outputFile: 'e2e-report.xml' }],
  ],

  use: {
    baseURL: process.env.UAT_BASE_URL || 'http://localhost:3000',
    headless: true,
    browserName: 'chromium',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
};
