#!/usr/bin/env bash
# Trident v1.7.8 Stop Script
# Usage: ./stop.sh

cd "$(dirname "$0")"

if [[ -f trident.pid ]]; then
    PID=$(cat trident.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill -TERM "$PID" 2>/dev/null
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -KILL "$PID" 2>/dev/null
        fi
        echo "Trident [PID $PID] stopped."
    else
        echo "Process $PID not running."
    fi
    rm -f trident.pid
else
    echo "No PID file found."
    # Try to find and kill python processes running app.py
    PIDS=$(pgrep -f "python.*app.py" || true)
    if [[ -n "$PIDS" ]]; then
        echo "Found processes: $PIDS"
        echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
        echo "Stopped."
    else
        echo "No Trident processes found."
    fi
fi
