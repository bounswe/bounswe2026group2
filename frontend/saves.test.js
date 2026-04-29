const { setupSaveButton, setSaveUi } = require("./saves");

describe("saves UI", () => {
    let assignMock;

    async function flushMicrotasks() {
        await Promise.resolve();
        await Promise.resolve();
    }

    async function waitForButtonEnabled() {
        const btn = document.getElementById("save-button");
        for (let i = 0; i < 5 && btn && btn.disabled; i++) {
            await flushMicrotasks();
        }
    }

    beforeEach(() => {
        document.body.innerHTML = `
      <button id="save-button" type="button" data-animating="false" class="bg-white text-primary hover:bg-stone-50">
        <span id="save-button-icon"></span>
        <span id="save-button-text">Save</span>
      </button>
      <span id="save-status" class="hidden"></span>
    `;

        assignMock = jest.fn();
        Object.defineProperty(window, "location", {
            value: { assign: assignMock, origin: "http://localhost" },
            writable: true,
            configurable: true
        });

        global.authFetch = jest.fn();
        global.isLoggedIn = jest.fn();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("setSaveUi toggles styles and labels", () => {
        setSaveUi({ saved: true });

        const btn = document.getElementById("save-button");
        expect(btn.getAttribute("aria-pressed")).toBe("true");
        expect(document.getElementById("save-button-text").textContent).toBe("Saved");

        setSaveUi({ saved: false });
        expect(btn.getAttribute("aria-pressed")).toBe("false");
        expect(document.getElementById("save-button-text").textContent).toBe("Save");
    });

    test("setupSaveButton renders default state when GET /stories/saved fails", async () => {
        global.isLoggedIn.mockReturnValue(true);
        global.authFetch.mockResolvedValueOnce({ ok: false, status: 500, json: () => Promise.resolve({}) });

        setupSaveButton("http://api", "story-1");
        await waitForButtonEnabled();

        expect(document.getElementById("save-button-text").textContent).toBe("Save");
        expect(document.getElementById("save-status").textContent).toMatch(/unavailable/i);
    });

    test("setupSaveButton reflects saved=true when story is in saved list", async () => {
        global.isLoggedIn.mockReturnValue(true);
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ stories: [{ id: "story-1" }, { id: "other" }] })
        });

        setupSaveButton("http://api", "story-1");
        await waitForButtonEnabled();

        expect(document.getElementById("save-button-text").textContent).toBe("Saved");
        expect(document.getElementById("save-button").getAttribute("aria-pressed")).toBe("true");
    });

    test("clicking Save sends POST and flips to saved", async () => {
        global.isLoggedIn.mockReturnValue(true);

        // Initial GET → not in saved list.
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ stories: [] })
        });
        // Toggle POST → returns saved=true.
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ story_id: "story-1", saved: true })
        });

        setupSaveButton("http://api", "story-1");
        await waitForButtonEnabled();

        document.getElementById("save-button").click();
        await flushMicrotasks();
        await waitForButtonEnabled();

        const lastCall = global.authFetch.mock.calls[global.authFetch.mock.calls.length - 1];
        expect(lastCall[0]).toBe("http://api/stories/story-1/save");
        expect(lastCall[1]).toEqual({ method: "POST" });
        expect(document.getElementById("save-button-text").textContent).toBe("Saved");
    });

    test("clicking Save while logged out redirects to login", async () => {
        global.isLoggedIn.mockReturnValue(false);

        setupSaveButton("http://api", "story-1");
        await waitForButtonEnabled();

        document.getElementById("save-button").click();
        await flushMicrotasks();

        expect(assignMock).toHaveBeenCalledWith("index.html");
        expect(global.authFetch).not.toHaveBeenCalled();
    });
});
