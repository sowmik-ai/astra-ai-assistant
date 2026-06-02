#!/bin/bash
# ─────────────────────────────────────────────
# check_astra.sh — Astra Service Status Checker
# Usage: bash check_astra.sh
# Place in: C:\Users\003CM2744\Videos\astra\
# ─────────────────────────────────────────────

cd ~/Videos/astra 2>/dev/null || {
    echo "ERROR: ~/Videos/astra folder not found"
    exit 1
}

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║           ASTRA SERVICE STATUS                   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Ollama ──
printf "  Ollama:             "
if curl -s http://localhost:11434 2>/dev/null | grep -q "Ollama"; then
    echo "✓ RUNNING"
else
    echo "✗ STOPPED  →  run: ollama serve"
fi

# ── 2. Astra server (port 8000) ──
printf "  Astra server:       "
if curl -s http://localhost:8000/status > /dev/null 2>&1; then
    echo "✓ RUNNING (port 8000)"
else
    echo "✗ STOPPED  →  run: python remote_server.py"
fi

# ── 3. Cloudflare tunnel ──
printf "  Cloudflare tunnel:  "
if [ -f "cloudflared.log" ] && \
   grep -q "trycloudflare\|Registered tunnel" cloudflared.log 2>/dev/null; then
    echo "✓ RUNNING"
elif pgrep -f "cloudflared" > /dev/null 2>&1; then
    echo "✓ RUNNING (process active)"
else
    echo "✗ NOT RUNNING  →  run: python astra_service.py"
fi

# ── 4. Public URL ──
echo ""
printf "  Public URL:         "
if [ -f "astra_public_url.txt" ]; then
    URL=$(grep "URL:" astra_public_url.txt | head -1 | sed 's/URL://' | tr -d ' ')
    if [ -n "$URL" ]; then
        echo "$URL"
    else
        echo "Not available yet"
    fi
else
    echo "Not generated yet  →  run: python astra_service.py"
fi

# ── 5. API Key ──
printf "  API Key:            "
if [ -f "astra_api_key.txt" ]; then
    echo "✓ Saved in astra_api_key.txt"
else
    echo "✗ Not generated  →  run: python remote_server.py"
fi

# ── 6. Voice profile ──
printf "  Voice profile:      "
if [ -f "my_voice.wav" ]; then
    SIZE=$(wc -c < my_voice.wav 2>/dev/null)
    echo "✓ my_voice.wav ($SIZE bytes)"
else
    echo "✗ Not found  →  run: python record_voice.py"
fi

# ── 7. Assets ──
printf "  Face assets:        "
if [ -f "assets/idle.gif" ] && \
   [ -f "assets/listening.gif" ] && \
   [ -f "assets/speaking.gif" ]; then
    echo "✓ All 3 GIFs present"
else
    echo "✗ Missing  →  copy idle.gif listening.gif speaking.gif to assets/"
fi

# ── 8. Virtual environment ──
printf "  Virtual env:        "
if [ -d "astra-env" ]; then
    echo "✓ astra-env exists"
else
    echo "✗ Not found  →  run: bash setup.sh"
fi

# ── 9. Auth config ──
printf "  MFA config:         "
if [ -f "astra_auth_config.json" ]; then
    PIN=$(python3 -c "import json; d=json.load(open('astra_auth_config.json')); print('PIN set' if d.get('voice_pin_hash') else 'PIN NOT set')" 2>/dev/null)
    echo "✓ Configured ($PIN)"
else
    echo "✗ Not set up  →  run python main.py to configure"
fi

# ── 10. Windows Task Scheduler ──
printf "  Auto-start task:    "
TASK_STATUS=$(schtasks /query /tn "AstraRemoteServer" /fo LIST 2>/dev/null | grep "Status" | sed 's/Status://;s/ //g')
if [ -n "$TASK_STATUS" ]; then
    echo "✓ Installed — Status: $TASK_STATUS"
else
    echo "✗ Not installed  →  run install_service.bat as Admin"
fi

# ── 11. Ollama model ──
printf "  llama3 model:       "
if ollama list 2>/dev/null | grep -q "llama3"; then
    echo "✓ llama3 downloaded"
else
    echo "✗ Not found  →  run: ollama pull llama3"
fi

# ── 12. Recent logs ──
if [ -f "astra_service.log" ]; then
    echo ""
    echo "  Last 5 log entries:"
    echo "  ─────────────────────────────────────────────────"
    tail -5 astra_service.log | while IFS= read -r line; do
        echo "  $line"
    done
fi

# ── Summary ──
echo ""
echo "  ─────────────────────────────────────────────────"

# Count issues
ISSUES=0
curl -s http://localhost:11434 2>/dev/null | grep -q "Ollama" || ISSUES=$((ISSUES+1))
[ ! -f "my_voice.wav" ] && ISSUES=$((ISSUES+1))
[ ! -f "assets/idle.gif" ] && ISSUES=$((ISSUES+1))
[ ! -d "astra-env" ] && ISSUES=$((ISSUES+1))

if [ "$ISSUES" -eq 0 ]; then
    echo "  ✓ All systems ready. Astra is good to go!"
else
    echo "  ✗ Found $ISSUES issue(s). Fix the items marked ✗ above."
fi
echo ""
