function googleAuthLoginUrl(apiBase) {
    return String(apiBase || "").replace(/\/$/, "") + "/auth/google/login";
}

function configureGoogleAuthButton(doc, apiBase) {
    var googleAuthButton = doc.getElementById("google-auth-button");
    if (!googleAuthButton || typeof apiBase === "undefined") {
        return false;
    }

    googleAuthButton.href = googleAuthLoginUrl(apiBase);
    return true;
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
        configureGoogleAuthButton(document, typeof API_BASE === "undefined" ? undefined : API_BASE);
    });
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        configureGoogleAuthButton: configureGoogleAuthButton,
        googleAuthLoginUrl: googleAuthLoginUrl,
    };
}
