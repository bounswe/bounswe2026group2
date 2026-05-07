function setCommentsStatus(message) {
    // Screen-reader friendly status line for fetch/post outcomes.
    var el = document.getElementById("comments-status");
    if (!el) return;
    if (!message) {
        el.classList.add("hidden");
        el.textContent = "";
        return;
    }
    el.textContent = message;
    el.classList.remove("hidden");
}

function setCommentError(message) {
    // Inline error for the comment composer only (validation/post failures).
    var el = document.getElementById("comment-error");
    if (!el) return;
    if (!message) {
        el.classList.add("hidden");
        el.textContent = "";
        return;
    }
    el.textContent = message;
    el.classList.remove("hidden");
}

function normalizeComment(raw) {
    // Backend returns `author: { id, username, display_name }`.
    // Older mocks/tests pass `author` as a plain string or use `username`/`user`.
    var rawAuthor = raw.author;
    var author;
    if (rawAuthor && typeof rawAuthor === "object") {
        author = rawAuthor.display_name || rawAuthor.username || "Anonymous";
    } else {
        author = rawAuthor || raw.username || raw.user || "Anonymous";
    }
    var content = raw.content || raw.text || raw.message || "";
    var createdAt = raw.created_at || raw.createdAt || raw.created || null;
    return {
        id: raw.id || raw.comment_id || raw.commentId || null,
        author: String(author),
        content: String(content),
        created_at: createdAt ? String(createdAt) : null
    };
}

function formatCommentTime(isoLike) {
    // Keep formatting local to the client; backend can ship a display string later if desired.
    if (!isoLike) return "";
    var d = new Date(isoLike);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString();
}

function renderComments(comments) {
    // Stateless render: caller owns the comments array ordering.
    var list = document.getElementById("comments-list");
    var empty = document.getElementById("comments-empty");
    if (!list || !empty) return;

    list.innerHTML = "";

    if (!comments || comments.length === 0) {
        empty.classList.remove("hidden");
        return;
    }

    empty.classList.add("hidden");

    comments.forEach(function (c) {
        var li = document.createElement("li");
        li.className = "rounded-2xl border border-border bg-white px-4 py-3";

        var header = document.createElement("div");
        header.className = "flex items-center justify-between gap-3";

        var author = document.createElement("p");
        author.className = "text-sm font-semibold text-textmain";
        author.textContent = c.author;

        var time = document.createElement("p");
        time.className = "text-xs font-medium text-textmuted";
        time.textContent = formatCommentTime(c.created_at);

        header.appendChild(author);
        header.appendChild(time);

        var body = document.createElement("p");
        body.className = "mt-2 whitespace-pre-wrap text-sm leading-6 text-textmain";
        body.textContent = c.content;

        li.appendChild(header);
        li.appendChild(body);

        list.appendChild(li);
    });
}

async function fetchComments(apiBase, storyId) {
    // Public read: comments should be visible without authentication.
    var res = await fetch(apiBase + "/stories/" + storyId + "/comments");
    if (!res.ok) {
        var err = new Error("Comments endpoint unavailable");
        err.status = res.status;
        throw err;
    }
    var data = await res.json();
    var items = Array.isArray(data) ? data : (data.comments || data.items || []);
    return items.map(normalizeComment);
}

async function postComment(apiBase, storyId, content) {
    // Write requires authentication. We redirect to login to match app conventions.
    if (!isLoggedIn()) {
        window.location.assign("index.html");
        return null;
    }

    var res = await authFetch(apiBase + "/stories/" + storyId + "/comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content })
    });
    if (!res.ok) {
        var err = new Error("Failed to post comment");
        err.status = res.status;
        throw err;
    }
    return await res.json();
}

function setupComments(apiBase, storyId) {
    // Wires the Comments UI for a single story detail page instance.
    var form = document.getElementById("comment-form");
    var input = document.getElementById("comment-input");
    var submit = document.getElementById("comment-submit");
    var loginPrompt = document.getElementById("comments-login-prompt");

    if (!form || !input || !submit || !loginPrompt) return;

    // Gate composer by auth state (view-only remains available).
    if (isLoggedIn()) {
        form.classList.remove("hidden");
        loginPrompt.classList.add("hidden");
    } else {
        form.classList.add("hidden");
        loginPrompt.classList.remove("hidden");
    }

    setCommentsStatus("");
    setCommentError("");

    // Keep local state so we can prepend on successful POST without refetching.
    var state = [];
    fetchComments(apiBase, storyId)
        .then(function (comments) {
            state = comments || [];
            renderComments(state);
        })
        .catch(function () {
            renderComments(state);
            setCommentsStatus("Comments unavailable (backend pending).");
        });

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        setCommentError("");
        setCommentsStatus("");

        var text = String(input.value || "").trim();
        if (!text) {
            setCommentError("Please write a comment before posting.");
            return;
        }

        // Disable double-submit; re-enable in finally.
        submit.disabled = true;
        try {
            var created = await postComment(apiBase, storyId, text);
            if (!created) {
                return;
            }

            // Prefer server response shape; fall back to a local echo until backend stabilizes.
            if (Array.isArray(created)) {
                state = created.map(normalizeComment);
            } else if (created && (created.comments || created.items)) {
                var items = created.comments || created.items || [];
                state = items.map(normalizeComment);
            } else if (created && (created.content || created.text || created.message)) {
                state = [normalizeComment(created)].concat(state);
            } else {
                state = [normalizeComment({ content: text, author: "You", created_at: new Date().toISOString() })].concat(state);
            }

            input.value = "";
            renderComments(state);
        } catch (err) {
            setCommentError("Unable to post comment yet.");
        } finally {
            submit.disabled = false;
        }
    });
}

if (typeof module !== "undefined" && module.exports) {
    // CommonJS exports for Jest unit tests (browser ignores this block).
    module.exports = {
        normalizeComment: normalizeComment,
        renderComments: renderComments,
        fetchComments: fetchComments,
        postComment: postComment,
        setupComments: setupComments
    };
}

