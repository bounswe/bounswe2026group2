var TAGS_MAX_DEFAULT = 10;
var TAGS_SUGGEST_MIN_CHARS = 2;
var TAGS_DEBOUNCE_MS = 300;

function fetchTagSuggestions(apiBase, query) {
    return fetch(apiBase + "/tags?q=" + encodeURIComponent(query) + "&limit=10")
        .then(function (res) {
            if (!res.ok) return [];
            return res.json();
        })
        .catch(function () { return []; });
}

function renderTagChips(containerEl, tags) {
    if (!containerEl) return;
    containerEl.innerHTML = "";

    if (!tags || tags.length === 0) {
        containerEl.style.display = "none";
        return;
    }

    containerEl.style.display = "";
    tags.forEach(function (tag) {
        var name = typeof tag === "string" ? tag : (tag && tag.name ? tag.name : "");
        if (!name) return;
        var chip = document.createElement("span");
        chip.className = "tag-chip inline-flex items-center rounded-full border border-border bg-[rgba(119,90,25,0.08)] px-3 py-1 text-xs font-semibold text-primary";
        chip.textContent = name;
        containerEl.appendChild(chip);
    });
}

function createTagInput(containerEl, options) {
    if (!containerEl) {
        return { getTags: function () { return []; }, setTags: function () {}, destroy: function () {} };
    }

    options = options || {};
    var maxTags = typeof options.maxTags === "number" ? options.maxTags : TAGS_MAX_DEFAULT;
    var apiBase = options.apiBase || null;

    var tags = [];
    var suggestTimer = null;
    var dropdownVisible = false;
    var activeIndex = -1;

    containerEl.style.position = "relative";
    containerEl.innerHTML = "";

    var wrapper = document.createElement("div");
    wrapper.className = "flex flex-wrap gap-2 items-center rounded-xl border border-border bg-white px-3 py-2 cursor-text min-h-[44px]";
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("aria-label", "Tag input");

    var chipsArea = document.createElement("div");
    chipsArea.className = "flex flex-wrap gap-1.5 items-center";

    var inputEl = document.createElement("input");
    inputEl.type = "text";
    inputEl.className = "flex-1 min-w-[120px] border-none bg-transparent text-sm outline-none placeholder:text-textmuted";
    inputEl.setAttribute("aria-label", "Add a tag");
    inputEl.setAttribute("autocomplete", "off");
    inputEl.placeholder = "Type a tag and press Enter";

    wrapper.appendChild(chipsArea);
    wrapper.appendChild(inputEl);
    wrapper.addEventListener("click", function () { inputEl.focus(); });

    var dropdownEl = document.createElement("div");
    dropdownEl.className = "tag-dropdown hidden absolute left-0 right-0 z-50 mt-1 max-h-48 overflow-y-auto rounded-xl border border-border bg-white shadow-soft";
    dropdownEl.setAttribute("role", "listbox");

    containerEl.appendChild(wrapper);
    containerEl.appendChild(dropdownEl);

    function renderChips() {
        chipsArea.innerHTML = "";
        tags.forEach(function (tag, i) {
            var chip = document.createElement("span");
            chip.className = "inline-flex items-center gap-1 rounded-full bg-[rgba(119,90,25,0.1)] px-2.5 py-0.5 text-xs font-semibold text-primary";

            var nameSpan = document.createElement("span");
            nameSpan.textContent = tag;

            var removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "tag-remove-btn ml-0.5 leading-none text-primary/60 hover:text-primary transition-colors";
            removeBtn.setAttribute("aria-label", "Remove tag " + tag);
            removeBtn.textContent = "×";
            (function (index) {
                removeBtn.addEventListener("click", function (e) {
                    e.stopPropagation();
                    removeTag(index);
                });
            }(i));

            chip.appendChild(nameSpan);
            chip.appendChild(removeBtn);
            chipsArea.appendChild(chip);
        });

        inputEl.disabled = tags.length >= maxTags;
        inputEl.placeholder = tags.length >= maxTags ? "Max tags reached" : "Type a tag and press Enter";
    }

    function addTag(name) {
        name = name.trim().toLowerCase();
        if (!name || tags.length >= maxTags) return false;
        if (tags.indexOf(name) !== -1) return false;
        tags.push(name);
        renderChips();
        return true;
    }

    function removeTag(index) {
        tags.splice(index, 1);
        renderChips();
        inputEl.focus();
    }

    function hideDropdown() {
        dropdownEl.classList.add("hidden");
        dropdownVisible = false;
        activeIndex = -1;
    }

    function updateActiveItem() {
        var items = dropdownEl.querySelectorAll("[role='option']");
        items.forEach(function (el, i) {
            if (i === activeIndex) {
                el.classList.add("bg-background");
            } else {
                el.classList.remove("bg-background");
            }
        });
    }

    function showDropdown(items) {
        dropdownEl.innerHTML = "";
        var shown = 0;
        (items || []).forEach(function (item) {
            var name = typeof item === "string" ? item : (item && item.name ? item.name : "");
            if (!name || tags.indexOf(name.toLowerCase()) !== -1) return;

            var opt = document.createElement("div");
            opt.className = "px-4 py-2 text-sm cursor-pointer hover:bg-background";
            opt.setAttribute("role", "option");
            opt.textContent = name;

            if (item && typeof item.story_count === "number") {
                var cnt = document.createElement("span");
                cnt.className = "ml-1 text-xs text-textmuted";
                cnt.textContent = "(" + item.story_count + ")";
                opt.appendChild(cnt);
            }

            opt.addEventListener("mousedown", function (e) {
                e.preventDefault();
                addTag(name);
                inputEl.value = "";
                hideDropdown();
                inputEl.focus();
            });
            dropdownEl.appendChild(opt);
            shown++;
        });

        if (shown === 0) { hideDropdown(); return; }
        dropdownEl.classList.remove("hidden");
        dropdownVisible = true;
        activeIndex = -1;
    }

    function triggerSuggestions(query) {
        clearTimeout(suggestTimer);
        if (!apiBase || query.length < TAGS_SUGGEST_MIN_CHARS) {
            hideDropdown();
            return;
        }
        suggestTimer = setTimeout(function () {
            fetchTagSuggestions(apiBase, query).then(function (items) {
                if (inputEl.value.trim() === query) {
                    showDropdown(items);
                }
            });
        }, TAGS_DEBOUNCE_MS);
    }

    inputEl.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            if (dropdownVisible && activeIndex >= 0) {
                var opts = dropdownEl.querySelectorAll("[role='option']");
                if (opts[activeIndex]) {
                    opts[activeIndex].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
                }
            } else {
                var val = inputEl.value.trim();
                if (val) { addTag(val); inputEl.value = ""; hideDropdown(); }
            }
        } else if (e.key === ",") {
            e.preventDefault();
            var val2 = inputEl.value.replace(/,/g, "").trim();
            if (val2) { addTag(val2); inputEl.value = ""; hideDropdown(); }
        } else if (e.key === "Backspace" && inputEl.value === "" && tags.length > 0) {
            removeTag(tags.length - 1);
        } else if (e.key === "ArrowDown" && dropdownVisible) {
            e.preventDefault();
            var downOpts = dropdownEl.querySelectorAll("[role='option']");
            activeIndex = Math.min(activeIndex + 1, downOpts.length - 1);
            updateActiveItem();
        } else if (e.key === "ArrowUp" && dropdownVisible) {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, -1);
            updateActiveItem();
        } else if (e.key === "Escape") {
            hideDropdown();
        }
    });

    inputEl.addEventListener("input", function () {
        triggerSuggestions(inputEl.value.trim());
    });

    inputEl.addEventListener("blur", function () {
        setTimeout(hideDropdown, 150);
    });

    document.addEventListener("click", function (e) {
        if (!containerEl.contains(e.target)) {
            hideDropdown();
        }
    });

    function getTags() { return tags.slice(); }

    function setTags(newTags) {
        tags = [];
        (newTags || []).forEach(function (t) {
            var name = typeof t === "string" ? t : (t && t.name ? t.name : "");
            if (name) tags.push(name.trim().toLowerCase());
        });
        renderChips();
    }

    function destroy() {
        clearTimeout(suggestTimer);
        containerEl.innerHTML = "";
    }

    if (options.initialTags && options.initialTags.length > 0) {
        setTags(options.initialTags);
    }

    return { getTags: getTags, setTags: setTags, destroy: destroy };
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        fetchTagSuggestions: fetchTagSuggestions,
        renderTagChips: renderTagChips,
        createTagInput: createTagInput
    };
}
