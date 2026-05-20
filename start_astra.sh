#!/bin/bash
# ─────────────────────────────────────────────
# start_astra.sh — Astra Quick Launch Script
# Usage: bash start_astra.sh
# Place this file in: C:\Users\003CM2744\Videos\astra\
# ─────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         A . S . T . R . A               ║"
echo "║     Autonomous AI Assistant              ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Go to Astra folder ──
cd ~/Videos/astra || {
    echo "ERROR: ~/Videos/astra folder not found."
    echo "Please copy all Astra files to ~/Videos/astra first."
    exit 1
}

# ── Check virtual environment exists ──
if [ ! -d "astra-env" ]; then
    echo "ERROR: Virtual environment not found."
    echo "Please run setup.sh first: bash setup.sh"
    exit 1
fi

# ── Activate virtual environment ──
echo "  Activating virtual environment..."
source astra-env/Scripts/activate

# ── Check Ollama is running ──
echo "  Checking Ollama..."
if curl -s http://localhost:11434 | grep -q "Ollama"; then
    echo "  Ollama is running OK"
else
    echo "  Ollama not running — starting it..."
    ollama serve &
    sleep 3
    if curl -s http://localhost:11434 | grep -q "Ollama"; then
        echo "  Ollama started OK"
    else
        echo "  WARNING: Ollama may not be running."
        echo "  Run manually: ollama serve"
    fi
fi

# ── Check voice profile exists ──
if [ ! -f "my_voice.wav" ]; then
    echo ""
    echo "  Voice profile not found."
    echo "  Running voice recorder now..."
    echo "  Speak for 8 seconds when prompted."
    echo ""
    python record_voice.py
fi

# ── Check assets exist ──
if [ ! -f "assets/idle.gif" ]; then
    echo ""
    echo "  WARNING: assets/idle.gif not found."
    echo "  Astra will use fallback face colours."
    echo "  Copy idle.gif, listening.gif, speaking.gif into assets/"
fi

# ── Launch Astra ──
echo ""
echo "  Launching Astra..."
echo "  Say 'Astra' to wake her up."
echo ""
python main.py

# ── Exit message ──
echo ""
echo "  Astra has stopped. Goodbye Sowmik."
echo ""
