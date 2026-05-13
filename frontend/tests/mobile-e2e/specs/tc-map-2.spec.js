// TC_MAP_2 - Multi-Location Story Display on Map (mobile Appium / WebdriverIO)
//
// Local-only test against the Android APK launched by wdio.conf.js. The test is
// intentionally skipped until Backend: Multi-Location Story Support #231 and
// Frontend: Multi-Location Story Support #241 are both shipped.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

const SEEDED_USER_EMAIL = process.env.MOBILE_SEEDED_EMAIL || process.env.UAT_SEEDED_EMAIL || 'seed_alice@example.com';
const SEEDED_USER_PASSWORD = process.env.MOBILE_SEEDED_PASSWORD || process.env.UAT_SEEDED_PASSWORD || 'ValidPass1!';

// Üsküdar coordinates
const USKUDAR = { lat: 41.0234, lng: 29.0153 };
// Galata coordinates
const GALATA = { lat: 41.0256, lng: 28.9744 };

async function getAppOrigin() {
  const url = await browser.getUrl();
  return new URL(url).origin;
}

async function navigateTo(path) {
  const origin = await getAppOrigin();
  await browser.url(`${origin}${path}`);
}

async function loginSeededUserViaUi() {
  await navigateTo('/index.html');
  await (await browser.$('[data-testid="login-email"]')).setValue(SEEDED_USER_EMAIL);
  await (await browser.$('[data-testid="login-password"]')).setValue(SEEDED_USER_PASSWORD);
  await (await browser.$('[data-testid="login-submit"]')).click();

  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('map.html'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to map.html after seeded-user login' },
  );
}

async function captureCreateStoryResponse() {
  await browser.execute(() => {
    localStorage.removeItem('__tcMap2CreatedStory');
    const originalFetch = window.fetch;

    window.fetch = async function patchedFetch(input, init) {
      const response = await originalFetch(input, init);
      const url = typeof input === 'string' ? input : (input && input.url) || '';

      if (url.includes('/stories') && init && init.method === 'POST') {
        const capture = { status: response.status, id: null };

        try {
          const data = await response.clone().json();
          capture.id = data && data.id ? String(data.id) : null;
        } catch (_) {
          // Ignore non-JSON failures; the status still tells us what happened.
        }

        localStorage.setItem('__tcMap2CreatedStory', JSON.stringify(capture));
      }

      return response;
    };
  });
}

async function waitForCreateStoryResponse() {
  await browser.waitUntil(
    async () => !!(await browser.execute(() => localStorage.getItem('__tcMap2CreatedStory'))),
    { timeout: 10_000, interval: 200, timeoutMsg: 'POST /stories response was not captured' },
  );

  return browser.execute(() => {
    const raw = localStorage.getItem('__tcMap2CreatedStory');
    localStorage.removeItem('__tcMap2CreatedStory');
    return raw ? JSON.parse(raw) : null;
  });
}

async function waitForCreateSuccess() {
  await browser.waitUntil(
    async () => browser.execute(() => {
      const success = document.getElementById('form-success');
      const badgeModal = document.getElementById('badge-unlock-modal');
      return Boolean(
        (success && !success.classList.contains('hidden')) ||
        (badgeModal && !badgeModal.classList.contains('hidden')),
      );
    }),
    { timeout: 10_000, interval: 250, timeoutMsg: 'Story creation success confirmation did not appear' },
  );
}

