#!/usr/bin/env bash
# Trident v1.7.8 Uninstall Script
# Usage: ./uninstall.sh
# Preserves: config.toml, logs/

echo "This will remove Trident virtual environment and runtime data."
echo "Your config.toml and logs will be preserved."
echo ""
read -rp "Are you sure? [y/N]: " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    rm -rf venv data __pycache__
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -f trident.pid
    echo "Uninstall complete."
    echo "Preserved: config.toml, logs/"
else
    echo "Cancelled."
fi
