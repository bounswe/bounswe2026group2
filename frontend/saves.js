function setSaveStatus(message) {
    var el = document.getElementById("save-status");
    if (!el) return;
    if (!message) {
        el.classList.add("hidden");
        el.textContent = "";
        return;
    }
    el.textContent = message;
    el.classList.remove("hidden");
}

function setSaveUi(state) {
    var btn = document.getElementById("save-button");
    var label = document.getElementById("save-button-text");
    var icon = document.getElementById("save-button-icon");
    if (!btn || !label) return;

    btn.dataset.saved = state.saved ? "true" : "false";
    btn.setAttribute("aria-pressed", state.saved ? "true" : "false");

    if (state.saved) {
        btn.classList.remove("bg-white", "text-primary", "hover:bg-stone-50");
        btn.classList.add("bg-primary", "text-white", "hover:opacity-95");
        label.textContent = "Saved";
        if (icon) icon.style.fontVariationSettings = "'FILL' 1";
        btn.setAttribute("aria-label", "Remove this story from your saved list");
    } else {
        btn.classList.remove("bg-primary", "text-white", "hover:opacity-95");
        btn.classList.add("bg-white", "text-primary", "hover:bg-stone-50");
        label.textContent = "Save";
        if (icon) icon.style.fontVariationSettings = "'FILL' 0";
        btn.setAttribute("aria-label", "Save this story");
    }
}

async function fetchIsSaved(apiBase, storyId) {
    // Backend has no per-story "saved by me" endpoint — derive membership from the saved list.
    var res = await authFetch(apiBase + "/stories/saved");
    if (!res.ok) {
        var err = new Error("Saved list unavailable");
        err.status = res.status;
        throw err;
    }
    var data = await res.json();
    var stories = (data && data.stories) || [];
    return stories.some(function (s) { return String(s.id) === String(storyId); });
}

async function sendSaveToggle(apiBase, storyId, savedNow) {
    if (!isLoggedIn()) {
        window.location.assign("index.html");
        return null;
    }

    var method = savedNow ? "DELETE" : "POST";
    var res = await authFetch(apiBase + "/stories/" + storyId + "/save", { method: method });
    if (!res.ok) {
        var err = new Error("Failed to update saved state");
        err.status = res.status;
        throw err;
    }
    return await res.json();
}

function setupSaveButton(apiBase, storyId) {
    var btn = document.getElementById("save-button");
    if (!btn) return;

    var state = { story_id: storyId, saved: false };

    btn.disabled = true;
    setSaveStatus("");

    if (!isLoggedIn()) {
        // Not signed in: show the button in default state; click will redirect to login.
        setSaveUi(state);
        btn.disabled = false;
    } else {
        fetchIsSaved(apiBase, storyId)
            .then(function (saved) {
                state = { story_id: storyId, saved: !!saved };
                setSaveUi(state);
            })
            .catch(function () {
                setSaveUi(state);
                setSaveStatus("Saved status unavailable.");
            })
            .finally(function () {
                btn.disabled = false;
            });
    }

    btn.addEventListener("click", async function () {
        if (btn.disabled) return;

        if (!isLoggedIn()) {
            window.location.assign("index.html");
            return;
        }

        btn.dataset.animating = "true";
        window.setTimeout(function () { btn.dataset.animating = "false"; }, 200);

        setSaveStatus("");

        var optimistic = { story_id: storyId, saved: !state.saved };
        setSaveUi(optimistic);

        btn.disabled = true;
        try {
            var updated = await sendSaveToggle(apiBase, storyId, state.saved);
            if (updated) {
                state = updated;
                setSaveUi(state);
            } else {
                state = optimistic;
                setSaveUi(state);
            }
        } catch {
            setSaveUi(state);
            setSaveStatus("Unable to update saved state.");
        } finally {
            btn.disabled = false;
        }
    });
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        setSaveStatus: setSaveStatus,
        setSaveUi: setSaveUi,
        fetchIsSaved: fetchIsSaved,
        sendSaveToggle: sendSaveToggle,
        setupSaveButton: setupSaveButton
    };
}
