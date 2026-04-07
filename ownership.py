"""
ownership.py — Astra Ownership Transfer System
Only the current owner can transfer ownership.
Transfer requires:
1. Voice command from current owner
2. Current owner speaks transfer phrase
3. Voice verification confirms it's really the owner
4. New owner name is recorded
5. New owner records their voice sample
6. Ownership file updated
7. Astra reboots with new owner profile
"""

import os
import json
import shutil
import wave
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OWNERSHIP_FILE       = "astra_owner.json"
VOICE_PROFILE_DIR    = "voice_profiles"
CURRENT_VOICE_FILE   = "my_voice.wav"
TRANSFER_LOG_FILE    = "astra_transfer_log.json"
VERIFICATION_PHRASE  = "astra transfer confirmed"
NEW_OWNER_RECORD_SEC = 10     # seconds to record new owner voice
SIMILARITY_THRESHOLD = 0.75

# Voice + mic callbacks — injected from main.py
_speak     = None
_listen_fn = None

def set_voice(speak_fn):
    global _speak
    _speak = speak_fn

def set_listener(listen_fn):
    global _listen_fn
    _listen_fn = listen_fn

def say(text: str):
    print(f"[Ownership] {text}")
    if _speak:
        _speak(text)


# ─────────────────────────────────────────────
# OWNER PROFILE
# ─────────────────────────────────────────────

def _load_owner() -> dict:
    """Load current owner profile."""
    if os.path.exists(OWNERSHIP_FILE):
        with open(OWNERSHIP_FILE, "r") as f:
            return json.load(f)
    # Default owner — Sowmik
    return {
        "name":            "Sowmik",
        "voice_file":      CURRENT_VOICE_FILE,
        "since":           datetime.now().isoformat(),
        "transfer_count":  0
    }


def _save_owner(profile: dict):
    """Save owner profile."""
    with open(OWNERSHIP_FILE, "w") as f:
        json.dump(profile, f, indent=2)


def get_current_owner() -> str:
    """Return current owner name."""
    return _load_owner().get("name", "Sowmik")


def get_owner_voice_file() -> str:
    """Return current owner voice profile path."""
    return _load_owner().get("voice_file", CURRENT_VOICE_FILE)


# ─────────────────────────────────────────────
# TRANSFER DETECTION
# Detect transfer command in spoken text
# ─────────────────────────────────────────────

def detect_transfer_command(text: str) -> tuple:
    """
    Detect ownership transfer command in spoken text.
    Patterns:
      "astra pass ownership to Rahul"
      "astra transfer ownership to Priya"
      "astra give your control to Amit"
      "astra change owner to Sara"
      "astra please pass the astra ownership to xxx"

    Returns: (is_transfer_command: bool, new_owner_name: str)
    """
    text_lower = text.lower().strip()

    trigger_phrases = [
        "pass ownership to",
        "transfer ownership to",
        "pass the astra ownership to",
        "transfer astra ownership to",
        "give ownership to",
        "give control to",
        "change owner to",
        "change ownership to",
        "hand over to",
        "pass astra to",
        "transfer to",
        "new owner is",
        "make owner",
    ]

    for phrase in trigger_phrases:
        if phrase in text_lower:
            # Extract new owner name — everything after the trigger phrase
            parts     = text_lower.split(phrase, 1)
            new_owner = parts[1].strip() if len(parts) > 1 else ""

            # Clean up common words
            for word in ["please", "now", "astra", "the", "my", "your"]:
                new_owner = new_owner.replace(word, "").strip()

            # Capitalise properly
            new_owner = new_owner.title().strip()

            if new_owner and len(new_owner) > 1:
                return True, new_owner

    return False, ""


# ─────────────────────────────────────────────
# TRANSFER PIPELINE
# ─────────────────────────────────────────────

