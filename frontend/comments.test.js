const { setupComments, normalizeComment } = require("./comments");

describe("comments UI", () => {
    let assignMock;

    async function flushMicrotasks() {
        await Promise.resolve();
        await Promise.resolve();
    }

    beforeEach(() => {
        document.body.innerHTML = `
      <p id="comments-status" class="hidden"></p>
      <div id="comments-login-prompt" class="hidden"></div>
      <form id="comment-form" class="hidden">
        <textarea id="comment-input"></textarea>
        <p id="comment-error" class="hidden"></p>
        <button id="comment-submit" type="submit">Post</button>
      </form>
      <ul id="comments-list"></ul>
      <p id="comments-empty">No comments yet.</p>
    `;

        assignMock = jest.fn();
        Object.defineProperty(window, "location", {
            value: { assign: assignMock, origin: "http://localhost" },
            writable: true,
            configurable: true
        });

        global.fetch = jest.fn();
        global.authFetch = jest.fn();
        global.isLoggedIn = jest.fn();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("normalizeComment maps common backend shapes", () => {
        expect(normalizeComment({ author: "A", content: "Hi" })).toEqual(
            expect.objectContaining({ author: "A", content: "Hi" })
        );
        expect(normalizeComment({ username: "U", text: "Hello" })).toEqual(
            expect.objectContaining({ author: "U", content: "Hello" })
        );
    });

    test("normalizeComment resolves nested author object from backend", () => {
        // Real backend shape: author = { id, username, display_name }.
        expect(normalizeComment({
            id: "c1",
            content: "Hi",
            author: { id: "u1", username: "alice", display_name: "Alice A." }
        })).toEqual(expect.objectContaining({ id: "c1", author: "Alice A.", content: "Hi" }));

        // Fall back to username when display_name is missing.
        expect(normalizeComment({
            content: "Hi",
            author: { id: "u2", username: "bob", display_name: null }
        })).toEqual(expect.objectContaining({ author: "bob" }));
    });

    test("shows login prompt when logged out", async () => {
        global.isLoggedIn.mockReturnValue(false);
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

        setupComments("http://api", "story-1");
        await flushMicrotasks();

        expect(document.getElementById("comments-login-prompt").classList.contains("hidden")).toBe(false);
        expect(document.getElementById("comment-form").classList.contains("hidden")).toBe(true);
    });

    test("renders empty state when no comments", async () => {
        global.isLoggedIn.mockReturnValue(true);
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

        setupComments("http://api", "story-1");
        await flushMicrotasks();

        expect(document.getElementById("comments-empty").classList.contains("hidden")).toBe(false);
    });

    test("soft-fails when GET comments endpoint unavailable", async () => {
        global.isLoggedIn.mockReturnValue(true);
        global.fetch.mockResolvedValueOnce({ ok: false, status: 404, json: () => Promise.resolve({}) });

        setupComments("http://api", "story-1");
        await flushMicrotasks();

        const status = document.getElementById("comments-status");
        expect(status.classList.contains("hidden")).toBe(false);
        expect(status.textContent).toContain("backend pending");
    });

    test("posting a comment prepends it to the list", async () => {
        global.isLoggedIn.mockReturnValue(true);
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ id: "c1", author: "Me", content: "Hello", created_at: "2026-01-01T00:00:00Z" })
        });

        setupComments("http://api", "story-1");
        await flushMicrotasks();

        document.getElementById("comment-input").value = "Hello";
        document.getElementById("comment-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

        await flushMicrotasks();

        expect(document.querySelectorAll("#comments-list li").length).toBe(1);
        expect(document.getElementById("comments-empty").classList.contains("hidden")).toBe(true);
        expect(global.authFetch).toHaveBeenCalledWith("http://api/stories/story-1/comments", expect.objectContaining({ method: "POST" }));
    });
});

