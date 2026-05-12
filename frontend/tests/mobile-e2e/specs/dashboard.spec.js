// Mobile E2E — TC_DASH_1 (Appium / WebdriverIO, Capacitor WebView)
//
// Web UAT equivalent lives in tests/uat/dashboard.spec.js (Playwright). This file
// does not change the web app markup; it targets stable login testids + profile DOM.
//
// Skipped by default until mobile dashboard + view tracking are verified on dev.
// Enable locally: MOBILE_E2E_RUN_TC_DASH_1=1 npm test
//
// Flow: one WebView session — sign out, open story as anonymous, sign back in —
// avoids a second Appium driver.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

const OWNER_EMAIL = process.env.MOBILE_E2E_OWNER_EMAIL || 'test@gmail.com';
const OWNER_PASSWORD = process.env.MOBILE_E2E_OWNER_PASSWORD || 'Test1234%';
const SEEDED_STORY_ID =
  process.env.MOBILE_E2E_SEEDED_STORY_ID || 'bb43034b-8e1a-49a8-92b9-56346f50767a';

async function mobileLogin(email, password) {
  await browser.url('index.html');
  await (await browser.$('[data-testid="login-email"]')).waitForDisplayed({ timeout: 15_000 });
  await (await browser.$('[data-testid="login-email"]')).setValue(email);
  await (await browser.$('[data-testid="login-password"]')).setValue(password);
  await (await browser.$('[data-testid="login-submit"]')).click();

  await browser.waitUntil(
    async () => {
      const url = await browser.getUrl();
      if (url.includes('map.html')) return true;
      const token = await browser.execute(() => localStorage.getItem('auth_token'));
      return Boolean(token);
    },
    { timeout: 30_000, interval: 500, timeoutMsg: 'Login did not complete (no map, no token)' },
  );

  const url = await browser.getUrl();
  if (!url.includes('map.html')) {
    await browser.url('map.html');
    await browser.waitUntil(async () => (await browser.getUrl()).includes('map.html'), {
      timeout: 15_000,
      interval: 250,
    });
  }
}

async function openProfileMenu() {
  const btn = await browser.$('#btn-profile');
  await btn.waitForDisplayed({ timeout: 15_000 });
  await btn.click();
  const menu = await browser.$('#profile-menu');
  await menu.waitForDisplayed({ timeout: 10_000 });
}

async function goToProfileFromMenu() {
  await openProfileMenu();
  const viewProfile = await browser.$('//a[@role="menuitem" and contains(.,"View Profile")]');
  await viewProfile.click();
  await browser.waitUntil(async () => (await browser.getUrl()).includes('profile.html'), {
    timeout: 15_000,
    interval: 250,
  });
}

async function signOutFromMenu() {
  await openProfileMenu();
  const signOut = await browser.$('//button[@role="menuitem" and contains(.,"Sign Out")]');
  await signOut.waitForDisplayed({ timeout: 10_000 });
  await signOut.click();
  await browser.pause(400);
}

async function readTotalViewsFromProfile() {
  const el = await browser.$('#stat-views');
  await el.waitForDisplayed({ timeout: 15_000 });
  await browser.waitUntil(
    async () => {
      const t = (await el.getText()).trim();
      return t.length > 0 && t !== '…';
    },
    { timeout: 15_000, interval: 300, timeoutMsg: 'stat-views did not settle' },
  );
  const txt = (await el.getText()).trim();
  const n = Number.parseInt(txt, 10);
  assert.ok(Number.isFinite(n), `Expected numeric stat-views, got: ${txt}`);
  return n;
}

describe('TC_DASH_1 — Dashboard / profile view counts (mobile)', () => {
  it('view count increases after an anonymous visit records a view', async function () {
    if (process.env.MOBILE_E2E_RUN_TC_DASH_1 !== '1') {
      return this.skip();
    }

    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    await mobileLogin(OWNER_EMAIL, OWNER_PASSWORD);

    await goToProfileFromMenu();

    const storiesSection = await browser.$('#profile-stories-container');
    await storiesSection.waitForDisplayed({ timeout: 15_000 });
    const cards = await browser.$$('#profile-stories-container article');
    assert.ok(cards.length >= 1, 'Expected at least one published story on profile');
    const firstViewEl = await browser.$('#profile-stories-container article span[title="Views on this story"]');
    await firstViewEl.waitForDisplayed({ timeout: 10_000 });
    const firstStoryViewsTxt = (await firstViewEl.getText()).replace(/\D/g, '');
    assert.ok(firstStoryViewsTxt.length > 0, 'Expected visible per-story view count');

    const beforeViews = await readTotalViewsFromProfile();

    await browser.url('map.html');
    await browser.waitUntil(async () => (await browser.getUrl()).includes('map.html'), {
      timeout: 15_000,
      interval: 250,
    });

    await signOutFromMenu();

    await browser.url(`story-detail.html?id=${encodeURIComponent(SEEDED_STORY_ID)}`);
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('story-detail.html'),
      { timeout: 15_000, interval: 250 },
    );
    const title = await browser.$('#story-title');
    await title.waitForDisplayed({ timeout: 20_000 });

    const back = await browser.$('//a[contains(.,"Back to Map")]');
    await back.waitForDisplayed({ timeout: 10_000 });
    await back.click();
    await browser.waitUntil(async () => (await browser.getUrl()).includes('map.html'), {
      timeout: 15_000,
      interval: 250,
    });

    await openProfileMenu();
    const signIn = await browser.$('//a[@role="menuitem" and contains(.,"Sign In")]');
    await signIn.waitForDisplayed({ timeout: 10_000 });
    await signIn.click();
    await browser.waitUntil(async () => (await browser.getUrl()).includes('index.html'), {
      timeout: 15_000,
      interval: 250,
    });

    await mobileLogin(OWNER_EMAIL, OWNER_PASSWORD);
    await goToProfileFromMenu();

    await browser.waitUntil(
      async () => {
        const v = await readTotalViewsFromProfile();
        return v >= beforeViews + 1;
      },
      { timeout: 25_000, interval: 800, timeoutMsg: 'Total views did not increase after anonymous visit' },
    );
  });
});
