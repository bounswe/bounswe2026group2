const {
    buildRecordedFile,
    formatRecordingTimestamp,
    getRecordingExtension,
    getSupportedRecordingMimeType,
    isMediaRecorderAvailable
} = require("./recording");

describe("recording helpers", () => {
    test("detects MediaRecorder support only when recorder and getUserMedia exist", () => {
        expect(isMediaRecorderAvailable({
            MediaRecorder: function MediaRecorder() {},
            navigator: {
                mediaDevices: {
                    getUserMedia: jest.fn()
                }
            }
        })).toBe(true);

        expect(isMediaRecorderAvailable({
            MediaRecorder: function MediaRecorder() {},
            navigator: {}
        })).toBe(false);
    });

    test("chooses the first supported mime type for audio", () => {
        const recorderClass = {
            isTypeSupported: jest.fn(type => type === "audio/webm")
        };

        expect(getSupportedRecordingMimeType("audio", recorderClass)).toBe("audio/webm");
        expect(recorderClass.isTypeSupported).toHaveBeenCalledWith("audio/webm;codecs=opus");
    });

    test("returns an empty mime type when no candidate is supported", () => {
        const recorderClass = {
            isTypeSupported: jest.fn(() => false)
        };

        expect(getSupportedRecordingMimeType("video", recorderClass)).toBe("");
    });

    test("builds a named audio File from captured chunks", () => {
        const file = buildRecordedFile(
            [new Blob(["sample audio"], { type: "audio/webm" })],
            "audio",
            "audio/webm",
            new Date("2026-04-28T10:20:30.000Z")
        );

        expect(file).toBeInstanceOf(File);
        expect(file.name).toBe("recorded-audio-2026-04-28T10-20-30-000Z.webm");
        expect(file.type).toBe("audio/webm");
        expect(file.size).toBeGreaterThan(0);
    });

    test("formats timestamps and extensions safely for filenames", () => {
        expect(formatRecordingTimestamp(new Date("2026-04-28T10:20:30.123Z"))).toBe("2026-04-28T10-20-30-123Z");
        expect(getRecordingExtension("video/mp4", "video")).toBe("mp4");
        expect(getRecordingExtension("audio/webm;codecs=opus", "audio")).toBe("webm");
    });
});
