#!/usr/bin/env bash
# Start VIKO — run from project root: ./scripts/start.sh [--app]
#
#   (no args)  → run via Python venv, log to /tmp/viko.log  (dev mode)
#   --app      → open dist/VIKO.app                         (release mode)
set -euo pipefail

cd "$(dirname "$0")/.."

LOG="/tmp/viko.log"

stop_existing() {
    if pgrep -qf "python viko.py" 2>/dev/null; then
        echo "Stopping existing VIKO process..."
        pkill -f "python viko.py" 2>/dev/null || true
        sleep 1
    fi
}

start_ollama() {
    # Start Ollama in background if installed but not already running
    local bin="/Applications/Ollama.app/Contents/Resources/ollama"
    [ -f "$bin" ] || return
    curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && { echo "Ollama already running."; return; }
    echo "Starting Ollama (offline LLM)..."
    OLLAMA_MODELS="$(pwd)/models/ollama" "$bin" serve >> /tmp/ollama.log 2>&1 &
    sleep 2
    curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && echo "Ollama ready." || echo "Ollama failed to start (non-fatal)."
}

if [[ "${1:-}" == "--app" ]]; then
    DIST="dist/VIKO.app"
    if [ ! -d "$DIST" ]; then
        echo "Error: $DIST not found. Run ./scripts/build.sh first."
        exit 1
    fi
    pkill -f "VIKO.app" 2>/dev/null || true
    sleep 1
    echo "Opening $DIST..."
    open "$DIST"
    echo "Done. Check Console.app or logtail for output."
else
    stop_existing
    start_ollama
    echo "Starting VIKO (dev) → log: $LOG"
    nohup .venv/bin/python -u viko.py > "$LOG" 2>&1 &
    PID=$!
    echo "PID: $PID"
    echo ""
    sleep 3
    if kill -0 "$PID" 2>/dev/null; then
        echo "VIKO is running. Tail log:"
        echo "  tail -f $LOG"
    else
        echo "VIKO failed to start. Last log:"
        tail -20 "$LOG"
        exit 1
    fi
fi
