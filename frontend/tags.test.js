const { fetchTagSuggestions, renderTagChips, createTagInput } = require("./tags");

// ─── Helpers ────────────────────────────────────────────────────────────────

function getContainer() {
    return document.getElementById("container");
}

function getInput() {
    return getContainer().querySelector("input");
}

function getChips() {
    return getContainer().querySelectorAll(".tag-remove-btn");
}

function getDropdownOptions() {
    return getContainer().querySelectorAll("[role='option']");
}

function pressKey(inputEl, key) {
    inputEl.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
}

function typeValue(inputEl, value) {
    inputEl.value = value;
    inputEl.dispatchEvent(new Event("input", { bubbles: true }));
}

// ─── renderTagChips ──────────────────────────────────────────────────────────

describe("renderTagChips", () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="container"></div>';
    });

    test("renders one chip per tag (string array)", () => {
        renderTagChips(getContainer(), ["history", "istanbul"]);
        const chips = getContainer().querySelectorAll(".tag-chip");
        expect(chips.length).toBe(2);
        expect(chips[0].textContent).toBe("history");
        expect(chips[1].textContent).toBe("istanbul");
    });

    test("renders chips from object array using .name", () => {
        renderTagChips(getContainer(), [{ id: "1", name: "culture" }, { id: "2", name: "art" }]);
        const chips = getContainer().querySelectorAll(".tag-chip");
        expect(chips.length).toBe(2);
        expect(chips[0].textContent).toBe("culture");
    });

    test("hides container when tags is empty array", () => {
        getContainer().style.display = "flex";
        renderTagChips(getContainer(), []);
        expect(getContainer().style.display).toBe("none");
    });

    test("hides container when tags is null", () => {
        getContainer().style.display = "flex";
        renderTagChips(getContainer(), null);
        expect(getContainer().style.display).toBe("none");
    });

    test("does not throw when containerEl is null", () => {
        expect(() => renderTagChips(null, ["foo"])).not.toThrow();
    });

    test("shows container when tags are present", () => {
        getContainer().style.display = "none";
        renderTagChips(getContainer(), ["foo"]);
        expect(getContainer().style.display).not.toBe("none");
    });

    test("clears previous chips before re-rendering", () => {
        renderTagChips(getContainer(), ["a", "b"]);
        renderTagChips(getContainer(), ["c"]);
        const chips = getContainer().querySelectorAll(".tag-chip");
        expect(chips.length).toBe(1);
        expect(chips[0].textContent).toBe("c");
    });
});

// ─── createTagInput ──────────────────────────────────────────────────────────

describe("createTagInput", () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="container"></div>';
    });

    test("renders an input element inside the container", () => {
        createTagInput(getContainer());
        expect(getInput()).not.toBeNull();
    });

    test("getTags returns empty array initially", () => {
        const ti = createTagInput(getContainer());
        expect(ti.getTags()).toEqual([]);
    });

    test("Enter key adds a tag", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "ottoman");
        pressKey(input, "Enter");
        expect(ti.getTags()).toEqual(["ottoman"]);
    });

    test("comma key adds a tag", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "byzantine");
        pressKey(input, ",");
        expect(ti.getTags()).toEqual(["byzantine"]);
    });

    test("Enter clears the input field after adding", () => {
        createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "culture");
        pressKey(input, "Enter");
        expect(input.value).toBe("");
    });

    test("does not add duplicate tags (case-insensitive)", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "history");
        pressKey(input, "Enter");
        typeValue(input, "History");
        pressKey(input, "Enter");
        expect(ti.getTags()).toEqual(["history"]);
    });

    test("tags are normalized to lowercase", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "ISTANBUL");
        pressKey(input, "Enter");
        expect(ti.getTags()).toEqual(["istanbul"]);
    });

    test("does not add empty string tag", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "   ");
        pressKey(input, "Enter");
        expect(ti.getTags()).toEqual([]);
    });

    test("Backspace on empty input removes last tag", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "art");
        pressKey(input, "Enter");
        typeValue(input, "");
        pressKey(input, "Backspace");
        expect(ti.getTags()).toEqual([]);
    });

    test("Backspace does nothing if input has text", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "art");
        pressKey(input, "Enter");
        typeValue(input, "a");
        pressKey(input, "Backspace");
        expect(ti.getTags()).toEqual(["art"]);
    });

    test("× button removes the corresponding tag", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "art");
        pressKey(input, "Enter");
        typeValue(input, "music");
        pressKey(input, "Enter");
        const removeBtns = getChips();
        removeBtns[0].click();
        expect(ti.getTags()).toEqual(["music"]);
    });

    test("disables input when maxTags is reached", () => {
        const ti = createTagInput(getContainer(), { maxTags: 2 });
        const input = getInput();
        typeValue(input, "a"); pressKey(input, "Enter");
        typeValue(input, "b"); pressKey(input, "Enter");
        expect(input.disabled).toBe(true);
    });

    test("getTags returns a copy, not a reference", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "foo"); pressKey(input, "Enter");
        const arr = ti.getTags();
        arr.push("injected");
        expect(ti.getTags()).toEqual(["foo"]);
    });

    test("setTags replaces current tags", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "old"); pressKey(input, "Enter");
        ti.setTags(["new1", "new2"]);
        expect(ti.getTags()).toEqual(["new1", "new2"]);
    });

    test("setTags accepts object array with .name", () => {
        const ti = createTagInput(getContainer());
        ti.setTags([{ id: "1", name: "Ottoman" }]);
        expect(ti.getTags()).toEqual(["ottoman"]);
    });

    test("setTags with null clears tags", () => {
        const ti = createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "foo"); pressKey(input, "Enter");
        ti.setTags(null);
        expect(ti.getTags()).toEqual([]);
    });

    test("initialTags option pre-populates tags", () => {
        const ti = createTagInput(getContainer(), { initialTags: ["history", "art"] });
        expect(ti.getTags()).toEqual(["history", "art"]);
    });

    test("destroy clears the container", () => {
        const ti = createTagInput(getContainer());
        ti.destroy();
        expect(getContainer().innerHTML).toBe("");
    });

    test("Escape key closes dropdown", () => {
        const ti = createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        const dropdown = getContainer().querySelector(".tag-dropdown");
        dropdown.classList.remove("hidden");
        pressKey(input, "Escape");
        expect(dropdown.classList.contains("hidden")).toBe(true);
    });

    test("returns safe object when containerEl is null", () => {
        const ti = createTagInput(null);
        expect(ti.getTags()).toEqual([]);
        expect(() => ti.setTags(["foo"])).not.toThrow();
        expect(() => ti.destroy()).not.toThrow();
    });
});

