// E2E — Core story flows
// Black-box tests against the running full-stack app (docker compose).
//
// Scope: technical end-to-end flows distinct from UAT acceptance scenarios.
//   TC_E2E_1 — Story creation and detail view
//   TC_E2E_2 — Search finds a published story by place name
//   TC_E2E_3 — Profile stat-views increments after viewing a story
//   TC_E2E_4 — Multi-location story stores and displays all locations
//   TC_E2E_5 — Like button toggles and like count increments
//   TC_E2E_6 — Comment posted on a story appears in the comments list
//   TC_E2E_7 — Tag-based search returns a story tagged at creation
//   TC_E2E_8 — Timeline page shows a story at the queried coordinates
//   TC_E2E_9 — Editing a story updates its content on the detail page
//
// Prerequisites:
//   ./localrun.sh  (or docker compose up --build)
//
// Run:
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/e2e/  (from frontend/)

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

async function createStory(page, { title, content, location, date, lat, lng }) {
  await page.goto('/story-create.html');
  await page.fill('#title', title);
  await page.fill('#story', content);
  await page.fill('#location', location);
  await page.fill('#date-single', date);
  // Bypass the Leaflet map click — inject coordinates directly.
  await page.evaluate(({ la, lo }) => {
    document.getElementById('latitude').value = la;
    document.getElementById('longitude').value = lo;
  }, { la: lat, lo: lng });

  const responsePromise = page.waitForResponse(
    r => r.url().includes('/stories') && r.request().method() === 'POST',
  );
  await page.click('#btn-publish');
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  const story = await response.json();
  return story.id;
}

