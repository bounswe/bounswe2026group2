// Mobile E2E — Authentication flows (Appium / WebdriverIO)
//
// Black-box tests against the Capacitor WebView. Requires a running Appium
// server, a connected Android emulator with the debug APK installed, and the
// backend reachable at MOBILE_API_BASE_URL (default: http://10.0.2.2:8000).
//
// Tests are skipped automatically when no WEBVIEW context is available.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

// ---------------------------------------------------------------------------
// TC_AUTH_1 — User Registration and Login
// ---------------------------------------------------------------------------
describe('TC_AUTH_1 — User Registration and Login', () => {
  // Unique credentials per run so repeated runs never collide.
  const ts = Date.now();
  const username = `testuser${ts}`;
  const email = `testuser${ts}@example.com`;
  // Meets register.html validation: uppercase, lowercase, digit, special char.
  const password = 'Test@1234';

  it('registers a new user then logs in with the same credentials', async function () {
    // ── Step 1: Switch to the Capacitor WebView ─────────────────────────────
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    // ── Step 2: Navigate to the registration page ────────────────────────────
    await browser.url('register.html');

    // ── Step 3: Fill in the registration form ───────────────────────────────
    await (await browser.$('[data-testid="register-username"]')).setValue(username);
    await (await browser.$('[data-testid="register-email"]')).setValue(email);
    await (await browser.$('[data-testid="register-password"]')).setValue(password);
    await (await browser.$('[data-testid="register-confirm-password"]')).setValue(password);

    // Check the terms checkbox via JS — native tap on a small checkbox can be
    // flaky on mobile; this is equivalent and deterministic.
    await browser.execute(() => {
      const cb = document.querySelector('[data-testid="register-terms"]');
      if (cb && !cb.checked) cb.click();
    });

    // ── Step 4: Submit the registration form ────────────────────────────────
    await (await browser.$('[data-testid="register-submit"]')).click();

    // ── Step 5: Wait for the success banner ─────────────────────────────────
    await browser.waitUntil(
      async () => {
        const el = await browser.$('[data-testid="register-success"]');
        return (await el.isDisplayed()) && (await el.getText()).includes('Account created successfully');
      },
      { timeout: 10_000, interval: 500, timeoutMsg: 'Registration success banner did not appear' },
    );

    // ── Step 6: Wait for auto-redirect to login page (1.5 s delay in register.html)
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('index.html'),
      { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to index.html after registration' },
    );

    // ── Step 7: Fill in the login form ───────────────────────────────────────
    await (await browser.$('[data-testid="login-email"]')).setValue(email);
    await (await browser.$('[data-testid="login-password"]')).setValue(password);

    // ── Step 8: Submit ───────────────────────────────────────────────────────
    await (await browser.$('[data-testid="login-submit"]')).click();

    // ── Step 9: Verify authenticated redirect to map ─────────────────────────
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('map.html'),
      { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to map.html after login' },
    );

    const finalUrl = await browser.getUrl();
    assert.ok(finalUrl.includes('map.html'), `Expected map.html, got: ${finalUrl}`);
  });
});

// ---------------------------------------------------------------------------
// TC_AUTH_2 — Google OAuth Login
// ---------------------------------------------------------------------------
// Real Google consent screens cannot be automated without live credentials,
// so this test exercises the frontend OAuth flow by injecting a test token
// directly into the WebView — bypassing the Google redirect — and then
// verifying that oauth-callback.js stores the token and navigates to map.html.
// ---------------------------------------------------------------------------
describe('TC_AUTH_2 — Google OAuth Login', () => {
  const FAKE_TOKEN = 'test.jwt.token';

  it('intercepts OAuth redirect, stores token in localStorage, and navigates to map', async function () {
    // ── Step 1: Switch to the Capacitor WebView ─────────────────────────────
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    // ── Step 2: Rewrite the Google auth button's href to the callback page ──
    // This simulates the backend redirect without hitting Google's servers.
    await browser.execute((token) => {
      const btn = document.getElementById('google-auth-button');
      if (btn) {
        btn.href = `oauth-callback.html#access_token=${token}`;
      }
    }, FAKE_TOKEN);

    // ── Step 3: Click "Continue with Google" ────────────────────────────────
    const googleBtn = await browser.$('[data-testid="login-google"]');
    await googleBtn.click();

    // ── Step 4: Wait for oauth-callback.js to redirect to map.html ──────────
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('map.html'),
      { timeout: 15_000, interval: 500, timeoutMsg: 'Timed out waiting for map.html after OAuth callback' },
    );

    // ── Step 5: Assert the JWT was persisted in localStorage ─────────────────
    const stored = await browser.execute(() => localStorage.getItem('auth_token'));
    assert.equal(stored, FAKE_TOKEN, 'auth_token should be stored in localStorage after OAuth sign-in');
  });
});
