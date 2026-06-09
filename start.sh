#!/usr/bin/env bash
# Trident v1.7.8 Launcher - Foreground Mode
# Usage: ./start.sh

cd "$(dirname "$0")"

# Try to activate venv
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
elif [[ -f "venv/Scripts/activate" ]]; then
    source venv/Scripts/activate
fi

echo ""
echo "  _____     _     _            _"
echo " |_   _| __(_) __| | ___ _ __ | |_"
echo "   | || '__| |/ _\` |/ _ \\ '_ \\| __|"
echo "   | || |  | | (_| |  __/ | | | |_"
echo "   |_||_|  |_|\\__,_|\\___|_| |_|\\__|"
echo ""
echo "  Trident v1.7.8 Starting..."
echo "  URL: http://127.0.0.1:8080"
echo "  Press Ctrl+C to stop"
echo ""
echo "  Logs: logs/Trident/"
echo ""
echo "  ========================================="
echo ""
python app.py
