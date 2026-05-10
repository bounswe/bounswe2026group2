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

if (typeof module !== "undefined" && module.exports) {
    module.exports = { renderTagChips: renderTagChips };
}
