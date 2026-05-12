// UAT - Badge award flows
// Black-box tests against the running full-stack app (docker compose).
//
// Prerequisites:
//   ./localrun.sh   (or docker compose up --build)
//
// Run:
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/uat/badge.spec.js  (from frontend/)

const { test, expect } = require('@playwright/test');

const PASSWORD = 'Test@1234';
const FIRST_STORY_BADGE = /First (Post|Story)/i;

async function registerAndLogin(page) {
  const ts = Date.now();
  const username = `badgeuser${ts}`;
  const email = `badgeuser${ts}@example.com`;

  await page.goto('/register.html');
  await page.getByTestId('register-username').fill(username);
  await page.getByTestId('register-email').fill(email);
  await page.getByTestId('register-password').fill(PASSWORD);
  await page.getByTestId('register-confirm-password').fill(PASSWORD);
  await page.getByTestId('register-terms').check();
  await page.getByTestId('register-submit').click();

  await expect(page.getByTestId('register-success')).toBeVisible();
  await page.waitForURL('**/index.html', { timeout: 5_000 });

  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(PASSWORD);
  await page.getByTestId('login-submit').click();

  await page.waitForURL('**/map.html', { timeout: 5_000 });

  return { username, email };
}

async function expectNoFirstStoryBadgeOnProfile(page) {
  await page.goto('/profile.html');
  await expect(page.locator('#profile-badges')).toBeVisible();
  await expect(page.locator('#profile-badges')).toContainText('No badges earned yet');
  await expect(page.locator('#profile-badges')).not.toContainText(FIRST_STORY_BADGE);
}

async function expectSingleFirstStoryBadgeOnProfile(page) {
  await page.goto('/profile.html');
  await expect(page.locator('#profile-badges')).toContainText(FIRST_STORY_BADGE);
  await expect(page.locator('#profile-badges span').filter({ hasText: FIRST_STORY_BADGE })).toHaveCount(1);
}

async function fillRequiredStoryFields(page, storyNumber) {
  await page.goto('/story-create.html');

  await page.locator('#title').fill(`TC_BADGE_1 Story ${storyNumber}`);
  await page.locator('#story').fill(
    `Automated acceptance story ${storyNumber} for verifying the first story badge award flow.`
  );
  await page.locator('#location').fill('Bogazici University, Istanbul');
  await page.locator('#date-single').fill('05/12/2026');

  await page.evaluate(() => {
    document.querySelector('#latitude').value = '41.0857';
    document.querySelector('#longitude').value = '29.0448';
  });
}

async function publishStory(page, storyNumber) {
  await fillRequiredStoryFields(page, storyNumber);
  await page.locator('#btn-publish').click();
}

test.describe('TC_BADGE_1 - First post badge awarded', () => {
  test('awards the first story badge once and displays it on the profile', async ({ page }) => {
    await registerAndLogin(page);

    await expectNoFirstStoryBadgeOnProfile(page);

    await publishStory(page, 1);

    const badgeModal = page.locator('#badge-unlock-modal');
    await expect(badgeModal).toBeVisible({ timeout: 10_000 });
    await expect(badgeModal).toContainText(FIRST_STORY_BADGE);

    await page.locator('#badge-keep-publishing').click();
    await page.waitForURL('**/story-create.html', { timeout: 5_000 });

    await expectSingleFirstStoryBadgeOnProfile(page);

    await publishStory(page, 2);

    await expect(page.locator('#badge-unlock-modal')).toBeHidden({ timeout: 10_000 });
    await expect(page.locator('#form-success')).toContainText('Story published successfully');

    await expectSingleFirstStoryBadgeOnProfile(page);
  });
});
