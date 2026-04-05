var AUTH_TOKEN_KEY = "auth_token";

function getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

function isLoggedIn() {
    return !!getToken();
}

function saveToken(token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
}

function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    window.location.assign("index.html");
}

function authFetch(url, options) {
    options = options || {};
    var token = getToken();
    if (token) {
        options.headers = options.headers || {};
        options.headers["Authorization"] = "Bearer " + token;
    }
    return fetch(url, options);
}

function requireAuth() {
    if (!isLoggedIn()) {
        window.location.assign("index.html");
        return false;
    }
    return true;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        getToken: getToken,
        isLoggedIn: isLoggedIn,
        saveToken: saveToken,
        logout: logout,
        authFetch: authFetch,
        requireAuth: requireAuth,
        AUTH_TOKEN_KEY: AUTH_TOKEN_KEY
    };
}
