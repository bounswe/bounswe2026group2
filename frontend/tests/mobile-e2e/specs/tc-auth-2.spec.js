// TC_AUTH_2 — Google OAuth Login (Mobile E2E, Appium / WebdriverIO)
//
// Real Google consent screens cannot be automated without live credentials,
// so this test exercises the frontend OAuth flow by injecting a test token
// directly into the WebView — bypassing the Google redirect — and then
// verifying that oauth-callback.js stores the token and navigates to map.html.
//
// Prerequisites:
//   - Appium server running (APPIUM_SERVER_URL in .env)
//   - Debug APK installed on emulator (ANDROID_APP_PATH / ANDROID_DEVICE_NAME)
//   - Backend reachable at MOBILE_API_BASE_URL (optional — not called here)
//
// Skipped automatically when no WEBVIEW context is available (e.g. pure-native
// launch without a loaded Capacitor page).

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

describe('TC_AUTH_2 — Google OAuth Login', () => {
  const FAKE_TOKEN = 'test.jwt.token';

  it('intercepts OAuth redirect, stores token in localStorage, and navigates to map', async function () {
    // ── Step 1: Switch to the Capacitor WebView ─────────────────────────────
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      // No WebView available (e.g. app not yet loaded); skip gracefully.
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
      async () => {
        const url = await browser.getUrl();
        return url.includes('map.html');
      },
      { timeout: 15_000, interval: 500, timeoutMsg: 'Timed out waiting for map.html after OAuth callback' },
    );

    // ── Step 5: Assert the JWT was persisted in localStorage ─────────────────
    const stored = await browser.execute(() => localStorage.getItem('auth_token'));
    assert.equal(stored, FAKE_TOKEN, 'auth_token should be stored in localStorage after OAuth sign-in');
  });
});
