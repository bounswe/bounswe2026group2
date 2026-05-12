// UAT - Keyword tagging flows
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

const SEEDED_USER_EMAIL = process.env.UAT_SEEDED_EMAIL || 'seed_alice@example.com';
const SEEDED_USER_PASSWORD = process.env.UAT_SEEDED_PASSWORD || 'ValidPass1!';

async function loginSeededUserViaUi(page) {
  await page.goto('/index.html');
  await page.getByTestId('login-email').fill(SEEDED_USER_EMAIL);
  await page.getByTestId('login-password').fill(SEEDED_USER_PASSWORD);
  await page.getByTestId('login-submit').click();
  await page.waitForURL('**/map.html', { timeout: 5_000 });
}

async function addStoryTag(page, tagName) {
  await page.getByTestId('story-tag-input').fill(tagName);
  await page.getByTestId('story-tag-input').press('Enter');
  await expect(page.getByTestId('story-tag-chip').filter({ hasText: tagName })).toBeVisible();
}

async function setGalataLocation(page) {
  await page.fill('#location', 'Galata');

  // The map click is intentionally bypassed for headless stability. The
  // creation form requires coordinates and the story location field carries
  // the user-visible Galata selection.
  await page.evaluate(() => {
    document.getElementById('latitude').value = '41.0256';
    document.getElementById('longitude').value = '28.9744';
  });
}

// ---------------------------------------------------------------------------
// TC_TAG_1 - Keyword Tagging on Story Creation
// ---------------------------------------------------------------------------
test.describe('TC_TAG_1 - Keyword Tagging on Story Creation', () => {
  test.skip(
    'authenticated user creates a tagged story and finds it through tag search',
    async ({ page }) => {
      // Skipped until Backend: Keyword Tagging System #230 and Frontend:
      // Tag-Based Search & Filtering UI #243 are both shipped. This test relies
      // on the tag creation/search data-testid contract added by #243.
      const unique = Date.now();
      const title = `Tagged Galata Memory ${unique}`;
      const content = 'A 19th-century Ottoman memory from the streets around Galata.';

      await loginSeededUserViaUi(page);

      // Step 1: Open story creation page and fill story details.
      await page.goto('/story-create.html');
      await page.fill('#title', title);
      await page.fill('#story', content);
      await page.fill('#date-single', '01/01/1890');

      // Step 2: Add keyword tags through the tag input UI.
      await addStoryTag(page, 'ottoman');
      await addStoryTag(page, '19th-century');

      // Step 3: Select Galata as the story location.
      await setGalataLocation(page);

      // Step 4: Submit and verify creation success.
      const createResponsePromise = page.waitForResponse(
        response => response.url().includes('/stories') && response.request().method() === 'POST',
      );
      await page.click('#btn-publish');
      const createResponse = await createResponsePromise;
      expect(createResponse.status()).toBe(201);

      const createdStory = await createResponse.json();
      expect(createdStory.id).toBeTruthy();

      await Promise.race([
        page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
        page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
      ]);

      // Step 5: Search by tag and verify the created story is returned.
      await page.goto('/search.html');
      await page.getByTestId('tag-filter-input').fill('ottoman');
      await page.getByTestId('tag-filter-input').press('Enter');

      await expect(page.getByTestId('active-tag-filter').filter({ hasText: 'ottoman' })).toBeVisible();
      await expect(page.getByTestId('search-result-card').filter({ hasText: title })).toBeVisible();

      // Cleanup is intentionally left to the isolated UAT test database fixture.
      // There is no public author-owned story deletion endpoint at the time of
      // writing; use the captured createdStory.id above if one is added later.
    },
  );
});
