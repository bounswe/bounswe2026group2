// UAT — Authentication flows
// Black-box tests against the running full-stack app (docker compose).
//
// Prerequisites:
//   ./localrun.sh   (or docker compose up --build)
//
// Run:
//   UAT_BASE_URL=http://localhost:3000 npm test          (from this directory)
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/uat/  (from frontend/)

const { test, expect } = require('@playwright/test');

// ---------------------------------------------------------------------------
// TC_AUTH_1 — User Registration and Login
// ---------------------------------------------------------------------------
test.describe('TC_AUTH_1 — User Registration and Login', () => {
  // Unique credentials per run so repeated runs never collide.
  const ts = Date.now();
  const username = `testuser${ts}`;
  const email = `testuser${ts}@example.com`;
  // Meets register.html validation: uppercase, lowercase, digit, special char.
  const password = 'Test@1234';

  test('registers a new user then logs in with the same credentials', async ({ page }) => {
    // ── Step 1: Open the registration page ──────────────────────────────────
    await page.goto('/register.html');

    // ── Step 2: Fill in the registration form ───────────────────────────────
    await page.getByTestId('register-username').fill(username);
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(password);
    await page.getByTestId('register-confirm-password').fill(password);
    await page.getByTestId('register-terms').check();

    // ── Step 3: Submit ───────────────────────────────────────────────────────
    await page.getByTestId('register-submit').click();

    // ── Step 4: Success banner should appear ─────────────────────────────────
    await expect(page.getByTestId('register-success')).toBeVisible();
    await expect(page.getByTestId('register-success')).toContainText('Account created successfully');

    // ── Step 5: Wait for redirect to login page (1.5 s delay in register.html)
    await page.waitForURL('**/index.html', { timeout: 5_000 });

    // ── Step 6: Fill in the login form ───────────────────────────────────────
    await page.getByTestId('login-email').fill(email);
    await page.getByTestId('login-password').fill(password);

    // ── Step 7: Submit ───────────────────────────────────────────────────────
    await page.getByTestId('login-submit').click();

    // ── Step 8: Verify authenticated redirect to map ─────────────────────────
    await page.waitForURL('**/map.html', { timeout: 5_000 });
    await expect(page).toHaveURL(/map\.html/);
  });
});

// ---------------------------------------------------------------------------
// TC_AUTH_2 — Google OAuth Login  (placeholder until issue #238 ships)
// ---------------------------------------------------------------------------
test.describe('TC_AUTH_2 — Google OAuth Login', () => {
  test.skip('logs in via Google OAuth and lands on the map', async ({ page }) => {
    // TODO: implement when issue #238 (Google OAuth backend) is complete.
    //
    // Suggested steps:
    //   1. page.goto('/index.html')
    //   2. page.click('[data-testid="login-google"]')   ← add testid to the button
    //   3. Complete the OAuth consent flow (use a test Google account or mock)
    //   4. await page.waitForURL('**/map.html')
    //   5. expect(page).toHaveURL(/map\.html/)
  });
});
