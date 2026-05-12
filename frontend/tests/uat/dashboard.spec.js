// UAT — Dashboard / Profile view count flow (web only; see tests/mobile-e2e for Appium).
//
// TC_DASH_1 — A user sees view counts; after another view, the count increases.

const { test, expect } = require('@playwright/test');

const OWNER_EMAIL = process.env.UAT_OWNER_EMAIL || 'test@gmail.com';
const OWNER_PASSWORD = process.env.UAT_OWNER_PASSWORD || 'Test1234%';

// Seeded story id used in the original UAT scenario (#276 / #276 steps).
const SEEDED_STORY_ID =
  process.env.UAT_SEEDED_STORY_ID || 'bb43034b-8e1a-49a8-92b9-56346f50767a';

async function login(page, { email, password }) {
  await page.goto('/');
  await expect(page.getByTestId('login-form')).toBeVisible();
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(password);
  // Attach the navigation wait before the click (best practice) and allow for
  // slow backend/auth under load.
  await Promise.all([
    page
      .waitForURL('**/map.html', { timeout: 30_000 })
      .catch(() => null), // some builds don't always redirect; token check below covers it
    page.getByTestId('login-submit').click(),
  ]);

  // If the app did not redirect but token exists, navigate explicitly.
  await page
    .waitForFunction(() => !!localStorage.getItem('auth_token'), null, { timeout: 30_000 })
    .catch(() => null);
  const token = await page.evaluate(() => localStorage.getItem('auth_token'));
  if (token && !/map\.html/.test(page.url())) {
    await page.goto('/map.html');
    await page.waitForURL('**/map.html', { timeout: 30_000 });
  }
}

async function openProfileMenu(page) {
  const button = page.locator('#btn-profile');
  await expect(button).toBeVisible();
  await button.click();
  await expect(page.locator('#profile-menu')).toBeVisible();
}

async function goToProfileFromMenu(page) {
  await openProfileMenu(page);
  await page.getByRole('menuitem', { name: 'View Profile' }).click();
  await page.waitForURL('**/profile.html', { timeout: 10_000 });
}

async function signOutFromMenu(page) {
  await openProfileMenu(page);
  await page.getByRole('menuitem', { name: 'Sign Out' }).click();
  // Best-effort: some builds redirect immediately, others just clear the token.
  await page.waitForTimeout(250);
}

async function readTotalViewsFromProfile(page) {
  await expect(page.locator('#stat-views')).toBeVisible();
  await expect(page.locator('#stat-views')).not.toHaveText('…');
  const txt = (await page.locator('#stat-views').innerText()).trim();
  const n = Number.parseInt(txt, 10);
  expect(Number.isFinite(n)).toBeTruthy();
  return n;
}

test.describe('TC_DASH_1 — Dashboard view counts', () => {
  test('view count increases after another user views a story', async ({ browser }) => {
    // Owner context (stays logged in)
    const ownerContext = await browser.newContext();
    const ownerPage = await ownerContext.newPage();

    await login(ownerPage, { email: OWNER_EMAIL, password: OWNER_PASSWORD });

    // Steps 3-6: profile menu → view profile → read views → go back to map
    await goToProfileFromMenu(ownerPage);
    const beforeViews = await readTotalViewsFromProfile(ownerPage);

    await ownerPage.getByRole('link', { name: 'Local History Map' }).click();
    await ownerPage.waitForURL('**/map.html', { timeout: 10_000 });

    // Steps 7-8: sign out (owner session ends)
    await signOutFromMenu(ownerPage);

    // Second context: unauthenticated user views story to record a view
    const viewerContext = await browser.newContext();
    const viewerPage = await viewerContext.newPage();

    // Steps 9-10: open story detail, then go back to map
    await viewerPage.goto(`/story-detail.html?id=${encodeURIComponent(SEEDED_STORY_ID)}`);
    await expect(viewerPage.locator('#story-title')).toBeVisible();
    await viewerPage.getByRole('link', { name: /Back to Map/i }).first().click();
    await viewerPage.waitForURL('**/map.html', { timeout: 10_000 });

    await viewerContext.close();

    // Steps 11-16: sign back in and verify views increased
    await openProfileMenu(ownerPage);
    await ownerPage.getByRole('menuitem', { name: 'Sign In' }).click();
    await ownerPage.waitForURL('**/index.html', { timeout: 10_000 });

    await login(ownerPage, { email: OWNER_EMAIL, password: OWNER_PASSWORD });
    await goToProfileFromMenu(ownerPage);

    // The profile stats load async; poll until the count updates.
    await expect
      .poll(async () => readTotalViewsFromProfile(ownerPage), {
        timeout: 20_000,
        intervals: [250, 500, 1000, 1500, 2000],
      })
      .toBeGreaterThanOrEqual(beforeViews + 1);

    await ownerContext.close();
  });
});

