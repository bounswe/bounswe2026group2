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
            <p id="profile-bio"></p>
            <span id="profile-location"><span class="material-symbols-outlined">location_on</span></span>
            <div id="profile-avatar"><span class="material-symbols-outlined">person</span></div>
        `;
        
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ 
                display_name: "Test User",
                created_at: "2026-04-07T00:00:00Z",
                bio: "My bio",
                location: "Istanbul",
                avatar_url: "http://cdn/avatar.png",
                username: "testuser"
            })
        });

        await loadProfile();

        expect(document.getElementById("profile-name").textContent).toBe("Test User");
        expect(document.getElementById("profile-joined").innerHTML).toContain("Joined ");
        expect(document.getElementById("profile-bio").textContent).toBe("My bio");
        expect(document.getElementById("profile-location").textContent).toContain("Istanbul");
    });

    test("loadProfile hides location row when location is empty", async () => {
        document.body.innerHTML = `
            <h1 id="profile-name"></h1>
            <span id="profile-joined"></span>
            <p id="profile-bio"></p>
            <span id="profile-location"><span class="material-symbols-outlined">location_on</span></span>
            <div id="profile-avatar"><span class="material-symbols-outlined">person</span></div>
            <div id="profile-stories-container"></div>
            <div id="stat-saved"></div>
            <div id="stat-stories"></div>
        `;

        global.authFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    username: "u1",
                    created_at: "2026-04-07T00:00:00Z",
                    location: ""
                })
            })
            // /stories
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ stories: [] })
            })
            // /stories/saved
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ stories: [] })
            });

        await loadProfile();
        expect(document.getElementById("profile-location").style.display).toBe("none");
    });

    test("loadProfile applies avatar image when avatar_url is present", async () => {
        document.body.innerHTML = `
            <h1 id="profile-name"></h1>
            <span id="profile-joined"></span>
            <p id="profile-bio"></p>
            <span id="profile-location"><span class="material-symbols-outlined">location_on</span></span>
            <div id="profile-avatar"><span class="material-symbols-outlined">person</span></div>
            <div id="profile-stories-container"></div>
            <div id="stat-saved"></div>
            <div id="stat-stories"></div>
        `;

        global.authFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    username: "u1",
                    created_at: "2026-04-07T00:00:00Z",
                    avatar_url: "http://cdn/avatar.png"
                })
            })
            // /stories
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ stories: [] })
            })
            // /stories/saved
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ stories: [] })
            });

        await loadProfile();
        var avatar = document.getElementById("profile-avatar");
        expect(avatar.style.backgroundImage).toContain("http://cdn/avatar.png");
        var icon = avatar.querySelector(".material-symbols-outlined");
        expect(icon.style.opacity).toBe("0");
    });

    test("loadProfile falls back to username when display_name is missing", async () => {
        document.body.innerHTML = `
            <h1 id="profile-name"></h1>
            <span id="profile-joined"></span>
            <p id="profile-bio"></p>
            <span id="profile-location"><span class="material-symbols-outlined">location_on</span></span>
            <div id="profile-avatar"><span class="material-symbols-outlined">person</span></div>
            <div id="profile-stories-container"></div>
            <div id="stat-saved"></div>
            <div id="stat-stories"></div>
        `;

        global.authFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    username: "fallback_user",
                    display_name: null,
                    created_at: "2026-04-07T00:00:00Z"
                })
            })
            // /stories
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ stories: [] })
            })
            // /stories/saved
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ stories: [] })
            });

        await loadProfile();
        expect(document.getElementById("profile-name").textContent).toBe("fallback_user");
    });
});
