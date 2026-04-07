global.API_BASE = "http://localhost";
global.requireAuth = jest.fn();
global.authFetch = jest.fn();
global.logout = jest.fn();

const { loadEditProfile, handleEditProfileSubmit, setupEditProfile } = require("./edit-profile");

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
        `;
        
        global.authFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ 
                display_name: "Test Edit User",
                email: "test@example.com"
            })
        });

        await loadEditProfile();

        expect(document.getElementById("fullName").value).toBe("Test Edit User");
        expect(document.getElementById("email").value).toBe("test@example.com");
    });
    
    test("handleEditProfileSubmit prevents default and redirects", () => {
        const fakeEvent = {
            preventDefault: jest.fn()
        };
        handleEditProfileSubmit(fakeEvent);
        expect(fakeEvent.preventDefault).toHaveBeenCalledTimes(1);
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
        form.dispatchEvent(submitEvent);
        
        expect(assignMock).toHaveBeenCalledWith("profile.html");
    });
});
