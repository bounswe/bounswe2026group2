// TC_TAG_1 - Keyword Tagging on Story Creation (mobile Appium / WebdriverIO)
//
// Local-only test against the Android APK launched by wdio.conf.js. The test is
// intentionally skipped until the mobile/dev tagging UI exposes the shared
// data-testid contract used by the web UAT scenario.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

const SEEDED_USER_EMAIL = process.env.MOBILE_SEEDED_EMAIL || process.env.UAT_SEEDED_EMAIL || 'seed_alice@example.com';
const SEEDED_USER_PASSWORD = process.env.MOBILE_SEEDED_PASSWORD || process.env.UAT_SEEDED_PASSWORD || 'ValidPass1!';

function xpathLiteral(value) {
  if (!value.includes("'")) {
    return `'${value}'`;
  }

  return `concat('${value.split("'").join("', \"'\", '")}')`;
}

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

async function waitForElementWithText(testId, text, timeoutMsg) {
  const selector = `//*[@data-testid=${xpathLiteral(testId)} and contains(normalize-space(.), ${xpathLiteral(text)})]`;
  const el = await browser.$(selector);
  await el.waitForDisplayed({ timeout: 10_000, timeoutMsg });
  return el;
}

async function addStoryTag(tagName) {
  const input = await browser.$('[data-testid="story-tag-input"]');
  await input.waitForDisplayed({ timeout: 10_000 });
  await input.setValue(tagName);
  await browser.keys('Enter');
  await waitForElementWithText(
    'story-tag-chip',
    tagName,
    `Story tag chip "${tagName}" did not appear`,
  );
}

async function setGalataLocation() {
  await (await browser.$('#location')).setValue('Galata');

  // The Leaflet map is flaky to tap through a WebView in Appium. The form
  // requires coordinates, while the visible location field carries Galata.
  await browser.execute(() => {
    document.getElementById('latitude').value = '41.0256';
    document.getElementById('longitude').value = '28.9744';
  });
}

async function captureCreateStoryResponse() {
  await browser.execute(() => {
    localStorage.removeItem('__tcTag1CreatedStory');
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

        localStorage.setItem('__tcTag1CreatedStory', JSON.stringify(capture));
      }

      return response;
    };
  });
}

async function waitForCreateStoryResponse() {
  await browser.waitUntil(
    async () => !!(await browser.execute(() => localStorage.getItem('__tcTag1CreatedStory'))),
    { timeout: 10_000, interval: 200, timeoutMsg: 'POST /stories response was not captured' },
  );

  return browser.execute(() => {
    const raw = localStorage.getItem('__tcTag1CreatedStory');
    localStorage.removeItem('__tcTag1CreatedStory');
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

describe('TC_TAG_1 - Keyword Tagging on Story Creation', () => {
  it.skip('creates a tagged story and finds it through tag search', async function () {
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    const unique = Date.now();
    const title = `Tagged Galata Memory ${unique}`;
    const content = 'A 19th-century Ottoman memory from the streets around Galata.';

    await loginSeededUserViaUi();

    await navigateTo('/story-create.html');
    await (await browser.$('#title')).setValue(title);
    await (await browser.$('#story')).setValue(content);
    await (await browser.$('#date-single')).setValue('01/01/1890');

    await addStoryTag('ottoman');
    await addStoryTag('19th-century');
    await setGalataLocation();

    await captureCreateStoryResponse();
    await (await browser.$('#btn-publish')).click();

    const createdStory = await waitForCreateStoryResponse();
    assert.equal(createdStory.status, 201, `Expected POST /stories status 201, got ${createdStory.status}`);
    assert.ok(createdStory.id, 'Created story id must be captured');

    await waitForCreateSuccess();

    await navigateTo('/search.html');
    const tagFilterInput = await browser.$('[data-testid="tag-filter-input"]');
    await tagFilterInput.waitForDisplayed({ timeout: 10_000 });
    await tagFilterInput.setValue('ottoman');
    await browser.keys('Enter');

    await waitForElementWithText(
      'active-tag-filter',
      'ottoman',
      'Active ottoman tag filter did not appear',
    );
    await waitForElementWithText(
      'search-result-card',
      title,
      `Created story "${title}" did not appear in tag search results`,
    );
  });
});
