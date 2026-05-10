const assert = require('node:assert/strict');
const { getAvailableContexts, switchToFirstWebviewContext } = require('../helpers/context');

describe('TC_MOBILE_SMOKE - Android APK launch', () => {
  it('opens the app and exposes at least one automation context', async () => {
    const contexts = await getAvailableContexts();

    assert.ok(Array.isArray(contexts), 'Appium should return automation contexts');
    assert.ok(contexts.length > 0, 'expected at least one native or webview context');
  });

  it('can switch to the Capacitor WebView when it is available', async function () {
    const webviewContext = await switchToFirstWebviewContext();

    if (!webviewContext) {
      return this.skip();
    }

    const title = await browser.getTitle();

    assert.equal(typeof title, 'string');
  });
});
