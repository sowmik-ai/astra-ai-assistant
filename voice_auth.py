"""
voice_auth.py — Speaker Verification
Uses resemblyzer to compare incoming audio against a stored voice profile.
Only the registered user (whose voice is in my_voice.wav) can control Astra.
"""

import os
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
VOICE_PROFILE_PATH = "my_voice.wav"     # Your 5-10 sec voice sample
DEFAULT_THRESHOLD = 0.75                # Cosine similarity threshold
                                        # Raise to 0.85 for stricter matching
                                        # Lower to 0.65 if getting false rejects


# ─────────────────────────────────────────────
# LOAD ENCODER AND REFERENCE EMBEDDING
# ─────────────────────────────────────────────
_encoder = VoiceEncoder()
_reference_embedding = None


def _load_reference():
    """Load the reference voice embedding from disk (once on first call)."""
    global _reference_embedding
    if _reference_embedding is not None:
        return  # Already loaded

    if not os.path.exists(VOICE_PROFILE_PATH):
        raise FileNotFoundError(
            f"Voice profile not found at '{VOICE_PROFILE_PATH}'.\n"
            "Record 5-10 seconds of your voice and save it as my_voice.wav\n"
            "in the project root directory."
        )

    wav = preprocess_wav(Path(VOICE_PROFILE_PATH))
    _reference_embedding = _encoder.embed_utterance(wav)
    print(f"[VoiceAuth] Loaded voice profile from '{VOICE_PROFILE_PATH}'")


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def is_my_voice(audio_path: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """
    Check whether the audio file matches the registered user's voice.

    Args:
        audio_path: Path to a .wav file to verify.
        threshold:  Minimum cosine similarity to accept (0.0 – 1.0).

    Returns:
        True if the voice matches, False otherwise.
    """
    _load_reference()

    try:
        wav = preprocess_wav(Path(audio_path))
        candidate_embedding = _encoder.embed_utterance(wav)
        similarity = float(np.dot(_reference_embedding, candidate_embedding))
        print(f"[VoiceAuth] Similarity: {similarity:.3f} (threshold: {threshold})")
        return similarity >= threshold
    except Exception as e:
        print(f"[VoiceAuth] Error during verification: {e}")
        return False


def get_similarity(audio_path: str) -> float:
    """
    Return the raw similarity score without making a pass/fail decision.
    Useful for calibrating your threshold.
    """
    _load_reference()
    wav = preprocess_wav(Path(audio_path))
    candidate_embedding = _encoder.embed_utterance(wav)
    return float(np.dot(_reference_embedding, candidate_embedding))


# ─────────────────────────────────────────────
# CALIBRATION TOOL
# ─────────────────────────────────────────────

def calibrate(test_wav_path: str):
    """
    Print the similarity score for a test recording.
    Use this to find a good threshold for your voice.

    Usage:
        python voice_auth.py calibrate test.wav
    """
    score = get_similarity(test_wav_path)
    print(f"\n=== Voice Auth Calibration ===")
    print(f"Reference:  {VOICE_PROFILE_PATH}")
    print(f"Test file:  {test_wav_path}")
    print(f"Similarity: {score:.4f}")
    print()
    if score >= 0.85:
        print("✅ Very strong match — you can use threshold=0.85")
    elif score >= 0.75:
        print("✅ Good match — default threshold=0.75 works well")
    elif score >= 0.65:
        print("⚠️  Weak match — lower threshold to 0.65 or re-record voice profile")
    else:
        print("❌ Poor match — re-record my_voice.wav in a quiet environment")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "calibrate":
        calibrate(sys.argv[2])
    else:
        print("Usage: python voice_auth.py calibrate <test_audio.wav>")
