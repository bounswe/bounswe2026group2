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
// TC_AUTH_2 — Google OAuth Login
// ---------------------------------------------------------------------------
// Real Google consent screens cannot be automated, so we intercept the backend
// OAuth redirect and inject a test token via the oauth-callback page.  This
// exercises the full frontend OAuth flow:
//   button click → /auth/google/login → (intercepted) → oauth-callback.html
//   → localStorage.setItem('auth_token', ...) → redirect to map.html
// ---------------------------------------------------------------------------
test.describe('TC_AUTH_2 — Google OAuth Login', () => {
  const FAKE_TOKEN = 'test.jwt.token';

  test('logs in via Google OAuth and lands on the map', async ({ page }) => {
    // map.html calls GET /auth/me on load; a 401 would remove the token from
    // localStorage before we can assert it.  Return a mock user to prevent that.
    await page.route('**/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'test-id', username: 'testuser', email: 'testuser@example.com' }),
      });
    });

    // ── Step 1: Open the login page ─────────────────────────────────────────
    await page.goto('/index.html');

    // ── Step 2: Rewrite the OAuth button href to the callback page ───────────
    // Avoids going through Google's consent screen while still exercising the
    // full frontend OAuth callback flow (token extraction → localStorage → redirect).
    // Using evaluate() keeps the navigation on the frontend origin so the
    // relative /oauth-callback.html URL resolves correctly.
    await page.evaluate((token) => {
      const btn = document.getElementById('google-auth-button');
      if (btn) btn.href = `/oauth-callback.html#access_token=${token}`;
    }, FAKE_TOKEN);

    // ── Step 3: Click "Continue with Google" ────────────────────────────────
    await page.getByTestId('login-google').click();

    // ── Step 4: oauth-callback.html reads the token and redirects to map ────
    await page.waitForURL('**/map.html', { timeout: 10_000 });
    await expect(page).toHaveURL(/map\.html/);

    // ── Step 5: Confirm the token was persisted ──────────────────────────────
    const stored = await page.evaluate(() => localStorage.getItem('auth_token'));
    expect(stored).toBe(FAKE_TOKEN);
  });
});