def initiate_transfer(new_owner_name: str) -> bool:
    """
    Full ownership transfer pipeline with voice verification.
    Called from main.py when transfer command is detected.
    Returns True if transfer succeeded.
    """
    current_owner = get_current_owner()

    say(f"Ownership transfer requested. "
        f"You want to transfer Astra ownership from {current_owner} "
        f"to {new_owner_name}.")

    say("This is a sensitive operation. "
        "I need to verify your identity before proceeding.")

    # ── Step 1: Current owner voice verification ──
    say(f"Step one. {current_owner}, please say the phrase: "
        f"Astra transfer confirmed.")

    verified = _verify_current_owner_voice()
    if not verified:
        say("Voice verification failed. "
            "I cannot transfer ownership without confirming "
            "it is really you, " + current_owner + ".")
        _log_transfer_attempt(current_owner, new_owner_name, False,
                              "voice verification failed")
        return False

    say("Voice verified. Identity confirmed.")

    # ── Step 2: Explicit spoken confirmation ──
    say(f"Step two. {current_owner}, please confirm by saying: "
        f"Yes I confirm transfer to {new_owner_name}.")

    confirmed = _get_spoken_confirmation(new_owner_name)
    if not confirmed:
        say("Confirmation not received. Transfer cancelled.")
        _log_transfer_attempt(current_owner, new_owner_name, False,
                              "spoken confirmation not received")
        return False

    say("Confirmation received. Proceeding with transfer.")

    # ── Step 3: Record new owner voice ──
    say(f"Step three. {new_owner_name}, please come to the microphone. "
        f"I will record your voice profile now. "
        f"You will have {NEW_OWNER_RECORD_SEC} seconds to speak. "
        f"Say your name and anything you like.")

    time.sleep(2)
    say("Recording starts in three.")
    time.sleep(1)
    say("Two.")
    time.sleep(1)
    say("One. Please speak now.")

    new_voice_file = _record_new_owner_voice(new_owner_name)
    if not new_voice_file:
        say("Voice recording failed. Transfer cancelled.")
        _log_transfer_attempt(current_owner, new_owner_name, False,
                              "new owner voice recording failed")
        return False

    say(f"Voice profile recorded for {new_owner_name}.")

    # ── Step 4: Backup old owner profile ──
    _backup_owner_profile(current_owner)

    # ── Step 5: Save new owner profile ──
    old_profile = _load_owner()
    new_profile = {
        "name":           new_owner_name,
        "voice_file":     new_voice_file,
        "since":          datetime.now().isoformat(),
        "transfer_count": old_profile.get("transfer_count", 0) + 1,
        "previous_owner": current_owner
    }
    _save_owner(new_profile)

    # ── Step 6: Update voice_auth to use new owner's voice ──
    _update_voice_auth(new_voice_file)

    # ── Step 7: Log the transfer ──
    _log_transfer_attempt(current_owner, new_owner_name, True, "success")

    # ── Step 8: Announce and reboot ──
    say(f"Ownership transfer complete. "
        f"Astra now belongs to {new_owner_name}. "
        f"Welcome, {new_owner_name}. I am Astra, your personal AI assistant. "
        f"Thank you {current_owner} for your service as my owner. "
        f"I will now restart to apply the new configuration.")

    time.sleep(3)
    _restart_astra()
    return True


# ─────────────────────────────────────────────
# VOICE VERIFICATION HELPERS
# ─────────────────────────────────────────────

def _verify_current_owner_voice() -> bool:
    """
    Record audio and verify it matches current owner's voice.
    """
    if not _listen_fn:
        print("[Ownership] No listener available — skipping verification")
        return True  # fallback for testing

    try:
        say("Listening for your voice now.")
        audio_bytes = _listen_fn()
        if not audio_bytes:
            return False

        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_bytes)

        try:
            from voice_auth import is_my_voice
            # Temporarily use current owner's voice file
            owner_voice = get_owner_voice_file()
            if not os.path.exists(owner_voice):
                print("[Ownership] Owner voice file not found")
                return False

            # Direct resemblyzer comparison
            from resemblyzer import VoiceEncoder, preprocess_wav
            import numpy as np

            encoder  = VoiceEncoder()
            ref      = encoder.embed_utterance(preprocess_wav(owner_voice))
            candidate = encoder.embed_utterance(preprocess_wav(tmp.name))
            similarity = float(np.dot(ref, candidate))
            print(f"[Ownership] Voice similarity: {similarity:.3f}")
            return similarity >= SIMILARITY_THRESHOLD

        finally:
            os.unlink(tmp.name)

    except Exception as e:
        print(f"[Ownership] Voice verification error: {e}")
        return False


def _get_spoken_confirmation(new_owner_name: str) -> bool:
    """
    Listen for explicit spoken confirmation.
    """
    if not _listen_fn:
        return True  # fallback for testing

    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        say("Listening for confirmation.")

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=8,
                                          phrase_time_limit=6)
                text  = recognizer.recognize_google(audio).lower()
                print(f"[Ownership] Confirmation heard: '{text}'")

                # Check for confirmation keywords
                name_lower    = new_owner_name.lower()
                has_yes       = any(w in text for w in
                                    ["yes", "confirm", "confirmed",
                                     "proceed", "transfer", "i confirm"])
                has_name      = name_lower in text or \
                                name_lower.split()[0] in text

                return has_yes and has_name

            except (sr.WaitTimeoutError, sr.UnknownValueError):
                return False

    except Exception as e:
        print(f"[Ownership] Confirmation error: {e}")
        return False


