#!/usr/bin/env python3
"""
Trident Background Launcher
Cross-platform background process starter.
Called by start_background.sh / start_background.bat

Design: Uses subprocess.Popen with pythonw (Windows) or nohup (Linux)
to start Trident detached from the terminal.
"""
import os
import sys
import subprocess
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(PROJECT_ROOT, 'trident.pid')
LOG_FILE = os.path.join(PROJECT_ROOT, 'logs', 'trident_background.log')


def get_venv_pythonw():
    """Find pythonw.exe (Windows) or python (Linux) in venv"""
    candidates = [
        os.path.join(PROJECT_ROOT, 'venv', 'Scripts', 'pythonw.exe'),  # Windows
        os.path.join(PROJECT_ROOT, 'venv', 'bin', 'python'),           # Linux/macOS
        os.path.join(PROJECT_ROOT, 'venv', 'Scripts', 'python.exe'),   # Windows fallback
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def is_trident_running(pid):
    """Check if a process with given PID is still running"""
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, False, pid)  # PROCESS_TERMINATE
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def stop_existing():
    """Stop any existing Trident process"""
    if not os.path.exists(PID_FILE):
        return
    try:
        with open(PID_FILE, 'r') as f:
            old_pid = int(f.read().strip())
        if is_trident_running(old_pid):
            print(f"[INFO] Stopping existing Trident [PID: {old_pid}]...")
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/PID', str(old_pid), '/F', '/T'], capture_output=True)
            else:
                os.kill(old_pid, 9)
            time.sleep(1)
    except Exception as e:
        print(f"[WARN] Could not stop existing process: {e}")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def main():
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Stop existing instance
    stop_existing()

    # Find python interpreter
    python_exe = get_venv_pythonw()
    if not python_exe:
        print("[ERROR] Could not find venv python interpreter.")
        print("        Please run install.bat / install.sh first.")
        sys.exit(1)

    # Start Trident in background
    print(f"[INFO] Starting Trident with {os.path.basename(python_exe)}...")

    kwargs = {
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
        'cwd': PROJECT_ROOT,
    }

    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs['start_new_session'] = True

    proc = subprocess.Popen([python_exe, 'app.py'], **kwargs)

    # Wait a moment to verify it didn't crash immediately
    time.sleep(2)

    if proc.poll() is not None:
        print(f"[ERROR] Trident exited immediately with code {proc.returncode}.")
        print(f"        Check {LOG_FILE} or run start.bat to see the error.")
        sys.exit(1)

    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(proc.pid))

    print(f"[OK] Started Trident [PID: {proc.pid}]")
    print(f"     Log: {LOG_FILE}")
    print(f"     URL: http://127.0.0.1:8080/admin")


if __name__ == '__main__':
    main()
