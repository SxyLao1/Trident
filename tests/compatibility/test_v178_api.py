#!/usr/bin/env python3
"""
Trident v1.7.8 API Compatibility Test
Ensures core APIs remain stable across version upgrades.

Usage:
    python tests/compatibility/test_v178_api.py
    python tests/compatibility/test_v178_api.py --verbose

Rules:
    - This test MUST pass before any v1.8.x release
    - Breaking changes require major version bump (v2.0)
"""
import sys
import os
import unittest
import tempfile
import json
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


class TestConfigAPI(unittest.TestCase):
    """Test config.version and config.loader APIs."""

    def test_version_import(self):
        from config.version import get_version
        version = get_version()
        self.assertIsInstance(version, str)
        # v1.8.0: 兼容 semver 后缀 (-dev, -alpha, -rc1 等)
        self.assertRegex(version, r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")
        self.assertNotEqual(version, "unknown")

    def test_config_load(self):
        from config.loader import load_config
        cfg = load_config()
        self.assertIn("system", cfg)
        self.assertIn("website", cfg)
        self.assertIn("web_admin", cfg)


class TestRegistryAPI(unittest.TestCase):
    """Test suspicious_registry function-level APIs."""

    def setUp(self):
        # Use temp directory for isolated testing
        self.temp_dir = tempfile.mkdtemp()
        os.environ["TRIDENT_DATA_DIR"] = self.temp_dir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.environ.pop("TRIDENT_DATA_DIR", None)

    def test_add_and_get_all(self):
        from core.suspicious_registry import add, get_all
        from pathlib import Path

        add(Path("/tmp/test.php"), ["eval", "base64"])
        records = get_all()
        self.assertIsInstance(records, list)

    def test_get_all_filter(self):
        from core.suspicious_registry import get_all
        records = get_all(include_deleted=False, include_false_positive=False)
        self.assertIsInstance(records, list)


class TestWALAPI(unittest.TestCase):
    """Test WAL manager APIs."""

    def test_wal_info(self):
        from core import wal_manager
        info = wal_manager.get_wal_info()
        self.assertIsInstance(info, dict)

    def test_wal_read(self):
        from core import wal_manager
        records = wal_manager.read_wal_records(limit=10)
        self.assertIsInstance(records, list)


class TestSIEMFormatter(unittest.TestCase):
    """Test SIEM formatter APIs."""

    def test_json_lines_format(self):
        from utils.siem_formatter import format_event
        event = {
            "file_path": "/tmp/shell.php",
            "rule_name": "php_eval_backdoor",
            "severity": "high",
        }
        output = format_event(event)
        parsed = json.loads(output)
        self.assertIn("event_id", parsed)
        self.assertIn("source", parsed)
        self.assertIn("detection", parsed)

    def test_cef_format(self):
        from utils.siem_formatter import SIEMFormatter
        fmt = SIEMFormatter({"format": "cef"})
        event = {"file_path": "/tmp/shell.php", "rule_name": "test", "severity": "high"}
        output = fmt.format_event(event)
        self.assertTrue(output.startswith("CEF:0|Trident|WebShellDetector|"))


class TestYaraEngineAPI(unittest.TestCase):
    """Test YARA engine APIs."""

    def test_get_engine(self):
        from core.yara_engine import get_yara_engine
        engine = get_yara_engine()
        self.assertIsNotNone(engine)


class TestToolsRunnable(unittest.TestCase):
    """Test that all tools can be imported without error."""

    def test_verify_rules_import(self):
        import tools.verify_rules

    def test_admin_passwd_import(self):
        import tools.admin_passwd

    def test_generate_demo_data_import(self):
        import tools.generate_demo_data


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
