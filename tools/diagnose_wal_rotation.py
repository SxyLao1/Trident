# -*- coding: utf-8 -*-
"""
@Time: 1/9/2026 7:44 PM
@Auth: SxyLao1
@File: diagnose_wal_rotation.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""
import os
import sys
from pathlib import Path

os.environ["TRIDENT_TOOL_MODE"] = "true"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.wal_manager import write_entry as _write_wal
from utils.path_utils import normalize_path


def run_stress_test():
    """生成10MB+ WAL数据并测试轮转"""
    # 创建测试文件
    test_file = normalize_path("temp/apt_attack_sim.php")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("<?php eval($_POST['cmd']); ?>")

    print(f"[STRESS] 开始生成10MB+ WAL数据...")
    target_size = 11 * 1024 * 1024  # 11MB确保触发轮转
    current_size = 0

    # 估算每条WAL记录大小（约500字节）
    records_needed = target_size // 500

    for i in range(records_needed):
        _write_wal("ADD", test_file, [f"APT_Backdoor_{i}", "ChinaChopper_variant"], "192.168.1.100")

        # 每1000条检查一次大小
        if i % 1000 == 0:
            wal_path = Path("data/registry_wal.log")
            if wal_path.exists():
                current_size = wal_path.stat().st_size
                print(
                    f"[STRESS] 进度: {current_size / 1024 / 1024:.2f}MB / {target_size / 1024 / 1024:.2f}MB ({i}/{records_needed}条)")

            # 检查是否已轮转
            rotated_files = list(Path("data").glob("registry_wal.log.20*"))
            if rotated_files:
                print(f"[SUCCESS] WAL已轮转: {rotated_files[0].name}")
                break

    print("[STRESS] 测试完成")
    print(f"最终WAL大小: {current_size / 1024 / 1024:.2f}MB")


if __name__ == "__main__":
    run_stress_test()
