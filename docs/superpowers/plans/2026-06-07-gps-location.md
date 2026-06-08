# GPS Live Location Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make the VIKO map marker reflect accurate GPS/WiFi-triangulated position by fixing the already-present CoreLocation implementation in `window.py`.

**Architecture:** CoreLocation (`_start_corelocation`) is already wired up in `window.py`. It uses PyObjC to load `CLLocationManager`, creates an ObjC delegate that emits `_loc_sig` on location updates, and falls back gracefully if unavailable. Missing pieces: `distanceFilter`/`desiredAccuracy` not configured, `print()` not converted to `logger`, country polygon not updated on GPS fix. No new module needed.

**Tech Stack:** PyObjC (already installed), CoreLocation framework (macOS), Python `logging` via `viko.core.logger`.

---

### Task 1: Configure distanceFilter, desiredAccuracy, and convert print() to logger

**Files:**
- Modify: `viko/ui/window.py:642-749`

Context: `_start_corelocation()` creates a `CLLocationManager` and starts location updates, but never sets accuracy or distance filter. It also uses `print()` for errors and status — these should go through `get_logger()` so they appear in the structured log file.

- [x] **Step 1: Read the current `_start_corelocation` method**

Read `viko/ui/window.py` lines 642–750 to locate:
- Where `self._cl_manager` is created (line 726)
- The three `print()` calls (lines 717, 746, 749)

- [x] **Step 2: Add distanceFilter and desiredAccuracy after manager creation**

Find this block (around line 726–727):
```python
            self._cl_delegate = _VikoCLDelegate.new()
            self._cl_manager  = CLLocationManager.new()
            self._cl_manager.setDelegate_(self._cl_delegate)
```

Replace with:
```python
            self._cl_delegate = _VikoCLDelegate.new()
            self._cl_manager  = CLLocationManager.new()
            self._cl_manager.setDelegate_(self._cl_delegate)
            self._cl_manager.setDistanceFilter_(50.0)
            self._cl_manager.setDesiredAccuracy_(100.0)  # kCLLocationAccuracyHundredMeters
```

- [x] **Step 3: Add logger import inside the method and replace print() calls**

At the top of `_start_corelocation`, after `try:`, add:
```python
            from viko.core.logger import get_logger as _gl
            _log = _gl(__name__)
```

Then replace the three `print()` calls:

Line ~717 (inside `locationManager_didFailWithError_`):
```python
# Before:
                    print(f"[Location] CoreLocation error: {err}")
# After:
                    _log.warning("CoreLocation error: %s", err)
```

Line ~746 (after `CLLocationManager.authorizationStatus()`):
```python
# Before:
            print(f"[Location] CoreLocation auth status: {status}")
# After:
            _log.info("CoreLocation auth status: %s (%s)", status, labels.get(status, "unknown"))
```

Add a `labels` dict before that line:
```python
            labels = {0: "not_determined", 1: "restricted", 2: "denied",
                      3: "authorized_always", 4: "authorized_when_in_use"}
```

Line ~749 (except block):
```python
# Before:
            print(f"[Location] CoreLocation unavailable: {e}")
# After:
            _log.warning("CoreLocation unavailable: %s", e)
```

- [x] **Step 4: Verify syntax**

```bash
.venv/bin/python -m py_compile viko/ui/window.py && echo "OK"
```
Expected: `OK`

- [x] **Step 5: Commit**

```bash
git add viko/ui/window.py
git commit -m "fix: configure CoreLocation accuracy/distance filter, replace print with logger"
```

---

### Task 2: Trigger country polygon update on GPS fix

**Files:**
- Modify: `viko/ui/window.py:681-698` (inside `_VikoCLDelegate.locationManager_didUpdateLocations_`)

Context: `_fetch_location()` (IP-based) does two things: emits `_loc_sig` (marker) AND emits `_country_sig` (country polygon highlight). The CoreLocation delegate only emits `_loc_sig`. This means after a GPS fix, the marker moves but the country polygon stays from the IP lookup. We need to reverse-geocode the GPS coordinates to get the country code and fetch the polygon.

- [x] **Step 1: Read the delegate's `locationManager_didUpdateLocations_` method**

Read `viko/ui/window.py` lines 681–698. Current code:
```python
                def locationManager_didUpdateLocations_(self_d, mgr, locs):
                    if not locs:
                        return
                    loc   = locs[-1]
                    coord = loc.coordinate()
                    try:
                        lat, lon = float(coord.latitude), float(coord.longitude)
                    except AttributeError:
                        lat, lon = float(coord[0]), float(coord[1])
                    parent._loc_sig.emit(lat, lon, _fmt_label(lat, lon))
```

- [x] **Step 2: Replace the delegate method to also trigger country polygon fetch**

Replace the `locationManager_didUpdateLocations_` method body with:
```python
                def locationManager_didUpdateLocations_(self_d, mgr, locs):
                    if not locs:
                        return
                    loc   = locs[-1]
                    coord = loc.coordinate()
                    try:
                        lat, lon = float(coord.latitude), float(coord.longitude)
                    except AttributeError:
                        lat, lon = float(coord[0]), float(coord[1])
                    parent._loc_sig.emit(lat, lon, _fmt_label(lat, lon))
                    import threading as _t
                    _t.Thread(
                        target=parent._fetch_country_from_gps,
                        args=(lat, lon),
                        daemon=True,
                    ).start()
```

- [x] **Step 3: Add `_fetch_country_from_gps` method to the window class**

Add this method directly after `_start_corelocation` (before `_push_latency` at line ~751):
```python
    def _fetch_country_from_gps(self, lat: float, lon: float):
        """Reverse-geocode GPS coordinates to get country code, then fetch polygon."""
        try:
            import urllib.request, json as _json
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "VIKO/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                d = _json.loads(r.read())
            cc2 = d.get("address", {}).get("country_code", "").upper()
            if cc2:
                polys = self._fetch_country_polys(cc2)
                if polys:
                    self._country_sig.emit(polys)
        except Exception:
            pass
```

- [x] **Step 4: Verify syntax**

```bash
.venv/bin/python -m py_compile viko/ui/window.py && echo "OK"
```
Expected: `OK`

- [x] **Step 5: Commit**

```bash
git add viko/ui/window.py
git commit -m "feat: fetch country polygon from GPS coordinates via Nominatim"
```

---

### Task 3: Grant location permission (manual step — no code)

This task has no code. It is a prerequisite for CoreLocation to deliver coordinates.

- [x] **Step 1: Open System Settings**

Go to: **System Settings → Privacy & Security → Location Services**

- [x] **Step 2: Enable location for Terminal (or the Python process)**

Scroll down to find **Terminal** in the app list. If it's not there, VIKO must be run once first (it triggers `requestWhenInUseAuthorization` which registers the app). Toggle it **ON**.

If you launch VIKO from a different terminal emulator (iTerm2, Warp, etc.), enable that app instead.

- [x] **Step 3: Restart VIKO**

```bash
pkill -f "python viko.py"
nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &
sleep 8 && grep -i "corelocation\|location" /tmp/viko.log
```

Expected log line: `CoreLocation auth status: 4 (authorized_when_in_use)`

After ~5–10 seconds, the HUD map marker should jump to your actual GPS position and label changes from `IP:...` to `GPS  ...`.
