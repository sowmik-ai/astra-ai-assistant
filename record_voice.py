"""
record_voice.py — Record Your Voice Profile
Run this script ONCE to create my_voice.wav used by voice_auth.py.

Usage:
    python record_voice.py
"""

import sounddevice as sd
import numpy as np
import wave
import time

SAMPLE_RATE = 16000
CHANNELS = 1
DURATION_SEC = 8
OUTPUT_FILE = "my_voice.wav"


def record_voice():
    print("=" * 50)
    print("  Astra Voice Profile Recorder")
    print("=" * 50)
    print()
    print("This will record 8 seconds of your voice.")
    print("Speak naturally — introduce yourself, count,")
    print("or just talk about anything.")
    print()
    input("Press ENTER when ready, then start speaking...")
    print()

    for i in range(3, 0, -1):
        print(f"  Starting in {i}...")
        time.sleep(1)

    print("🎤 RECORDING — speak now!")
    print()

    audio = sd.rec(
        int(DURATION_SEC * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16"
    )
    sd.wait()

    print("✅ Done recording!")
    print()

    # Save to WAV
    with wave.open(OUTPUT_FILE, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)          # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    print(f"Saved to: {OUTPUT_FILE}")
    print()
    print("You can now run: python main.py")
    print()
    print("TIP: To calibrate the similarity threshold, record another sample")
    print("     and run: python voice_auth.py calibrate <other_sample.wav>")


if __name__ == "__main__":
    record_voice()
