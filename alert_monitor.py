"""
alert_monitor.py — Astra Proactive Alert Monitor
=================================================
Runs as a background thread. Monitors:
  • Upcoming rain / heavy rain / storm (next 24 hours forecast)
  • Cyclone / severe weather warnings
  • Earthquakes near Kolkata (within 1000 km radius)

Behaves like a smartphone weather/disaster app:
  → Warns BEFORE something hits using forecast data
  → Speaks alert immediately via ASTRA's voice
  → Never repeats the same alert within cooldown period
  → All APIs are free, no key needed

Check intervals:
  Weather forecast : every 10 minutes
  Earthquake       : every 5 minutes (faster — sudden events)

Sources:
  Weather  — Open-Meteo forecast API (hourly, free)
  Cyclone  — Open-Meteo weather codes (WMO standard)
  Quake    — USGS Earthquake Hazards API (real-time, free)
"""

import threading
import time
import datetime
import requests
import os

# ── Location config ───────────────────────────────────────────────────
LAT          = 22.5726       # Kolkata
LON          = 88.3639
CITY         = "Kolkata"
REGION       = "West Bengal"
IST_OFFSET   = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# ── Check intervals (seconds) ─────────────────────────────────────────
WEATHER_INTERVAL   = 10 * 60    # 10 minutes
EARTHQUAKE_INTERVAL = 5 * 60    # 5 minutes

# ── Earthquake radius ─────────────────────────────────────────────────
QUAKE_RADIUS_KM  = 1000         # Alert if quake within 1000 km
QUAKE_MIN_MAG    = 2.5          # Any magnitude 2.5+ (felt locally)

# ── Alert cooldown — avoid repeating same alert ───────────────────────
# Key = alert_type string, Value = last spoken datetime
_last_spoken: dict = {}
WEATHER_COOLDOWN_MIN  = 60      # Don't repeat weather alert for 60 min
QUAKE_COOLDOWN_MIN    = 30      # Don't repeat same quake for 30 min

# ── WMO weather code mappings ─────────────────────────────────────────
# Open-Meteo returns WMO codes. Map to (label, severity, spoken_message)
WMO_ALERTS = {
    # Drizzle
    51: ("light_drizzle",   "low",      "Light drizzle is expected in {city} soon."),
    53: ("drizzle",         "low",      "Drizzle expected in {city}."),
    55: ("heavy_drizzle",   "medium",   "Heavy drizzle approaching {city}."),
    # Rain
    61: ("light_rain",      "medium",   "Light rain is expected in {city} in the coming hours. You may want to carry an umbrella."),
    63: ("rain",            "medium",   "Rain is forecast for {city}. Please carry an umbrella."),
    65: ("heavy_rain",      "high",     "Warning! Heavy rain is forecast for {city}. Please stay indoors if possible."),
    # Freezing rain
    66: ("freezing_rain",   "high",     "Warning! Freezing rain expected in {city}. Roads may be dangerous."),
    67: ("heavy_freezing",  "high",     "Warning! Heavy freezing rain forecast for {city}. Please stay safe."),
    # Snow (unlikely in Kolkata but included)
    71: ("light_snow",      "medium",   "Light snowfall expected near {city}."),
    73: ("snow",            "high",     "Snowfall forecast for {city}. Please take precautions."),
    75: ("heavy_snow",      "high",     "Warning! Heavy snowfall forecast for {city}."),
    # Thunderstorm
    80: ("rain_showers",    "medium",   "Rain showers expected in {city} soon."),
    81: ("showers",         "medium",   "Moderate rain showers forecast for {city}."),
    82: ("heavy_showers",   "high",     "Warning! Heavy rain showers approaching {city}. Please stay indoors."),
    95: ("thunderstorm",    "high",     "Storm alert! Thunderstorm forecast for {city}. Please stay safe and avoid open areas."),
    96: ("thunderstorm_hail","critical","Critical alert! Thunderstorm with hail approaching {city}. Stay indoors immediately."),
    99: ("severe_storm",    "critical", "Critical alert! Severe thunderstorm with heavy hail forecast for {city}. Take shelter immediately."),
    # Fog
    45: ("fog",             "medium",   "Dense fog expected in {city}. Drive carefully."),
    48: ("icy_fog",         "high",     "Warning! Freezing fog forecast for {city}. Visibility will be very low."),
}

