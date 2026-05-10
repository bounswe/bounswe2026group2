const { renderTagChips } = require("./tags");

describe("renderTagChips", () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="container"></div>';
    });

    function getContainer() {
        return document.getElementById("container");
    }

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
