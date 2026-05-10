const {
    isAnonymousStory,
    getAuthorLabel,
    getAuthorByLine
} = require("./anonymous");

describe("anonymous story display helpers", () => {
    test("isAnonymousStory is true only when is_anonymous === true", () => {
        expect(isAnonymousStory({ is_anonymous: true })).toBe(true);
        expect(isAnonymousStory({ is_anonymous: false })).toBe(false);
        expect(isAnonymousStory({})).toBe(false);
        expect(isAnonymousStory(null)).toBe(false);
        expect(isAnonymousStory(undefined)).toBe(false);
    });

    test("getAuthorLabel returns 'Anonymous' for anonymous stories even if author is somehow set", () => {
        // Defense in depth: if the backend ever leaks an author for an
        // anonymous story, the UI must still hide it.
        expect(getAuthorLabel({ is_anonymous: true, author: "alice" })).toBe("Anonymous");
        expect(getAuthorLabel({ is_anonymous: true, author: null })).toBe("Anonymous");
    });

    test("getAuthorLabel returns the username for non-anonymous stories", () => {
        expect(getAuthorLabel({ is_anonymous: false, author: "alice" })).toBe("alice");
    });

    test("getAuthorLabel falls back to 'Unknown' when author is missing", () => {
        expect(getAuthorLabel({ is_anonymous: false, author: null })).toBe("Unknown");
        expect(getAuthorLabel({ is_anonymous: false, author: "" })).toBe("Unknown");
        expect(getAuthorLabel({})).toBe("Unknown");
    });

    test("getAuthorByLine prefixes the label with 'by '", () => {
        expect(getAuthorByLine({ is_anonymous: true, author: "alice" })).toBe("by Anonymous");
        expect(getAuthorByLine({ is_anonymous: false, author: "alice" })).toBe("by alice");
        expect(getAuthorByLine({})).toBe("by Unknown");
    });
});
