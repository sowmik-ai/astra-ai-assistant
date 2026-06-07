"""
main.py — Astra Entry Point
============================
Full autonomous AI assistant with:
  - Wake word detection (SpeechRecognition)
  - Voice-only MFA (identity + PIN + optional passphrase)
  - Ownership transfer system
  - Keyword intent routing with suggestions
  - ReAct agent loop with self-learning
  - Self-repair on errors
  - Live dashboard + reminder scheduler
  - Animated face UI (Tkinter)
"""

import threading
import tempfile
import wave
import os
import time
import traceback
import pyttsx3
import speech_recognition as sr
from faster_whisper import WhisperModel
from listener  import listen_audio
from ui        import AstraUI

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
WAKE_WORD       = "astra"
WHISPER_MODEL   = "tiny"    # tiny | base | small | medium
TTS_RATE        = 165       # speech speed
TTS_VOICE_INDEX = 1         # 0=David (male)  1=Zira (female)


# ─────────────────────────────────────────────
# STEP 1 — TTS (must be first — other modules use it)
# ─────────────────────────────────────────────
_tts = pyttsx3.init()
_tts.setProperty("rate", TTS_RATE)
_tts.setProperty("volume", 1.0)
_voices = _tts.getProperty("voices")
if len(_voices) > TTS_VOICE_INDEX:
    _tts.setProperty("voice", _voices[TTS_VOICE_INDEX].id)
    print(f"[TTS] Voice: {_voices[TTS_VOICE_INDEX].name}")


def speak(text: str):
    """Speak text via pyttsx3 Zira — safe to call from any thread."""
    try:
        print(f"[Astra] {text}")
        _tts.say(text)
        _tts.runAndWait()
    except Exception as e:
        print(f"[TTS ERROR] {e}")


# ─────────────────────────────────────────────
# STEP 2 — Import and wire all modules with speak()
# ─────────────────────────────────────────────
import agent        as _agent_mod
import self_improve as _si_mod
import self_learn   as _sl_mod
import self_repair  as _sr_mod
import ownership    as _own_mod
import auth         as _auth_mod

_agent_mod.set_voice(speak)
_si_mod.set_voice(speak)
_sl_mod.set_voice(speak)
_sr_mod.set_voice(speak)
_own_mod.set_voice(speak)
_auth_mod.set_voice(speak)

# Wire listener (for ownership transfer + auth MFA recording)
_own_mod.set_listener(listen_audio)
_auth_mod.set_listener(listen_audio)

# Now safe to import their functions
from agent      import agent_loop
from ownership  import (detect_transfer_command, initiate_transfer,
                        get_current_owner)
from auth       import (authenticate, is_session_valid,
                        get_auth_status, end_session,
                        run_setup_wizard, is_locked_out)
from intent     import route, execute, KEYWORD_COMMANDS
from self_improve import process_verbal_feedback


# ─────────────────────────────────────────────
# STEP 3 — Wake word listener
# ─────────────────────────────────────────────
_recognizer = sr.Recognizer()
_recognizer.energy_threshold         = 300
_recognizer.dynamic_energy_threshold = True
_recognizer.pause_threshold          = 0.6


def listen_for_wake_word() -> bool:
    """Listen passively for 'astra'. Returns True when heard."""
    with sr.Microphone() as source:
        _recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = _recognizer.listen(
                source, timeout=5, phrase_time_limit=4
            )
            text = _recognizer.recognize_google(audio).lower()
            print(f"[WakeWord] Heard: '{text}'")
            return WAKE_WORD in text
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return False
        except sr.RequestError as e:
            print(f"[WakeWord] API error: {e}")
            return False


# ─────────────────────────────────────────────
# STEP 4 — STT (Whisper)
# ─────────────────────────────────────────────
print("[Astra] Loading Whisper model...")
_whisper = WhisperModel(WHISPER_MODEL, compute_type="int8")
print("[Astra] Whisper ready.")