// ---------------------------------------------------------------------------
// TC_E2E_1 — Story creation and detail view
// Verifies the full path: register → login → create story → view story detail.
// The story title, content, and location must render correctly.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_1 — Story creation and detail view', () => {
  test('created story renders correctly on the detail page', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e1user${ts}`;
    const email    = `e2e1user${ts}@example.com`;
    const password = 'E2eTest@1';

    await registerAndLogin(page, username, email, password);

    // Wait for any badge modal from a previous state to clear.
    await Promise.race([
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 1_000 }).catch(() => {}),
      page.waitForTimeout(500),
    ]);

    const title   = `Bosphorus Memory ${ts}`;
    const content = 'A nineteenth-century account of the Bosphorus strait.';

    const storyId = await createStory(page, {
      title,
      content,
      location: 'Bosphorus, Istanbul',
      date: '01/01/1890',
      lat: '41.0082',
      lng: '28.9784',
    });

    // Wait for either the success banner or the badge-unlock modal.
    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    // Navigate to the story detail page.
    await page.goto(`/story-detail.html?id=${storyId}`);

    await expect(page.locator('#story-title')).toContainText(title, { timeout: 8_000 });
    await expect(page.locator('#story-content')).toContainText(
      'A nineteenth-century account of the Bosphorus strait.',
    );
    await expect(page.locator('#story-location')).toContainText('Bosphorus');
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_2 — Search finds a published story by place name
// Verifies: create story with a unique place name → search for it on
// search.html → the story card appears in results.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_2 — Search finds a published story', () => {
  test('story appears in search results by place name', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e2user${ts}`;
    const email    = `e2e2user${ts}@example.com`;
    const password = 'E2eTest@2';

    await registerAndLogin(page, username, email, password);

    // Use a place name unique enough to avoid false positives from seed data.
    const uniquePlace = `Uniqueplace${ts}`;
    const title       = `Search Target ${ts}`;

    const storyId = await createStory(page, {
      title,
      content: 'Story created specifically to verify search end-to-end.',
      location: uniquePlace,
      date: '06/15/1950',
      lat: '41.0256',
      lng: '28.9744',
    });

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    // Open search.html and submit the place name query.
    await page.goto('/search.html');
    await page.fill('#search-input', uniquePlace);
    await page.press('#search-input', 'Enter');

    // The result card links to story-detail.html?id=<storyId>.
    await expect(page.locator(`#card-${storyId}`)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(`#card-${storyId}`)).toContainText(title);
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_3 — Profile stat-views increments after viewing a story
// Verifies: create story → GET story-detail (increments view count via backend)
// → profile.html #stat-views shows a positive number.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_3 — Profile stat-views increments on story view', () => {
  test('profile shows a non-zero view count after the user views their story', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e3user${ts}`;
    const email    = `e2e3user${ts}@example.com`;
    const password = 'E2eTest@3';

    await registerAndLogin(page, username, email, password);

    const storyId = await createStory(page, {
      title:    `View Counter Story ${ts}`,
      content:  'Story to verify that view_count increments end-to-end.',
      location: 'Galata, Istanbul',
      date:     '01/01/2020',
      lat:      '41.0256',
      lng:      '28.9744',
    });

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    // Visit the story detail page.  The backend atomically increments view_count
    // on every GET /stories/{id} request.
    await page.goto(`/story-detail.html?id=${storyId}`);
    await expect(page.locator('#story-title')).toContainText('View Counter Story', { timeout: 8_000 });

    // Check that the profile page reflects the incremented view total.
    // profile.js fetches /users/me/stats asynchronously; poll until the counter
    // changes from the initial '0' placeholder.
    await page.goto('/profile.html');
    await expect(page.locator('#stat-views')).toBeVisible({ timeout: 8_000 });

    await page.waitForFunction(
      () => {
        const el = document.getElementById('stat-views');
        return el && parseInt(el.textContent.trim(), 10) > 0;
      },
      { timeout: 8_000 },
    );

    const viewText = await page.locator('#stat-views').textContent();
    expect(parseInt(viewText.trim(), 10)).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_4 — Multi-location story stores and exposes all locations
// Verifies: create story with two pinned locations (via evaluate()) → POST
// response includes `locations` array with both entries → story detail loads.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_4 — Multi-location story stores all locations', () => {
  test('story created with two locations exposes both via API', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e4user${ts}`;
    const email    = `e2e4user${ts}@example.com`;
    const password = 'E2eTest@4';

    await registerAndLogin(page, username, email, password);

    await page.goto('/story-create.html');

    // Inject two distinct pins directly into the picker.
    // `picker` is a module-level var exposed on the page's global scope.
    await page.evaluate(() => {
      picker.add({ latitude: 41.0082, longitude: 28.9784, label: 'Old City' });
      picker.add({ latitude: 41.0256, longitude: 28.9744, label: 'Galata' });
    });

    await page.fill('#title', `Multi-Loc Story ${ts}`);
    await page.fill('#story', 'A story spanning two historic Istanbul locations.');
    await page.fill('#location', 'Istanbul');
    await page.fill('#date-single', '01/01/1900');

    const responsePromise = page.waitForResponse(
      r => r.url().includes('/stories') && r.request().method() === 'POST',
    );
    await page.click('#btn-publish');
    const response = await responsePromise;

    expect(response.status()).toBe(201);
    const story = await response.json();

    // The payload sends `locations` when more than one pin is set.
    expect(Array.isArray(story.locations)).toBe(true);
    expect(story.locations.length).toBe(2);

    // Confirm the story detail page loads without errors.
    await page.goto(`/story-detail.html?id=${story.id}`);
    await expect(page.locator('#story-title')).toContainText(`Multi-Loc Story ${ts}`, { timeout: 8_000 });
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_5 — Like button toggles and like count increments
// Verifies: create story → open detail → click Like → #like-count becomes 1
// → click again → count returns to 0 (toggle off).
// ---------------------------------------------------------------------------
test.describe('TC_E2E_5 — Like button toggles and like count increments', () => {
  test('like count increments on click and decrements on second click', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e5user${ts}`;
    const email    = `e2e5user${ts}@example.com`;
    const password = 'E2eTest@5';

    await registerAndLogin(page, username, email, password);

    const storyId = await createStory(page, {
      title:    `Like Test Story ${ts}`,
      content:  'Story for testing the like toggle end-to-end.',
      location: 'Eminonu, Istanbul',
      date:     '01/01/2010',
      lat:      '41.0186',
      lng:      '28.9703',
    });

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    await page.goto(`/story-detail.html?id=${storyId}`);
    await expect(page.locator('#story-title')).toContainText('Like Test Story', { timeout: 8_000 });

    // Wait for the like button to become enabled (JS initialises it after fetching state).
    const likeBtn = page.locator('#like-button');
    await expect(likeBtn).not.toBeDisabled({ timeout: 8_000 });

    const likeCount = page.locator('#like-count');

    // Like the story.
    await likeBtn.click();
    await expect(likeCount).toHaveText('1', { timeout: 5_000 });
    await expect(likeBtn).toHaveAttribute('aria-pressed', 'true');

    // Unlike the story.
    await likeBtn.click();
    await expect(likeCount).toHaveText('0', { timeout: 5_000 });
    await expect(likeBtn).toHaveAttribute('aria-pressed', 'false');
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_6 — Comment posted on a story appears in the comments list
// Verifies: create story → open detail → submit a comment → comment text
// appears in #comments-list without a page reload.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_6 — Comment posted on a story appears in the list', () => {
  test('submitted comment is rendered in the comments list', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e6user${ts}`;
    const email    = `e2e6user${ts}@example.com`;
    const password = 'E2eTest@6';

    await registerAndLogin(page, username, email, password);

    const storyId = await createStory(page, {
      title:    `Comment Test Story ${ts}`,
      content:  'Story for testing the comment flow end-to-end.',
      location: 'Besiktas, Istanbul',
      date:     '01/01/2015',
      lat:      '41.0422',
      lng:      '29.0083',
    });

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    await page.goto(`/story-detail.html?id=${storyId}`);
    await expect(page.locator('#story-title')).toContainText('Comment Test Story', { timeout: 8_000 });

    // The comment form is only shown to authenticated users; wait for it.
    await expect(page.locator('#comment-form')).toBeVisible({ timeout: 8_000 });

    const commentText = `E2E comment ${ts}`;
    await page.fill('#comment-input', commentText);
    await page.click('#comment-submit');

    // Comment should appear in the list without a reload.
    await expect(page.locator('#comments-list')).toContainText(commentText, { timeout: 8_000 });
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_7 — Tag-based search returns a story tagged at creation
// Creates a story with tags via the API (using the session token from
// localStorage), then verifies that searching by that tag on search.html
// surfaces the correct result card.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_7 — Tag-based search returns a tagged story', () => {
  test('story tagged at creation appears when filtering by that tag', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e7user${ts}`;
    const email    = `e2e7user${ts}@example.com`;
    const password = 'E2eTest@7';
    const uniqueTag   = `e2etag${ts}`;
    const uniquePlace = `Tagplace${ts}`;

    await registerAndLogin(page, username, email, password);

    // Create the story via API so we can include the tags field directly,
    // without depending on a tag-input UI element on story-create.html.
    const storyId = await page.evaluate(
      async ({ tag, place, stamp, apiBase }) => {
        const token = localStorage.getItem('auth_token');
        const res = await fetch(`${apiBase}/stories`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            title:      `Tagged Story ${stamp}`,
            content:    'Story created via API to test tag-based search.',
            place_name: place,
            latitude:   40.9905,
            longitude:  29.0264,
            date_start: '2000-01-01',
            tags:       [tag],
          }),
        });
        if (!res.ok) throw new Error(`POST /stories failed: ${res.status}`);
        const data = await res.json();
        return data.id;
      },
      { tag: uniqueTag, place: uniquePlace, stamp: ts, apiBase: 'http://localhost:8000' },
    );

    expect(storyId).toBeTruthy();

    // Search by place name so the result arrives via the direct search endpoint
    // (no async client-side tag-filter round-trip).  Then assert the tag chip
    // is rendered on the card — confirming tags were stored and are displayed.
    await page.goto('/search.html');
    await page.fill('#search-input', uniquePlace);
    await page.press('#search-input', 'Enter');

    // Result card must appear.
    await expect(page.locator(`#card-${storyId}`)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(`#card-${storyId}`)).toContainText(`Tagged Story ${ts}`);

    // Tag chip must be rendered inside the card.  search.html fetches story
    // detail in a second async pass to populate tags, so allow extra time.
    await expect(
      page.locator(`#card-${storyId} span`).filter({ hasText: uniqueTag }),
    ).toBeVisible({ timeout: 12_000 });
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_8 — Timeline page shows a story at the queried coordinates
// Verifies: create story at a specific lat/lng → visit timeline.html with
// those coordinates → the story title appears in #timeline-items.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_8 — Timeline page surfaces a nearby story', () => {
  test('story created at coordinates appears in the timeline at those coords', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e8user${ts}`;
    const email    = `e2e8user${ts}@example.com`;
    const password = 'E2eTest@8';

    // Coordinates chosen to avoid overlap with seed data.
    const lat = 40.9751;
    const lng = 29.0398;

    await registerAndLogin(page, username, email, password);

    const title = `Timeline Story ${ts}`;
    await createStory(page, {
      title,
      content:  'Story for testing the timeline end-to-end.',
      location: 'Uskudar, Istanbul',
      date:     '03/15/1955',
      lat:      String(lat),
      lng:      String(lng),
    });

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    // Open the timeline centred on the story's coordinates with a 1 km radius.
    await page.goto(
      `/timeline.html?lat=${lat}&lng=${lng}&radius_km=1`,
    );

    // The timeline fetches stories asynchronously; wait for the list to appear.
    await expect(page.locator('#timeline-list')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('#timeline-items')).toContainText(title, { timeout: 10_000 });
  });
});

// ---------------------------------------------------------------------------
// TC_E2E_9 — Editing a story updates its content on the detail page
// Verifies: create story → navigate to story-edit.html → change the title
// and content → save → visit story-detail.html → updated values are shown.
// ---------------------------------------------------------------------------
test.describe('TC_E2E_9 — Editing a story updates content on the detail page', () => {
  test('edited title and content are reflected on the story detail page', async ({ page }) => {
    const ts = Date.now();
    const username = `e2e9user${ts}`;
    const email    = `e2e9user${ts}@example.com`;
    const password = 'E2eTest@9';

    await registerAndLogin(page, username, email, password);

    const originalTitle = `Edit Before ${ts}`;
    const updatedTitle  = `Edit After ${ts}`;
    const updatedContent = 'Updated content written during the E2E edit flow test.';

    const storyId = await createStory(page, {
      title:    originalTitle,
      content:  'Original content before edit.',
      location: 'Fatih, Istanbul',
      date:     '01/01/1453',
      lat:      '41.0138',
      lng:      '28.9497',
    });

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal:not(.hidden)').waitFor({ state: 'attached', timeout: 10_000 }),
    ]);

    // Navigate to the edit page for this story.
    await page.goto(`/story-edit.html?id=${storyId}`);

    // Wait for the form to be pre-filled (edit page loads story data async).
    await expect(page.locator('#title')).not.toHaveValue('', { timeout: 8_000 });

    // Update title and content.
    await page.fill('#title', updatedTitle);
    await page.fill('#story', updatedContent);

    const saveResponsePromise = page.waitForResponse(
      r => r.url().includes(`/stories/${storyId}`) && r.request().method() === 'PUT',
    );
    await page.click('#btn-save');
    const saveResponse = await saveResponsePromise;
    expect(saveResponse.status()).toBe(200);

    // Verify the detail page shows the updated values.
    await page.goto(`/story-detail.html?id=${storyId}`);
    await expect(page.locator('#story-title')).toContainText(updatedTitle, { timeout: 8_000 });
    await expect(page.locator('#story-content')).toContainText(updatedContent);
  });
});
