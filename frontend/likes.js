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

async function fetchLikeSummary(apiBase, storyId) {
    var res = await authFetch(apiBase + "/stories/" + storyId + "/likes");
    if (!res.ok) {
        var err = new Error("Likes endpoint unavailable");
        err.status = res.status;
        throw err;
    }
    return await res.json();
}

async function sendLikeToggle(apiBase, storyId, likedByMe) {
    if (!isLoggedIn()) {
        window.location.assign("index.html");
        return null;
    }

    var method = likedByMe ? "DELETE" : "POST";
    var res = await authFetch(apiBase + "/stories/" + storyId + "/likes", { method: method });
    if (!res.ok) {
        var err = new Error("Failed to update like");
        err.status = res.status;
        throw err;
    }
    return await res.json();
}

function setupLikes(apiBase, storyId) {
    var btn = document.getElementById("like-button");
    if (!btn) return;

    var state = { story_id: storyId, likes_count: 0, liked_by_me: false };

    btn.disabled = true;
    setLikeStatus("");

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
        } catch (err) {
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
        fetchLikeSummary: fetchLikeSummary,
        sendLikeToggle: sendLikeToggle,
        setupLikes: setupLikes
    };
}

