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

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/uat',
  timeout: 30_000,
  retries: 0,

  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'uat-report.xml' }],
  ],

  use: {
    baseURL: process.env.UAT_BASE_URL || 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
