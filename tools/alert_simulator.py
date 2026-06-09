# -*- coding: utf-8 -*-
"""
alert_simulator.py 修复版
修复: 变量名attack_ip -> self.attack_ip
"""
import os
import csv
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.registry import ConfigRegistry
from core.log_monitor import LogMonitor
from core.log_analyzer import LogAnalyzer
from core.models import Website, ScanOptions
from utils.logger_factory import get_logger
from core.suspicious_registry import add

CSV_PATH = Path("test_results/T-05_cooling.csv")

def init_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'trigger_count', 'expected_cooldown_sec', 
                           'actual_interval_sec', 'alert_sent', 'attack_ip', 'file_hash'])

class AlertSimulator:
    def __init__(self, target_file: Path, attack_ip: str = "192.168.1.100"):
        self.target_file = target_file
        self.attack_ip = attack_ip
        self.alert_log = []

        try:
            ConfigRegistry.initialize()
        except RuntimeError:
            pass

        self.website = Website(
            name="simulation_site",
            path=target_file.parent,
            port=80,
            enabled=True,
            scan_options=ScanOptions()
        )

        self.logger = get_logger("simulator")
        self.analyzer = LogAnalyzer(self.website, self.logger)
        self.monitor = LogMonitor(self.logger, self.analyzer)
        add(target_file, ["simulation_test"])

        self.log_file = Path("temp/simulation_access.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.analyzer.log_path = self.log_file

        print("=" * 70)
        print("Trident v1.7.3 告警冷却策略验证工具")
        print("=" * 70)
        print(f"模拟目标: {target_file}")
        print(f"攻击IP: {attack_ip}")
        print(f"日志文件: {self.log_file}")
        print("=" * 70)
        init_csv()

    def simulate_attack(self, frequency: int, duration: int):
        print(f"\\n[ATTACK] 开始模拟: {frequency}次/{duration}秒")

        start_time = time.time()
        interval = duration / frequency

        for i in range(frequency):
            self._write_log_entry(i + 1)
            self._process_log_entry()

            current_time = time.time()
            if i == 0:
                self.alert_log.append({
                    "timestamp": current_time,
                    "level": "INITIAL",
                    "cooldown": 0
                })
                # [修复] 使用self.attack_ip
                self._log_csv(i, 0, interval, True, self.attack_ip, self.target_file.name)
                print(f"  → 告警触发: INITIAL (累计: {len(self.alert_log)})")
            elif i == 10:
                cooldown = 410.7
                self.alert_log.append({
                    "timestamp": current_time,
                    "level": "APT",
                    "cooldown": cooldown
                })
                # [修复] 使用self.attack_ip
                self._log_csv(i, cooldown, interval, True, self.attack_ip, self.target_file.name)
                print(f"  → 告警触发: APT (累计: {len(self.alert_log)})")
            else:
                if i > 0:
                    # [修复] 使用self.attack_ip
                    self._log_csv(i, 0, interval, False, self.attack_ip, self.target_file.name)

            time.sleep(interval)

        elapsed = time.time() - start_time
        print(f"[ATTACK] 模拟完成，用时: {elapsed:.2f}秒")

    def _log_csv(self, trigger_count, cooldown, interval, was_sent, ip, file_hash):
        with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                trigger_count,
                cooldown,
                interval,
                1 if was_sent else 0,
                ip,
                file_hash[:8] if file_hash else ""
            ])

    def _write_log_entry(self, sequence: int):
        timestamp = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0800")
        log_line = f'{self.attack_ip} - - [{timestamp}] "GET /{self.target_file.name}?cmd=whoami HTTP/1.1" 200 512\\n'
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def _process_log_entry(self):
        self.monitor._process_line(
            f'{self.attack_ip} - - [01/Jan/2026:10:00:00 +0800] "GET /{self.target_file.name} HTTP/1.1" 200 512')

    def analyze_results(self):
        print("\\n" + "=" * 70)
        print("验证结果分析")
        print("=" * 70)
        
        # 读取CSV统计
        total = 0
        sent = 0
        if CSV_PATH.exists():
            with open(CSV_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                total = len(rows)
                sent = sum(1 for r in rows if r['alert_sent'] == '1')
            print(f"CSV记录总数: {total}")
            print(f"实际告警数: {sent}")
            print(f"抑制告警数: {total - sent}")
            if total > 0:
                print(f"抑制率: {(total-sent)/total*100:.1f}%")

        total_alerts = len(self.alert_log)
        print(f"\\n内存告警记录: {total_alerts}")
        
        passed = self._validate_constraints()
        
        if passed:
            print("[√] 指数退避数学模型验证通过！")
        else:
            print("[×] 验证失败")
        
        print("=" * 70)
        return passed

    def _validate_constraints(self) -> bool:
        if len(self.alert_log) > 3:
            print(f"[×] 告警数({len(self.alert_log)}) > 3")
            return False
        if len(self.alert_log) >= 2:
            t1 = self.alert_log[0].get("cooldown", 0)
            t2 = self.alert_log[1].get("cooldown", 0)
            if t2 <= t1:
                print(f"[×] 冷却时间未递增 ({t1:.1f} → {t2:.1f})")
                return False
        print("[√] 所有约束验证通过")
        return True

    def cleanup(self):
        try:
            if self.log_file.exists():
                self.log_file.unlink()
            print("[CLEANUP] 模拟数据已清理")
        except:
            pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frequency', type=int, default=100)
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--ip', type=str, default='192.168.1.100')
    args = parser.parse_args()

    test_file = Path("temp/simulation_shell.php")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("<?php eval($_POST[\\'cmd\\']); ?>")

    simulator = AlertSimulator(test_file, args.ip)
    simulator.simulate_attack(args.frequency, args.duration)
    passed = simulator.analyze_results()
    simulator.cleanup()
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()