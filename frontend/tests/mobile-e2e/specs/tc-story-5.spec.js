// TC_STORY_5 — Anonymous Story Sharing (mobile Appium / WebdriverIO)
//
// Skipped until #242 (Frontend: Anonymous Story Sharing UI) ships on dev.
// When #242 merges:
//   1. Remove describe.skip — change to describe(...)
//   2. Uncomment Step 4: add the anonymous toggle click + assertion using the
//      data-testid="story-anonymous-toggle" added by that PR
//   3. Uncomment Step 5: add the post-submit redirect assertion once #242
//      defines the redirect behaviour (currently redirects to map.html)
//   4. Replace '#story-author' with data-testid once #242 adds it
//
// Two-user flow (sequential single Appium session):
//   Author registers → creates anonymous story → session cleared
//   Reader registers/logs in → opens story → asserts author is anonymous
//   Session cleared → visitor opens story → asserts author is anonymous

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
  await $('[data-testid="register-username"]').setValue(username);
  await $('[data-testid="register-email"]').setValue(email);
  await $('[data-testid="register-password"]').setValue(password);
  await $('[data-testid="register-confirm-password"]').setValue(password);
  await $('[data-testid="register-terms"]').click();
  await $('[data-testid="register-submit"]').click();
  await $('[data-testid="login-email"]').waitForExist({ timeout: 8_000 });
  await $('[data-testid="login-email"]').setValue(email);
  await $('[data-testid="login-password"]').setValue(password);
  await $('[data-testid="login-submit"]').click();
  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('map.html'),
    { timeout: 8_000, timeoutMsg: 'expected to reach map.html after login' }
  );
}

async function clearSession() {
  await browser.execute(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
  });
}

describe.skip('TC_STORY_5 — Anonymous Story Sharing', () => {
  before(async () => {
    await switchToFirstWebviewContext();
  });

  it('author identity is hidden when story is published anonymously', async () => {
    // ── Step 1: Register and log in as the author ────────────────────────────
    await registerAndLogin(AUTHOR_USERNAME, AUTHOR_EMAIL, PASSWORD);

    // ── Step 2: Open story creation page ─────────────────────────────────────
    await navigateTo('/story-create.html');

    // ── Step 3: Fill in title, content, date and location ────────────────────
    await $('#title').setValue('Old Fountain');
    await $('#story').setValue('A forgotten fountain in the heart of the old city.');
    await $('#location').setValue('Istanbul');
    await $('#date-single').setValue('01/01/2024');

    // ── Step 4: Enable anonymous toggle — assert it is visually selected ─────
    // TODO: uncomment once #242 adds the anonymous toggle with data-testid
    // await $('[data-testid="story-anonymous-toggle"]').click();
    // assert.ok(
    //   await $('[data-testid="story-anonymous-toggle"]').isSelected(),
    //   'anonymous toggle must be checked before submitting'
    // );

    // ── Step 5: Submit and assert story is published ──────────────────────────
    await $('#btn-publish').click();
    // TODO: assert post-submit state once #242 defines redirect / success element
    // Currently story-create.html redirects to map.html on success; #242 may change
    // this to story-detail.html or expose a dedicated success indicator.
    // e.g.  await browser.waitUntil(
    //         async () => (await browser.getUrl()).includes('story-detail.html'),
    //         { timeout: 8_000 }
    //       );

    // ── Step 6: Capture the story URL (contains story ID for later navigation)
    // TODO: once the post-submit redirect lands on story-detail.html, remove the
    // comment below and use browser.getUrl() directly.
    // const storyUrl = await browser.getUrl();
    const storyUrl = await browser.getUrl(); // placeholder — likely map.html until #242

    // ── Step 7: Clear author session and register/login as reader ────────────
    await clearSession();
    await registerAndLogin(READER_USERNAME, READER_EMAIL, PASSWORD);

    // ── Step 8: Navigate to the story as the reader and verify anonymous author
    await browser.url(storyUrl);
    // TODO: replace '#story-author' with data-testid once #242 defines it
    const authorEl = await $('#story-author');
    await authorEl.waitForExist({ timeout: 5_000 });
    const authorText = await authorEl.getText();
    assert.ok(!authorText.includes(AUTHOR_USERNAME), 'real author username must not be visible to a logged-in reader');
    assert.ok(authorText.includes('Anonymous'), 'author must appear as Anonymous to a logged-in reader');

    // ── Step 9: Clear reader session and open story as unauthenticated visitor
    await clearSession();
    await browser.url(storyUrl);
    const visitorAuthorEl = await $('#story-author');
    await visitorAuthorEl.waitForExist({ timeout: 5_000 });
    const visitorAuthorText = await visitorAuthorEl.getText();
    assert.ok(!visitorAuthorText.includes(AUTHOR_USERNAME), 'real author username must not be visible to an unauthenticated visitor');
    assert.ok(visitorAuthorText.includes('Anonymous'), 'author must appear as Anonymous to an unauthenticated visitor');

    // ── Step 10: Assert story content is visible ──────────────────────────────
    const contentEl = await $('#story-content');
    await contentEl.waitForExist({ timeout: 5_000 });
    const contentText = await contentEl.getText();
    assert.ok(contentText.includes('Old Fountain'), 'story content must remain visible regardless of anonymous setting');
  });
});
