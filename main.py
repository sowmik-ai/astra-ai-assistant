"""
main.py — Astra entry point
Full autonomous AI with ownership transfer system.
Only the registered owner can control Astra or transfer ownership.
"""

import threading
import tempfile
import wave
import os
import time
import pyttsx3
import speech_recognition as sr
from faster_whisper import WhisperModel
from listener import listen_audio
from voice_auth import is_my_voice
from ui import AstraUI

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
WAKE_WORD            = "astra"
WHISPER_MODEL        = "tiny"
SIMILARITY_THRESHOLD = 0.75
TTS_RATE             = 165
TTS_VOICE_INDEX      = 1

# ─────────────────────────────────────────────
# INITIALISE TTS — must be first
# ─────────────────────────────────────────────
_tts = pyttsx3.init()
_tts.setProperty('rate', TTS_RATE)
_tts.setProperty('volume', 1.0)
_voices = _tts.getProperty('voices')
if len(_voices) > TTS_VOICE_INDEX:
    _tts.setProperty('voice', _voices[TTS_VOICE_INDEX].id)
    print(f"[TTS] Voice: {_voices[TTS_VOICE_INDEX].name}")


def speak(text: str):
    try:
        print(f"[Astra] {text}")
        _tts.say(text)
        _tts.runAndWait()
    except Exception as e:
        print(f"[TTS ERROR] {e}")


# ─────────────────────────────────────────────
# WIRE VOICE INTO ALL MODULES
# ─────────────────────────────────────────────
import agent          as _agent_mod
import self_improve   as _si_mod
import self_learn     as _sl_mod
import self_repair    as _sr_mod
import voice_commands as _vc_mod
import ownership      as _own_mod

_agent_mod.set_voice(speak)
_si_mod.set_voice(speak)
_sl_mod.set_voice(speak)
_sr_mod.set_voice(speak)
_vc_mod.set_voice(speak)
_own_mod.set_voice(speak)

# Wire listener into ownership module
_own_mod.set_listener(listen_audio)

from agent          import agent_loop
from ownership      import (
    detect_transfer_command,
    initiate_transfer,
    get_current_owner,
    get_owner_voice_file,
    get_owner_info
)
from voice_commands import (
    process_command,
    check_confirmation,
    set_pending_confirmation
)
from self_improve   import process_verbal_feedback

# ─────────────────────────────────────────────
# INITIALISE WAKE WORD
# ─────────────────────────────────────────────
_recognizer = sr.Recognizer()
_recognizer.energy_threshold         = 300
_recognizer.dynamic_energy_threshold = True
_recognizer.pause_threshold          = 0.6


def listen_for_wake_word() -> bool:
    with sr.Microphone() as source:
        _recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = _recognizer.listen(source, timeout=5,
                                       phrase_time_limit=4)
            text  = _recognizer.recognize_google(audio).lower()
            print(f"[WakeWord] Heard: '{text}'")
            return WAKE_WORD in text
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return False
        except sr.RequestError as e:
            print(f"[WakeWord] Error: {e}")
            return False


# ─────────────────────────────────────────────
# INITIALISE STT + UI
# ─────────────────────────────────────────────
print("[Astra] Loading Whisper model...")
whisper = WhisperModel(WHISPER_MODEL, compute_type="int8")
print("[Astra] Whisper ready.")
ui = AstraUI()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def save_audio_to_tempfile(audio_bytes: bytes) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_bytes)
    return tmp.name


def transcribe(audio_bytes: bytes) -> str:
    wav_path = save_audio_to_tempfile(audio_bytes)
    try:
        segments, _ = whisper.transcribe(wav_path)
        return " ".join([s.text for s in segments]).strip()
    finally:
        os.unlink(wav_path)


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
last_query    = ""
last_response = ""


