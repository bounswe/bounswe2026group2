// Shared helpers + picker for multi-location story support.
//
// Data shape used throughout the frontend:
//   { latitude: number, longitude: number, label: string|null }
//
// The picker manages an ordered list of these and renders numbered, draggable
// markers on a Leaflet map plus a chip strip in a DOM container. Single-pin
// usage is unchanged: callers can read locations[0] for backwards
// compatibility with the existing latitude/longitude/place_name flow.

function normalizeLocation(loc) {
    if (!loc) return null;
    var lat = typeof loc.latitude === "number" ? loc.latitude : parseFloat(loc.latitude);
    var lng = typeof loc.longitude === "number" ? loc.longitude : parseFloat(loc.longitude);
    if (!isFinite(lat) || !isFinite(lng)) return null;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
    var label = (loc.label == null || loc.label === "") ? null : String(loc.label).trim();
    return { latitude: lat, longitude: lng, label: label || null };
}

function serializeLocations(arr) {
    if (!Array.isArray(arr)) return [];
    var out = [];
    for (var i = 0; i < arr.length; i++) {
        var loc = normalizeLocation(arr[i]);
        if (loc) out.push(loc);
    }
    return out;
}

function findDuplicateIndex(arr) {
    // Backend rejects duplicate (lat, lng) — match that on the client to
    // give immediate feedback instead of a 422.
    var seen = {};
    for (var i = 0; i < arr.length; i++) {
        var key = arr[i].latitude.toFixed(6) + "," + arr[i].longitude.toFixed(6);
        if (seen[key] !== undefined) return i;
        seen[key] = i;
    }
    return -1;
}

function hasMultipleLocations(story) {
    if (!story) return false;
    var locs = Array.isArray(story.locations) ? story.locations : [];
    return locs.length > 1;
}

function getEffectiveLocations(story) {
    // Returns the list of {latitude, longitude, label} to render for a
    // story. Multi-location stories return their full list; legacy
    // single-location stories return a one-item list from
    // story.latitude/longitude/place_name so callers can use one code path.
    if (!story) return [];
    var locs = Array.isArray(story.locations) ? story.locations.slice() : [];
    if (locs.length > 0) return serializeLocations(locs);
    if (typeof story.latitude === "number" && typeof story.longitude === "number") {
        return [{
            latitude: story.latitude,
            longitude: story.longitude,
            label: story.place_name || null
        }];
    }
    return [];
}

// ─── Map markers ───────────────────────────────────────────────────────────

function buildNumberedIcon(L, index, options) {
    var color = (options && options.color) || "#775a19"; // primary brown
    var size = (options && options.size) || 32;
    var html =
        '<div style="' +
        'width:' + size + 'px;height:' + size + 'px;' +
        'background:' + color + ';color:#fff;' +
        'border:2px solid #fff;border-radius:9999px;' +
        'display:flex;align-items:center;justify-content:center;' +
        'font-family:Inter,sans-serif;font-weight:700;font-size:13px;' +
        'box-shadow:0 4px 12px rgba(0,0,0,0.25);' +
        '">' + (index + 1) + '</div>';
    return L.divIcon({
        className: "multi-location-pin",
        html: html,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
        popupAnchor: [0, -size / 2]
    });
}

// ─── Picker (used on story-create / story-edit) ────────────────────────────

