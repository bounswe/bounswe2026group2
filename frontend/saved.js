function escapeHtml(value) {
    if (value === undefined || value === null) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderEmptyState(container) {
    container.innerHTML = `
        <div class="bg-surface rounded-2xl p-8 border border-border flex flex-col items-center justify-center text-center shadow-sm">
            <span class="material-symbols-outlined text-4xl text-stone-300 mb-3">bookmark</span>
            <p class="text-textmain font-medium">You haven't saved any stories yet.</p>
            <p class="text-sm text-textmuted mt-1">Tap the Save button on a story to bookmark it for later.</p>
            <a href="map.html" class="mt-4 px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:opacity-95 transition">Browse stories on the map</a>
        </div>
    `;
}

function renderSavedCard(story) {
    var dateLabel = story.created_at
        ? new Date(story.created_at).toLocaleDateString()
        : "";
    var preview = (story.content || "").length > 200
        ? story.content.substring(0, 200) + "…"
        : (story.content || "");
    var place = story.place_name || story.location_name || "";

    return `
        <article class="bg-surface rounded-2xl p-6 border border-border shadow-sm hover:shadow-md transition-shadow" data-story-id="${escapeHtml(story.id)}">
            <div class="flex justify-between items-start mb-2 gap-3">
                <h3 class="font-headline text-xl font-bold text-textmain">${escapeHtml(story.title || "Untitled")}</h3>
                ${dateLabel ? `<span class="text-xs font-medium px-2 py-1 bg-background rounded-full border border-border whitespace-nowrap">${escapeHtml(dateLabel)}</span>` : ""}
            </div>
            <p class="text-textmuted text-sm line-clamp-2 mb-4">${escapeHtml(preview)}</p>
            <div class="flex items-center justify-between text-xs text-textmuted gap-3">
                <span class="flex items-center gap-1 truncate">
                    <span class="material-symbols-outlined text-sm">location_on</span>
                    ${escapeHtml(place || "Unknown location")}
                </span>
                <div class="flex items-center gap-3 shrink-0">
                    <button type="button" data-action="unsave"
                        class="inline-flex items-center gap-1 text-xs font-semibold text-red-600 hover:text-red-700 transition-colors">
                        <span class="material-symbols-outlined text-[16px]">bookmark_remove</span>
                        Unsave
                    </button>
                    <a href="story-detail.html?id=${encodeURIComponent(story.id)}" class="text-primary font-semibold hover:underline">Read more</a>
                </div>
            </div>
        </article>
    `;
}

async function unsaveStory(storyId) {
    var res = await authFetch(API_BASE + "/stories/" + storyId + "/save", { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to unsave");
    return await res.json();
}

function attachUnsaveHandlers(container, onCountChange) {
    container.addEventListener("click", async function (e) {
        var btn = e.target.closest("[data-action='unsave']");
        if (!btn) return;
        var card = btn.closest("article[data-story-id]");
        if (!card) return;

        var storyId = card.getAttribute("data-story-id");
        btn.disabled = true;
        try {
            await unsaveStory(storyId);
            card.remove();
            onCountChange();
        } catch (err) {
            console.error("Unsave failed:", err);
            btn.disabled = false;
            alert("Could not remove from saved. Please try again.");
        }
    });
}

async function loadSavedStories() {
    if (typeof requireAuth === "function" && !requireAuth()) return;

    var container = document.getElementById("saved-container");
    var countEl = document.getElementById("saved-count");
    if (!container) return;

    function updateCount() {
        var n = container.querySelectorAll("article[data-story-id]").length;
        if (countEl) countEl.textContent = n + " saved " + (n === 1 ? "story" : "stories");
        if (n === 0) renderEmptyState(container);
    }

    try {
        var res = await authFetch(API_BASE + "/stories/saved");
        if (!res.ok) {
            if (res.status === 401 && typeof logout === "function") {
                logout();
                return;
            }
            throw new Error("Failed to fetch saved stories");
        }
        var data = await res.json();
        var stories = (data && data.stories) || [];

        if (stories.length === 0) {
            renderEmptyState(container);
            if (countEl) countEl.textContent = "0 saved stories";
            return;
        }

        container.innerHTML = stories.map(renderSavedCard).join("");
        if (countEl) {
            countEl.textContent = stories.length + " saved " + (stories.length === 1 ? "story" : "stories");
        }
        attachUnsaveHandlers(container, updateCount);
    } catch (err) {
        console.error("Error loading saved stories:", err);
        container.innerHTML = `<p class="text-red-600 text-center p-4">Could not load your saved stories. Please try again later.</p>`;
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", loadSavedStories);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        loadSavedStories: loadSavedStories,
        renderSavedCard: renderSavedCard,
        renderEmptyState: renderEmptyState
    };
}
