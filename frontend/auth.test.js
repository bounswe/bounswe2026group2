const {
    getToken,
    isLoggedIn,
    saveToken,
    logout,
    authFetch,
    requireAuth,
    AUTH_TOKEN_KEY
} = require("./auth");

global.fetch = jest.fn();

describe("auth utility", () => {
    let assignMock;
    let store;

    beforeEach(() => {
        store = {};
        assignMock = jest.fn();

        Object.defineProperty(window, "location", {
            value: { assign: assignMock, origin: "http://localhost" },
            writable: true,
            configurable: true
        });

        jest.spyOn(Storage.prototype, "getItem").mockImplementation((key) => store[key] || null);
        jest.spyOn(Storage.prototype, "setItem").mockImplementation((key, val) => { store[key] = val; });
        jest.spyOn(Storage.prototype, "removeItem").mockImplementation((key) => { delete store[key]; });

        global.fetch.mockReset();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("getToken returns null when no token stored", () => {
        expect(getToken()).toBeNull();
    });

    test("saveToken stores token and getToken retrieves it", () => {
        saveToken("abc123");
        expect(store[AUTH_TOKEN_KEY]).toBe("abc123");
    });

    test("isLoggedIn returns false when no token", () => {
        expect(isLoggedIn()).toBe(false);
    });

    test("isLoggedIn returns true when token exists", () => {
        store[AUTH_TOKEN_KEY] = "abc123";
        expect(isLoggedIn()).toBe(true);
    });

    test("logout removes token and redirects to login", () => {
        store[AUTH_TOKEN_KEY] = "abc123";
        logout();
        expect(store[AUTH_TOKEN_KEY]).toBeUndefined();
        expect(assignMock).toHaveBeenCalledWith("index.html");
    });

    test("authFetch adds Authorization header when token exists", async () => {
        store[AUTH_TOKEN_KEY] = "my-token";
        global.fetch.mockResolvedValueOnce({ ok: true });

        await authFetch("/api/test", { method: "GET" });

        expect(global.fetch).toHaveBeenCalledWith("/api/test", {
            method: "GET",
            headers: { "Authorization": "Bearer my-token" }
        });
    });

    test("authFetch works without token", async () => {
        global.fetch.mockResolvedValueOnce({ ok: true });

        await authFetch("/api/test");

        expect(global.fetch).toHaveBeenCalledWith("/api/test", {});
    });

    test("requireAuth redirects when not logged in", () => {
        var result = requireAuth();
        expect(result).toBe(false);
        expect(assignMock).toHaveBeenCalledWith("index.html");
    });

    test("requireAuth returns true when logged in", () => {
        store[AUTH_TOKEN_KEY] = "abc123";
        var result = requireAuth();
        expect(result).toBe(true);
        expect(assignMock).not.toHaveBeenCalled();
    });
});