describe('TC_MAP_2 — Multi-Location Story Display on Map', () => {
  it.skip('story pinned to two locations shows both markers on the map and both open the same story', async function () {
    // ── Step 1: Switch to the Capacitor WebView ─────────────────────────────
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    const unique = Date.now();
    const title = `Multi-Pin Memory ${unique}`;
    const content = 'A story spanning Üsküdar and Galata, two shores of the Bosphorus.';

    // ── Step 2: Log in as the seeded test user ──────────────────────────────
    await loginSeededUserViaUi();

    // ── Step 3: Open story creation page ────────────────────────────────────
    await navigateTo('/story-create.html');

    // ── Step 4: Pin the first location (Üsküdar) ───────────────────────────
    // The Leaflet map is not reliably tappable in a WebView. Invoke the
    // picker function directly through the page context.
    await browser.execute((lat, lng) => {
      window.addPinFromMapClick(lat, lng);
    }, USKUDAR.lat, USKUDAR.lng);

    // Assert the first location chip appears.
    const chipCount1 = await browser.execute(
      () => document.querySelectorAll('#location-chips [data-index]').length,
    );
    assert.strictEqual(chipCount1, 1, `Expected 1 location chip after first pin, got ${chipCount1}`);

    // ── Step 5: Pin the second location (Galata) ────────────────────────────
    await browser.execute((lat, lng) => {
      window.addPinFromMapClick(lat, lng);
    }, GALATA.lat, GALATA.lng);

    // Assert both location chips are now visible.
    const chipCount2 = await browser.execute(
      () => document.querySelectorAll('#location-chips [data-index]').length,
    );
    assert.strictEqual(chipCount2, 2, `Expected 2 location chips after second pin, got ${chipCount2}`);

    // ── Step 6: Fill story text, location name, and date fields ─────────────
    await (await browser.$('#title')).setValue(title);
    await (await browser.$('#story')).setValue(content);
    await (await browser.$('#location')).setValue('Üsküdar – Galata');
    await (await browser.$('#date-single')).setValue('06/15/2024');

    // ── Step 7: Submit the story and capture the response ───────────────────
    await captureCreateStoryResponse();
    await (await browser.$('#btn-publish')).click();

    const createdStory = await waitForCreateStoryResponse();
    assert.equal(createdStory.status, 201, `Expected POST /stories status 201, got ${createdStory.status}`);
    assert.ok(createdStory.id, 'Created story id must be captured');

    await waitForCreateSuccess();

    // ── Step 8: Navigate to the map page and wait for stories to load ───────
    await navigateTo('/map.html');

    // Wait for the stories API response to arrive and markers to render.
    await browser.waitUntil(
      async () => browser.execute(
        () => document.querySelectorAll('.story-marker').length > 0,
      ),
      { timeout: 15_000, interval: 500, timeoutMsg: 'Story markers did not appear on the map' },
    );

    // ── Step 9: Wait for the multi-location marker to appear ──────────────
    await browser.waitUntil(
      async () => browser.execute(
        () => document.querySelectorAll('.story-marker.multi').length > 0,
      ),
      { timeout: 15_000, interval: 500, timeoutMsg: 'Multi-location story marker did not appear on the map' },
    );

    // ── Step 10: Click the multi-location marker to enter focus mode ────────
    // Leaflet markers are rendered inside the map pane as absolute-positioned
    // divs. Use execute + click() to avoid coordinate-based tap flakiness.
    await browser.execute(() => {
      const marker = document.querySelector('.story-marker.multi');
      if (marker) marker.click();
    });

    // ── Step 11: Assert the focus banner shows the story title ──────────────
    await browser.waitUntil(
      async () => browser.execute(() => {
        const banner = document.getElementById('focus-banner');
        return banner && banner.classList.contains('visible');
      }),
      { timeout: 5_000, interval: 250, timeoutMsg: 'Focus banner did not appear after clicking multi-location marker' },
    );

    const bannerTitle = await browser.execute(
      () => (document.getElementById('focus-banner-title') || {}).textContent || '',
    );
    assert.ok(
      bannerTitle.includes(title),
      `Focus banner title should contain "${title}", got "${bannerTitle}"`,
    );

    // ── Step 12: Assert two numbered pins are rendered in focus mode ────────
    const pinCount = await browser.execute(
      () => document.querySelectorAll('.multi-location-pin').length,
    );
    assert.strictEqual(pinCount, 2, `Expected 2 numbered route pins, got ${pinCount}`);

    // ── Step 13: Tap first pin and verify the popup opens ───────────────────
    await browser.execute(() => {
      const pins = document.querySelectorAll('.multi-location-pin');
      if (pins[0]) pins[0].click();
    });

    await browser.waitUntil(
      async () => browser.execute(
        () => document.querySelectorAll('.leaflet-popup-content').length > 0,
      ),
      { timeout: 5_000, interval: 250, timeoutMsg: 'Popup did not appear after clicking first route pin' },
    );

    const popup1Text = await browser.execute(
      () => (document.querySelector('.leaflet-popup-content') || {}).textContent || '',
    );
    assert.ok(popup1Text.includes('Stop 1'), `First pin popup should contain "Stop 1", got "${popup1Text}"`);
    assert.ok(popup1Text.includes('Read Story'), `First pin popup should contain story link, got "${popup1Text}"`);

    // ── Step 14: Tap second pin and verify the same story link appears ──────
    // Close the current popup first.
    await browser.execute(() => {
      const closeBtn = document.querySelector('.leaflet-popup-close-button');
      if (closeBtn) closeBtn.click();
    });

    await browser.execute(() => {
      const pins = document.querySelectorAll('.multi-location-pin');
      if (pins[1]) pins[1].click();
    });

    await browser.waitUntil(
      async () => browser.execute(
        () => document.querySelectorAll('.leaflet-popup-content').length > 0,
      ),
      { timeout: 5_000, interval: 250, timeoutMsg: 'Popup did not appear after clicking second route pin' },
    );

    const popup2Text = await browser.execute(
      () => (document.querySelector('.leaflet-popup-content') || {}).textContent || '',
    );
    assert.ok(popup2Text.includes('Stop 2'), `Second pin popup should contain "Stop 2", got "${popup2Text}"`);

    // Both pins must link to the same story detail page.
    const storyId = createdStory.id;
    const popup2Href = await browser.execute(
      () => {
        const link = document.querySelector('.leaflet-popup-content a[href*="story-detail"]');
        return link ? link.getAttribute('href') : '';
      },
    );
    assert.ok(
      popup2Href.includes(`story-detail.html?id=${storyId}`),
      `Second pin link should point to story ${storyId}, got "${popup2Href}"`,
    );
  });
});
