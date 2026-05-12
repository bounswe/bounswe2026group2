// TC_BADGE_1 - First Post Badge Awarded (mobile Appium / WebdriverIO)
//
// Black-box test against the Capacitor WebView. Requires a running Appium
// server, a connected Android device/emulator with the debug APK installed,
// and the backend reachable at MOBILE_API_BASE_URL.
//
// The test is skipped automatically when no WEBVIEW context is available.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

const TS = Date.now();
const USERNAME = `badgeuser${TS}`;
const EMAIL = `badgeuser${TS}@example.com`;
const PASSWORD = 'Test@1234';
const FIRST_STORY_BADGE = /First (Post|Story)/i;

async function getAppOrigin() {
  const url = await browser.getUrl();
  return new URL(url).origin;
}

async function navigateTo(path) {
  const origin = await getAppOrigin();
  await browser.url(`${origin}${path}`);
}

async function registerAndLogin() {
  await navigateTo('/register.html');

  await (await browser.$('[data-testid="register-username"]')).setValue(USERNAME);
  await (await browser.$('[data-testid="register-email"]')).setValue(EMAIL);
  await (await browser.$('[data-testid="register-password"]')).setValue(PASSWORD);
  await (await browser.$('[data-testid="register-confirm-password"]')).setValue(PASSWORD);

  await browser.execute(() => {
    const cb = document.querySelector('[data-testid="register-terms"]');
    if (cb && !cb.checked) cb.click();
  });

  await (await browser.$('[data-testid="register-submit"]')).click();
  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('index.html'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to index.html after registration' },
  );

  await (await browser.$('[data-testid="login-email"]')).setValue(EMAIL);
  await (await browser.$('[data-testid="login-password"]')).setValue(PASSWORD);
  await (await browser.$('[data-testid="login-submit"]')).click();
  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('map.html'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to map.html after login' },
  );
}

async function getBadgeSectionText() {
  return browser.execute(() => {
    const badges = document.querySelector('#profile-badges');
    return badges ? badges.textContent : '';
  });
}

async function getFirstStoryBadgeCount() {
  return browser.execute((patternSource) => {
    const pattern = new RegExp(patternSource, 'i');
    return Array.from(document.querySelectorAll('#profile-badges span'))
      .filter((el) => pattern.test(el.textContent || '')).length;
  }, FIRST_STORY_BADGE.source);
}

async function expectNoFirstStoryBadgeOnProfile() {
  await navigateTo('/profile.html');
  await (await browser.$('#profile-badges')).waitForExist({ timeout: 10_000 });

  await browser.waitUntil(
    async () => (await getBadgeSectionText()).includes('No badges earned yet'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Profile did not show the empty badge state' },
  );

  const badgeText = await getBadgeSectionText();
  assert.ok(!FIRST_STORY_BADGE.test(badgeText), `first story badge should not be visible yet: "${badgeText}"`);
}

async function expectSingleFirstStoryBadgeOnProfile() {
  await navigateTo('/profile.html');
  await (await browser.$('#profile-badges')).waitForExist({ timeout: 10_000 });

  await browser.waitUntil(
    async () => FIRST_STORY_BADGE.test(await getBadgeSectionText()),
    { timeout: 10_000, interval: 500, timeoutMsg: 'First story badge did not appear on profile' },
  );

  const badgeCount = await getFirstStoryBadgeCount();
  assert.strictEqual(badgeCount, 1, `expected exactly one first story badge, got ${badgeCount}`);

  const imageLoaded = await browser.execute((patternSource) => {
    const pattern = new RegExp(patternSource, 'i');
    const badgeCard = Array.from(document.querySelectorAll('#profile-badges div'))
      .find((el) => pattern.test(el.textContent || ''));
    const image = badgeCard ? badgeCard.querySelector('img') : null;
    return Boolean(image && image.complete && image.naturalWidth > 0 && image.naturalHeight > 0);
  }, FIRST_STORY_BADGE.source);

  assert.ok(imageLoaded, 'profile first story badge image should load from bundled assets');
}

async function fillRequiredStoryFields(storyNumber) {
  await navigateTo('/story-create.html');

  await (await browser.$('#title')).setValue(`TC_BADGE_1 Story ${storyNumber}`);
  await (await browser.$('#story')).setValue(
    `Automated mobile story ${storyNumber} for verifying the first story badge award flow.`,
  );
  await (await browser.$('#location')).setValue('Bogazici University, Istanbul');
  await (await browser.$('#date-single')).setValue('2026-05-12');

  await browser.execute(() => {
    document.querySelector('#latitude').value = '41.0857';
    document.querySelector('#longitude').value = '29.0448';
  });
}

async function publishStory(storyNumber) {
  await fillRequiredStoryFields(storyNumber);
  await (await browser.$('#btn-publish')).click();
}

async function expectBadgeUnlockModal() {
  const modal = await browser.$('#badge-unlock-modal');
  await browser.waitUntil(
    async () => {
      const classes = await modal.getAttribute('class');
      return !classes.includes('hidden');
    },
    { timeout: 10_000, interval: 500, timeoutMsg: 'Badge unlock modal did not appear' },
  );

  const modalText = await modal.getText();
  assert.ok(FIRST_STORY_BADGE.test(modalText), `badge modal should mention the first story badge: "${modalText}"`);

  const imageLoaded = await browser.execute(() => {
    const image = document.querySelector('#badge-unlock-image');
    return Boolean(
      image
        && image.getAttribute('src')
        && image.getAttribute('src').includes('assets/1st story.png')
        && image.complete
        && image.naturalWidth > 0
        && image.naturalHeight > 0,
    );
  });

  assert.ok(imageLoaded, 'badge unlock image should load from bundled assets');
}

async function expectNoBadgeUnlockModalAfterSecondStory() {
  await browser.waitUntil(
    async () => {
      const success = await browser.$('#form-success');
      return (await success.isExisting()) && (await success.getText()).includes('Story published successfully');
    },
    { timeout: 10_000, interval: 500, timeoutMsg: 'Second story success confirmation did not appear' },
  );

  const modalVisible = await browser.execute(() => {
    const modal = document.querySelector('#badge-unlock-modal');
    return Boolean(modal && !modal.classList.contains('hidden'));
  });

  assert.strictEqual(modalVisible, false, 'second story should not show a duplicate first story badge modal');
}

describe('TC_BADGE_1 - First post badge awarded', () => {
  it('awards the first story badge once and displays it on the profile', async function () {
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    await registerAndLogin();

    await expectNoFirstStoryBadgeOnProfile();

    await publishStory(1);
    await expectBadgeUnlockModal();

    await (await browser.$('#badge-keep-publishing')).click();
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('story-create.html'),
      { timeout: 5_000, interval: 500, timeoutMsg: 'Keep publishing did not open story-create.html' },
    );

    await expectSingleFirstStoryBadgeOnProfile();

    await publishStory(2);
    await expectNoBadgeUnlockModalAfterSecondStory();

    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('map.html'),
      { timeout: 10_000, interval: 500, timeoutMsg: 'Second publish did not redirect to map.html' },
    );

    await expectSingleFirstStoryBadgeOnProfile();
  });
});
