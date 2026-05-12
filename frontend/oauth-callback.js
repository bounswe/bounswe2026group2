var OAUTH_ERROR_MESSAGE = "Something went wrong while signing you in. Please try again.";

function getOAuthParams(win) {
    var hashParams = new URLSearchParams((win.location.hash || "").replace(/^#/, ""));
    var queryParams = new URLSearchParams(win.location.search || "");

    return {
        token: hashParams.get("access_token"),
        error: hashParams.get("error") || queryParams.get("error") || queryParams.get("google_auth_error"),
    };
}

function showOAuthError(doc) {
    var title = doc.getElementById("oauth-title");
    var status = doc.getElementById("oauth-status");
    var loginLink = doc.getElementById("oauth-login-link");

    if (title) title.textContent = "Sign in failed";
    if (status) status.textContent = OAUTH_ERROR_MESSAGE;
    if (loginLink) loginLink.classList.remove("hidden");
}

function completeOAuthSignIn(win, doc, storage) {
    var params = getOAuthParams(win);

    if (params.error || !params.token) {
        showOAuthError(doc);
        return false;
    }

    try {
        storage.setItem("auth_token", params.token);
        win.history.replaceState({}, doc.title, win.location.pathname);
        win.location.assign("map.html");
        return true;
    } catch {
        showOAuthError(doc);
        return false;
    }
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
    completeOAuthSignIn(window, document, localStorage);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        OAUTH_ERROR_MESSAGE: OAUTH_ERROR_MESSAGE,
        completeOAuthSignIn: completeOAuthSignIn,
        getOAuthParams: getOAuthParams,
        showOAuthError: showOAuthError,
    };
}
