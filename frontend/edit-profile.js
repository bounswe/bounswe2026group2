async function loadEditProfile() {
    if (typeof requireAuth === "function" && !requireAuth()) return;

    try {
        var res = await authFetch(API_BASE + "/auth/me");
        if (!res.ok) {
            if (res.status === 401 && typeof logout === "function") logout();
            throw new Error("Failed to load profile");
        }
        var data = await res.json();
        
        var nameEl = document.getElementById("fullName");
        var emailEl = document.getElementById("email");
        
        if (nameEl) nameEl.value = data.display_name || data.username || "";
        if (emailEl) emailEl.value = data.email || "";
        
    } catch(err) {
        console.error("Error loading edit profile:", err);
    }
}

function handleEditProfileSubmit(e) {
    e.preventDefault();
    // Cannot submit to backend yet (no endpoint exists), so just redirect for now
    window.location.assign('profile.html');
}

function setupEditProfile() {
    loadEditProfile();
    var form = document.getElementById('edit-profile-form');
    if (form) {
        form.addEventListener('submit', handleEditProfileSubmit);
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", setupEditProfile);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        loadEditProfile: loadEditProfile,
        handleEditProfileSubmit: handleEditProfileSubmit,
        setupEditProfile: setupEditProfile
    };
}
