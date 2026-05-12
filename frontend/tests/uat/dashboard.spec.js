// UAT — Profile total view count (web). Mirrors manual steps against the deployed app.
//
// Default app origin for this file (CI / quick runs). Override any time:
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/uat/dashboard.spec.js

const { test, expect } = require('@playwright/test');
const { execSync } = require('node:child_process');
const path = require('node:path');

/** CI default frontend origin; env UAT_BASE_URL overrides for remote runs. */
const DEFAULT_UAT_BASE_URL = 'http://localhost:3000';

const UAT_EMAIL = process.env.UAT_OWNER_EMAIL || 'test@gmail.com';
const UAT_PASSWORD = process.env.UAT_OWNER_PASSWORD || 'Test1234%';
const SEEDED_STORY_ID =
  process.env.UAT_SEEDED_STORY_ID || 'bb43034b-8e1a-49a8-92b9-56346f50767a';

const profileBtn = (page) => page.locator('#site-header-profile-btn');
const profileMenu = (page) => page.locator('#site-header-profile-menu');

async function loginFromIndex(page) {
  await page.goto('/');
  await expect(page.getByTestId('login-form')).toBeVisible({ timeout: 20_000 });
  await page.getByTestId('login-email').fill(UAT_EMAIL);
  await page.getByTestId('login-password').fill(UAT_PASSWORD);
  await Promise.all([
    page.waitForURL('**/map.html', { timeout: 45_000 }),
    page.getByTestId('login-submit').click(),
  ]);
  await page.waitForLoadState('domcontentloaded');
  await expect(profileBtn(page)).toBeVisible({ timeout: 20_000 });
}

async function openAccountMenu(page) {
  const menu = profileMenu(page);
  if (await menu.isVisible()) return;
  await expect(profileBtn(page)).toBeVisible({ timeout: 20_000 });
  await profileBtn(page).click();
  await expect(menu).toBeVisible({ timeout: 15_000 });
}

async function clickViewProfile(page) {
  await openAccountMenu(page);
  await page.getByRole('menuitem', { name: 'View Profile' }).click();
  await page.waitForURL('**/profile.html', { timeout: 15_000 });
}

async function clickSignOut(page) {
  await openAccountMenu(page);
  await page.getByRole('menuitem', { name: 'Sign Out' }).click();
  await page.waitForURL('**/index.html', { timeout: 15_000 });
}

async function clickSignInFromMenu(page) {
  await openAccountMenu(page);
  await page.getByRole('menuitem', { name: 'Sign In' }).click();
  await page.waitForURL('**/index.html', { timeout: 15_000 });
}

async function waitForProfileStats(page) {
  await page.waitForResponse(
    (resp) =>
      resp.request().method() === 'GET' &&
      resp.ok() &&
      /\/users\/me\/stats(\?|$)/.test(resp.url()),
    { timeout: 25_000 }
  );
}

async function readTotalViews(page) {
  await expect(page.locator('#stat-views')).toBeVisible();
  const raw = (await page.locator('#stat-views').innerText()).trim();
  const n = Number.parseInt(raw, 10);
  expect(Number.isFinite(n), `Expected numeric view count, got: ${raw}`).toBeTruthy();
  return n;
}

/** Step 10: some builds use “Back to Map”; this repo’s story-detail may only expose the header brand or “View on full map”. */
async function leaveStoryDetailToMap(page) {
  const back = page.getByRole('link', { name: /Back to Map/i });
  if ((await back.count()) > 0) {
    await back.first().click();
  } else {
    await page.getByRole('link', { name: 'Local History Map' }).click();
  }
  await page.waitForURL('**/map.html', { timeout: 20_000 });
}

test.describe('TC_DASH — Profile view count (UAT script)', () => {
  test.use({ baseURL: DEFAULT_UAT_BASE_URL });

  test.beforeAll(() => {
    if (process.env.SKIP_UAT_SEED === '1') return;
    const repoRoot = path.resolve(__dirname, '../../..');
    execSync(
      [
        'docker compose run --rm -T',
        `-e SEED_EMAIL="${UAT_EMAIL}"`,
        `-e SEED_PASSWORD="${UAT_PASSWORD}"`,
        `-e SEED_STORY_ID="${SEEDED_STORY_ID}"`,
        "backend sh -c 'cd /app && PYTHONPATH=/app python scripts/seed_test_account.py'",
      ].join(' '),
      {
        cwd: repoRoot,
        stdio: 'inherit',
        env: { ...process.env },
      }
    );
  });

  test('view count after anonymous story visit matches manual UAT steps', async ({ page }) => {
    // 1–2
    await loginFromIndex(page);

    // 3–5
    await clickViewProfile(page);
    await waitForProfileStats(page);
    const viewsBefore = await readTotalViews(page);

    // 6
    await page.getByRole('link', { name: 'Local History Map' }).click();
    await page.waitForURL('**/map.html', { timeout: 15_000 });

    // 7–8
    await clickSignOut(page);

    // 9 (anonymous visit — should record at least one view for the story owner)
    await page.goto(`/story-detail.html?id=${encodeURIComponent(SEEDED_STORY_ID)}`);
    await expect(page.locator('#story-title')).not.toHaveText(/loading/i, { timeout: 20_000 });

    // 10
    await leaveStoryDetailToMap(page);

    // 11–13
    await clickSignInFromMenu(page);
    await loginFromIndex(page);

    // 14–16
    await clickViewProfile(page);
    await waitForProfileStats(page);

    await expect
      .poll(async () => readTotalViews(page), {
        timeout: 30_000,
        intervals: [300, 600, 1200, 2000, 3000],
      })
      .toBeGreaterThanOrEqual(viewsBefore + 1);
  });
});