def astra_loop():
    global last_query, last_response

    owner = get_current_owner()
    print(f"[Astra] Owner: {owner}. Say '{WAKE_WORD}' to activate.")

    while True:
        try:
            # ── Step 1: Wake word ──
            if not listen_for_wake_word():
                continue

            owner = get_current_owner()
            print("[Astra] Wake word detected!")
            ui.set_face("listening")
            speak(f"Yes {owner}, how can I help you?")

            # ── Step 2: Capture command ──
            audio_bytes = listen_audio()
            if not audio_bytes:
                speak(f"Sorry {owner}, I didn't catch that.")
                ui.set_face("idle")
                continue

            # ── Step 3: Transcribe ──
            text = transcribe(audio_bytes)
            if not text:
                speak(f"Sorry {owner}, could you repeat that?")
                ui.set_face("idle")
                continue

            print(f"[Astra] Heard: '{text}'")
            ui.set_text(f"You: {text}")

            # ── Step 4: Check stop command ──
            if any(w in text.lower() for w in
                   ["stop astra", "goodbye astra", "shut down"]):
                speak(f"Stopping now. Goodbye {owner}!")
                ui.set_face("idle")
                break

            # ── Step 5: OWNERSHIP TRANSFER CHECK ──
            # Must happen BEFORE voice auth so owner can initiate
            is_transfer, new_owner = detect_transfer_command(text)
            if is_transfer:
                ui.set_face("listening")
                speak(f"Ownership transfer to {new_owner} requested. "
                      f"Starting verification process.")

                # Run transfer in thread so UI stays responsive
                transfer_thread = threading.Thread(
                    target=_handle_transfer,
                    args=(new_owner,),
                    daemon=True
                )
                transfer_thread.start()
                continue

            # ── Step 6: Check pending confirmation ──
            confirmed, conf_response = check_confirmation(text)
            if confirmed:
                ui.set_face("speaking")
                speak(conf_response)
                ui.set_text(f"Astra: {conf_response}")
                ui.set_face("idle")
                ui.set_text("")
                continue

            # ── Step 7: Voice commands ──
            handled, cmd_response = process_command(text)
            if handled:
                if cmd_response == "STOP_SIGNAL":
                    speak(f"Stopping now. Goodbye {owner}!")
                    break
                if cmd_response and cmd_response.startswith(
                        "AWAITING_CONFIRMATION:"):
                    action = cmd_response.split(":", 1)[1]
                    set_pending_confirmation(action)
                    ui.set_face("idle")
                    continue
                if cmd_response:
                    ui.set_face("speaking")
                    ui.set_text(f"Astra: {cmd_response}")
                    speak(cmd_response)
                    ui.set_face("idle")
                    ui.set_text("")
                continue

            # ── Step 8: Verbal feedback ──
            if last_query and last_response:
                feedback = process_verbal_feedback(
                    text, last_query, last_response
                )
                if feedback:
                    ui.set_face("speaking")
                    ui.set_text(f"Astra: {feedback}")
                    speak(feedback)
                    ui.set_face("idle")
                    last_query    = ""
                    last_response = ""
                    continue

            # ── Step 9: Voice authentication ──
            # Uses the CURRENT OWNER's voice file dynamically
            owner_voice = get_owner_voice_file()
            wav_path    = save_audio_to_tempfile(audio_bytes)
            try:
                from resemblyzer import VoiceEncoder, preprocess_wav
                import numpy as np
                encoder    = VoiceEncoder()
                ref        = encoder.embed_utterance(
                    preprocess_wav(owner_voice)
                )
                candidate  = encoder.embed_utterance(
                    preprocess_wav(wav_path)
                )
                similarity = float(np.dot(ref, candidate))
                print(f"[Auth] Similarity: {similarity:.3f}")
                if similarity < SIMILARITY_THRESHOLD:
                    print("[Astra] Voice not recognised.")
                    speak(f"Sorry, I only respond to {owner}.")
                    ui.set_face("idle")
                    continue
            finally:
                os.unlink(wav_path)

            # ── Step 10: Run agent ──
            ui.set_face("idle")
            try:
                response = agent_loop(text)
            except Exception as e:
                tb = __import__('traceback').format_exc()
                speak("I encountered an error. Repairing myself.")
                from self_repair import diagnose_and_repair
                repaired = diagnose_and_repair({
                    "function":  "agent_loop",
                    "error":     str(e),
                    "traceback": tb
                })
                response = (
                    "Repaired. Please try again."
                    if repaired else
                    "Could not repair. Please restart me."
                )

            # ── Step 11: Respond ──
            last_query    = text
            last_response = response
            ui.set_face("speaking")
            ui.set_text(f"Astra: {response}")
            speak(response)
            ui.set_face("idle")
            ui.set_text("")

        except KeyboardInterrupt:
            speak(f"Shutting down. Goodbye {get_current_owner()}!")
            break
        except Exception as e:
            print(f"[Astra] Error: {e}")
            ui.set_face("idle")
            time.sleep(1)


def _handle_transfer(new_owner_name: str):
    """Run transfer pipeline and update UI."""
    ui.set_face("listening")
    success = initiate_transfer(new_owner_name)
    if not success:
        ui.set_face("idle")
        ui.set_text("")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    owner = get_current_owner()

    speak(f"Astra is initialising. Running startup checks.")
    from self_repair import run_health_check
    report = run_health_check()
    if report["errors"]:
        speak(f"Warning. Found {len(report['errors'])} errors. "
              f"Attempting repairs.")
    else:
        speak(f"All {len(report['healthy'])} systems healthy.")

    speak(f"Astra is online. I am ready for you, {owner}. "
          f"Say Astra to wake me.")

    thread = threading.Thread(target=astra_loop, daemon=True)
    thread.start()
    ui.run()
    
