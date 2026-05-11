function parseTagsFromUrl(searchString) {
    var params = new URLSearchParams(searchString);
    var tagsParam = params.get("tags") || "";
    if (!tagsParam) return [];
    return tagsParam.split(",")
        .map(function (t) { return t.trim().toLowerCase(); })
        .filter(Boolean);
}

function serializeTagsToUrl(tags) {
    return (tags || []).join(",");
}

function parseSortFromUrl(searchString) {
    var params = new URLSearchParams(searchString);
    var sort = params.get("sort") || "relevance";
    return ["relevance", "newest", "oldest"].indexOf(sort) !== -1 ? sort : "relevance";
}

function filterStoriesByTags(stories, selectedTags) {
    if (!selectedTags || selectedTags.length === 0) return stories || [];
    return (stories || []).filter(function (story) {
        var storyTags = (story.tags || []).map(function (t) {
            return typeof t === "string" ? t.toLowerCase() : ((t && t.name) || "").toLowerCase();
        });
        return selectedTags.every(function (tag) {
            return storyTags.some(function (storyTag) {
                return storyTag.indexOf(tag) !== -1;
            });
        });
    });
}

function sortStories(stories, order) {
    if (!order || order === "relevance") return stories || [];
    var sorted = (stories || []).slice();
    sorted.sort(function (a, b) {
        var aDate = a.date_start || "";
        var bDate = b.date_start || "";
        if (order === "newest") {
            if (!aDate) return 1;
            if (!bDate) return -1;
            return bDate < aDate ? -1 : aDate < bDate ? 1 : 0;
        }
        if (order === "oldest") {
            if (!aDate) return 1;
            if (!bDate) return -1;
            return aDate < bDate ? -1 : bDate < aDate ? 1 : 0;
        }
        return 0;
    });
    return sorted;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { parseTagsFromUrl, serializeTagsToUrl, parseSortFromUrl, filterStoriesByTags, sortStories };
}
