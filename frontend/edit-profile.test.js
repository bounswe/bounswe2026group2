global.API_BASE = "http://localhost";
global.requireAuth = jest.fn();
global.authFetch = jest.fn();
global.logout = jest.fn();

const { loadEditProfile, handleEditProfileSubmit, setupEditProfile, uploadAvatarFromInput } = require("./edit-profile");

describe("edit profile page unit tests", () => {
    let assignMock;

    beforeEach(() => {
        document.body.innerHTML = "";
        global.requireAuth.mockReset().mockReturnValue(true);
        global.authFetch.mockReset();
        global.logout.mockReset();
        
        assignMock = jest.fn();
        Object.defineProperty(window, "location", {
            value: { assign: assignMock, origin: "http://localhost" },
            writable: true,
            configurable: true
        });

        window.alert = jest.fn();
        if (!global.URL) global.URL = {};
        global.URL.createObjectURL = jest.fn(() => "blob:mock");
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("loadEditProfile returns early if not authenticated", async () => {
        global.requireAuth.mockReturnValue(false);
        await loadEditProfile();
        expect(global.authFetch).not.toHaveBeenCalled();
    });

    test("loadEditProfile populates form elements on success", async () => {
        document.body.innerHTML = `
            <input id="fullName" value="" />
            <input id="email" value="" />
            <textarea id="bio"></textarea>
            <input id="location" value="" />
            <div><span class="material-symbols-outlined"></span><input type="file" id="avatar-upload" /></div>
        `;
        
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ 
                display_name: "Test Edit User",
                email: "test@example.com",
                bio: "Hello",
                location: "Istanbul",
                avatar_url: null
            })
        });

        await loadEditProfile();

        expect(document.getElementById("fullName").value).toBe("Test Edit User");
        expect(document.getElementById("email").value).toBe("test@example.com");
        expect(document.getElementById("bio").value).toBe("Hello");
        expect(document.getElementById("location").value).toBe("Istanbul");
    });
    
    test("handleEditProfileSubmit patches profile and redirects", async () => {
        document.body.innerHTML = `
            <form id="edit-profile-form"></form>
            <input id="fullName" value="Name" />
            <textarea id="bio">Bio</textarea>
            <input id="location" value="Loc" />
            <input id="currentPassword" value="" />
            <input id="newPassword" value="" />
            <input id="confirmPassword" value="" />
        `;

        const fakeEvent = {
            preventDefault: jest.fn()
        };

        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({}) // PATCH /auth/me response body
        });

        await handleEditProfileSubmit(fakeEvent);
        expect(fakeEvent.preventDefault).toHaveBeenCalledTimes(1);
        expect(global.authFetch).toHaveBeenCalledWith(
            "http://localhost/auth/me",
            expect.objectContaining({ method: "PATCH" })
        );
        expect(assignMock).toHaveBeenCalledWith("profile.html");
    });
    
    test("setupEditProfile attaches submit listener", async () => {
        document.body.innerHTML = `
            <form id="edit-profile-form">
                <button type="submit"></button>
            </form>
        `;
        
        // mock authFetch for loadEditProfile call within setupEditProfile
        global.authFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
        
        setupEditProfile();
        
        const form = document.getElementById("edit-profile-form");
        const submitEvent = new Event("submit", { bubbles: true, cancelable: true });
        // For submit, handleEditProfileSubmit will PATCH /auth/me
        global.authFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
        await form.dispatchEvent(submitEvent);
        
        expect(assignMock).toHaveBeenCalledWith("profile.html");
    });

    test("handleEditProfileSubmit calls password endpoint when password fields are provided", async () => {
        document.body.innerHTML = `
            <form id="edit-profile-form"></form>
            <input id="fullName" value="Name" />
            <textarea id="bio">Bio</textarea>
            <input id="location" value="Loc" />
            <input id="currentPassword" value="OldPass1!" />
            <input id="newPassword" value="NewPass1!" />
            <input id="confirmPassword" value="NewPass1!" />
        `;

        const fakeEvent = { preventDefault: jest.fn() };

        global.authFetch
            // PATCH /auth/me
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
            // POST /auth/me/password (204, no body)
            .mockResolvedValueOnce({ ok: true, status: 204, json: () => Promise.resolve({}) });

        await handleEditProfileSubmit(fakeEvent);

        expect(global.authFetch).toHaveBeenNthCalledWith(
            1,
            "http://localhost/auth/me",
            expect.objectContaining({ method: "PATCH" })
        );
        expect(global.authFetch).toHaveBeenNthCalledWith(
            2,
            "http://localhost/auth/me/password",
            expect.objectContaining({ method: "POST" })
        );
        expect(assignMock).toHaveBeenCalledWith("profile.html");
    });

    test("handleEditProfileSubmit blocks password change when confirmation mismatches", async () => {
        document.body.innerHTML = `
            <form id="edit-profile-form"></form>
            <input id="fullName" value="Name" />
            <textarea id="bio">Bio</textarea>
            <input id="location" value="Loc" />
            <input id="currentPassword" value="OldPass1!" />
            <input id="newPassword" value="NewPass1!" />
            <input id="confirmPassword" value="Different1!" />
        `;

        const fakeEvent = { preventDefault: jest.fn() };

        global.authFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

        await handleEditProfileSubmit(fakeEvent);

        // Only PATCH should have happened; password call should not.
        expect(global.authFetch).toHaveBeenCalledTimes(1);
        expect(window.alert).toHaveBeenCalled();
        expect(assignMock).not.toHaveBeenCalledWith("profile.html");
    });

    test("uploadAvatarFromInput posts multipart to /auth/me/avatar", async () => {
        document.body.innerHTML = `
            <div>
                <span class="material-symbols-outlined"></span>
                <input type="file" id="avatar-upload" />
            </div>
        `;

        const input = document.getElementById("avatar-upload");
        const file = new File(["x"], "a.png", { type: "image/png" });
        Object.defineProperty(input, "files", { value: [file] });

        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ avatar_url: "http://cdn/new.png" })
        });

        await uploadAvatarFromInput();

        expect(global.authFetch).toHaveBeenCalledWith(
            "http://localhost/auth/me/avatar",
            expect.objectContaining({ method: "POST" })
        );
    });
});
