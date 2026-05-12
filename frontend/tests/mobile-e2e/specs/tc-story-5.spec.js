// TC_STORY_5 — Anonymous Story Sharing (mobile Appium / WebdriverIO)
//
// Black-box tests against the Capacitor WebView. Requires a running Appium
// server, a connected Android emulator with the debug APK installed, and the
// backend reachable at MOBILE_API_BASE_URL (default: http://10.0.2.2:8000).
//
// Tests are skipped automatically when no WEBVIEW context is available.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

const TS = Date.now();
const AUTHOR_USERNAME = `author${TS}`;
const AUTHOR_EMAIL = `author${TS}@example.com`;
const READER_USERNAME = `reader${TS}`;
const READER_EMAIL = `reader${TS}@example.com`;
const PASSWORD = 'Test@1234';

async function getAppOrigin() {
  const url = await browser.getUrl();
  return new URL(url).origin;
}

async function navigateTo(path) {
  const origin = await getAppOrigin();
  await browser.url(`${origin}${path}`);
}

async function registerAndLogin(username, email, password) {
  await navigateTo('/register.html');
  await (await browser.$('[data-testid="register-username"]')).setValue(username);
  await (await browser.$('[data-testid="register-email"]')).setValue(email);
  await (await browser.$('[data-testid="register-password"]')).setValue(password);
  await (await browser.$('[data-testid="register-confirm-password"]')).setValue(password);
  // Use execute() — native tap on a small checkbox is flaky on mobile.
  await browser.execute(() => {
    const cb = document.querySelector('[data-testid="register-terms"]');
    if (cb && !cb.checked) cb.click();
  });
  await (await browser.$('[data-testid="register-submit"]')).click();
  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('index.html'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to index.html after registration' },
  );
  await (await browser.$('[data-testid="login-email"]')).setValue(email);
  await (await browser.$('[data-testid="login-password"]')).setValue(password);
  await (await browser.$('[data-testid="login-submit"]')).click();
  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('map.html'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to map.html after login' },
  );
}

async function clearSession() {
  await browser.execute(() => {
    localStorage.removeItem('auth_token');
  });
}

describe('TC_STORY_5 — Anonymous Story Sharing', () => {
  it('author identity is hidden when story is published anonymously', async function () {
    // ── Step 1: Switch to the Capacitor WebView ─────────────────────────────
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    // ── Step 2: Register and log in as the author ────────────────────────────
    await registerAndLogin(AUTHOR_USERNAME, AUTHOR_EMAIL, PASSWORD);

    // ── Step 3: Open story creation page ─────────────────────────────────────
    await navigateTo('/story-create.html');

    // ── Step 4: Fill in title, content, location and date ────────────────────
    await (await browser.$('#title')).setValue('Old Fountain');
    await (await browser.$('#story')).setValue('A forgotten fountain in the heart of the old city.');
    await (await browser.$('#location')).setValue('Istanbul');
    await (await browser.$('#date-single')).setValue('2024-01-01');
    // Set lat/lng hidden fields directly — the Leaflet map is not interactive
    // in the WebView and the submit handler requires non-empty coordinates.
    await browser.execute(() => {
      document.getElementById('latitude').value = '41.0082';
      document.getElementById('longitude').value = '28.9784';
    });

    // ── Step 5: Enable anonymous toggle ──────────────────────────────────────
    await (await browser.$('#anon-card')).click();
    const isAnonymous = await browser.execute(
      () => document.getElementById('is-anonymous').value,
    );
    assert.strictEqual(isAnonymous, 'true', 'anonymous hidden input must be "true" after toggling');

    // ── Step 6: Inject fetch interceptor to capture the story ID ─────────────
    // story-create.html redirects to map.html after publish, so the story ID
    // cannot be read from the URL.  We monkey-patch window.fetch to intercept
    // the POST /stories response and persist the ID in localStorage so it
    // survives the navigation.
    await browser.execute(() => {
      const origFetch = window.fetch;
      window.fetch = async function (input, init) {
        const res = await origFetch(input, init);
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        if (url.includes('/stories') && init && init.method === 'POST') {
          try {
            const data = await res.clone().json();
            if (data && data.id) localStorage.setItem('__capturedStoryId', String(data.id));
          } catch (_) { /* ignore parse errors */ }
        }
        return res;
      };
    });

    // ── Step 7: Submit the form ───────────────────────────────────────────────
    await (await browser.$('#btn-publish')).click();

    // Wait until the interceptor has stored the story ID (POST response arrived).
    await browser.waitUntil(
      async () => !!(await browser.execute(() => localStorage.getItem('__capturedStoryId'))),
      { timeout: 10_000, interval: 200, timeoutMsg: 'POST /stories response was not captured within timeout' },
    );
    const storyId = await browser.execute(() => {
      const id = localStorage.getItem('__capturedStoryId');
      localStorage.removeItem('__capturedStoryId');
      return id;
    });
    assert.ok(storyId, 'story ID must be a non-empty string');

    // ── Step 8: Clear author session, register and log in as the reader ───────
    await clearSession();
    await registerAndLogin(READER_USERNAME, READER_EMAIL, PASSWORD);

    // ── Step 9: Navigate to the story as the reader ───────────────────────────
    await navigateTo(`/story-detail.html?id=${storyId}`);
    const readerAuthorEl = await browser.$('#story-author');
    await readerAuthorEl.waitForExist({ timeout: 8_000 });
    const readerAuthorText = await readerAuthorEl.getText();
    assert.ok(
      readerAuthorText.includes('Anonymous'),
      `reader must see "Anonymous", got: "${readerAuthorText}"`,
    );
    assert.ok(
      !readerAuthorText.includes(AUTHOR_USERNAME),
      `real username "${AUTHOR_USERNAME}" must not be visible to the reader`,
    );

    // ── Step 10: Clear reader session and verify as an unauthenticated visitor ─
    await clearSession();
    await navigateTo(`/story-detail.html?id=${storyId}`);
    const visitorAuthorEl = await browser.$('#story-author');
    await visitorAuthorEl.waitForExist({ timeout: 8_000 });
    const visitorAuthorText = await visitorAuthorEl.getText();
    assert.ok(
      visitorAuthorText.includes('Anonymous'),
      `visitor must see "Anonymous", got: "${visitorAuthorText}"`,
    );
    assert.ok(
      !visitorAuthorText.includes(AUTHOR_USERNAME),
      `real username "${AUTHOR_USERNAME}" must not be visible to the visitor`,
    );

    // ── Step 11: Assert story content is visible ──────────────────────────────
    const contentEl = await browser.$('#story-content');
    await contentEl.waitForExist({ timeout: 8_000 });
    const contentText = await contentEl.getText();
    assert.ok(
      contentText.includes('A forgotten fountain in the heart of the old city.'),
      `story body must be visible to unauthenticated visitors, got: "${contentText}"`,
    );
  });
});
