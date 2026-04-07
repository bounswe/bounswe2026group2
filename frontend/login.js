function redirectToMap() {
    window.location.assign("map.html");
}

function redirectToRegister() {
    window.location.assign("register.html");
}

function showLoginError(msg) {
    var el = document.getElementById("login-error");
    if (el) {
        el.textContent = msg;
        el.classList.remove("hidden");
    }
}

function hideLoginError() {
    var el = document.getElementById("login-error");
    if (el) {
        el.classList.add("hidden");
    }
}

async function handleLogin(event) {
    event.preventDefault();
    hideLoginError();

    var email = document.getElementById("email").value.trim();
    var password = document.getElementById("password").value;

    if (!email || !password) {
        showLoginError("Please enter your email and password.");
        return;
    }

    var submitBtn = event.target.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Signing in...";
    }

    try {
        var res = await fetch(API_BASE + "/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: password })
        });

        if (!res.ok) {
            var data = await res.json().catch(function () { return {}; });
            throw new Error(data.detail || "Invalid email or password.");
        }

        var result = await res.json();
        localStorage.setItem("auth_token", result.access_token);
        redirectToMap();
    } catch (err) {
        showLoginError(err.message);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Sign In";
        }
    }
}

function setupLoginForm() {
    var form = document.getElementById("login-form");
    var registerButton = document.getElementById("register-button");

    if (form) {
        form.addEventListener("submit", handleLogin);
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
        redirectToMap: redirectToMap,
        redirectToRegister: redirectToRegister,
        handleLogin: handleLogin,
        setupLoginForm: setupLoginForm
    };
}
