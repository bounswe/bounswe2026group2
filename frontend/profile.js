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
        var bioEl = document.getElementById("profile-bio");
        var locationEl = document.getElementById("profile-location");
        var avatarEl = document.getElementById("profile-avatar");

        if (nameEl) nameEl.textContent = data.display_name || data.username;
        if (bioEl) bioEl.textContent = data.bio || "";
        if (locationEl) {
            // Keep the icon span but replace the trailing text
            var iconSpan = locationEl.querySelector(".material-symbols-outlined");
            locationEl.textContent = "";
            if (iconSpan) locationEl.appendChild(iconSpan);
            var text = document.createTextNode(" " + (data.location || ""));
            locationEl.appendChild(text);
            if (!data.location) locationEl.style.display = "none";
        }
        if (avatarEl && data.avatar_url) {
            avatarEl.style.backgroundImage = "url('" + data.avatar_url + "')";
            avatarEl.style.backgroundSize = "cover";
            avatarEl.style.backgroundPosition = "center";
            avatarEl.style.backgroundRepeat = "no-repeat";
            var icon = avatarEl.querySelector(".material-symbols-outlined");
            if (icon) icon.style.opacity = "0";
        }
        if (joinedEl && data.created_at) {
            var date = new Date(data.created_at);
            var options = { month: 'long', year: 'numeric' };
            joinedEl.innerHTML = '<span class="material-symbols-outlined text-[18px]">calendar_month</span> Joined ' + date.toLocaleDateString('en-US', options);
        }
        renderBadges(data.badges || []);
        await loadUserStories(data.username);
        await loadSavedCount();
    } catch (err) {
        console.error("Error loading profile:", err);
    }
}

var BADGE_ASSET_BY_NAME = {
    "first story": "assets/1st story.png",
    "1st story": "assets/1st story.png",
    "story teller": "assets/story teller.png",
    "story master": "assets/story master.png"
};

function getBadgeAssetPath(badge) {
    var name = typeof badge === "string" ? badge : (badge && badge.name ? badge.name : "");
    return BADGE_ASSET_BY_NAME[name.trim().toLowerCase()] || "";
}

function renderBadges(badges) {
    var container = document.getElementById("profile-badges");
    if (!container) return;

    container.innerHTML = "";
    if (!Array.isArray(badges) || badges.length === 0) {
        var empty = document.createElement("p");
        empty.className = "text-sm text-textmuted italic col-span-3";
        empty.textContent = "No badges earned yet.";
        container.appendChild(empty);
        return;
    }

    badges.forEach(function (badge) {
        var name = badge && badge.name ? badge.name : "";
        var assetPath = getBadgeAssetPath(badge);
        if (!name || !assetPath) return;

        var badgeEl = document.createElement("div");
        badgeEl.className = "flex flex-col items-center gap-2 rounded-xl border border-border bg-background p-3 text-center";
        if (badge.description) badgeEl.title = badge.description;

        var img = document.createElement("img");
        img.src = assetPath;
        img.alt = name;
        img.className = "h-16 w-16 object-contain";

        var label = document.createElement("span");
        label.className = "text-xs font-semibold leading-snug text-textmain";
        label.textContent = name;

        badgeEl.appendChild(img);
        badgeEl.appendChild(label);
        container.appendChild(badgeEl);
    });

    if (!container.children.length) {
        var fallback = document.createElement("p");
        fallback.className = "text-sm text-textmuted italic col-span-3";
        fallback.textContent = "No badges earned yet.";
        container.appendChild(fallback);
    }
}

async function loadSavedCount() {
    var el = document.getElementById("stat-saved");
    if (!el) return;
    try {
        var res = await authFetch(API_BASE + "/stories/saved");
        if (!res.ok) return;
        var data = await res.json();
        var n = ((data && data.stories) || []).length;
        el.textContent = String(n);
    } catch (err) {
        console.error("Error loading saved count:", err);
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

        // Update likes/comments received on my stories (best-effort; may be slow for many stories)
        void updateEngagementStatsForStories(myStories);

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

async function updateEngagementStatsForStories(stories) {
    var likesEl = document.getElementById("stat-likes");
    var commentsEl = document.getElementById("stat-comments");
    if (!likesEl && !commentsEl) return;

    if (likesEl) likesEl.textContent = "…";
    if (commentsEl) commentsEl.textContent = "…";

    var totalLikes = 0;
    var totalComments = 0;

    // Limit concurrency to avoid spamming the API.
    var concurrency = 4;
    var index = 0;

    async function worker() {
        while (index < stories.length) {
            var i = index;
            index++;
            var story = stories[i];
            if (!story || !story.id) continue;

            try {
                // Likes: use story detail's like_count
                if (likesEl) {
                    var detailRes = await authFetch(API_BASE + "/stories/" + story.id);
                    if (detailRes.ok) {
                        var detail = await detailRes.json();
                        if (detail && typeof detail.like_count === "number") {
                            totalLikes += detail.like_count;
                        }
                    }
                }
            } catch (err) {
                // ignore per-story failures
                void err;
            }

            try {
                // Comments: use comments list response total
                if (commentsEl) {
                    var commentsRes = await authFetch(API_BASE + "/stories/" + story.id + "/comments");
                    if (commentsRes.ok) {
                        var commentsData = await commentsRes.json();
                        if (commentsData && typeof commentsData.total === "number") {
                            totalComments += commentsData.total;
                        } else if (commentsData && Array.isArray(commentsData.comments)) {
                            totalComments += commentsData.comments.length;
                        }
                    }
                }
            } catch (err) {
                void err;
            }
        }
    }

    var workers = [];
    for (var w = 0; w < Math.min(concurrency, stories.length || 0); w++) {
        workers.push(worker());
    }

    await Promise.all(workers);

    if (likesEl) likesEl.textContent = String(totalLikes);
    if (commentsEl) commentsEl.textContent = String(totalComments);
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", loadProfile);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        loadProfile: loadProfile,
        renderBadges: renderBadges,
        getBadgeAssetPath: getBadgeAssetPath
    };
}
