/**
 * Helpers for story audio transcript display and polling (frontend-only).
 */

function mediaTypeKey(media) {
    if (!media || media.media_type == null) {
        return "";
    }
    return String(media.media_type).toLowerCase();
}

function isAudioMedia(media) {
    return mediaTypeKey(media) === "audio";
}

/**
 * @param {Array<{ media_type?: string, transcript?: string | null }>|null|undefined} mediaFiles
 * @returns {boolean}
 */
function needsAudioTranscriptPoll(mediaFiles) {
    if (!mediaFiles || !mediaFiles.length) {
        return false;
    }
    for (var i = 0; i < mediaFiles.length; i++) {
        var m = mediaFiles[i];
        if (!isAudioMedia(m)) {
            continue;
        }
        var t = m.transcript;
        if (t === null || t === undefined) {
            return true;
        }
    }
    return false;
}

/**
 * @param {{ transcript?: string | null }} media - audio item
 * @param {boolean} pollExhausted
 * @returns {{ kind: 'text', text: string } | { kind: 'processing' } | { kind: 'unavailable' }}
 */
function transcriptDisplayState(media, pollExhausted) {
    var t = media && media.transcript;
    if (typeof t === "string" && t.trim().length > 0) {
        return { kind: "text", text: t };
    }
    if (t === null || t === undefined) {
        if (!pollExhausted) {
            return { kind: "processing" };
        }
        return { kind: "unavailable" };
    }
    return { kind: "unavailable" };
}

/**
 * @param {HTMLElement} el
 * @param {{ kind: 'text', text: string } | { kind: 'processing' } | { kind: 'unavailable' }} state
 */
function applyTranscriptBody(el, state) {
    el.textContent = "";
    el.className =
        "mt-2 text-sm leading-6 border-t border-border/60 pt-2 " +
        "whitespace-pre-wrap break-words";
    if (state.kind === "text") {
        el.textContent = state.text;
        el.classList.add("text-textmain");
    } else if (state.kind === "processing") {
        el.textContent = "Processing…";
        el.classList.add("text-textmuted", "italic");
    } else {
        el.textContent = "Transcript unavailable";
        el.classList.add("text-textmuted");
    }
}

var StoryTranscript = {
    mediaTypeKey: mediaTypeKey,
    isAudioMedia: isAudioMedia,
    needsAudioTranscriptPoll: needsAudioTranscriptPoll,
    transcriptDisplayState: transcriptDisplayState,
    applyTranscriptBody: applyTranscriptBody
};

if (typeof window !== "undefined") {
    window.StoryTranscript = StoryTranscript;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = StoryTranscript;
}
