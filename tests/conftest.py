# Trident: test path setup
import sys
from pathlib import Path
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
    print(f"[conftest] Added {_project_root} to sys.path")
