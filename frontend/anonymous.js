// Display helpers for anonymous story sharing.
// Backend masks `author` to null when `is_anonymous` is true, so we never
// have access to the real username here


function isAnonymousStory(story) {
    if (!story) return false;
    return story.is_anonymous === true;
}

function getAuthorLabel(story) {
    if (isAnonymousStory(story)) return "Anonymous";
    if (story && typeof story.author === "string" && story.author.length > 0) {
        return story.author;
    }
    return "Unknown";
}

function getAuthorByLine(story) {
    return "by " + getAuthorLabel(story);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        isAnonymousStory: isAnonymousStory,
        getAuthorLabel: getAuthorLabel,
        getAuthorByLine: getAuthorByLine
    };
}
