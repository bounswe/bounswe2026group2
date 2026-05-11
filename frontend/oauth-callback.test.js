const {
    OAUTH_ERROR_MESSAGE,
    completeOAuthSignIn,
    getOAuthParams,
} = require("./oauth-callback");

function setupDom() {
    document.body.innerHTML = `
      <h1 id="oauth-title">Completing sign in...</h1>
      <p id="oauth-status">Please wait while we finish Google sign in.</p>
      <a id="oauth-login-link" class="hidden" href="index.html">Return to login</a>
    `;
}

function makeWindow(hash, search) {
    return {
        location: {
            hash: hash || "",
            search: search || "",
            pathname: "/oauth-callback.html",
            assign: jest.fn(),
        },
        history: {
            replaceState: jest.fn(),
        },
    };
}

describe("oauth callback handling", () => {
    beforeEach(() => {
        setupDom();
    });

    test("stores token and redirects to map on successful callback", () => {
        const win = makeWindow("#access_token=test-token&token_type=bearer");
        const storage = { setItem: jest.fn() };

        const result = completeOAuthSignIn(win, document, storage);

        expect(result).toBe(true);
        expect(storage.setItem).toHaveBeenCalledWith("auth_token", "test-token");
        expect(win.history.replaceState).toHaveBeenCalledWith({}, document.title, "/oauth-callback.html");
        expect(win.location.assign).toHaveBeenCalledWith("map.html");
    });

    test("shows friendly error when token is missing", () => {
        const win = makeWindow("");
        const storage = { setItem: jest.fn() };

        const result = completeOAuthSignIn(win, document, storage);

        expect(result).toBe(false);
        expect(document.getElementById("oauth-title").textContent).toBe("Sign in failed");
        expect(document.getElementById("oauth-status").textContent).toBe(OAUTH_ERROR_MESSAGE);
        expect(document.getElementById("oauth-login-link").classList.contains("hidden")).toBe(false);
        expect(storage.setItem).not.toHaveBeenCalled();
    });

    test("shows friendly error when callback includes an error", () => {
        const win = makeWindow("", "?error=access_denied");
        const storage = { setItem: jest.fn() };

        const result = completeOAuthSignIn(win, document, storage);

        expect(result).toBe(false);
        expect(document.getElementById("oauth-status").textContent).toBe(OAUTH_ERROR_MESSAGE);
        expect(win.location.assign).not.toHaveBeenCalled();
    });

    test("reads oauth error from frontend-friendly query parameter", () => {
        const win = makeWindow("", "?google_auth_error=1");

        expect(getOAuthParams(win)).toEqual({
            token: null,
            error: "1",
        });
    });
});
