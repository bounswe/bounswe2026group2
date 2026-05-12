// UAT — Media flows
// Black-box tests against the running full-stack app (docker compose).
//
// Prerequisites:
//   ./localrun.sh   (or docker compose up --build)
//
// Run:
//   UAT_BASE_URL=http://localhost:3000 npm test          (from this directory)
//   UAT_BASE_URL=http://localhost:3000 npx playwright test tests/uat/  (from frontend/)

const fs = require('fs');
const path = require('path');

const { test, expect } = require('@playwright/test');

const SEEDED_USER = {
  email: 'seed_alice@example.com',
  password: 'ValidPass1!',
};

const RECORDED_AUDIO_FIXTURE_BASE64 = fs.readFileSync(
  path.resolve(process.cwd(), 'tests', 'uat', 'fixtures', 'tc-media-2-sample.wav'),
).toString('base64');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function postJsonFromPage(page, path, payload) {
  return page.evaluate(async ({ path: requestPath, payload: requestPayload }) => {
    const response = await fetch(API_BASE + requestPath, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestPayload),
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  }, { path, payload });
}

async function resolveStoryAuthorCredentials(page) {
  await page.goto('/index.html');

  // Prefer the seeded account requested in the scenario when the running
  // environment provides it. If the docker stack is not seeded, provision a
  // dedicated UAT user so this spec remains runnable on its own.
  const seededLogin = await postJsonFromPage(page, '/auth/login', SEEDED_USER);
  if (seededLogin.ok) {
    return SEEDED_USER;
  }

  const ts = Date.now();
  const fallbackUser = {
    username: `mediauat${ts}`,
    email: `mediauat${ts}@example.com`,
    password: 'Test@1234',
  };

  const registerResponse = await postJsonFromPage(page, '/auth/register', {
    username: fallbackUser.username,
    email: fallbackUser.email,
    password: fallbackUser.password,
    display_name: 'Media UAT',
  });

  if (!registerResponse.ok) {
    throw new Error(
      `Unable to provision UAT user (${registerResponse.status}): ` +
      `${registerResponse.data && registerResponse.data.detail ? registerResponse.data.detail : 'unknown error'}`,
    );
  }

  return {
    email: fallbackUser.email,
    password: fallbackUser.password,
  };
}

async function loginThroughUi(page, email, password) {
  await page.goto('/index.html');
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();
  await page.waitForURL('**/map.html', { timeout: 5_000 });
}

async function installRecordedAudioMocks(page, previewTranscript) {
  await page.route('**/transcription/preview', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ transcript: previewTranscript }),
    });
  });

  await page.addInitScript(({ recordedAudioFixtureBase64 }) => {
    class MockMediaRecorder {
      static isTypeSupported(type) {
        return typeof type === 'string' && type.indexOf('audio/') === 0;
      }

      constructor(stream, options) {
        this.stream = stream;
        this.state = 'inactive';
        this.mimeType = (options && options.mimeType) || 'audio/webm';
        this._listeners = {};
      }

      addEventListener(type, listener) {
        if (!this._listeners[type]) {
          this._listeners[type] = [];
        }
        this._listeners[type].push(listener);
      }

      _dispatch(type, event) {
        const listeners = this._listeners[type] || [];
        listeners.forEach((listener) => listener(event));
      }

      start() {
        this.state = 'recording';
      }

      stop() {
        if (this.state === 'inactive') {
          return;
        }

        this.state = 'inactive';
        const binary = globalThis.atob(recordedAudioFixtureBase64);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
          bytes[index] = binary.charCodeAt(index);
        }
        const blob = new Blob([bytes], { type: 'audio/wav' });

        this._dispatch('dataavailable', { data: blob });
        this._dispatch('stop', {});
      }
    }

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => ({
          getTracks: () => [
            {
              stop() {},
            },
          ],
        }),
      },
    });

    window.MediaRecorder = MockMediaRecorder;
    window.AudioContext = undefined;
    window.webkitAudioContext = undefined;
    window.addEventListener('DOMContentLoaded', () => {
      if (!window.RecordingUtils) {
        return;
      }

      window.RecordingUtils.buildRecordedFile = function buildRecordedFixture(chunks) {
        const blob = new Blob(chunks, { type: 'audio/wav' });
        return new File([blob], 'tc-media-2-sample.wav', { type: 'audio/wav' });
      };
    });
  }, { recordedAudioFixtureBase64: RECORDED_AUDIO_FIXTURE_BASE64 });
}

async function fillRequiredStoryFields(page, storyTitle) {
  await page.fill('#title', storyTitle);
  await page.fill('#story', 'An oral history about the old waterfront told from a personal recording.');
  await page.fill('#location', 'Istanbul Waterfront');
  await page.fill('#date-single', '05/12/2026');

  // Setting hidden coordinates directly avoids flaky map clicks in headless CI.
  await page.evaluate(() => {
    document.getElementById('latitude').value = '41.0082';
    document.getElementById('longitude').value = '28.9784';
  });
}

