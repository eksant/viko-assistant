# Design: GPS Live Location via CoreLocation

**Date:** 2026-06-07
**Status:** Approved

## Problem

VIKO currently reads location from `ip-api.com` — IP-based geolocation that reflects the ISP/VPN exit node, not the device's physical position. This causes the vector map marker to show the wrong location, especially when behind a VPN.

## Goal

Replace IP-based location with macOS CoreLocation (`CLLocationManager`) for accurate GPS/WiFi-triangulated coordinates. Update live as the user moves, with a 50-meter distance filter.

## Approach

Create a new `viko/core/location.py` module that wraps `CLLocationManager` and exposes a clean callback interface. `window.py` replaces the old `_fetch_location()` thread with `LocationSource.start()`.

## Architecture

### New: `viko/core/location.py`

```
LocationSource
  .start(callback)  → starts CLLocationManager, calls callback(lat, lon, label) on each update
  .stop()           → stops location updates
```

**Internal flow per update:**
1. `CLLocationManager` delegate fires `locationManager_didUpdateLocations_`
2. Extract `(lat, lon)` from latest `CLLocation`
3. Run `CLGeocoder.reverseGeocodeLocation_completionHandler_` to get city + countryCode
4. Format label: `"GPS:CITY, CC  03°08′N  101°41′E"`
5. Call `callback(lat, lon, label)` — thread-safe via Python GIL

**CLLocationManager config:**
- `distanceFilter = 50.0` (meters) — skip updates smaller than 50m
- `desiredAccuracy = kCLLocationAccuracyHundredMeters`

**Fallback:** if `import CoreLocation` fails or permission denied, fall back to `ip-api.com` (existing logic, copied into location.py).

**Dependency:** `pyobjc-framework-CoreLocation` — install once, macOS only.

### Modified: `viko/ui/window.py`

- Remove `_fetch_location()` method and the `threading.Thread` that calls it
- On boot (`_on_boot_finished` or equivalent startup hook): call `LocationSource.start(self._on_gps_update)`
- Add `_on_gps_update(lat, lon, label)` → `self._loc_sig.emit(lat, lon, label)`
- On window close: call `LocationSource.stop()`
- Keep `_on_location`, `_on_country`, `_fetch_country_polys` unchanged — they still receive the signal

## Data Flow

```
CLLocationManager → delegate → CLGeocoder → callback(lat, lon, label)
                                                  ↓
                                     _loc_sig.emit(lat, lon, label)   [Qt signal, thread-safe]
                                                  ↓
                                     _on_location → set_location (HUD widget)
```

## macOS Permission

CoreLocation shows a one-time system dialog on first run ("Allow VIKO to use your location?"). If denied, `LocationSource` silently falls back to IP. No `Info.plist` needed for non-bundled Python scripts — permission is granted to the Python process.

## Out of Scope

- Reverse geocoding caching (CLGeocoder handles its own caching internally)
- Windows/Linux support (macOS only; fallback covers other platforms)
- Configurable update interval (50m distance filter is sufficient)
