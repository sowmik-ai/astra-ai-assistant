"""
main.py — Astra entry point
Wake word: SpeechRecognition (no API key needed)
STT:       faster-whisper (local, offline)
TTS:       pyttsx3 Microsoft Zira (offline, free)
Agent:     ReAct loop with tools
UI:        Tkinter animated GIF face
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
from agent import agent_loop
from voice_auth import is_my_voice
from ui import AstraUI

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
WAKE_WORD            = "astra"    # word to listen for
WHISPER_MODEL        = "tiny"     # tiny | base | small | medium
SIMILARITY_THRESHOLD = 0.75       # voice auth sensitivity
TTS_RATE             = 165        # speech speed
TTS_VOICE_INDEX      = 1          # 0=David (male) 1=Zira (female)

# ─────────────────────────────────────────────
# INITIALISE TTS — Microsoft Zira (offline)
# ─────────────────────────────────────────────
_tts = pyttsx3.init()
_tts.setProperty('rate', TTS_RATE)
_tts.setProperty('volume', 1.0)
_voices = _tts.getProperty('voices')
if len(_voices) > TTS_VOICE_INDEX:
    _tts.setProperty('voice', _voices[TTS_VOICE_INDEX].id)
    print(f"[TTS] Voice: {_voices[TTS_VOICE_INDEX].name}")


def speak(text: str):
    """Speak text via pyttsx3 (offline, free)."""
    try:
        print(f"[Astra] Speaking: {text}")
        _tts.say(text)
        _tts.runAndWait()
    except Exception as e:
        print(f"[TTS ERROR] {e}")


# ─────────────────────────────────────────────
# INITIALISE WAKE WORD — SpeechRecognition
# ─────────────────────────────────────────────
_recognizer = sr.Recognizer()
_recognizer.energy_threshold    = 300   # mic sensitivity
_recognizer.dynamic_energy_threshold = True
_recognizer.pause_threshold     = 0.6


def listen_for_wake_word() -> bool:
    """
    Listen passively for the wake word 'Astra'.
    Returns True when detected, False on timeout/error.
    Uses Google free speech API for wake word only.
    """
    with sr.Microphone() as source:
        _recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = _recognizer.listen(source, timeout=5, phrase_time_limit=4)
            text = _recognizer.recognize_google(audio).lower()
            print(f"[WakeWord] Heard: '{text}'")
            return WAKE_WORD in text
        except sr.WaitTimeoutError:
            return False
        except sr.UnknownValueError:
            return False
        except sr.RequestError as e:
            print(f"[WakeWord] Google API error: {e}")
            return False


# ─────────────────────────────────────────────
# INITIALISE STT — Faster Whisper (offline)
# ─────────────────────────────────────────────
print("[Astra] Loading Whisper model...")
whisper = WhisperModel(WHISPER_MODEL, compute_type="int8")
print("[Astra] Whisper ready.")

# ─────────────────────────────────────────────
# INITIALISE UI
# ─────────────────────────────────────────────
ui = AstraUI()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def save_audio_to_tempfile(audio_bytes: bytes) -> str:
    """Save raw PCM bytes to a temp WAV file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_bytes)
    return tmp.name


def transcribe(audio_bytes: bytes) -> str:
    """Convert raw PCM bytes to text via Whisper."""
    wav_path = save_audio_to_tempfile(audio_bytes)
    try:
        segments, _ = whisper.transcribe(wav_path)
        return " ".join([s.text for s in segments]).strip()
    finally:
        os.unlink(wav_path)


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def astra_loop():
    print(f"[Astra] Listening for wake word: '{WAKE_WORD}'")
    print("[Astra] Make sure microphone is connected and say 'Astra'")

    while True:
        try:
            # ── Step 1: Wait for wake word ──
            detected = listen_for_wake_word()
            if not detected:
                continue

            print("[Astra] Wake word detected!")
            ui.set_face("listening")
            speak("Yes Sowmik, how can I help you?")

            # ── Step 2: Capture command ──
            audio_bytes = listen_audio()
            if not audio_bytes:
                speak("Sorry, I didn't catch that.")
                ui.set_face("idle")
                continue

            # ── Step 3: Transcribe with Whisper ──
            text = transcribe(audio_bytes)
            if not text:
                speak("Sorry, I didn't catch that.")
                ui.set_face("idle")
                continue

            print(f"[Astra] Heard: {text}")

            # ── Step 4: Check stop command ──
            if "stop astra" in text.lower() or "stop" == text.lower().strip():
                speak("Stopping. Goodbye.")
                ui.set_face("idle")
                continue

            # ── Step 5: Voice authentication ──
            wav_path = save_audio_to_tempfile(audio_bytes)
            try:
                if not is_my_voice(wav_path, threshold=SIMILARITY_THRESHOLD):
                    print("[Astra] Voice not recognised.")
                    ui.set_face("idle")
                    continue
            finally:
                os.unlink(wav_path)

            # ── Step 6: Run agent ──
            ui.set_text(f"You: {text}")
            ui.set_face("idle")
            print("[Astra] Thinking...")

            response = agent_loop(text)

            # ── Step 7: Respond ──
            print(f"[Astra] Response: {response}")
            ui.set_face("speaking")
            ui.set_text(f"Astra: {response}")
            speak(response)
            ui.set_face("idle")
            ui.set_text("")

        except KeyboardInterrupt:
            print("\n[Astra] Shutting down.")
            break
        except Exception as e:
            print(f"[Astra] Error: {e}")
            ui.set_face("idle")
            time.sleep(1)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    speak("Astra is online. Say Astra to wake me.")
    thread = threading.Thread(target=astra_loop, daemon=True)
    thread.start()
    ui.run()
