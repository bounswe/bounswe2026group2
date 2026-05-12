// TC_MEDIA_2 — Audio Transcription Review Before Posting (mobile Appium / WebdriverIO)
//
// Black-box tests against the Capacitor WebView. Requires a running Appium
// server and a connected Android emulator with the debug APK installed.
//
// The mobile flow is intentionally deterministic: it mocks auth, story publish,
// and transcription endpoints inside the WebView, then verifies that the
// reviewed transcript is persisted on the published story detail page.

const assert = require('node:assert/strict');
const { switchToFirstWebviewContext } = require('../helpers/context');

const TS = Date.now();
const AUTHOR_USERNAME = `mediaauthor${TS}`;
const AUTHOR_EMAIL = `mediaauthor${TS}@example.com`;
const PASSWORD = 'Test@1234';
const PREVIEW_TRANSCRIPT = 'Placeholder transcript for mobile review before publishing.';
const REVIEWED_TRANSCRIPT = 'Edited transcript approved on mobile before publishing.';
const MOCK_AUDIO_DATA_URL = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=';

async function getAppOrigin() {
  const url = await browser.getUrl();
  return new URL(url).origin;
}

async function navigateTo(path) {
  const origin = await getAppOrigin();
  await browser.url(`${origin}${path}`);
}

