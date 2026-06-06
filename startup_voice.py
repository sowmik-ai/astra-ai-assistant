"""
startup_voice.py — Astra Spoken Startup Sequence
=================================================
Delivers a warm, time-aware greeting followed by a spoken
self-health check. Called once at launch from main.py.

Spoken on boot:
  "Welcome back, Sowmik. Good Afternoon. It is 2:45 PM.
   Today is Saturday, the 6th of June 2026.
   Current temperature in Kolkata is 33 degrees Celsius.
   Let me run a quick self-health check."

  → All clear  : "All 4 systems are healthy.
                  Health check passed. ASTRA is online."
  → Warnings   : "Health check completed with 1 warning.
                  Issue detected in: Face assets.
                  3 systems are healthy.
                  ASTRA is running in degraded mode."
  → Critical   : "Health check failed.
                  Critical error detected in: Ollama.
                  ASTRA is offline. Please resolve and restart."

After ASTRA is online, the existing auth flow in main.py takes over:
  → Say wake word "Astra"
  → Voice identity check
  → Voice PIN check

Dependencies (already in your project):
  pyttsx3   — TTS (passed in as speak callable)
  requests  — Open-Meteo weather (free, no API key)
  datetime  — live IST date / time
"""

import datetime
import subprocess
import os
import time

# ── Location / timezone config ────────────────────────────────────────
WEATHER_LAT  = 22.5726          # Kolkata latitude
WEATHER_LON  = 88.3639          # Kolkata longitude
WEATHER_CITY = "Kolkata"
IST_OFFSET   = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


# ─────────────────────────────────────────────
# GREETING HELPERS  (all use live IST clock)
# ─────────────────────────────────────────────

def _now_ist() -> datetime.datetime:
    """Return current datetime in IST (UTC+5:30)."""
    return datetime.datetime.now(tz=IST_OFFSET)


def _get_period() -> str:
    """Morning / Afternoon / Evening based on current IST hour."""
    hour = _now_ist().hour
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    else:
        return "Evening"


def _get_time_string() -> str:
    """
    Returns e.g. 'It is 2 45 PM' in IST.
    Uses int() to strip leading zero — works on both Windows and Linux.
    """
    now  = _now_ist()
    hour = int(now.strftime("%I"))      # 1-12, int strips leading zero
    mins = now.strftime("%M")           # 00-59
    ampm = now.strftime("%p")           # AM / PM
    if mins == "00":
        return f"It is {hour} {ampm}"
    return f"It is {hour} {mins} {ampm}"


def _get_date_string() -> str:
    """Returns e.g. 'Saturday, the 6th of June 2026' using live IST clock."""
    now = _now_ist()
    day = now.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return now.strftime(f"%A, the {day}{suffix} of %B %Y")


# ─────────────────────────────────────────────
# WEATHER
# ─────────────────────────────────────────────

def _get_temperature() -> str:
    """
    Fetches current temperature from Open-Meteo (free, no API key).
    Returns e.g. '33 degrees Celsius', or '' on any failure.
    """
    try:
        import requests
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
            f"&current_weather=true"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            temp = resp.json()["current_weather"]["temperature"]
            return f"{int(round(temp))} degrees Celsius"
    except Exception as e:
        print(f"[Startup] Weather fetch failed: {e}")
    return ""


# ─────────────────────────────────────────────
# HEALTH CHECK FUNCTIONS
# ─────────────────────────────────────────────

def _check_ollama() -> tuple:
    """Check Ollama is running on localhost:11434."""
    try:
        import requests
        r = requests.get("http://localhost:11434", timeout=3)
        if "Ollama" in r.text:
            return True, "Ollama"
    except Exception:
        pass
    return False, "Ollama"


def _check_voice_profile() -> tuple:
    """Check my_voice.wav exists and is not empty."""
    wav = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_voice.wav")
    if os.path.isfile(wav) and os.path.getsize(wav) > 1000:
        return True, "Voice profile"
    return False, "Voice profile"


