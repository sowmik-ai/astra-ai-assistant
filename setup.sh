#!/bin/bash
# ─────────────────────────────────────────────
# Astra Setup Script — Windows Git Bash
# Run this once on a fresh machine
# Usage: bash setup.sh
# ─────────────────────────────────────────────

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║       ASTRA SETUP SCRIPT v1.0         ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# ── Check Python ──
echo "[1/6] Checking Python..."
python --version 2>/dev/null || python3 --version 2>/dev/null
if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
    echo "ERROR: Python not found."
    echo "Download Python 3.11 from https://www.python.org/downloads/"
    echo "IMPORTANT: Check 'Add Python to PATH' during install."
    exit 1
fi
echo "  Python OK"

# ── Check Ollama ──
echo ""
echo "[2/6] Checking Ollama..."
if curl -s http://localhost:11434 | grep -q "Ollama"; then
    echo "  Ollama is running OK"
else
    echo "  WARNING: Ollama not running."
    echo "  Download from: https://ollama.com/download/windows"
    echo "  After install run: ollama pull llama3"
    echo "  Continuing setup..."
fi

# ── Create virtual environment ──
echo ""
echo "[3/6] Creating virtual environment..."
python -m venv astra-env
source astra-env/Scripts/activate
python -m pip install --upgrade pip --quiet
echo "  Virtual environment ready: (astra-env)"

# ── Install packages ──
echo ""
echo "[4/6] Installing packages..."

echo "  Installing PyAudio..."
pip install pyaudio --quiet

echo "  Installing webrtcvad replacement..."
pip install webrtcvad-wheels --quiet

echo "  Installing resemblyzer (no-deps)..."
pip install resemblyzer --no-deps --quiet

echo "  Installing core packages..."
pip install \
    faster-whisper \
    sounddevice \
    SpeechRecognition \
    pyttsx3 \
    requests \
    chromadb \
    sentence-transformers \
    Pillow \
    duckduckgo-search \
    numpy \
    --quiet

echo "  Packages installed OK"

# ── Create assets folder ──
echo ""
echo "[5/6] Creating folders..."
mkdir -p assets
mkdir -p astra_memory
mkdir -p astra_backups
mkdir -p voice_profiles
echo "  Folders created OK"

# ── Verify imports ──
echo ""
echo "[6/6] Verifying imports..."
python -c "
import faster_whisper, sounddevice, resemblyzer
import chromadb, pyaudio, PIL, numpy
import speech_recognition, pyttsx3, requests
print('  All imports OK')
" 2>&1

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║         SETUP COMPLETE                ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "NEXT STEPS:"
echo "  1. Make sure Ollama is running:  ollama pull llama3"
echo "  2. Record your voice:            python record_voice.py"
echo "  3. Launch Astra:                 python main.py"
echo ""
