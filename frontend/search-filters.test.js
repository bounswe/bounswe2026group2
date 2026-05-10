const { parseTagsFromUrl, serializeTagsToUrl, parseSortFromUrl, filterStoriesByTags, sortStories } = require("./search-filters");

// ─── parseTagsFromUrl ─────────────────────────────────────────────────────────

describe("parseTagsFromUrl", () => {
    test("returns empty array when no tags param", () => {
        expect(parseTagsFromUrl("?q=istanbul")).toEqual([]);
    });

    test("returns empty array for empty search string", () => {
        expect(parseTagsFromUrl("")).toEqual([]);
    });

    test("parses a single tag", () => {
        expect(parseTagsFromUrl("?tags=history")).toEqual(["history"]);
    });

    test("parses multiple comma-separated tags", () => {
        expect(parseTagsFromUrl("?tags=history,art,culture")).toEqual(["history", "art", "culture"]);
    });

    test("lowercases all tags", () => {
        expect(parseTagsFromUrl("?tags=History,ART")).toEqual(["history", "art"]);
    });

    test("trims whitespace around tags", () => {
        expect(parseTagsFromUrl("?tags=history, art")).toEqual(["history", "art"]);
    });

    test("filters out empty segments from double commas", () => {
        expect(parseTagsFromUrl("?tags=history,,art")).toEqual(["history", "art"]);
    });

    test("returns empty array when tags param value is empty", () => {
        expect(parseTagsFromUrl("?tags=")).toEqual([]);
    });

    test("ignores other params and only reads tags", () => {
        expect(parseTagsFromUrl("?q=istanbul&tags=history&sort=newest")).toEqual(["history"]);
    });
});

// ─── serializeTagsToUrl ───────────────────────────────────────────────────────

describe("serializeTagsToUrl", () => {
    test("returns empty string for empty array", () => {
        expect(serializeTagsToUrl([])).toBe("");
    });

    test("returns empty string for null", () => {
        expect(serializeTagsToUrl(null)).toBe("");
    });

    test("serializes a single tag", () => {
        expect(serializeTagsToUrl(["culture"])).toBe("culture");
    });

    test("joins multiple tags with comma", () => {
        expect(serializeTagsToUrl(["history", "art"])).toBe("history,art");
    });

    test("round-trips with parseTagsFromUrl", () => {
        var tags = ["history", "art", "culture"];
        var serialized = serializeTagsToUrl(tags);
        expect(parseTagsFromUrl("?tags=" + serialized)).toEqual(tags);
    });
});

// ─── parseSortFromUrl ─────────────────────────────────────────────────────────

describe("parseSortFromUrl", () => {
    test("returns relevance when no sort param", () => {
        expect(parseSortFromUrl("?q=istanbul")).toBe("relevance");
    });

    test("returns relevance for empty search string", () => {
        expect(parseSortFromUrl("")).toBe("relevance");
    });

    test("parses newest", () => {
        expect(parseSortFromUrl("?sort=newest")).toBe("newest");
    });

    test("parses oldest", () => {
        expect(parseSortFromUrl("?sort=oldest")).toBe("oldest");
    });

    test("parses relevance explicitly", () => {
        expect(parseSortFromUrl("?sort=relevance")).toBe("relevance");
    });

    test("returns relevance for an invalid sort value", () => {
        expect(parseSortFromUrl("?sort=random")).toBe("relevance");
    });

    test("returns relevance for an empty sort value", () => {
        expect(parseSortFromUrl("?sort=")).toBe("relevance");
    });
});

// ─── filterStoriesByTags ──────────────────────────────────────────────────────

