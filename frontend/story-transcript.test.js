/**
 * @jest-environment jsdom
 */

const {
    needsAudioTranscriptPoll,
    transcriptDisplayState,
    mediaTypeKey,
    applyTranscriptBody
} = require("./story-transcript");

describe("story transcript helpers", () => {
    test("mediaTypeKey normalizes to lowercase", () => {
        expect(mediaTypeKey({ media_type: "AUDIO" })).toBe("audio");
        expect(mediaTypeKey({ media_type: "audio" })).toBe("audio");
        expect(mediaTypeKey(null)).toBe("");
    });

    test("needsAudioTranscriptPoll returns false for empty or missing lists", () => {
        expect(needsAudioTranscriptPoll(null)).toBe(false);
        expect(needsAudioTranscriptPoll(undefined)).toBe(false);
        expect(needsAudioTranscriptPoll([])).toBe(false);
    });

    test("needsAudioTranscriptPoll returns true when any audio item has null transcript", () => {
        expect(
            needsAudioTranscriptPoll([
                { media_type: "audio", transcript: null },
                { media_type: "image", transcript: null }
            ])
        ).toBe(true);
    });

    test("needsAudioTranscriptPoll treats media_type case-insensitively", () => {
        expect(
            needsAudioTranscriptPoll([{ media_type: "AUDIO", transcript: null }])
        ).toBe(true);
    });

    test("needsAudioTranscriptPoll returns true when transcript is undefined", () => {
        expect(needsAudioTranscriptPoll([{ media_type: "audio" }])).toBe(true);
    });

    test("needsAudioTranscriptPoll returns false when all audio items have a transcript string", () => {
        expect(
            needsAudioTranscriptPoll([
                { media_type: "audio", transcript: "Hello" },
                { media_type: "audio", transcript: "World" }
            ])
        ).toBe(false);
    });

    test("transcriptDisplayState shows transcript text when non-empty", () => {
        expect(
            transcriptDisplayState({ transcript: "  hi  " }, false)
        ).toEqual({ kind: "text", text: "  hi  " });
    });

    test("transcriptDisplayState shows unavailable for empty string", () => {
        expect(transcriptDisplayState({ transcript: "" }, false)).toEqual({
            kind: "unavailable"
        });
        expect(transcriptDisplayState({ transcript: "   " }, false)).toEqual({
            kind: "unavailable"
        });
    });

    test("transcriptDisplayState shows Processing when null and poll not exhausted", () => {
        expect(transcriptDisplayState({ transcript: null }, false)).toEqual({
            kind: "processing"
        });
    });

    test("transcriptDisplayState shows unavailable when null but poll exhausted", () => {
        expect(transcriptDisplayState({ transcript: null }, true)).toEqual({
            kind: "unavailable"
        });
    });

    test("applyTranscriptBody sets text for processing state", () => {
        const el = document.createElement("div");
        applyTranscriptBody(el, { kind: "processing" });
        expect(el.textContent).toBe("Processing…");
    });
});
