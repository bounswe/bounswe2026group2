// UAT — Story flows
// Black-box tests against the running full-stack app (docker compose).
//
// Prerequisites:
//   ./localrun.sh   (or docker compose up --build)
//
// Run:
//   UAT_BASE_URL=http://localhost:3000 npm test          (from this directory)
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/uat/  (from frontend/)

const { test, expect } = require('@playwright/test');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function registerAndLogin(page, username, email, password) {
  await page.goto('/register.html');
  await page.getByTestId('register-username').fill(username);
  await page.getByTestId('register-email').fill(email);
  await page.getByTestId('register-password').fill(password);
  await page.getByTestId('register-confirm-password').fill(password);
  await page.getByTestId('register-terms').check();
  await page.getByTestId('register-submit').click();
  await page.waitForURL('**/index.html', { timeout: 5_000 });
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();
  await page.waitForURL('**/map.html', { timeout: 5_000 });
}

// ---------------------------------------------------------------------------
// TC_STORY_5 — Anonymous Story Sharing
// ---------------------------------------------------------------------------
test.describe('TC_STORY_5 — Anonymous Story Sharing', () => {
  test('author identity is hidden when story is published anonymously', async ({ browser }) => {
    const ts = Date.now();
    const authorUsername = `author${ts}`;
    const authorEmail = `author${ts}@example.com`;
    const readerUsername = `reader${ts}`;
    const readerEmail = `reader${ts}@example.com`;
    const password = 'Test@1234';

    // ── Step 1: Register and log in as the author ────────────────────────────
    const authorContext = await browser.newContext();
    const authorPage = await authorContext.newPage();
    await registerAndLogin(authorPage, authorUsername, authorEmail, password);

    // ── Step 2: Open story creation page ─────────────────────────────────────
    await authorPage.goto('/story-create.html');

    // ── Step 3: Fill in title, content, location name, date, and coordinates ─
    await authorPage.fill('#title', 'Old Fountain');
    await authorPage.fill('#story', 'A forgotten fountain in the heart of the old city.');
    await authorPage.fill('#location', 'Istanbul');
    await authorPage.fill('#date-single', '2024-01-01');

    // Set lat/lng hidden fields directly — the Leaflet map click is not
    // reliable in headless mode and the submit handler requires these values.
    await authorPage.evaluate(() => {
      document.getElementById('latitude').value = '41.0082';
      document.getElementById('longitude').value = '28.9784';
    });

    // ── Step 4: Enable anonymous toggle and assert it is visually selected ───
    await authorPage.click('#anon-card');
    await expect(authorPage.locator('#anon-card')).toHaveAttribute('aria-checked', 'true');
    await expect(authorPage.locator('#is-anonymous')).toHaveValue('true');

    // ── Step 5: Submit and capture the new story ID from the API response ────
    // waitForResponse resolves as soon as the POST /stories response arrives,
    // before the page redirects or shows the badge modal.
    const responsePromise = authorPage.waitForResponse(
      r => r.url().includes('/stories') && r.request().method() === 'POST',
    );
    await authorPage.click('#btn-publish');
    const createResponse = await responsePromise;
    expect(createResponse.status()).toBe(201);
    const createdStory = await createResponse.json();
    const storyId = createdStory.id;
    expect(storyId).toBeTruthy();

    // Wait for either the success banner or the badge-unlock modal so the
    // browser has finished processing the response before we move on.
    await Promise.race([
      authorPage.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      authorPage.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    // ── Step 6: Open the story as a logged-in reader ─────────────────────────
    const readerContext = await browser.newContext();
    const readerPage = await readerContext.newPage();
    await registerAndLogin(readerPage, readerUsername, readerEmail, password);
    await readerPage.goto(`/story-detail.html?id=${storyId}`);

    // Story detail loads asynchronously; expect() retries until timeout.
    await expect(readerPage.locator('#story-author')).toContainText('Anonymous');
    await expect(readerPage.locator('#story-author')).not.toContainText(authorUsername);

    // ── Step 7: Open the story as an unauthenticated visitor ─────────────────
    const visitorContext = await browser.newContext();
    const visitorPage = await visitorContext.newPage();
    await visitorPage.goto(`/story-detail.html?id=${storyId}`);

    await expect(visitorPage.locator('#story-author')).toContainText('Anonymous');
    await expect(visitorPage.locator('#story-author')).not.toContainText(authorUsername);

    // ── Step 8: Assert story content is visible ───────────────────────────────
    await expect(visitorPage.locator('#story-content')).toContainText(
      'A forgotten fountain in the heart of the old city.',
    );

    await authorContext.close();
    await readerContext.close();
    await visitorContext.close();
  });
});