def _check_assets() -> tuple:
    """Check all three face GIFs are present."""
    base    = os.path.dirname(os.path.abspath(__file__))
    needed  = ["assets/idle.gif", "assets/listening.gif", "assets/speaking.gif"]
    missing = [n for n in needed if not os.path.isfile(os.path.join(base, n))]
    if not missing:
        return True, "Face assets"
    return False, "Face assets"


def _check_llama3() -> tuple:
    """Check llama3 is pulled in Ollama."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if "llama3" in result.stdout:
            return True, "llama3 model"
    except Exception:
        pass
    return False, "llama3 model"


# Ordered list of (label, check_function)
_CHECKS = [
    ("Ollama",        _check_ollama),
    ("Voice profile", _check_voice_profile),
    ("Face assets",   _check_assets),
    ("llama3 model",  _check_llama3),
]

# Labels here are warnings only — ASTRA still boots in degraded mode.
_OPTIONAL = {"Face assets"}


def _run_all_checks() -> dict:
    """
    Runs every check and returns:
      passed   : list of passing label strings
      failed   : list of failing label strings
      critical : True if any non-optional check failed
    """
    passed   = []
    failed   = []
    critical = False

    for label, fn in _CHECKS:
        ok, lbl = fn()
        if ok:
            passed.append(lbl)
            print(f"[Startup] ✓ {lbl}")
        else:
            failed.append(lbl)
            print(f"[Startup] ✗ {lbl}")
            if label not in _OPTIONAL:
                critical = True

    return {"passed": passed, "failed": failed, "critical": critical}


def _build_fail_phrase(names: list) -> str:
    """Turn a list of names into a natural spoken phrase."""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def run_startup_voice(speak_fn, owner: str = "sir") -> bool:
    """
    Run the full spoken startup sequence.

    Parameters
    ----------
    speak_fn : callable
        The speak() function from main.py (pyttsx3-backed).
    owner : str
        Owner name from get_current_owner(), e.g. 'Sowmik'.

    Returns
    -------
    bool
        True  — healthy or degraded (main loop may continue)
        False — critical failure (recommend fixing before use)
    """

    # ── 1. Greeting ──────────────────────────────────────────────────
    period   = _get_period()
    time_str = _get_time_string()
    date_str = _get_date_string()

    speak_fn(f"Welcome back, {owner}. Good {period}. {time_str}.")
    time.sleep(0.25)

    speak_fn(f"Today is {date_str}.")
    time.sleep(0.2)

    # ── 2. Weather ───────────────────────────────────────────────────
    temperature = _get_temperature()
    if temperature:
        speak_fn(f"Current temperature in {WEATHER_CITY} is {temperature}.")
        time.sleep(0.2)

    # ── 3. Health check announcement ─────────────────────────────────
    speak_fn("Let me run a quick self-health check.")
    time.sleep(0.35)

    # ── 4. Run checks ────────────────────────────────────────────────
    result       = _run_all_checks()
    passed_count = len(result["passed"])
    failed_names = result["failed"]
    is_critical  = result["critical"]

    # ── 5. Speak result ──────────────────────────────────────────────
    if not failed_names:
        speak_fn(
            f"All {passed_count} systems are healthy. "
            "Health check passed. ASTRA is online."
        )
        return True

    fail_phrase  = _build_fail_phrase(failed_names)
    failed_count = len(failed_names)
    warn_word    = "warning" if failed_count == 1 else "warnings"

    if is_critical:
        speak_fn(
            f"Health check failed. "
            f"Critical error detected in: {fail_phrase}. "
            "ASTRA is offline. Please resolve these issues and restart."
        )
        return False
    else:
        speak_fn(
            f"Health check completed with {failed_count} {warn_word}. "
            f"Issue detected in: {fail_phrase}. "
            f"{passed_count} systems are healthy. "
            "ASTRA is running in degraded mode."
        )
        return True
