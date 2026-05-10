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
        var bioEl = document.getElementById("bio");
        var locationEl = document.getElementById("location");
        var avatarInputEl = document.getElementById("avatar-upload");
        
        if (nameEl) nameEl.value = data.display_name || data.username || "";
        if (emailEl) emailEl.value = data.email || "";
        if (bioEl) bioEl.value = data.bio || "";
        if (locationEl) locationEl.value = data.location || "";
        if (avatarInputEl && avatarInputEl.parentElement && data.avatar_url) {
            applyAvatarPreview(data.avatar_url);
        }
        
    } catch(err) {
        console.error("Error loading edit profile:", err);
    }
}

function getErrorDetail(payload) {
    if (!payload) return null;
    if (typeof payload === "string") return payload;
    if (payload.detail) return payload.detail;
    return null;
}

function applyAvatarPreview(url) {
    var avatarInputEl = document.getElementById("avatar-upload");
    if (!avatarInputEl || !avatarInputEl.parentElement) return;

    var container = avatarInputEl.parentElement;
    container.style.backgroundImage = "url('" + url + "')";
    container.style.backgroundSize = "cover";
    container.style.backgroundPosition = "center";
    container.style.backgroundRepeat = "no-repeat";

    // Hide the placeholder icon when we have an avatar image.
    var icon = container.querySelector(".material-symbols-outlined");
    if (icon) icon.style.opacity = "0";
}

async function uploadAvatarFromInput() {
    var input = document.getElementById("avatar-upload");
    if (!input || !input.files || !input.files[0]) return;

    var file = input.files[0];

    // Local preview immediately
    try {
        var objectUrl = URL.createObjectURL(file);
        applyAvatarPreview(objectUrl);
    } catch (err) {
        // Ignore preview failures; upload can still succeed.
        void err;
    }

    var form = new FormData();
    form.append("file", file);

    var res = await authFetch(API_BASE + "/auth/me/avatar", {
        method: "POST",
        body: form
    });

    if (!res.ok) {
        if (res.status === 401 && typeof logout === "function") logout();
        var payload = null;
        try { payload = await res.json(); } catch (err) { void err; }
        throw new Error(getErrorDetail(payload) || "Failed to upload avatar");
    }

    var data = await res.json();
    if (data && data.avatar_url) applyAvatarPreview(data.avatar_url);
}

async function handleEditProfileSubmit(e) {
    e.preventDefault();

    if (typeof requireAuth === "function" && !requireAuth()) return;

    var nameEl = document.getElementById("fullName");
    var bioEl = document.getElementById("bio");
    var locationEl = document.getElementById("location");

    var currentPasswordEl = document.getElementById("currentPassword");
    var newPasswordEl = document.getElementById("newPassword");
    var confirmPasswordEl = document.getElementById("confirmPassword");

    var profilePayload = {
        display_name: nameEl ? nameEl.value : null,
        bio: bioEl ? bioEl.value : null,
        location: locationEl ? locationEl.value : null
    };

    try {
        var wantsPasswordChange = false;
        var currentPassword = currentPasswordEl ? currentPasswordEl.value : "";
        var newPassword = newPasswordEl ? newPasswordEl.value : "";
        var confirmPassword = confirmPasswordEl ? confirmPasswordEl.value : "";

        if (currentPassword || newPassword || confirmPassword) wantsPasswordChange = true;

        if (wantsPasswordChange) {
            if (!currentPassword || !newPassword) {
                throw new Error("Please enter current password and a new password.");
            }
            if (newPassword !== confirmPassword) {
                throw new Error("New password and confirmation do not match.");
            }

            var pwRes = await authFetch(API_BASE + "/auth/me/password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            if (!pwRes.ok) {
                if (pwRes.status === 401 && typeof logout === "function") logout();
                var pwPayload = null;
                try { pwPayload = await pwRes.json(); } catch (err) { void err; }
                throw new Error(getErrorDetail(pwPayload) || "Failed to change password");
            }

            // Clear password inputs after successful change
            if (currentPasswordEl) currentPasswordEl.value = "";
            if (newPasswordEl) newPasswordEl.value = "";
            if (confirmPasswordEl) confirmPasswordEl.value = "";
        }

        var updateRes = await authFetch(API_BASE + "/auth/me", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profilePayload)
        });
        if (!updateRes.ok) {
            if (updateRes.status === 401 && typeof logout === "function") logout();
            var updatePayload = null;
            try { updatePayload = await updateRes.json(); } catch (err) { void err; }
            throw new Error(getErrorDetail(updatePayload) || "Failed to update profile");
        }

        window.location.assign("profile.html");
    } catch (err) {
        console.error("Error saving profile:", err);
        if (typeof window !== "undefined" && typeof window.alert === "function") {
            window.alert(err && err.message ? err.message : "Failed to save changes");
        }
    }
}

function setupEditProfile() {
    loadEditProfile();
    var form = document.getElementById('edit-profile-form');
    if (form) {
        form.addEventListener('submit', handleEditProfileSubmit);
    }

    var avatarInput = document.getElementById("avatar-upload");
    if (avatarInput) {
        avatarInput.addEventListener("change", function() {
            uploadAvatarFromInput().catch(function(err) {
                console.error("Error uploading avatar:", err);
                if (typeof window !== "undefined" && typeof window.alert === "function") {
                    window.alert(err && err.message ? err.message : "Failed to upload avatar");
                }
            });
        });
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", setupEditProfile);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        loadEditProfile: loadEditProfile,
        handleEditProfileSubmit: handleEditProfileSubmit,
        setupEditProfile: setupEditProfile,
        applyAvatarPreview: applyAvatarPreview,
        uploadAvatarFromInput: uploadAvatarFromInput
    };
}
