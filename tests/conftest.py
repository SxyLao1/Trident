# Anteumbra test path setup
import sys
from pathlib import Path
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
print(f"[conftest] Added {_root} to sys.path")
