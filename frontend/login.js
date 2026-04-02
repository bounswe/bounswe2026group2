function redirectToMap() {
    window.location.assign("map.html");
}

function redirectToRegister() {
    window.location.assign("register.html");
}

function handleLogin(event) {
    event.preventDefault();
    redirectToMap();
}

function handleDemoClick() {
    redirectToMap();
}

function setupLoginForm() {
    const form = document.getElementById("login-form");
    const demoButton = document.getElementById("demo-button");
    const registerButton = document.getElementById("register-button");

    if (form) {
        form.addEventListener("submit", handleLogin);
    }

    if (demoButton) {
        demoButton.addEventListener("click", handleDemoClick);
    }

    if (registerButton) {
        registerButton.addEventListener("click", redirectToRegister);
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", setupLoginForm);
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        redirectToMap,
        redirectToRegister,
        handleLogin,
        handleDemoClick,
        setupLoginForm
    };
}