describe("filterStoriesByTags", () => {
    var stories = [
        { id: "1", tags: [{ name: "history" }, { name: "art" }] },
        { id: "2", tags: [{ name: "history" }] },
        { id: "3", tags: [] },
        { id: "4", tags: [{ name: "culture" }] },
    ];

    test("returns all stories when selectedTags is empty", () => {
        expect(filterStoriesByTags(stories, [])).toHaveLength(4);
    });

    test("returns all stories when selectedTags is null", () => {
        expect(filterStoriesByTags(stories, null)).toHaveLength(4);
    });

    test("returns empty array when stories is null", () => {
        expect(filterStoriesByTags(null, ["history"])).toEqual([]);
    });

    test("filters by a single tag", () => {
        var result = filterStoriesByTags(stories, ["history"]);
        expect(result.map(function (s) { return s.id; })).toEqual(["1", "2"]);
    });

    test("applies AND logic for multiple tags", () => {
        var result = filterStoriesByTags(stories, ["history", "art"]);
        expect(result.map(function (s) { return s.id; })).toEqual(["1"]);
    });

    test("returns empty array when no stories match", () => {
        expect(filterStoriesByTags(stories, ["nonexistent"])).toHaveLength(0);
    });

    test("excludes stories with no tags when a filter is active", () => {
        var result = filterStoriesByTags(stories, ["history"]);
        var ids = result.map(function (s) { return s.id; });
        expect(ids).not.toContain("3");
    });

    test("handles stories with string tags", () => {
        var strStories = [
            { id: "1", tags: ["history", "art"] },
            { id: "2", tags: ["culture"] },
        ];
        var result = filterStoriesByTags(strStories, ["history"]);
        expect(result.map(function (s) { return s.id; })).toEqual(["1"]);
    });

    test("is case-insensitive (object tags with uppercase)", () => {
        var mixedCase = [{ id: "1", tags: [{ name: "History" }] }];
        expect(filterStoriesByTags(mixedCase, ["history"])).toHaveLength(1);
    });

    test("is case-insensitive (string tags with uppercase)", () => {
        var mixedCase = [{ id: "1", tags: ["HISTORY"] }];
        expect(filterStoriesByTags(mixedCase, ["history"])).toHaveLength(1);
    });

    test("handles stories without a tags field", () => {
        var noTagStories = [{ id: "1", title: "No tags" }];
        expect(filterStoriesByTags(noTagStories, ["history"])).toHaveLength(0);
    });

    test("does not mutate the original stories array", () => {
        var original = stories.slice();
        filterStoriesByTags(stories, ["history"]);
        expect(stories).toEqual(original);
    });
});

// ─── sortStories ──────────────────────────────────────────────────────────────

describe("sortStories", () => {
    var stories = [
        { id: "1", date_start: "1900-01-01" },
        { id: "2", date_start: "1800-06-15" },
        { id: "3", date_start: "2000-12-31" },
    ];

    test("relevance returns stories in original order", () => {
        var sorted = sortStories(stories, "relevance");
        expect(sorted.map(function (s) { return s.id; })).toEqual(["1", "2", "3"]);
    });

    test("relevance with null order returns stories in original order", () => {
        var sorted = sortStories(stories, null);
        expect(sorted.map(function (s) { return s.id; })).toEqual(["1", "2", "3"]);
    });

    test("newest sorts by date_start descending", () => {
        var sorted = sortStories(stories, "newest");
        expect(sorted.map(function (s) { return s.id; })).toEqual(["3", "1", "2"]);
    });

    test("oldest sorts by date_start ascending", () => {
        var sorted = sortStories(stories, "oldest");
        expect(sorted.map(function (s) { return s.id; })).toEqual(["2", "1", "3"]);
    });

    test("stories without date_start are pushed to end (newest)", () => {
        var withNoDates = [
            { id: "a", date_start: "1900-01-01" },
            { id: "b" },
            { id: "c", date_start: "2000-01-01" },
        ];
        var sorted = sortStories(withNoDates, "newest");
        expect(sorted[sorted.length - 1].id).toBe("b");
    });

    test("stories without date_start are pushed to end (oldest)", () => {
        var withNoDates = [
            { id: "a", date_start: "1900-01-01" },
            { id: "b" },
        ];
        var sorted = sortStories(withNoDates, "oldest");
        expect(sorted[sorted.length - 1].id).toBe("b");
    });

    test("does not mutate the original array", () => {
        var original = stories.map(function (s) { return s.id; });
        sortStories(stories, "newest");
        expect(stories.map(function (s) { return s.id; })).toEqual(original);
    });

    test("handles empty array", () => {
        expect(sortStories([], "newest")).toEqual([]);
    });

    test("handles null array", () => {
        expect(sortStories(null, "newest")).toEqual([]);
    });

    test("handles single story", () => {
        var single = [{ id: "1", date_start: "1900-01-01" }];
        expect(sortStories(single, "newest")).toEqual(single);
    });
});
