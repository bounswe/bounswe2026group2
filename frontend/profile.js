async function loadProfile() {
    if (typeof requireAuth === "function" && !requireAuth()) return;

    try {
        var res = await authFetch(API_BASE + "/auth/me");
        if (!res.ok) {
            if (res.status === 401 && typeof logout === "function") logout();
            throw new Error("Failed to load profile");
        }
        var data = await res.json();
        
        var nameEl = document.getElementById("profile-name");
        var joinedEl = document.getElementById("profile-joined");
        
        if (nameEl) nameEl.textContent = data.display_name || data.username;
        if (joinedEl && data.created_at) {
            var date = new Date(data.created_at);
            var options = { month: 'long', year: 'numeric' };
            joinedEl.innerHTML = '<span class="material-symbols-outlined text-[18px]">calendar_month</span> Joined ' + date.toLocaleDateString('en-US', options);
        }
        
    } catch(err) {
        console.error("Error loading profile:", err);
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", loadProfile);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        loadProfile: loadProfile
    };
}
