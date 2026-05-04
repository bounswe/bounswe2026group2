var RECORDING_MIME_TYPES = {
    audio: [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4"
    ],
    video: [
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8,opus",
        "video/webm",
        "video/mp4"
    ]
};

function isMediaRecorderAvailable(scope) {
    scope = scope || window;
    return !!(
        scope.MediaRecorder &&
        scope.navigator &&
        scope.navigator.mediaDevices &&
        scope.navigator.mediaDevices.getUserMedia
    );
}

function getSupportedRecordingMimeType(kind, mediaRecorderClass) {
    var candidates = RECORDING_MIME_TYPES[kind] || [];
    if (!mediaRecorderClass || typeof mediaRecorderClass.isTypeSupported !== "function") {
        return "";
    }

    for (var i = 0; i < candidates.length; i++) {
        if (mediaRecorderClass.isTypeSupported(candidates[i])) {
            return candidates[i];
        }
    }

    return "";
}

function getRecordingExtension(mimeType, kind) {
    if (mimeType && mimeType.indexOf("mp4") !== -1) return "mp4";
    if (mimeType && mimeType.indexOf("webm") !== -1) return "webm";
    return kind === "video" ? "webm" : "webm";
}

function formatRecordingTimestamp(date) {
    return date.toISOString().replace(/[:.]/g, "-");
}

function buildRecordedFile(chunks, kind, mimeType, date) {
    var blob = new Blob(chunks, { type: mimeType || (kind === "video" ? "video/webm" : "audio/webm") });
    var extension = getRecordingExtension(blob.type, kind);
    var timestamp = formatRecordingTimestamp(date || new Date());
    return new File([blob], "recorded-" + kind + "-" + timestamp + "." + extension, { type: blob.type });
}

var RecordingUtils = {
    RECORDING_MIME_TYPES: RECORDING_MIME_TYPES,
    isMediaRecorderAvailable: isMediaRecorderAvailable,
    getSupportedRecordingMimeType: getSupportedRecordingMimeType,
    getRecordingExtension: getRecordingExtension,
    formatRecordingTimestamp: formatRecordingTimestamp,
    buildRecordedFile: buildRecordedFile
};

if (typeof window !== "undefined") {
    window.RecordingUtils = RecordingUtils;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = RecordingUtils;
}
