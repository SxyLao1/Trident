#!/usr/bin/env bash
# Trident Installer Entry Point (Linux/macOS/WSL)
# Design: This script ONLY detects Python, then delegates ALL logic to scripts/install.py
# Benefit: Version upgrades never require changing this file — only scripts/install.py

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}  _____     _     _            _   ${NC}"
echo -e "${CYAN} |_   _| __(_) __| | ___ _ __ | |_ ${NC}"
echo -e "${CYAN}   | || '__| |/ _\` |/ _ \\ '_ \\| __|${NC}"
echo -e "${CYAN}   | || |  | | (_| |  __/ | | | |_ ${NC}"
echo -e "${CYAN}   |_||_|  |_|\\__,_|\\___|_| |_|\\__|${NC}"
echo ""

# Detect Python 3.8+
PYTHON_CMD=""
for cmd in python3 python py3 py; do
    if command -v "$cmd" &> /dev/null; then
        ver_str=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || true)
        if [[ -n "$ver_str" ]]; then
            major=$(echo "$ver_str" | cut -d. -f1)
            minor=$(echo "$ver_str" | cut -d. -f2)
            if [[ "$major" -ge 3 && "$minor" -ge 8 ]]; then
                PYTHON_CMD=$cmd
                break
            fi
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "${RED}[ERROR] Python 3.8+ is required but not found.${NC}"
    echo ""
    echo "Tried: python3, python, py3, py"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian:  sudo apt update && sudo apt install python3 python3-venv python3-pip"
    echo "  macOS:          brew install python@3.12"
    echo "  Verify:         python3 --version"
    exit 1
fi

# Delegate to Python installer (Single Source of Truth for all install logic)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}[OK] Python found, delegating to scripts/install.py...${NC}"
echo ""

$PYTHON_CMD scripts/install.py
