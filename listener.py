"""
listener.py — Microphone Audio Capture
Records audio after wake word is detected.
Uses RMS-based silence detection to know when user has finished speaking.
Returns raw int16 PCM bytes at 16kHz mono.
"""

import sounddevice as sd
import numpy as np
import queue

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SAMPLE_RATE        = 16000   # Hz — matches Whisper input
CHANNELS           = 1       # mono
DTYPE              = "int16"
BLOCKSIZE          = 4000    # samples per callback chunk (~250ms)

MIN_DURATION_SEC   = 1.0     # always record at least this long
MAX_DURATION_SEC   = 10.0    # hard cutoff
SILENCE_THRESHOLD  = 350     # RMS below this = silence (tune for your mic)
SILENCE_DURATION   = 1.2     # seconds of silence before stopping


def listen_audio() -> bytes:
    """
    Record from microphone until the user stops speaking.
    Returns raw int16 PCM bytes at 16kHz mono.
    """
    audio_queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        audio_queue.put(indata.copy())

    chunks         = []
    silence_chunks = 0
    max_silence    = int(SILENCE_DURATION * SAMPLE_RATE / BLOCKSIZE)
    min_chunks     = int(MIN_DURATION_SEC * SAMPLE_RATE / BLOCKSIZE)
    max_chunks     = int(MAX_DURATION_SEC * SAMPLE_RATE / BLOCKSIZE)

    print("[Listener] Recording command...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=BLOCKSIZE,
        callback=callback
    ):
        while len(chunks) < max_chunks:
            try:
                chunk = audio_queue.get(timeout=3.0)
            except queue.Empty:
                break

            chunks.append(chunk)
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

            if len(chunks) >= min_chunks:
                if rms < SILENCE_THRESHOLD:
                    silence_chunks += 1
                    if silence_chunks >= max_silence:
                        break
                else:
                    silence_chunks = 0

    duration = len(chunks) * BLOCKSIZE / SAMPLE_RATE
    print(f"[Listener] Captured {duration:.1f}s of audio")

    if not chunks:
        return b""

    return np.concatenate(chunks, axis=0).tobytes()


if __name__ == "__main__":
    import wave, tempfile, os
    print("Say something...")
    audio = listen_audio()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio)
    print(f"Saved to {tmp.name} ({len(audio)} bytes)")
