// UAT — Map flows
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

// Üsküdar coordinates
const USKUDAR = { lat: 41.0234, lng: 29.0153 };
// Galata coordinates
const GALATA = { lat: 41.0256, lng: 28.9744 };

// ---------------------------------------------------------------------------
// TC_MAP_2 — Multi-Location Story Display on Map
// ---------------------------------------------------------------------------
test.describe('TC_MAP_2 — Multi-Location Story Display on Map', () => {
  test.skip(
    'story pinned to two locations shows both markers on the map and both open the same story',
    async ({ page }) => {
      // Skipped until Backend: Multi-Location Story Support #231 and Frontend:
      // Multi-Location Story Support #241 are both shipped. This test relies
      // on the multi-location picker and the map rendering multiple markers
      // per story.
      const unique = Date.now();
      const title = `Multi-Pin Memory ${unique}`;
      const content = 'A story spanning Üsküdar and Galata, two shores of the Bosphorus.';

      await loginSeededUserViaUi(page);

      // ── Step 1: Open story creation page ──────────────────────────────────
      await page.goto('/story-create.html');

      // ── Step 2: Pin the first location (Üsküdar) via map click ────────────
      // Bypass the Leaflet map click for headless stability by invoking the
      // picker directly through the page context.
      await page.evaluate(({ lat, lng }) => {
        window.addPinFromMapClick(lat, lng);
      }, USKUDAR);

      // Assert the first location chip appears.
      const chips = page.locator('#location-chips [data-index]');
      await expect(chips).toHaveCount(1);

      // ── Step 3: Pin the second location (Galata) ──────────────────────────
      await page.evaluate(({ lat, lng }) => {
        window.addPinFromMapClick(lat, lng);
      }, GALATA);

      // Assert both location chips are now visible.
      await expect(chips).toHaveCount(2);

      // ── Step 4: Fill story text, location name, and date fields ───────────
      await page.fill('#title', title);
      await page.fill('#story', content);
      await page.fill('#location', 'Üsküdar – Galata');
      await page.fill('#date-single', '2024-06-15');

      // ── Step 5: Submit the story and capture the response ─────────────────
      const createResponsePromise = page.waitForResponse(
        response => response.url().includes('/stories') && response.request().method() === 'POST',
      );
      await page.click('#btn-publish');
      const createResponse = await createResponsePromise;
      expect(createResponse.status()).toBe(201);

      const createdStory = await createResponse.json();
      const storyId = createdStory.id;
      expect(storyId).toBeTruthy();

      await Promise.race([
        page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
        page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
      ]);

      // ── Step 6: Navigate to the map page and wait for stories to load ─────
      await page.goto('/map.html');
      await page.waitForResponse(
        response => response.url().includes('/stories') && response.request().method() === 'GET',
      );
      // Let the marker cluster layer render.
      await page.waitForTimeout(1_000);

      // ── Step 7: Assert the multi-location marker is visible on the map ────
      // Multi-location stories render a single marker with the "multi" class.
      // Clicking it enters focus mode which shows individual numbered pins.
      const multiMarker = page.locator('.story-marker.multi');
      await expect(multiMarker.first()).toBeVisible({ timeout: 10_000 });

      // Click the multi-location marker to enter focus mode.
      await multiMarker.first().click();

      // The focus banner should appear with the story title.
      const focusBanner = page.locator('#focus-banner');
      await expect(focusBanner).toBeVisible({ timeout: 5_000 });
      await expect(page.locator('#focus-banner-title')).toContainText(title);

      // Two numbered pins should be rendered (one per location) using the
      // buildNumberedIcon helper which applies the "multi-location-pin" class.
      const routePins = page.locator('.multi-location-pin');
      await expect(routePins).toHaveCount(2, { timeout: 10_000 });

      // ── Step 8: Click first pin and verify the story popup opens ──────────
      await routePins.nth(0).click();
      const popup = page.locator('.leaflet-popup-content');
      await expect(popup).toBeVisible({ timeout: 5_000 });
      await expect(popup).toContainText('Stop 1');
      await expect(popup).toContainText('Read Story');

      // ── Step 9: Click second pin and verify the same story link appears ───
      await page.locator('.leaflet-popup-close-button').click();
      await routePins.nth(1).click();
      await expect(popup).toBeVisible({ timeout: 5_000 });
      await expect(popup).toContainText('Stop 2');
      // Both pins link to the same story detail page.
      await expect(popup.locator('a[href*="story-detail.html"]')).toHaveAttribute('href', `story-detail.html?id=${storyId}`);
    },
  );
});
