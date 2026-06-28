# Trident: must run before any test import
import sys, os
_project_root = r'F:\Home\Github\Trident\Trident_v1.0\Trident_1.8'
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