# WMO codes considered cyclone-level / severe
CYCLONE_CODES = {96, 99, 95}


def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(tz=IST_OFFSET)


def _cooldown_ok(key: str, minutes: int) -> bool:
    """Return True if enough time has passed since last alert of this type."""
    last = _last_spoken.get(key)
    if last is None:
        return True
    elapsed = (_now_ist() - last).total_seconds() / 60
    return elapsed >= minutes


def _mark_spoken(key: str):
    """Record that an alert was just spoken."""
    _last_spoken[key] = _now_ist()


# ─────────────────────────────────────────────
# WEATHER MONITOR
# ─────────────────────────────────────────────

def _fetch_forecast() -> dict | None:
    """
    Fetch next 24-hour hourly forecast from Open-Meteo.
    Returns raw JSON or None on failure.
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            f"&hourly=weathercode,precipitation_probability,precipitation"
            f"&forecast_days=1"
            f"&timezone=Asia/Kolkata"
        )
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[AlertMonitor] Weather fetch error: {e}")
    return None


def _check_weather_alerts(speak_fn):
    """
    Analyse next 24-hour forecast.
    Speaks alert if any significant weather event is approaching.
    """
    data = _fetch_forecast()
    if not data:
        return

    hours        = data["hourly"]["time"]
    codes        = data["hourly"]["weathercode"]
    precip_prob  = data["hourly"]["precipitation_probability"]
    precip_mm    = data["hourly"]["precipitation"]

    now_ist      = _now_ist()
    highest_sev  = None   # track worst event to speak once
    highest_code = None
    hours_away   = None

    sev_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}

    for i, time_str in enumerate(hours):
        try:
            hour_dt = datetime.datetime.fromisoformat(time_str).replace(
                tzinfo=IST_OFFSET
            )
        except Exception:
            continue

        if hour_dt <= now_ist:
            continue                  # skip past hours

        diff_hours = (hour_dt - now_ist).total_seconds() / 3600
        if diff_hours > 24:
            break                     # only look 24 hours ahead

        code = codes[i]
        prob = precip_prob[i] or 0
        mm   = precip_mm[i] or 0

        if code not in WMO_ALERTS:
            continue
        if prob < 40 and mm < 1:      # skip unlikely events
            continue

        _, sev, _ = WMO_ALERTS[code]

        if (highest_sev is None or
                sev_rank.get(sev, 0) > sev_rank.get(highest_sev, 0)):
            highest_sev  = sev
            highest_code = code
            hours_away   = diff_hours

    if highest_code is None:
        print(f"[AlertMonitor] Weather: no significant events in next 24h")
        return

    alert_key = f"weather_{highest_code}"
    if not _cooldown_ok(alert_key, WEATHER_COOLDOWN_MIN):
        print(f"[AlertMonitor] Weather alert on cooldown: {alert_key}")
        return

    _, sev, msg_template = WMO_ALERTS[highest_code]
    message = msg_template.format(city=CITY)

    # Add timing
    if hours_away < 1:
        timing = "very soon"
    elif hours_away < 3:
        timing = f"in about {int(hours_away)} hour"
        if int(hours_away) > 1:
            timing += "s"
    else:
        timing = f"in approximately {int(hours_away)} hours"

    full_alert = f"Weather alert! {message} Expected {timing}."

    print(f"[AlertMonitor] ⚠ Speaking weather alert: {full_alert}")
    speak_fn(full_alert)
    _show_on_screen(full_alert, severity="critical" if sev == "critical" else "warn")
    _mark_spoken(alert_key)


# ─────────────────────────────────────────────
# EARTHQUAKE MONITOR
# ─────────────────────────────────────────────

def _fetch_earthquakes() -> list:
    """
    Fetch earthquakes from USGS in the last 1 hour within radius.
    Returns list of quake dicts or empty list.
    """
    try:
        # USGS real-time earthquake feed — last hour, all magnitudes
        url = (
            f"https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson"
            f"&starttime={_usgs_start_time()}"
            f"&latitude={LAT}&longitude={LON}"
            f"&maxradiuskm={QUAKE_RADIUS_KM}"
            f"&minmagnitude={QUAKE_MIN_MAG}"
            f"&orderby=time"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            features = resp.json().get("features", [])
            return features
    except Exception as e:
        print(f"[AlertMonitor] Earthquake fetch error: {e}")
    return []


def _usgs_start_time() -> str:
    """Return ISO time string for 1 hour ago in UTC."""
    utc_now   = datetime.datetime.utcnow()
    one_hour  = utc_now - datetime.timedelta(hours=1)
    return one_hour.strftime("%Y-%m-%dT%H:%M:%S")


def _quake_severity(mag: float) -> str:
    """Return spoken severity description for magnitude."""
    if mag < 3.0:   return "minor"
    if mag < 4.0:   return "light"
    if mag < 5.0:   return "moderate"
    if mag < 6.0:   return "strong"
    if mag < 7.0:   return "major"
    return "great"


def _check_earthquake_alerts(speak_fn):
    """
    Check for recent earthquakes near Kolkata.
    Speaks alert for any new quake not yet announced.
    """
    quakes = _fetch_earthquakes()
    if not quakes:
        print(f"[AlertMonitor] Earthquake: no events near {CITY}")
        return

    for quake in quakes:
        props    = quake.get("properties", {})
        mag      = props.get("mag", 0) or 0
        place    = props.get("place", "near you")
        quake_id = quake.get("id", "unknown")
        felt     = props.get("felt") or 0

        alert_key = f"quake_{quake_id}"
        if not _cooldown_ok(alert_key, QUAKE_COOLDOWN_MIN):
            continue

        severity = _quake_severity(mag)

        if mag >= 5.0:
            prefix = "Earthquake alert!"
        elif mag >= 4.0:
            prefix = "Earthquake detected!"
        else:
            prefix = "Minor earthquake detected."

        message = (
            f"{prefix} A {severity} earthquake of magnitude "
            f"{mag:.1f} has been detected {place}. "
        )

        if mag >= 5.0:
            message += "Please move away from windows and take cover."
        elif mag >= 4.0:
            message += "Stay calm and be alert for aftershocks."
        else:
            message += "No immediate danger expected, but stay alert."

        print(f"[AlertMonitor] ⚠ Speaking quake alert: M{mag} {place}")
        speak_fn(message)
        _show_on_screen(message, severity="critical" if mag >= 5.0 else "warn")
        _mark_spoken(alert_key)
        time.sleep(1)   # brief pause between multiple quake alerts


# ─────────────────────────────────────────────
# BACKGROUND THREAD
# ─────────────────────────────────────────────

def _weather_loop(speak_fn):
    """Weather check loop — runs every 10 minutes."""
    print("[AlertMonitor] Weather monitor started.")
    while True:
        try:
            _check_weather_alerts(speak_fn)
        except Exception as e:
            print(f"[AlertMonitor] Weather loop error: {e}")
        time.sleep(WEATHER_INTERVAL)


def _earthquake_loop(speak_fn):
    """Earthquake check loop — runs every 5 minutes."""
    print("[AlertMonitor] Earthquake monitor started.")
    while True:
        try:
            _check_earthquake_alerts(speak_fn)
        except Exception as e:
            print(f"[AlertMonitor] Earthquake loop error: {e}")
        time.sleep(EARTHQUAKE_INTERVAL)


# ── Global UI reference (set by start_alert_monitor) ─────────────────
_ui_ref = None


def _show_on_screen(message: str, severity: str = "warn"):
    """
    Show alert as a chat bubble on the ASTRA UI screen.
    severity: 'warn' | 'critical'
    """
    global _ui_ref
    if _ui_ref is None:
        return
    prefix = "🔴 CRITICAL ALERT" if severity == "critical" else "⚠ ALERT"
    _ui_ref.add_chat_bubble("astra", f"{prefix}\n{message}")


def start_alert_monitor(speak_fn, ui=None):
    """
    Start all alert monitors as background daemon threads.
    Call this once from main.py after ASTRA is online.

    Parameters
    ----------
    speak_fn : callable
        The speak() function from main.py.
    ui : AstraUI, optional
        The UI instance — alerts will appear as chat bubbles on screen.
    """
    global _ui_ref
    _ui_ref = ui

    threading.Thread(
        target=_weather_loop,
        args=(speak_fn,),
        daemon=True,
        name="AstraWeatherMonitor"
    ).start()

    threading.Thread(
        target=_earthquake_loop,
        args=(speak_fn,),
        daemon=True,
        name="AstraEarthquakeMonitor"
    ).start()

    print("[AlertMonitor] ✓ All alert monitors running.")
