"""Anteumbra v2.0-alpha entry point — migrated from Trident app.py"""
import sys
import os

def main():
    print(f"Anteumbra v2.0.0.dev0 — WebShell Detection System")
    print(f"Python {sys.version}")
    print(f"Run via: python -m anteumbra.interfaces.web.factory")
    print(f"Or use legacy: python -m trident_app")

if __name__ == "__main__":
    main()
