global.API_BASE = "http://localhost";
global.requireAuth = jest.fn();
global.authFetch = jest.fn();
global.logout = jest.fn();

const { loadProfile } = require("./profile");

describe("profile page unit tests", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
        global.requireAuth.mockReset().mockReturnValue(true);
        global.authFetch.mockReset();
        global.logout.mockReset();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("loadProfile returns early if not authenticated", async () => {
        global.requireAuth.mockReturnValue(false);
        await loadProfile();
        expect(global.authFetch).not.toHaveBeenCalled();
    });

    test("loadProfile calls logout on 401 response", async () => {
        global.authFetch.mockResolvedValueOnce({
            ok: false,
            status: 401
        });
        
        // suppress console.error for clean test output
        const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

        await loadProfile();
        expect(global.logout).toHaveBeenCalledTimes(1);
        
        consoleSpy.mockRestore();
    });

    test("loadProfile populates DOM elements on success", async () => {
        document.body.innerHTML = `
            <h1 id="profile-name"></h1>
            <span id="profile-joined"></span>
        `;
        
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ 
                display_name: "Test User",
                created_at: "2026-04-07T00:00:00Z"
            })
        });

        await loadProfile();

        expect(document.getElementById("profile-name").textContent).toBe("Test User");
        expect(document.getElementById("profile-joined").innerHTML).toContain("Joined ");
    });
});
