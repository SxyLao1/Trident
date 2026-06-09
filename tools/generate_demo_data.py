#!/usr/bin/env python3
"""
Trident Demo Data Generator
Generates simulated detection records for demonstration and testing.

Usage:
    python tools/generate_demo_data.py
    python tools/generate_demo_data.py --count 50
"""
import sys
import os
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Ensure project root is in path when running from tools/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.suspicious_registry import add, get_all

# Demo data templates
WEBSHELL_SIGNATURES = [
    {"name": "php_eval_backdoor", "desc": "PHP eval() backdoor"},
    {"name": "php_base64_decode", "desc": "Base64 encoded PHP payload"},
    {"name": "php_gzinflate", "desc": "Gzip compressed PHP shell"},
    {"name": "asp_shell", "desc": "ASP command execution shell"},
    {"name": "jsp_webshell", "desc": "JSP runtime.exec() shell"},
    {"name": "aspx_ice_shell", "desc": "ASPX IceShell variant"},
    {"name": "godzilla_php", "desc": "Godzilla PHP webshell"},
    {"name": "behinder_php", "desc": "Behinder PHP webshell"},
    {"name": "china_chopper", "desc": "China Chopper variant"},
    {"name": "b374k_shell", "desc": "b374k PHP shell"},
]

DEMO_FILES = [
    "uploads/shell.php", "images/logo.php", "css/style.php", "js/config.php",
    "backup/backup.asp", "temp/temp.jsp", "cache/cache.aspx", "data/data.php",
    "include/header.php", "plugin/plugin.php", "theme/footer.php", "vendor/autoload.php",
    "public/index.php", "admin/login.php", "api/v1/endpoint.php", "cron/job.php",
    "logs/error.php", "tmp/session.php", "assets/script.php", "media/upload.php",
]

DEMO_IPS = [
    "192.168.1.100", "10.0.0.55", "172.16.0.23", "192.168.0.15",
    "10.255.71.61", "202.117.118.10", "45.33.22.11", "185.220.101.42",
    "91.207.175.104", "198.51.100.33", "203.0.113.7", "192.0.2.50",
]


def generate_demo_record(index, is_false_positive=False):
    """Generate a single demo detection record"""
    sig = random.choice(WEBSHELL_SIGNATURES)
    file_path = random.choice(DEMO_FILES)
    ip = random.choice(DEMO_IPS)

    days_ago = random.randint(0, 30)
    hours_ago = random.randint(0, 23)
    detected_at = datetime.now() - timedelta(days=days_ago, hours=hours_ago)

    record = {
        "id": f"demo_{index:04d}",
        "file_path": file_path,
        "display_name": os.path.basename(file_path),
        "detected_at": detected_at.strftime("%Y-%m-%d %H:%M:%S"),
        "rule_name": sig["name"],
        "rule_description": sig["desc"],
        "communication_count": random.randint(1, 50),
        "features": ["eval", "base64", "gzinflate", "assert", "system"][:random.randint(1, 3)],
        "alerted": True,
        "false_positive": is_false_positive,
        "source_ip": ip,
        "confidence": random.randint(60, 99),
        "severity": random.choice(["low", "medium", "high", "critical"]),
    }

    return record


def main():
    parser = argparse.ArgumentParser(description='Generate demo detection data for Trident')
    parser.add_argument('--count', type=int, default=30, help='Number of demo records (default: 30)')
    parser.add_argument('--fp-rate', type=float, default=0.15, help='False positive rate 0-1 (default: 0.15)')
    args = parser.parse_args()

    print(f"Trident Demo Data Generator")
    print(f"Generating {args.count} records with ~{args.fp_rate*100:.0f}% false positive rate...")
    print()

    for i in range(args.count):
        is_fp = random.random() < args.fp_rate
        record = generate_demo_record(i, is_fp)

        try:
            add(Path(record['file_path']), record['features'])
            status = "[FP]" if is_fp else "[DET]"
            print(f"  {status} {record['file_path']:<35} {record['rule_name']:<20} {record['detected_at']}")
        except Exception as e:
            print(f"  [ERR] Failed to add {record['file_path']}: {e}")

    print()
    print(f"Done! {args.count} demo records generated.")
    print(f"Start Trident and open http://127.0.0.1:8080/admin to view the demo data.")


if __name__ == '__main__':
    main()
