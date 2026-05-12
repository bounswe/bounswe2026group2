function setLikeStatus(message) {
    var el = document.getElementById("like-status");
    if (!el) return;
    if (!message) {
        el.classList.add("hidden");
        el.textContent = "";
        return;
    }
    el.textContent = message;
    el.classList.remove("hidden");
}

function setLikeUi(state) {
    var btn = document.getElementById("like-button");
    var count = document.getElementById("like-count");
    var label = document.getElementById("like-button-text");
    if (!btn || !count || !label) return;

    btn.dataset.liked = state.liked_by_me ? "true" : "false";
    btn.setAttribute("aria-pressed", state.liked_by_me ? "true" : "false");
    count.textContent = String(state.likes_count || 0);

    if (state.liked_by_me) {
        btn.classList.remove("bg-white", "text-primary", "hover:bg-stone-50");
        btn.classList.add("bg-primary", "text-white", "hover:opacity-95");
        label.textContent = "Liked";
        btn.setAttribute("aria-label", "Unlike this story");
    } else {
        btn.classList.remove("bg-primary", "text-white", "hover:opacity-95");
        btn.classList.add("bg-white", "text-primary", "hover:bg-stone-50");
        label.textContent = "Like";
        btn.setAttribute("aria-label", "Like this story");
    }
}

function normalizeLikeSummary(raw, fallbackStoryId) {
    // Backend returns { story_id, liked, like_count }; UI uses { story_id, liked_by_me, likes_count }.
    // Tolerate either shape so older tests/mocks keep working.
    if (!raw || typeof raw !== "object") {
        return { story_id: fallbackStoryId, liked_by_me: false, likes_count: 0 };
    }
    var liked = (typeof raw.liked === "boolean") ? raw.liked : !!raw.liked_by_me;
    var count = (typeof raw.like_count === "number") ? raw.like_count
        : (typeof raw.likes_count === "number") ? raw.likes_count
        : 0;
    return {
        story_id: raw.story_id || fallbackStoryId,
        liked_by_me: liked,
        likes_count: Math.max(0, count)
    };
}

async function fetchLikeSummary(apiBase, storyId) {
    var res = await authFetch(apiBase + "/stories/" + storyId + "/like");
    if (!res.ok) {
        var err = new Error("Likes endpoint unavailable");
        err.status = res.status;
        throw err;
    }
    var data = await res.json();
    return normalizeLikeSummary(data, storyId);
}

async function sendLikeToggle(apiBase, storyId, likedByMe) {
    if (!isLoggedIn()) {
        window.location.assign("index.html");
        return null;
    }

    var method = likedByMe ? "DELETE" : "POST";
    var res = await authFetch(apiBase + "/stories/" + storyId + "/like", { method: method });
    if (!res.ok) {
        var err = new Error("Failed to update like");
        err.status = res.status;
        throw err;
    }
    var data = await res.json();
    return normalizeLikeSummary(data, storyId);
}

function setupLikes(apiBase, storyId, seed) {
    // `seed` is optional: { like_count?: number } from the public story detail.
    // Used to render the count for anonymous viewers (GET /like requires auth).
    var btn = document.getElementById("like-button");
    if (!btn) return;

    var seedCount = (seed && typeof seed.like_count === "number") ? Math.max(0, seed.like_count) : 0;
    var state = { story_id: storyId, likes_count: seedCount, liked_by_me: false };

    btn.disabled = true;
    setLikeStatus("");

    if (!isLoggedIn()) {
        // GET /like requires auth; render seed-only state and let click redirect to login.
        setLikeUi(state);
        btn.disabled = false;
    } else {
        fetchLikeSummary(apiBase, storyId)
            .then(function (summary) {
                state = summary || state;
                setLikeUi(state);
            })
            .catch(function () {
                setLikeUi(state);
                setLikeStatus("Likes unavailable (backend pending).");
            })
            .finally(function () {
                btn.disabled = false;
            });
    }

    btn.addEventListener("click", async function () {
        if (btn.disabled) return;

        btn.dataset.animating = "true";
        window.setTimeout(function () {
            btn.dataset.animating = "false";
        }, 200);

        setLikeStatus("");

        var optimistic = {
            story_id: storyId,
            liked_by_me: !state.liked_by_me,
            likes_count: Math.max(0, (state.likes_count || 0) + (state.liked_by_me ? -1 : 1))
        };
        setLikeUi(optimistic);

        btn.disabled = true;
        try {
            var updated = await sendLikeToggle(apiBase, storyId, state.liked_by_me);
            if (updated) {
                state = updated;
                setLikeUi(state);
            } else {
                setLikeUi(state);
            }
        } catch (_err) {
            setLikeUi(state);
            setLikeStatus("Unable to save like yet.");
        } finally {
            btn.disabled = false;
        }
    });
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        setLikeStatus: setLikeStatus,
        setLikeUi: setLikeUi,
        normalizeLikeSummary: normalizeLikeSummary,
        fetchLikeSummary: fetchLikeSummary,
        sendLikeToggle: sendLikeToggle,
        setupLikes: setupLikes
    };
}

