const {
    normalizeLocation,
    serializeLocations,
    findDuplicateIndex,
    hasMultipleLocations,
    getEffectiveLocations,
    renderLocationChips
} = require("./multi-location");

describe("multi-location helpers", () => {
    describe("normalizeLocation", () => {
        test("returns null for missing/invalid input", () => {
            expect(normalizeLocation(null)).toBeNull();
            expect(normalizeLocation(undefined)).toBeNull();
            expect(normalizeLocation({})).toBeNull();
            expect(normalizeLocation({ latitude: "abc", longitude: 1 })).toBeNull();
            expect(normalizeLocation({ latitude: 91, longitude: 1 })).toBeNull();
            expect(normalizeLocation({ latitude: 1, longitude: 181 })).toBeNull();
        });

        test("parses numeric strings and trims the label", () => {
            expect(normalizeLocation({ latitude: "41.0", longitude: "29.0", label: "  Eminönü  " }))
                .toEqual({ latitude: 41, longitude: 29, label: "Eminönü" });
        });

        test("nulls out empty labels", () => {
            expect(normalizeLocation({ latitude: 1, longitude: 1, label: "" }).label).toBeNull();
            expect(normalizeLocation({ latitude: 1, longitude: 1, label: "   " }).label).toBeNull();
            expect(normalizeLocation({ latitude: 1, longitude: 1 }).label).toBeNull();
        });
    });

    describe("serializeLocations", () => {
        test("drops invalid items but keeps valid ones in order", () => {
            const out = serializeLocations([
                { latitude: 1, longitude: 1 },
                { latitude: "bad" },
                { latitude: 2, longitude: 2, label: "B" }
            ]);
            expect(out).toEqual([
                { latitude: 1, longitude: 1, label: null },
                { latitude: 2, longitude: 2, label: "B" }
            ]);
        });

        test("returns empty array for non-array input", () => {
            expect(serializeLocations(null)).toEqual([]);
            expect(serializeLocations(undefined)).toEqual([]);
            expect(serializeLocations("nope")).toEqual([]);
        });
    });

    describe("findDuplicateIndex", () => {
        test("detects exact-coordinate duplicates", () => {
            expect(findDuplicateIndex([
                { latitude: 1, longitude: 2 },
                { latitude: 3, longitude: 4 },
                { latitude: 1, longitude: 2 }
            ])).toBe(2);
        });

        test("returns -1 when all locations are distinct", () => {
            expect(findDuplicateIndex([
                { latitude: 1, longitude: 2 },
                { latitude: 3, longitude: 4 }
            ])).toBe(-1);
        });
    });

    describe("hasMultipleLocations", () => {
        test("true only when story.locations has length > 1", () => {
            expect(hasMultipleLocations({ locations: [{}, {}] })).toBe(true);
            expect(hasMultipleLocations({ locations: [{}] })).toBe(false);
            expect(hasMultipleLocations({ locations: [] })).toBe(false);
            expect(hasMultipleLocations({})).toBe(false);
            expect(hasMultipleLocations(null)).toBe(false);
        });
    });

    describe("getEffectiveLocations", () => {
        test("returns the locations array for multi-location stories", () => {
            const story = {
                latitude: 0, longitude: 0,
                locations: [
                    { latitude: 1, longitude: 1, label: "A" },
                    { latitude: 2, longitude: 2, label: null }
                ]
            };
            const out = getEffectiveLocations(story);
            expect(out).toHaveLength(2);
            expect(out[0]).toEqual({ latitude: 1, longitude: 1, label: "A" });
        });

        test("falls back to top-level lat/lng for legacy single-location stories", () => {
            const story = { latitude: 41, longitude: 29, place_name: "Galata" };
            expect(getEffectiveLocations(story)).toEqual([
                { latitude: 41, longitude: 29, label: "Galata" }
            ]);
        });

        test("returns empty array when no coordinates are available", () => {
            expect(getEffectiveLocations({})).toEqual([]);
            expect(getEffectiveLocations(null)).toEqual([]);
        });
    });

    describe("renderLocationChips", () => {
        let container;
        beforeEach(() => {
            container = document.createElement("div");
            document.body.appendChild(container);
        });
        afterEach(() => {
            container.remove();
        });

        test("renders empty-state message when there are no locations", () => {
            renderLocationChips(container, [], {});
            expect(container.textContent).toMatch(/No locations yet/i);
        });

        test("renders one numbered chip per location with label fallback to coords", () => {
            renderLocationChips(container, [
                { latitude: 41.012345, longitude: 28.998765, label: "Galata" },
                { latitude: 41.5, longitude: 29.5, label: null }
            ], {});

            const chips = container.querySelectorAll('[data-index]');
            expect(chips).toHaveLength(2);
            expect(chips[0].textContent).toContain("Galata");
            expect(chips[1].textContent).toContain("41.5000, 29.5000");
            expect(chips[0].querySelectorAll("span")[0].textContent).toBe("1");
            expect(chips[1].querySelectorAll("span")[0].textContent).toBe("2");
        });

        test("remove button calls onRemove with the chip index", () => {
            const onRemove = jest.fn();
            renderLocationChips(container, [
                { latitude: 1, longitude: 1, label: "A" },
                { latitude: 2, longitude: 2, label: "B" }
            ], { onRemove });

            const removeButtons = container.querySelectorAll('button[aria-label^="Remove"]');
            removeButtons[1].click();
            expect(onRemove).toHaveBeenCalledWith(1);
        });

        test("label button calls onFocus with the chip index", () => {
            const onFocus = jest.fn();
            renderLocationChips(container, [
                { latitude: 1, longitude: 1, label: "A" }
            ], { onFocus });

            const labelBtn = container.querySelector('[data-index="0"] button.text-left');
            labelBtn.click();
            expect(onFocus).toHaveBeenCalledWith(0);
        });
    });
});
