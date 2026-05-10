const {
    configureGoogleAuthButton,
    googleAuthLoginUrl,
} = require("./oauth-button");

describe("Google OAuth button wiring", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
    });

    test("builds backend Google login URL from API base", () => {
        expect(googleAuthLoginUrl("http://localhost:8000")).toBe("http://localhost:8000/auth/google/login");
        expect(googleAuthLoginUrl("http://localhost:8000/")).toBe("http://localhost:8000/auth/google/login");
    });

    test("sets login page Google button href to backend endpoint", () => {
        document.body.innerHTML = '<a id="google-auth-button" data-testid="login-google" href="/auth/google/login"></a>';

        const configured = configureGoogleAuthButton(document, "http://api.test");

        expect(configured).toBe(true);
        expect(document.getElementById("google-auth-button").href).toBe("http://api.test/auth/google/login");
    });

    test("sets register page Google button href to backend endpoint", () => {
        document.body.innerHTML = '<a id="google-auth-button" data-testid="register-google" href="/auth/google/login"></a>';

        const configured = configureGoogleAuthButton(document, "http://api.test");

        expect(configured).toBe(true);
        expect(document.querySelector('[data-testid="register-google"]').href).toBe("http://api.test/auth/google/login");
    });

    test("does nothing when Google button is absent", () => {
        expect(configureGoogleAuthButton(document, "http://api.test")).toBe(false);
    });
});