function isCreateStoryResponse(response) {
  const url = new URL(response.url());
  return url.pathname === '/stories' && response.request().method() === 'POST';
}

function isUploadMediaResponse(response) {
  const url = new URL(response.url());
  return /^\/stories\/[^/]+\/media$/.test(url.pathname) && response.request().method() === 'POST';
}

// ---------------------------------------------------------------------------
// TC_MEDIA_2 — Audio Transcription Review Before Posting
// ---------------------------------------------------------------------------
test.describe('TC_MEDIA_2 — Audio Transcription Review Before Posting', () => {
  test('records audio, reviews the transcript, edits it, and publishes the story', async ({ page }) => {
    test.setTimeout(180_000);

    const storyTitle = `Audio Story ${Date.now()}`;
    const previewTranscript = 'Placeholder transcript for review before publishing.';
    const reviewedTranscript = 'The edited transcript the author approves before publishing.';

    // ── Step 1: Resolve usable credentials and log in through the UI ────────
    const credentials = await resolveStoryAuthorCredentials(page);
    await loginThroughUi(page, credentials.email, credentials.password);

    // ── Step 2: Mock browser audio capture and return a placeholder transcript
    await installRecordedAudioMocks(page, previewTranscript);

    // ── Step 3: Open story creation page ────────────────────────────────────
    await page.goto('/story-create.html');

    // ── Step 4: Record audio through the UI and load the placeholder review text
    const previewResponsePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === '/transcription/preview' &&
        response.request().method() === 'POST',
    );

    await page.click('#btn-start-recording');
    await expect(page.locator('#btn-stop-recording')).toBeEnabled();

    await page.click('#btn-stop-recording');

    const previewResponse = await previewResponsePromise;
    expect(previewResponse.status()).toBe(200);

    await expect(page.locator('#recording-audio-preview')).toBeVisible();
    await expect(page.locator('#recording-transcript-panel')).toBeVisible();
    await expect(page.locator('#recording-transcript-draft')).toHaveValue(previewTranscript);
    await expect(page.locator('#recording-transcript-draft')).toBeEditable();

    // ── Step 5: Review and edit the transcript before publishing ────────────
    await page.locator('#recording-transcript-draft').fill(reviewedTranscript);
    await expect(page.locator('#recording-transcript-draft')).toHaveValue(reviewedTranscript);

    // ── Step 6: Fill the remaining required story fields ────────────────────
    await fillRequiredStoryFields(page, storyTitle);

    // ── Step 7: Publish and capture both story and media upload responses ───
    const createStoryResponsePromise = page.waitForResponse(isCreateStoryResponse);
    const uploadMediaResponsePromise = page.waitForResponse(isUploadMediaResponse);

    await page.click('#btn-publish');

    const createStoryResponse = await createStoryResponsePromise;
    expect(createStoryResponse.status()).toBe(201);
    const createdStory = await createStoryResponse.json();
    expect(createdStory.id).toBeTruthy();

    const uploadMediaResponse = await uploadMediaResponsePromise;
    expect(uploadMediaResponse.status()).toBe(201);
    const uploadedMedia = await uploadMediaResponse.json();
    expect(uploadedMedia.media.media_type).toBe('audio');
    expect(uploadedMedia.media.transcript).toBe(reviewedTranscript);

    await Promise.race([
      page.locator('#form-success').waitFor({ state: 'visible', timeout: 10_000 }),
      page.locator('#badge-unlock-modal').waitFor({ state: 'visible', timeout: 10_000 }),
    ]);

    // ── Step 8: Open the published story and verify audio + transcript ──────
    const storyId = createdStory.id;
    const storyDetailResponsePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === `/stories/${storyId}` &&
        response.request().method() === 'GET',
    );

    await page.goto(`/story-detail.html?id=${storyId}`);

    const storyDetailResponse = await storyDetailResponsePromise;
    expect(storyDetailResponse.status()).toBe(200);

    const storyDetail = await storyDetailResponse.json();
    const audioMedia = storyDetail.media_files.find((media) => media.media_type === 'audio');
    expect(audioMedia).toBeTruthy();
    expect(audioMedia.transcript).toBe(reviewedTranscript);

    await expect(page.locator('#story-title')).toContainText(storyTitle);
    await expect(page.locator('#story-media audio')).toHaveCount(1);

    await page.locator('#story-media details summary').first().click();
    await expect(
      page.locator('#story-media details div.whitespace-pre-wrap').first(),
    ).toContainText(reviewedTranscript);
  });
});
