#!/usr/bin/env bash
# Trident v1.7.8 Launcher - Background Mode
# Usage: ./start_background.sh

cd "$(dirname "$0")"

# Try to activate venv
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
elif [[ -f "venv/Scripts/activate" ]]; then
    source venv/Scripts/activate
fi

echo "Starting Trident in background..."
python scripts/background_launcher.py
