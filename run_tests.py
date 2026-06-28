#!/usr/bin/env python3
"""Test runner — explicitly sets PYTHONPATH for pytest."""
import os, sys, subprocess
root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
env = os.environ.copy()
env["PYTHONPATH"] = root
sys.exit(subprocess.run(
    [sys.executable, "-m", "pytest", "tests/core/", "-v", "--tb=short"],
    cwd=root, env=env
).returncode)