function createMultiLocationPicker(L, map, options) {
    options = options || {};
    var onChange = options.onChange || function () { };
    var maxLocations = options.maxLocations || 10;
    var locations = [];
    var markers = [];
    var polyline = null;

    function redrawPolyline() {
        if (polyline) {
            map.removeLayer(polyline);
            polyline = null;
        }
        if (locations.length < 2) return;
        var coords = locations.map(function (l) { return [l.latitude, l.longitude]; });
        polyline = L.polyline(coords, {
            color: "#775a19",
            weight: 3,
            opacity: 0.6,
            dashArray: "6 8"
        }).addTo(map);
    }

    function rebuildMarkers() {
        markers.forEach(function (m) { map.removeLayer(m); });
        markers = [];
        locations.forEach(function (loc, idx) {
            var marker = L.marker([loc.latitude, loc.longitude], {
                draggable: true,
                icon: buildNumberedIcon(L, idx)
            }).addTo(map);

            marker.on("dragend", function () {
                var pos = marker.getLatLng();
                locations[idx] = {
                    latitude: pos.lat,
                    longitude: pos.lng,
                    label: locations[idx].label
                };
                redrawPolyline();
                onChange(getLocations());
            });

            markers.push(marker);
        });
        redrawPolyline();
    }

    function getLocations() {
        return locations.map(function (l) { return { latitude: l.latitude, longitude: l.longitude, label: l.label }; });
    }

    function add(loc) {
        var n = normalizeLocation(loc);
        if (!n) return false;
        if (locations.length >= maxLocations) return false;
        var dupIndex = findDuplicateIndex(locations.concat([n]));
        if (dupIndex !== -1) return false;
        locations.push(n);
        rebuildMarkers();
        onChange(getLocations());
        return true;
    }

    function remove(index) {
        if (index < 0 || index >= locations.length) return;
        locations.splice(index, 1);
        rebuildMarkers();
        onChange(getLocations());
    }

    function setLabel(index, label) {
        if (index < 0 || index >= locations.length) return;
        var trimmed = (label || "").trim();
        locations[index].label = trimmed || null;
        onChange(getLocations());
    }

    function clear() {
        locations = [];
        rebuildMarkers();
        onChange(getLocations());
    }

    function setAll(arr) {
        locations = serializeLocations(arr);
        rebuildMarkers();
        onChange(getLocations());
    }

    function focus(index) {
        if (index < 0 || index >= locations.length) return;
        var loc = locations[index];
        map.setView([loc.latitude, loc.longitude], Math.max(map.getZoom(), 15));
        if (markers[index]) markers[index].openPopup();
    }

    return {
        add: add,
        remove: remove,
        setLabel: setLabel,
        clear: clear,
        setAll: setAll,
        focus: focus,
        getLocations: getLocations,
        count: function () { return locations.length; }
    };
}

// ─── Chip strip renderer (vanilla DOM) ─────────────────────────────────────

function renderLocationChips(container, locations, callbacks) {
    callbacks = callbacks || {};
    container.innerHTML = "";

    if (!locations.length) {
        var empty = document.createElement("p");
        empty.className = "text-xs text-textmuted italic";
        empty.textContent = "No locations yet — click the map to drop a pin.";
        container.appendChild(empty);
        return;
    }

    locations.forEach(function (loc, idx) {
        var chip = document.createElement("div");
        chip.className =
            "group flex items-center gap-2 rounded-full border border-border bg-white pl-1 pr-2 py-1 " +
            "text-xs shadow-sm transition hover:border-primary-light";
        chip.setAttribute("data-index", String(idx));

        var num = document.createElement("span");
        num.className =
            "flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary text-white " +
            "text-[11px] font-bold";
        num.textContent = String(idx + 1);
        chip.appendChild(num);

        var labelBtn = document.createElement("button");
        labelBtn.type = "button";
        labelBtn.className = "max-w-[12rem] truncate text-left text-textmain hover:text-primary";
        var coordsText = loc.latitude.toFixed(4) + ", " + loc.longitude.toFixed(4);
        labelBtn.textContent = loc.label || coordsText;
        labelBtn.title = loc.label ? loc.label + " — " + coordsText : coordsText;
        labelBtn.addEventListener("click", function () {
            if (callbacks.onFocus) callbacks.onFocus(idx);
        });
        chip.appendChild(labelBtn);

        var removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.setAttribute("aria-label", "Remove location " + (idx + 1));
        removeBtn.className =
            "flex h-5 w-5 flex-none items-center justify-center rounded-full text-textmuted " +
            "transition hover:bg-red-50 hover:text-red-600";
        removeBtn.innerHTML =
            '<svg aria-hidden="true" viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" ' +
            'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
            '<line x1="18" y1="6" x2="6" y2="18"></line>' +
            '<line x1="6" y1="6" x2="18" y2="18"></line></svg>';
        removeBtn.addEventListener("click", function () {
            if (callbacks.onRemove) callbacks.onRemove(idx);
        });
        chip.appendChild(removeBtn);

        container.appendChild(chip);
    });
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        normalizeLocation: normalizeLocation,
        serializeLocations: serializeLocations,
        findDuplicateIndex: findDuplicateIndex,
        hasMultipleLocations: hasMultipleLocations,
        getEffectiveLocations: getEffectiveLocations,
        renderLocationChips: renderLocationChips,
        createMultiLocationPicker: createMultiLocationPicker,
        buildNumberedIcon: buildNumberedIcon
    };
}