def _record_new_owner_voice(new_owner_name: str) -> str:
    """
    Record the new owner's voice and save it.
    Returns path to saved WAV file.
    """
    try:
        import sounddevice as sd
        import numpy as np

        sample_rate = 16000
        duration    = NEW_OWNER_RECORD_SEC

        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16"
        )
        sd.wait()

        # Save to voice_profiles directory
        os.makedirs(VOICE_PROFILE_DIR, exist_ok=True)
        safe_name  = new_owner_name.lower().replace(" ", "_")
        voice_file = os.path.join(
            VOICE_PROFILE_DIR,
            f"{safe_name}_voice.wav"
        )

        with wave.open(voice_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(recording.tobytes())

        print(f"[Ownership] New owner voice saved: {voice_file}")
        return voice_file

    except Exception as e:
        print(f"[Ownership] Voice recording error: {e}")
        return None


def _update_voice_auth(new_voice_file: str):
    """
    Update voice_auth.py to use new owner's voice profile.
    Also copy as the default my_voice.wav.
    """
    # Copy new voice as current default
    shutil.copy2(new_voice_file, CURRENT_VOICE_FILE)

    # Reset the cached embedding in voice_auth
    try:
        import voice_auth
        voice_auth._reference_embedding = None
        print("[Ownership] Voice auth cache reset.")
    except Exception as e:
        print(f"[Ownership] Voice auth reset warning: {e}")


def _backup_owner_profile(owner_name: str):
    """Back up current owner's voice and profile."""
    os.makedirs(VOICE_PROFILE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = owner_name.lower().replace(" ", "_")

    # Back up voice file
    if os.path.exists(CURRENT_VOICE_FILE):
        backup_path = os.path.join(
            VOICE_PROFILE_DIR,
            f"{safe_name}_voice_{timestamp}.wav"
        )
        shutil.copy2(CURRENT_VOICE_FILE, backup_path)
        print(f"[Ownership] Backed up {owner_name}'s voice: {backup_path}")

    # Back up ownership file
    if os.path.exists(OWNERSHIP_FILE):
        backup_path = os.path.join(
            VOICE_PROFILE_DIR,
            f"owner_{safe_name}_{timestamp}.json"
        )
        shutil.copy2(OWNERSHIP_FILE, backup_path)


def _restart_astra():
    """Restart the Astra process to apply new ownership."""
    import sys
    import subprocess
    print("[Ownership] Restarting Astra with new owner profile...")
    subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


# ─────────────────────────────────────────────
# TRANSFER LOG
# ─────────────────────────────────────────────

def _log_transfer_attempt(from_owner: str, to_owner: str,
                          success: bool, note: str):
    """Log every transfer attempt."""
    log = []
    if os.path.exists(TRANSFER_LOG_FILE):
        with open(TRANSFER_LOG_FILE, "r") as f:
            log = json.load(f)

    log.append({
        "timestamp":  datetime.now().isoformat(),
        "from":       from_owner,
        "to":         to_owner,
        "success":    success,
        "note":       note
    })

    with open(TRANSFER_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def get_transfer_history() -> str:
    """Return ownership transfer history."""
    if not os.path.exists(TRANSFER_LOG_FILE):
        return "No ownership transfers have been performed."

    with open(TRANSFER_LOG_FILE, "r") as f:
        log = json.load(f)

    if not log:
        return "No transfers recorded."

    lines = [f"Ownership transfer history ({len(log)} records):"]
    for entry in log[-5:]:   # last 5
        status = "success" if entry["success"] else "failed"
        lines.append(
            f"  {entry['timestamp'][:10]} — "
            f"{entry['from']} to {entry['to']}: {status}"
        )
    return "\n".join(lines)


def get_owner_info() -> str:
    """Return current owner information."""
    profile = _load_owner()
    name    = profile.get("name", "Unknown")
    since   = profile.get("since", "")[:10]
    count   = profile.get("transfer_count", 0)
    prev    = profile.get("previous_owner", None)

    info = f"Current owner: {name}, since {since}."
    if count > 0:
        info += f" Ownership has been transferred {count} time(s)."
    if prev:
        info += f" Previous owner was {prev}."
    return info
