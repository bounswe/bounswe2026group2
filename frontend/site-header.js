/* global AUTH_TOKEN_KEY, API_BASE, isLoggedIn, authFetch, logout */

// Shared top navigation header.
// Include after auth.js + config.js, then put <div id="site-header"></div>
// where the header should appear and call mountSiteHeader().
//
//   <script src="auth.js"></script>
//   <script src="config.js"></script>
//   <script src="site-header.js"></script>
//   <div id="site-header"></div>
//   <script>mountSiteHeader();</script>
//
// Options:
//   extraCenter — raw HTML to drop between the title and the profile button
//                 (used by map.html for the inline search form)

(function () {
    function buildHeaderHtml(options) {
        var extra = (options && options.extraCenter) || "";

        return (
            '<header class="fixed top-0 left-0 right-0 z-[1100] bg-[#f8f3ea]/95 backdrop-blur-sm border-b border-border/30">' +
            '<div class="flex justify-between items-center w-full px-6 sm:px-8 py-4 max-w-screen-2xl mx-auto gap-4">' +
            '<div class="flex items-center gap-8 shrink-0">' +
            '<a href="map.html" class="text-xl sm:text-2xl font-bold font-headline text-textmain tracking-tight hover:text-tertiary transition-colors">Local History Map</a>' +
            '</div>' +
            (extra ? '<div class="hidden md:flex flex-1 items-center justify-center min-w-0">' + extra + '</div>' : '') +
            '<div class="flex items-center gap-3 sm:gap-4 shrink-0">' +
            (options && options.extraRight ? options.extraRight : '') +
            '<div class="relative">' +
            '<button id="site-header-profile-btn" type="button"' +
            ' class="inline-flex h-11 min-w-11 items-center justify-center rounded-full border border-border bg-white px-2 text-textmain shadow-sm transition hover:bg-stone-50"' +
            ' aria-label="Open account menu" aria-haspopup="menu" aria-expanded="false">' +
            '<img id="site-header-profile-avatar" alt="" class="hidden h-9 w-9 rounded-full object-cover" />' +
            '<span id="site-header-profile-icon" class="material-symbols-outlined text-[20px] leading-none">account_circle</span>' +
            '<span id="site-header-profile-initials" class="hidden h-7 min-w-7 items-center justify-center rounded-full bg-primary text-xs font-bold uppercase text-white"></span>' +
            '</button>' +
            '<div id="site-header-profile-menu" hidden' +
            ' class="absolute right-0 top-[calc(100%+0.75rem)] z-[1100] w-72 rounded-2xl border border-border bg-white p-2 shadow-soft"' +
            ' role="menu" aria-labelledby="site-header-profile-btn">' +
            '<div id="site-header-menu-state" class="px-4 py-3 text-sm text-textmuted">Checking account status...</div>' +
            '<div id="site-header-menu-actions" class="space-y-1"></div>' +
            '<div id="site-header-menu-user" class="hidden border-t border-border/70 px-4 py-3">' +
            '<p id="site-header-menu-name" class="text-sm font-semibold text-textmain"></p>' +
            '<p id="site-header-menu-email" class="mt-1 text-xs text-textmuted break-all"></p>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</header>'
        );
    }

    var els = {};
    var currentUser = null;

    function profileLabel(user) {
        if (!user) return "";
        return (user.display_name || user.username || user.email || "").trim();
    }

    function profileInitials(user) {
        var label = profileLabel(user);
        if (!label) return "";
        return label
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map(function (p) { return p.charAt(0).toUpperCase(); })
            .join("");
    }

    function setButtonFace(user) {
        var avatarUrl = user && user.avatar_url;
        if (avatarUrl) {
            els.avatar.src = avatarUrl;
            els.avatar.classList.remove("hidden");
            els.icon.classList.add("hidden");
            els.initials.textContent = "";
            els.initials.classList.add("hidden");
            els.initials.classList.remove("inline-flex");
            els.btn.setAttribute("aria-label", "Open account menu for " + profileLabel(user));
            return;
        }

        els.avatar.removeAttribute("src");
        els.avatar.classList.add("hidden");

        var initials = profileInitials(user);
        if (initials) {
            els.icon.classList.add("hidden");
            els.initials.textContent = initials;
            els.initials.classList.remove("hidden");
            els.initials.classList.add("inline-flex");
            els.btn.setAttribute("aria-label", "Open account menu for " + profileLabel(user));
            return;
        }

        els.icon.classList.remove("hidden");
        els.initials.textContent = "";
        els.initials.classList.add("hidden");
        els.initials.classList.remove("inline-flex");
        els.btn.setAttribute("aria-label", "Open account menu");
    }

    function closeMenu() {
        els.menu.hidden = true;
        els.btn.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
        els.menu.hidden = false;
        els.btn.setAttribute("aria-expanded", "true");
    }

    function renderMenu() {
        els.actions.innerHTML = "";

        if (!currentUser) {
            els.state.textContent = "Sign in to create stories and manage your account.";
            els.user.classList.add("hidden");

            var signIn = document.createElement("a");
            signIn.href = "index.html";
            signIn.className = "flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:opacity-95";
            signIn.textContent = "Sign In";
            signIn.setAttribute("role", "menuitem");
            els.actions.appendChild(signIn);

            setButtonFace(null);
            return;
        }

        els.state.textContent = "Signed in";
        els.user.classList.remove("hidden");
        els.name.textContent = profileLabel(currentUser);
        els.email.textContent = currentUser.email || "";

        appendMenuLink("View Profile", "profile.html", "person");
        appendMenuLink("Saved Stories", "saved.html", "bookmark");

        if (currentUser.role === "admin") {
            appendMenuLink("Reports", "admin-panel.html", "flag");
        }

        var signOut = document.createElement("button");
        signOut.type = "button";
        signOut.className = "flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-red-600 transition hover:bg-red-50";
        signOut.setAttribute("role", "menuitem");
        signOut.innerHTML = '<span>Sign Out</span><span class="material-symbols-outlined text-[18px]">logout</span>';
        signOut.addEventListener("click", function () { logout(); });
        els.actions.appendChild(signOut);

        setButtonFace(currentUser);
    }

    function appendMenuLink(label, href, icon) {
        var a = document.createElement("a");
        a.href = href;
        a.className = "flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-textmain transition hover:bg-stone-50";
        a.setAttribute("role", "menuitem");
        a.innerHTML = '<span>' + label + '</span><span class="material-symbols-outlined text-[18px] text-textmuted">' + icon + '</span>';
        els.actions.appendChild(a);
    }

    async function loadCurrentUser() {
        currentUser = null;
        renderMenu();

        if (typeof isLoggedIn !== "function" || !isLoggedIn()) return;

        try {
            var resp = await authFetch(API_BASE + "/auth/me");
            if (!resp.ok) {
                localStorage.removeItem(AUTH_TOKEN_KEY);
                renderMenu();
                return;
            }
            currentUser = await resp.json();
            renderMenu();
        } catch (_err) {
            els.state.textContent = "Unable to load account details right now.";
            setButtonFace(null);
        }
    }

    function wire() {
        els.btn = document.getElementById("site-header-profile-btn");
        els.avatar = document.getElementById("site-header-profile-avatar");
        els.icon = document.getElementById("site-header-profile-icon");
        els.initials = document.getElementById("site-header-profile-initials");
        els.menu = document.getElementById("site-header-profile-menu");
        els.state = document.getElementById("site-header-menu-state");
        els.actions = document.getElementById("site-header-menu-actions");
        els.user = document.getElementById("site-header-menu-user");
        els.name = document.getElementById("site-header-menu-name");
        els.email = document.getElementById("site-header-menu-email");

        els.btn.addEventListener("click", function () {
            if (els.menu.hidden) openMenu(); else closeMenu();
        });

        document.addEventListener("click", function (e) {
            if (!els.menu.hidden && !els.menu.contains(e.target) && !els.btn.contains(e.target)) {
                closeMenu();
            }
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") closeMenu();
        });
    }

    function mount(options) {
        var slot = document.getElementById("site-header");
        if (!slot) {
            console.warn("[site-header] no #site-header element found");
            return;
        }
        slot.outerHTML = buildHeaderHtml(options);
        wire();
        loadCurrentUser();
    }

    window.mountSiteHeader = mount;
    window.refreshSiteHeaderUser = loadCurrentUser;
})();