def _save_wav(audio_bytes: bytes) -> str:
    """Save raw PCM bytes as WAV. Returns temp file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_bytes)
    return tmp.name


def transcribe(audio_bytes: bytes) -> str:
    """Convert raw PCM audio to text via Whisper."""
    wav = _save_wav(audio_bytes)
    try:
        segs, _ = _whisper.transcribe(wav)
        return " ".join(s.text for s in segs).strip()
    finally:
        os.unlink(wav)


# ─────────────────────────────────────────────
# STEP 5 — UI + Dashboard + Scheduler
# ─────────────────────────────────────────────
ui        = AstraUI()

def handle_typed_input(text: str):
    """Called when user types a message and presses Enter or Send."""
    if not text.strip():
        return
    try:
        from intent import route, execute
        command_id, extras = route(text)

        if command_id == "suggestion":
            response = extras.get("message", "")
        elif command_id == "stop_astra":
            response = "Stopping now. Goodbye Sowmik!"
        elif command_id and command_id != "general":
            response = execute(command_id, text, extras)
        else:
            ui.set_face("idle")
            response = agent_loop(text)

        if response:
            ui.set_face("speaking")
            ui.add_chat_bubble("astra", response)
            speak(response)
            ui.set_face("idle")
    except Exception as e:
        ui.add_chat_bubble("astra", f"Error: {e}")
        ui.set_face("idle")

ui.set_text_callback(handle_typed_input)

# ── File / Image attachment handler ──
def handle_file_input(file_path: str, question: str = ""):
    """
    Called when user attaches a file via the 📎 button.
    Analyses the file using llama3 and responds in chat.
    Supports: images, PDF, DOCX, XLSX, CSV, JSON,
              code files, text files, ZIP archives.
    """
    import os
    from file_analyzer import analyze_file, get_file_icon

    filename = os.path.basename(file_path)
    icon     = get_file_icon(file_path)

    ui.set_face("idle")
    ui.add_chat_bubble(
        "astra",
        f"Analysing {icon} {filename}... please wait."
    )

    try:
        speak(f"Analysing {filename}. Please wait.")
        response = analyze_file(file_path, question)

        ui.set_face("speaking")
        ui.add_chat_bubble("astra", response)
        speak(response[:300])   # speak first 300 chars
        ui.set_face("idle")

        # Save to memory
        from rag import add_to_memory
        add_to_memory(
            f"Analysed file '{filename}': {response[:300]}",
            metadata={"type": "file_analysis", "file": filename}
        )

    except Exception as e:
        error_msg = f"Could not analyse {filename}: {e}"
        ui.add_chat_bubble("astra", error_msg)
        ui.set_face("idle")

ui.set_file_callback(handle_file_input)

# Dashboard — optional, skip if fails
try:
    from dashboard import AstraDashboard
    dashboard = AstraDashboard()
    _has_dashboard = True
except Exception as e:
    print(f"[Dashboard] Could not start: {e}")
    dashboard       = None
    _has_dashboard  = False

# Scheduler
from scheduler import start_scheduler, set_ui as _sched_set_ui
_sched_set_ui(ui)


# ─────────────────────────────────────────────
# CONFIRMATION STATE
# For commands that need "yes confirm" follow-up
# ─────────────────────────────────────────────
_pending_confirm_action = None

def _set_pending_confirmation(action: str):
    global _pending_confirm_action
    _pending_confirm_action = action

def _check_confirmation(text: str) -> tuple:
    """
    If a confirmation is pending and user says yes → execute it.
    Returns (handled: bool, response: str)
    """
    global _pending_confirm_action
    if not _pending_confirm_action:
        return False, ""

    t = text.lower()
    if any(w in t for w in ["yes", "confirm", "proceed", "do it"]):
        action = _pending_confirm_action
        _pending_confirm_action = None
        if action == "clear_memory":
            from rag import clear_memory
            clear_memory()
            return True, "All memories cleared."
        return True, f"Confirmed: {action}"

    if any(w in t for w in ["no", "cancel", "abort", "never mind"]):
        _pending_confirm_action = None
        return True, "Cancelled."

    return False, ""


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
_last_query    = ""
_last_response = ""


def astra_loop():
    global _last_query, _last_response

    owner = get_current_owner()
    print(f"[Astra] Owner: {owner}")
    print(f"[Astra] Listening for wake word: '{WAKE_WORD}'")

    while True:
        try:

            # ══════════════════════════════════════
            # STEP A — Wait for wake word
            # ══════════════════════════════════════
            if not listen_for_wake_word():
                continue

            owner = get_current_owner()
            print("[Astra] Wake word detected!")
            ui.set_face("listening")
            speak(f"Yes {owner}?")

            # ══════════════════════════════════════
            # STEP B — Record command audio
            # ══════════════════════════════════════
            audio_bytes = listen_audio()
            if not audio_bytes:
                speak(f"Sorry {owner}, I didn't catch that.")
                ui.set_face("idle")
                continue

            # ══════════════════════════════════════
            # STEP C — Transcribe to text
            # ══════════════════════════════════════
            text = transcribe(audio_bytes)
            if not text:
                speak(f"Sorry {owner}, could you repeat that?")
                ui.set_face("idle")
                continue

            print(f"[Astra] Heard: '{text}'")
            ui.add_chat_bubble("user", text)

            # ══════════════════════════════════════
            # STEP D — Hard stop command
            # ══════════════════════════════════════
            if any(p in text.lower() for p in
                   ["stop astra", "shutdown astra",
                    "goodbye astra", "turn off astra"]):
                speak(f"Stopping. Goodbye {owner}!")
                ui.set_face("idle")
                break

            # ══════════════════════════════════════
            # STEP E — Ownership transfer
            # Checked BEFORE auth so current owner can transfer
            # ══════════════════════════════════════
            is_transfer, new_owner = detect_transfer_command(text)
            if is_transfer:
                ui.set_face("listening")
                speak(f"Ownership transfer to {new_owner} "
                      f"requested. Starting verification.")
                threading.Thread(
                    target=_run_transfer,
                    args=(new_owner,),
                    daemon=True
                ).start()
                continue

            # ══════════════════════════════════════
            # STEP F — Pending confirmation check
            # e.g. "yes confirm" after "clear memory"
            # ══════════════════════════════════════
            handled, conf_resp = _check_confirmation(text)
            if handled:
                if conf_resp:
                    ui.set_face("speaking")
                    ui.set_text(f"Astra: {conf_resp}")
                    speak(conf_resp)
                    ui.set_face("idle")
                    ui.set_text("")
                continue

            # ══════════════════════════════════════
            # STEP G — Intent keyword matching
            # If keywords match → execute directly
            # If partial match → suggest missing keyword
            # If no match → falls through to MFA + agent
            # ══════════════════════════════════════
            command_id, extras = route(text)

            if command_id == "suggestion":
                # Partial keyword match — tell user what's missing
                msg = extras.get("message", "")
                if msg:
                    ui.set_face("speaking")
                    ui.set_text(f"Astra: {msg}")
                    speak(msg)
                    ui.set_face("idle")
                    ui.set_text("")
                continue

            if command_id:
                # Full keyword match — execute the command
                ui.set_face("idle")
                response = execute(command_id, text, extras)

                if response == "STOP_SIGNAL":
                    speak(f"Stopping. Goodbye {owner}!")
                    break

                if response and response.startswith(
                        "AWAITING_CONFIRMATION:"):
                    action = response.split(":", 1)[1]
                    _set_pending_confirmation(action)
                    speak("Are you sure? "
                          "Say yes confirm to proceed, "
                          "or no to cancel.")
                    ui.set_face("idle")
                    continue

                if response:
                    ui.set_face("speaking")
                    ui.set_text(f"Astra: {response}")
                    speak(response)
                    ui.set_face("idle")
                    ui.set_text("")
                continue

            # ══════════════════════════════════════
            # STEP H — Verbal feedback on last response
            # e.g. "that's wrong, the answer is X"
            # ══════════════════════════════════════
            if _last_query and _last_response:
                feedback = process_verbal_feedback(
                    text, _last_query, _last_response
                )
                if feedback:
                    ui.set_face("speaking")
                    ui.set_text(f"Astra: {feedback}")
                    speak(feedback)
                    ui.set_face("idle")
                    _last_query    = ""
                    _last_response = ""
                    continue

            # ══════════════════════════════════════
            # STEP I — Voice MFA Authentication
            # Required before agent handles any task.
            # Factors checked sequentially:
            #   1. voice_identity  (always first)
            #   2. voice_pin       (speak your PIN)
            #   3. voice_passphrase (if enabled)
            # Session valid for 30 min after success.
            # ══════════════════════════════════════

            # Skip auth if session is still valid
            if not is_session_valid():
                speak(f"Please authenticate, {owner}.")
                auth_ok, auth_msg = authenticate(
                    audio_bytes=audio_bytes,
                    spoken_text=text
                )

                if not auth_ok:
                    locked, remaining = is_locked_out()
                    if locked:
                        mins = remaining // 60
                        secs = remaining % 60
                        ui.set_face("idle")
                        ui.set_text(
                            f"Locked {mins}m {secs}s remaining"
                        )
                        time.sleep(3)
                        ui.set_text("")
                    else:
                        ui.set_face("idle")
                        ui.set_text(f"Auth failed: {auth_msg}")
                        speak(auth_msg)
                        time.sleep(2)
                        ui.set_text("")
                    continue

            # ══════════════════════════════════════
            # STEP J — Agent loop (AI answers)
            # llama3 reasons, uses tools, speaks answer
            # "agent loop" = Astra answers your question
            # ══════════════════════════════════════
            ui.set_face("idle")

            try:
                response = agent_loop(text)
            except Exception as e:
                tb = traceback.format_exc()
                speak("I encountered an error. Let me repair myself.")
                from self_repair import diagnose_and_repair
                repaired = diagnose_and_repair({
                    "function":  "agent_loop",
                    "error":     str(e),
                    "traceback": tb
                })
                response = (
                    "I repaired the error. "
                    "Please try your question again."
                    if repaired else
                    "Could not repair. Please restart me."
                )

            # ══════════════════════════════════════
            # STEP K — Speak and display response
            # ══════════════════════════════════════
            _last_query    = text
            _last_response = response

            ui.set_face("speaking")
            ui.add_chat_bubble("astra", response)
            speak(response)
            ui.set_face("idle")

            if _has_dashboard and dashboard:
                dashboard.update_last_interaction(text, response)

        except KeyboardInterrupt:
            speak(f"Shutting down. Goodbye {get_current_owner()}!")
            break
        except Exception as e:
            print(f"[Astra] Unexpected error: {e}")
            traceback.print_exc()
            ui.set_face("idle")
            time.sleep(1)


def _run_transfer(new_owner: str):
    """Run ownership transfer pipeline (in background thread)."""
    ui.set_face("listening")
    success = initiate_transfer(new_owner)
    if not success:
        ui.set_face("idle")
        ui.set_text("")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    owner = get_current_owner()

    # ── Spoken startup: greeting + live date/time + weather + health check ──
    from startup_voice import run_startup_voice
    astra_healthy = run_startup_voice(speak, owner=owner)

    # If critical failure, warn but attempt to continue anyway
    if not astra_healthy:
        speak("Attempting to continue in safe mode. "
              "Some features may not work correctly.")

    # ── First-time MFA setup ──
    from auth import _load_config
    auth_cfg = _load_config()
    if not auth_cfg.get("setup_complete"):
        speak("First time setup. I will configure your "
              "voice multi-factor authentication now.")
        time.sleep(1)
        result = run_setup_wizard()
        speak(result)
    else:
        active = auth_cfg.get("factors", [])
        speak(f"Voice M F A active with "
              f"{len(active)} factor authentication.")

    # ── Start background scheduler ──
    start_scheduler()

    # ── Final ready prompt ──
    if astra_healthy:
        speak("Say Astra to wake me.")

    # ── Start main loop in background thread ──
    threading.Thread(target=astra_loop, daemon=True).start()

    # ── Tkinter must run on main thread ──
    ui.run()