// ─── fetchTagSuggestions ────────────────────────────────────────────────────

describe("fetchTagSuggestions", () => {
    beforeEach(() => {
        global.fetch = jest.fn();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("calls fetch with encoded query URL", async () => {
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve([{ id: "1", name: "history", story_count: 5 }])
        });

        await fetchTagSuggestions("http://api", "hist");
        expect(global.fetch).toHaveBeenCalledWith("http://api/tags?q=hist&limit=10");
    });

    test("encodes special characters in the query", async () => {
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });
        await fetchTagSuggestions("http://api", "a&b");
        expect(global.fetch).toHaveBeenCalledWith("http://api/tags?q=a%26b&limit=10");
    });

    test("returns parsed array on success", async () => {
        const payload = [{ id: "1", name: "culture" }];
        global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(payload) });
        const result = await fetchTagSuggestions("http://api", "cult");
        expect(result).toEqual(payload);
    });

    test("returns empty array when response is not ok", async () => {
        global.fetch.mockResolvedValueOnce({ ok: false, status: 500 });
        const result = await fetchTagSuggestions("http://api", "test");
        expect(result).toEqual([]);
    });

    test("returns empty array on network error", async () => {
        global.fetch.mockRejectedValueOnce(new Error("Network failure"));
        const result = await fetchTagSuggestions("http://api", "test");
        expect(result).toEqual([]);
    });
});

// ─── Autocomplete integration ────────────────────────────────────────────────

describe("createTagInput autocomplete", () => {
    async function flushPromises() {
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
    }

    beforeEach(() => {
        jest.useFakeTimers();
        document.body.innerHTML = '<div id="container"></div>';
        global.fetch = jest.fn();
    });

    afterEach(() => {
        jest.useRealTimers();
        jest.restoreAllMocks();
    });

    test("does not fetch when query is shorter than 2 chars", () => {
        createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        typeValue(input, "a");
        jest.runAllTimers();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    test("does not fetch when apiBase is not provided", () => {
        createTagInput(getContainer());
        const input = getInput();
        typeValue(input, "history");
        jest.runAllTimers();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    test("fetches after debounce delay with 2+ chars", () => {
        global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve([]) });
        createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        typeValue(input, "hi");
        expect(global.fetch).not.toHaveBeenCalled();
        jest.advanceTimersByTime(300);
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    test("debounce: rapid typing sends only one request", () => {
        global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve([]) });
        createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        typeValue(input, "hi");
        jest.advanceTimersByTime(100);
        typeValue(input, "his");
        jest.advanceTimersByTime(100);
        typeValue(input, "hist");
        jest.advanceTimersByTime(300);
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    test("clicking a suggestion adds that tag", async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([{ name: "ottoman", story_count: 3 }])
        });
        const ti = createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        typeValue(input, "ott");
        jest.advanceTimersByTime(300);
        await flushPromises();

        const opts = getDropdownOptions();
        expect(opts.length).toBe(1);
        opts[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        expect(ti.getTags()).toContain("ottoman");
    });

    test("dropdown is hidden after selecting a suggestion", async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([{ name: "history" }])
        });
        createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        typeValue(input, "his");
        jest.advanceTimersByTime(300);
        await flushPromises();

        const dropdown = getContainer().querySelector(".tag-dropdown");
        getDropdownOptions()[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
        expect(dropdown.classList.contains("hidden")).toBe(true);
    });

    test("already-added tags do not appear in suggestions", async () => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([{ name: "history" }, { name: "art" }])
        });
        const ti = createTagInput(getContainer(), { apiBase: "http://api" });
        const input = getInput();
        typeValue(input, "history"); pressKey(input, "Enter");
        typeValue(input, "his");
        jest.advanceTimersByTime(300);
        await flushPromises();

        const opts = getDropdownOptions();
        const names = Array.from(opts).map(o => o.textContent.trim());
        expect(names).not.toContain("history");
        expect(names).toContain("art");
    });
});