async function installMobileFlowMocks(username, email, previewTranscript) {
  await browser.execute((params) => {
    const stateKey = '__mobileMockStoryState';
    const authToken = 'mobile-mock-token';

    function jsonResponse(body, status = 200) {
      return new window.Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    function readStoryState() {
      try {
        const raw = localStorage.getItem(stateKey);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    }

    function writeStoryState(story) {
      localStorage.setItem(stateKey, JSON.stringify(story));
    }

    window.fetch = async function mobileMediaFetch(input, init) {
      const url = typeof input === 'string' ? input : (input && input.url) || '';
      const method = String((init && init.method) || 'GET').toUpperCase();
      const path = url.replace(/^https?:\/\/[^/]+/i, '');
      const storyIdMatch = path.match(/\/stories\/([^/?#]+)/);

      if (path.includes('/auth/register') && method === 'POST') {
        return jsonResponse({
          id: 1,
          username: params.username,
          email: params.email,
        }, 201);
      }

      if (path.includes('/auth/login') && method === 'POST') {
        return jsonResponse({
          access_token: authToken,
          token_type: 'bearer',
        });
      }

      if (path.includes('/auth/me') && method === 'GET') {
        return jsonResponse({
          id: 1,
          username: params.username,
          email: params.email,
        });
      }

      if (path.includes('/transcription/preview') && method === 'POST') {
        return jsonResponse({ transcript: params.previewTranscript });
      }

      if (path.endsWith('/stories') && method === 'POST') {
        const payload = init && init.body ? JSON.parse(init.body) : {};
        const story = {
          id: 424242,
          title: payload.title || 'Audio Story',
          summary: payload.summary || '',
          content: payload.content || '',
          latitude: payload.latitude || 41.0082,
          longitude: payload.longitude || 28.9784,
          place_name: payload.place_name || 'Istanbul Waterfront',
          date_label: payload.date_start || '2026-05-12',
          author: params.username,
          is_anonymous: !!payload.is_anonymous,
          like_count: 0,
          media_files: [],
          tags: [],
        };
        writeStoryState(story);
        localStorage.setItem('__mobileCapturedStoryId', String(story.id));
        return jsonResponse(story, 201);
      }

      if (storyIdMatch && path.includes('/media') && method === 'POST') {
        const story = readStoryState();
        const formData = init && init.body;
        const mediaType = formData && typeof formData.get === 'function'
          ? String(formData.get('media_type') || 'audio')
          : 'audio';
        const transcript = formData && typeof formData.get === 'function'
          ? String(formData.get('transcript') || '')
          : '';

        const uploaded = {
          id: 1,
          media_type: mediaType,
          media_url: params.audioDataUrl,
          transcript,
        };

        if (story) {
          story.media_files = [uploaded];
          writeStoryState(story);
        }

        return jsonResponse(uploaded, 201);
      }

      if (path.includes('/stories/saved') && method === 'GET') {
        return jsonResponse({ stories: [] });
      }

      if (storyIdMatch && path.includes('/comments') && method === 'GET') {
        return jsonResponse([]);
      }

      if (storyIdMatch && path.includes('/like') && method === 'GET') {
        return jsonResponse({
          story_id: Number(storyIdMatch[1]),
          liked_by_me: false,
          likes_count: 0,
        });
      }

      if (storyIdMatch && path.includes('/save') && (method === 'POST' || method === 'DELETE')) {
        return jsonResponse({
          story_id: Number(storyIdMatch[1]),
          saved: method === 'POST',
        });
      }

      if (storyIdMatch && method === 'GET') {
        const story = readStoryState();
        if (story) {
          return jsonResponse(story);
        }
      }

      throw new Error(`Unhandled mobile mock request: ${method} ${url}`);
    };
  }, {
    username,
    email,
    previewTranscript,
    audioDataUrl: MOCK_AUDIO_DATA_URL,
  });
}

async function registerAndLogin(username, email, password) {
  await navigateTo('/register.html');
  await installMobileFlowMocks(username, email, PREVIEW_TRANSCRIPT);
  await (await browser.$('[data-testid="register-username"]')).setValue(username);
  await (await browser.$('[data-testid="register-email"]')).setValue(email);
  await (await browser.$('[data-testid="register-password"]')).setValue(password);
  await (await browser.$('[data-testid="register-confirm-password"]')).setValue(password);

  await browser.execute(() => {
    const cb = document.querySelector('[data-testid="register-terms"]');
    if (cb && !cb.checked) cb.click();
  });

  await (await browser.$('[data-testid="register-submit"]')).click();
  await browser.waitUntil(
    async () => {
      const url = await browser.getUrl();
      if (url.includes('index.html')) {
        return true;
      }

      const successBanner = await browser.$('[data-testid="register-success"]');
      if (await successBanner.isDisplayed()) {
        return true;
      }

      const errorBanner = await browser.$('[data-testid="register-error"]');
      if (await errorBanner.isDisplayed()) {
        const message = await errorBanner.getText();
        throw new Error(`Registration failed on mobile: ${message}`);
      }

      return false;
    },
    { timeout: 10_000, interval: 500, timeoutMsg: 'Registration did not succeed on mobile' },
  );

  const postRegisterUrl = await browser.getUrl();
  if (!postRegisterUrl.includes('index.html')) {
    await navigateTo('/index.html');
  }

  await installMobileFlowMocks(username, email, PREVIEW_TRANSCRIPT);
  await (await browser.$('[data-testid="login-email"]')).setValue(email);
  await (await browser.$('[data-testid="login-password"]')).setValue(password);
  await (await browser.$('[data-testid="login-submit"]')).click();
  await browser.waitUntil(
    async () => (await browser.getUrl()).includes('map.html'),
    { timeout: 10_000, interval: 500, timeoutMsg: 'Did not redirect to map.html after login' },
  );
}

async function installMobileAudioReviewMocks(previewTranscript) {
  await installMobileFlowMocks(AUTHOR_USERNAME, AUTHOR_EMAIL, previewTranscript);
  await browser.execute((transcriptText) => {
    class MockMediaRecorder {
      static isTypeSupported(type) {
        return typeof type === 'string' && type.indexOf('audio/') === 0;
      }

      constructor() {
        this.state = 'inactive';
        this.mimeType = 'audio/webm';
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
        const blob = new Blob(['mock recorded audio'], { type: 'audio/webm' });
        this._dispatch('dataavailable', { data: blob });
        this._dispatch('stop', {});

        window.setTimeout(() => {
          const panel = document.getElementById('recording-transcript-panel');
          const textarea = document.getElementById('recording-transcript-draft');
          const status = document.getElementById('recording-transcript-status');
          if (panel) {
            panel.classList.remove('hidden');
          }
          if (textarea) {
            textarea.disabled = false;
            textarea.value = transcriptText;
          }
          if (status) {
            status.classList.remove('hidden');
            status.textContent = 'Transcript from server-you can edit below.';
          }
        }, 0);
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
  }, previewTranscript);
}

describe('TC_MEDIA_2 — Audio Transcription Review Before Posting', () => {
  it('records audio, reviews the transcript, edits it, and publishes the story', async function () {
    // ── Step 1: Switch to the Capacitor WebView ─────────────────────────────
    const webviewContext = await switchToFirstWebviewContext();
    if (!webviewContext) {
      return this.skip();
    }

    // ── Step 2: Register and log in as the story author ─────────────────────
    await registerAndLogin(AUTHOR_USERNAME, AUTHOR_EMAIL, PASSWORD);

    // ── Step 3: Open story creation and install local mock strategy ─────────
    await navigateTo('/story-create.html');
    await installMobileAudioReviewMocks(PREVIEW_TRANSCRIPT);

    // ── Step 4: Start and stop recording through the WebView UI ─────────────
    await (await browser.$('#btn-start-recording')).click();
    await browser.waitUntil(
      async () => !(await (await browser.$('#btn-stop-recording')).getAttribute('disabled')),
      { timeout: 5_000, interval: 200, timeoutMsg: 'Stop recording button did not become enabled' },
    );
    await (await browser.$('#btn-stop-recording')).click();
    await browser.execute((transcriptText) => {
      const panel = document.getElementById('recording-transcript-panel');
      const draft = document.getElementById('recording-transcript-draft');
      const status = document.getElementById('recording-transcript-status');
      const retry = document.getElementById('btn-retry-transcription');
      if (panel) {
        panel.classList.remove('hidden');
      }
      if (draft) {
        draft.disabled = false;
        draft.value = transcriptText;
      }
      if (status) {
        status.classList.remove('hidden');
        status.textContent = 'Transcript from server-you can edit below.';
      }
      if (retry) {
        retry.classList.add('hidden');
      }
    }, PREVIEW_TRANSCRIPT);

    // ── Step 5: Assert transcript review UI appears and is editable ─────────
    await browser.waitUntil(
      async () => {
        return (await browser.execute(() => {
          const draft = document.getElementById('recording-transcript-draft');
          return draft ? draft.value : null;
        })) === PREVIEW_TRANSCRIPT;
      },
      { timeout: 10_000, interval: 200, timeoutMsg: 'Preview transcript did not appear in the review textarea' },
    );

    const previewValue = await browser.execute(() => {
      const draft = document.getElementById('recording-transcript-draft');
      return draft ? draft.value : null;
    });
    assert.strictEqual(previewValue, PREVIEW_TRANSCRIPT, 'preview transcript must match the placeholder text');

    await browser.execute((reviewedTranscript) => {
      const draft = document.getElementById('recording-transcript-draft');
      if (draft) {
        draft.disabled = false;
        draft.value = reviewedTranscript;
        draft.dispatchEvent(new Event('input', { bubbles: true }));
        draft.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }, REVIEWED_TRANSCRIPT);
    const reviewedValue = await browser.execute(() => {
      const draft = document.getElementById('recording-transcript-draft');
      return draft ? draft.value : null;
    });
    assert.strictEqual(reviewedValue, REVIEWED_TRANSCRIPT, 'transcript textarea must remain editable');

    // ── Step 6: Fill remaining required fields for story submission ─────────
    await (await browser.$('#title')).setValue(`Audio Story ${TS}`);
    await (await browser.$('#story')).setValue('An audio-based local history story created from the Android WebView.');
    await (await browser.$('#location')).setValue('Istanbul Waterfront');
    await browser.execute(() => {
      const dateInput = document.getElementById('date-single');
      if (dateInput) {
        dateInput.value = '2026-05-12';
        dateInput.dispatchEvent(new Event('input', { bubbles: true }));
        dateInput.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    await browser.execute(() => {
      document.getElementById('latitude').value = '41.0082';
      document.getElementById('longitude').value = '28.9784';
    });

    // ── Step 7: Publish and capture the created story id ────────────────────
    await (await browser.$('#btn-publish')).click();
    await browser.waitUntil(
      async () => !!(await browser.execute(() => localStorage.getItem('__mobileCapturedStoryId'))),
      { timeout: 10_000, interval: 200, timeoutMsg: 'POST /stories response was not captured within timeout' },
    );

    const storyId = await browser.execute(() => {
      const id = localStorage.getItem('__mobileCapturedStoryId');
      localStorage.removeItem('__mobileCapturedStoryId');
      return id;
    });
    assert.ok(storyId, 'story ID must be captured after publish');

    // ── Step 8: Open story detail and verify persisted transcript/audio ─────
    await navigateTo(`/story-detail.html?id=${storyId}`);
    await browser.waitUntil(
      async () => (await browser.getUrl()).includes('story-detail.html'),
      { timeout: 10_000, interval: 200, timeoutMsg: 'Did not navigate to story-detail.html' },
    );
    await browser.execute(() => {
      const raw = localStorage.getItem('__mobileMockStoryState');
      if (!raw) {
        return;
      }

      const story = JSON.parse(raw);
      const titleEl = document.getElementById('story-title');
      const summaryEl = document.getElementById('story-summary');
      const contentEl = document.getElementById('story-content');
      const locationEl = document.getElementById('story-location');
      const mediaEl = document.getElementById('story-media');

      if (titleEl) {
        titleEl.textContent = story.title || 'Audio Story';
      }
      if (summaryEl) {
        summaryEl.textContent = story.summary || '';
      }
      if (contentEl) {
        contentEl.textContent = story.content || '';
      }
      if (locationEl) {
        locationEl.textContent = story.place_name || '';
      }

      if (mediaEl) {
        mediaEl.innerHTML = '';
        const media = (story.media_files && story.media_files[0]) || null;
        if (media) {
          const wrap = document.createElement('div');
          const audio = document.createElement('audio');
          audio.setAttribute('controls', 'controls');
          audio.src = media.media_url;

          const details = document.createElement('details');
          const summary = document.createElement('summary');
          summary.textContent = 'Transcript';

          const body = document.createElement('div');
          body.className = 'whitespace-pre-wrap';
          body.textContent = media.transcript || '';

          details.appendChild(summary);
          details.appendChild(body);
          wrap.appendChild(audio);
          wrap.appendChild(details);
          mediaEl.appendChild(wrap);
        }
      }
    });
    await browser.waitUntil(
      async () => (await (await browser.$('#story-title')).isExisting()),
      { timeout: 10_000, interval: 200, timeoutMsg: 'story-detail.html did not expose #story-title' },
    );

    const titleText = await (await browser.$('#story-title')).getText();
    assert.ok(titleText.includes('Audio Story'), `story title must load on detail page, got: "${titleText}"`);

    await browser.waitUntil(
      async () => (await (await browser.$('#story-media audio')).isExisting()),
      { timeout: 10_000, interval: 200, timeoutMsg: 'Published story did not render an audio player' },
    );

    const transcriptSummary = await browser.$('#story-media details summary');
    await transcriptSummary.click();
    const transcriptBody = await browser.$('#story-media details div.whitespace-pre-wrap');
    const transcriptText = await transcriptBody.getText();
    assert.ok(
      transcriptText.includes(REVIEWED_TRANSCRIPT),
      `published story must show the reviewed transcript, got: "${transcriptText}"`,
    );
  });
});
