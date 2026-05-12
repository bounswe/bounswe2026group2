async function getAvailableContexts() {
  if (typeof browser.getContexts !== 'function') {
    return [];
  }

  return browser.getContexts();
}

async function switchToFirstWebviewContext() {
  const contexts = await getAvailableContexts();
  const webviewContext = contexts.find((contextName) => String(contextName).startsWith('WEBVIEW'));

  if (!webviewContext) {
    return null;
  }

  await browser.switchContext(webviewContext);
  return webviewContext;
}

module.exports = {
  getAvailableContexts,
  switchToFirstWebviewContext,
};
