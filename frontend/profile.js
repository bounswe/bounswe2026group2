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
        await loadUserStories(data.username);
    } catch (err) {
        console.error("Error loading profile:", err);
    }
}

async function loadUserStories(username) {
    const container = document.getElementById("profile-stories-container");
    if (!container) return;

    try {
        // Tüm hikayeleri çek
        const res = await authFetch(API_BASE + "/stories");
        if (!res.ok) throw new Error("Failed to fetch stories");

        const data = await res.json();

        // Sadece bu kullanıcıya ait olanları filtrele
        const myStories = (data.stories || []).filter(s => s.author === username);

        // Update the Stories Activity Counter
        const statStoriesEl = document.getElementById("stat-stories");
        if (statStoriesEl) statStoriesEl.textContent = myStories.length;

        // EĞER HİKAYE YOKSA: Senin orijinal güzel tasarımını göster
        if (myStories.length === 0) {
            container.innerHTML = `
                <div class="bg-surface rounded-2xl p-8 border border-border flex flex-col items-center justify-center text-center shadow-sm">
                    <span class="material-symbols-outlined text-4xl text-stone-300 mb-3">auto_stories</span>
                    <p class="text-textmain font-medium">You haven't published any stories yet.</p>
                    <p class="text-sm text-textmuted mt-1">Start sharing your historical memories with the community.</p>
                    <a href="story-create.html" class="mt-4 px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:opacity-95 transition">Create your first story</a>
                </div>
            `;
            return;
        }

        // EĞER HİKAYE VARSA: Hikaye kartlarını oluştur ve ekrana bas
        container.innerHTML = myStories.map(story => `
            <article class="bg-surface rounded-2xl p-6 border border-border shadow-sm hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-headline text-xl font-bold text-textmain">${story.title}</h3>
                    <span class="text-xs font-medium px-2 py-1 bg-background rounded-full border border-border">
                        ${new Date(story.created_at || Date.now()).toLocaleDateString()}
                    </span>
                </div>
                <p class="text-textmuted text-sm line-clamp-2 mb-4">${story.content}</p>
                <div class="flex items-center justify-between text-xs text-textmuted">
                    <span class="flex items-center gap-1">
                        <span class="material-symbols-outlined text-sm">location_on</span> 
                        ${story.location_name || 'Galata, Istanbul'}
                    </span>
                    <a href="story-detail.html?id=${story.id}" class="text-primary font-semibold hover:underline">Read more</a>
                </div>
            </article>
        `).join('');

    } catch (err) {
        console.error("Error loading user stories:", err);
        container.innerHTML = `<p class="text-red-500 text-center p-4">Error loading stories. Please try again.</p>`;
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