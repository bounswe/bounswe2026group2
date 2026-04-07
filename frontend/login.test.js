global.API_BASE = "http://localhost";
global.fetch = jest.fn();

const {
    redirectToMap,
    handleLogin,
    setupLoginForm
} = require("./login");

describe("login page unit tests", () => {
    let assignMock;

    beforeEach(() => {
        document.body.innerHTML = "";
        assignMock = jest.fn();

        Object.defineProperty(window, "location", {
            value: { assign: assignMock, origin: "http://localhost" },
            writable: true,
            configurable: true
        });

        global.fetch.mockReset();

        const store = {};
        jest.spyOn(Storage.prototype, "setItem").mockImplementation((key, val) => { store[key] = val; });
        jest.spyOn(Storage.prototype, "getItem").mockImplementation((key) => store[key] || null);
        jest.spyOn(Storage.prototype, "removeItem").mockImplementation((key) => { delete store[key]; });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("redirectToMap sends user to map.html", () => {
        redirectToMap();
        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("handleLogin calls API and stores token on success", async () => {
        document.body.innerHTML = `
      <form id="login-form">
        <input id="email" type="email" value="test@example.com" />
        <input id="password" type="password" value="Password1!" />
        <button type="submit">Sign In</button>
        <div id="login-error" class="hidden"></div>
      </form>
    `;

        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ access_token: "test-jwt-token", token_type: "bearer" })
        });

        const event = {
            preventDefault: jest.fn(),
            target: document.getElementById("login-form")
        };

        await handleLogin(event);

        expect(event.preventDefault).toHaveBeenCalledTimes(1);
        expect(global.fetch).toHaveBeenCalledWith(
            "http://localhost/auth/login",
            expect.objectContaining({
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: "test@example.com", password: "Password1!" })
            })
        );
        expect(localStorage.setItem).toHaveBeenCalledWith("auth_token", "test-jwt-token");
        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("handleLogin shows error on API failure", async () => {
        document.body.innerHTML = `
      <form id="login-form">
        <input id="email" type="email" value="test@example.com" />
        <input id="password" type="password" value="wrong" />
        <button type="submit">Sign In</button>
        <div id="login-error" class="hidden"></div>
      </form>
    `;

        global.fetch.mockResolvedValueOnce({
            ok: false,
            json: () => Promise.resolve({ detail: "Invalid email or password" })
        });

        const event = {
            preventDefault: jest.fn(),
            target: document.getElementById("login-form")
        };

        await handleLogin(event);

        var errorEl = document.getElementById("login-error");
        expect(errorEl.textContent).toBe("Invalid email or password");
        expect(errorEl.classList.contains("hidden")).toBe(false);
        expect(assignMock).not.toHaveBeenCalled();
    });

    test("handleLogin shows error when fields are empty", async () => {
        document.body.innerHTML = `
      <form id="login-form">
        <input id="email" type="email" value="" />
        <input id="password" type="password" value="" />
        <button type="submit">Sign In</button>
        <div id="login-error" class="hidden"></div>
      </form>
    `;

        const event = {
            preventDefault: jest.fn(),
            target: document.getElementById("login-form")
        };

        await handleLogin(event);

        var errorEl = document.getElementById("login-error");
        expect(errorEl.textContent).toBe("Please enter your email and password.");
        expect(global.fetch).not.toHaveBeenCalled();
    });

    test("setupLoginForm attaches submit listener to form", () => {
        document.body.innerHTML = `
      <form id="login-form">
        <input id="email" type="email" />
        <input id="password" type="password" />
        <button type="submit">Sign In</button>
      </form>
    `;

        setupLoginForm();

        const form = document.getElementById("login-form");
        const submitEvent = new Event("submit", { bubbles: true, cancelable: true });

        form.dispatchEvent(submitEvent);
    });

    test("setupLoginForm does not crash if elements are missing", () => {
        expect(() => setupLoginForm()).not.toThrow();
    });
});
