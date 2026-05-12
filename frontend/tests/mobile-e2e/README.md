# Mobile E2E Testing

This directory contains the local-only Appium skeleton for Android APK E2E tests. It is intentionally small: one smoke test verifies that Appium can launch the APK, and the Lab 9/web UAT scenarios are represented as skipped placeholders until each flow is ready to automate.

## Frameworks

- Appium 2
- WebdriverIO
- Mocha
- UiAutomator2 Android driver

## Environment

Copy `.env.example` to `.env` and adjust the values for your machine:

```text
ANDROID_APP_PATH=../../android/app/build/outputs/apk/debug/app-debug.apk
APPIUM_SERVER_URL=http://127.0.0.1:4723
MOBILE_API_BASE_URL=http://10.0.2.2:8000
ANDROID_DEVICE_NAME=Pixel_6_API_35
MOBILE_SEEDED_EMAIL=seed_alice@example.com
MOBILE_SEEDED_PASSWORD=ValidPass1!
```

`MOBILE_API_BASE_URL` is used when preparing Capacitor web assets before the APK is built. Android emulators should usually call the host machine through `10.0.2.2`.
`MOBILE_SEEDED_EMAIL` and `MOBILE_SEEDED_PASSWORD` are used by skipped scenario specs that mirror seeded web UAT flows.

## Local Run

From `frontend/tests/mobile-e2e`:

```powershell
npm install
npm run appium:install-driver
npm run appium
npm test
```

In another terminal, prepare and build the APK before running the tests:

```powershell
cd frontend
$env:MOBILE_API_BASE_URL="http://10.0.2.2:8000"
npm run capacitor:sync
cd android
.\gradlew.bat assembleDebug
```

Start the Android emulator named by `ANDROID_DEVICE_NAME` before running `npm test`.

## Scope

The first mobile E2E scope mirrors the Lab 9/current web UAT scenarios:

- `TC_AUTH_1` - user registration and login baseline
- `TC_AUTH_2` - Google OAuth login
- `TC_TAG_1` - keyword tagging on story creation
- `TC_MEDIA_2` - audio transcription review before posting
- `TC_TAG_2` - keyword tagging UI during story creation
- `TC_STORY_5` - anonymous story sharing
- `TC_MAP_2` - multi-location story display on map
- `TC_DASH_1` - user dashboard / profile view count ([`specs/dashboard.spec.js`](./specs/dashboard.spec.js), **skipped unless** `MOBILE_E2E_RUN_TC_DASH_1=1`)
- `TC_BADGE_1` - first post badge awarded

Keep unstable or dependency-blocked flows skipped until the related app behavior is available on `dev`.

### TC_DASH_1 (dashboard / profile view counts)

Implementation: `specs/dashboard.spec.js`. By default the test calls `this.skip()` unless you set:

```bash
MOBILE_E2E_RUN_TC_DASH_1=1
```

Profile assertions use `#profile-stories-container`, `article`, and `span[title="Views on this story"]` (no extra `data-testid` on profile markup). Login still uses the same `data-testid` fields as `auth.spec.js`.

Optional overrides: `MOBILE_E2E_OWNER_EMAIL`, `MOBILE_E2E_OWNER_PASSWORD`, `MOBILE_E2E_SEEDED_STORY_ID` (see `.env.example`).

## Selector Strategy

Prefer shared `data-testid` selectors in the Capacitor WebView when the same UI exists on web and mobile. Use native selectors only for Android system UI or native permission flows.
