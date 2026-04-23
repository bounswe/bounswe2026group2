const { setupLikes, setLikeUi } = require("./likes");

describe("likes UI", () => {
    let assignMock;

    async function flushMicrotasks() {
        // Ensure promise chains (.then/.catch/.finally and async handlers) have run.
        await Promise.resolve();
        await Promise.resolve();
    }

    async function waitForButtonEnabled() {
        const btn = document.getElementById("like-button");
        for (let i = 0; i < 5 && btn && btn.disabled; i++) {
            await flushMicrotasks();
        }
    }

    beforeEach(() => {
        document.body.innerHTML = `
      <button id="like-button" type="button" data-animating="false" class="bg-white text-primary hover:bg-stone-50">
        <span id="like-button-text">Like</span>
      </button>
      <span id="like-count">0</span>
      <span id="like-status" class="hidden"></span>
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

    test("setLikeUi toggles liked state styles and labels", () => {
        setLikeUi({ liked_by_me: true, likes_count: 3 });

        const btn = document.getElementById("like-button");
        expect(btn.getAttribute("aria-pressed")).toBe("true");
        expect(document.getElementById("like-button-text").textContent).toBe("Liked");
        expect(document.getElementById("like-count").textContent).toBe("3");

        setLikeUi({ liked_by_me: false, likes_count: 2 });
        expect(btn.getAttribute("aria-pressed")).toBe("false");
        expect(document.getElementById("like-button-text").textContent).toBe("Like");
        expect(document.getElementById("like-count").textContent).toBe("2");
    });

    test("setupLikes shows backend pending message when GET /likes fails", async () => {
        global.authFetch.mockResolvedValueOnce({ ok: false, status: 404, json: () => Promise.resolve({}) });

        setupLikes("http://api", "story-1");

        await flushMicrotasks();

        const status = document.getElementById("like-status");
        expect(status.classList.contains("hidden")).toBe(false);
        expect(status.textContent).toContain("backend pending");
    });

    test("click optimistically increments count and sets animating flag", async () => {
        jest.useFakeTimers();
        global.authFetch
            // initial GET /likes
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ story_id: "story-1", likes_count: 10, liked_by_me: false })
            })
            // POST /likes
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ story_id: "story-1", likes_count: 11, liked_by_me: true })
            });

        global.isLoggedIn.mockReturnValue(true);

        setupLikes("http://api", "story-1");

        await flushMicrotasks();
        await waitForButtonEnabled();

        const btn = document.getElementById("like-button");
        expect(btn.disabled).toBe(false);
        btn.click();

        // Optimistic immediately
        expect(document.getElementById("like-count").textContent).toBe("11");
        expect(btn.dataset.animating).toBe("true");

        jest.advanceTimersByTime(210);
        expect(btn.dataset.animating).toBe("false");

        // Resolve async POST
        await flushMicrotasks();

        expect(document.getElementById("like-button-text").textContent).toBe("Liked");
        expect(global.authFetch).toHaveBeenCalledWith("http://api/stories/story-1/likes");
        expect(global.authFetch).toHaveBeenCalledWith("http://api/stories/story-1/likes", { method: "POST" });
        jest.useRealTimers();
    });

    test("click redirects to index when not logged in", async () => {
        global.authFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ likes_count: 0, liked_by_me: false }) });
        global.isLoggedIn.mockReturnValue(false);

        setupLikes("http://api", "story-1");
        await flushMicrotasks();
        await waitForButtonEnabled();

        document.getElementById("like-button").click();

        // allow sendLikeToggle to run
        await flushMicrotasks();
        expect(assignMock).toHaveBeenCalledWith("index.html");
    });
});

