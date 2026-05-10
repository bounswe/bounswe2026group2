// Playwright configuration for UAT tests.
//
// Run locally from repo root:
//   UAT_BASE_URL=http://localhost:3000 npx playwright test frontend/tests/uat/
//
// Run locally from frontend/tests/uat/:
//   UAT_BASE_URL=http://localhost:3000 npm test
//
// CI runs:
//   cd frontend && npx playwright test tests/uat/ --reporter=html,junit

// Plain object export — no require('@playwright/test') needed so the CI UAT
// job can load this config without running npm ci first.
module.exports = {
  timeout: 30_000,
  retries: 0,

  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'uat-report.xml' }],
  ],

  use: {
    baseURL: process.env.UAT_BASE_URL || 'http://localhost:3000',
    headless: true,
    browserName: 'chromium',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
};
