# -*- coding: utf-8 -*-
"""
@Time: 1/19/2026 3:22 PM
@Auth: SxyLao1
@File: generate_test_data.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.6: 生成用于Registry压缩和WAL重放的测试数据
"""
import json
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# 强制设置工具模式
os.environ["TRIDENT_TOOL_MODE"] = "true"

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.path_utils import normalize_path
from config.registry import ConfigRegistry


def backup_registry():
    """备份当前Registry文件"""
    registry_path = normalize_path("data/suspicious_registry.json")
    backup_path = normalize_path("data/suspicious_registry.json.backup.{}".format(
        datetime.now().strftime("%Y%m%d_%H%M%S")
    ))

    if registry_path.exists():
        shutil.copy2(registry_path, backup_path)
        print(f"[BACKUP] Registry已备份到: {backup_path}")
        return backup_path
    else:
        print("[WARN] Registry文件不存在，跳过备份")
        return None


def create_compressible_records():
    """制造可压缩的Registry记录（30天前删除）"""
    print("\n" + "=" * 60)
    print("[STEP 1] 制造可压缩的Registry记录")
    print("=" * 60)

    registry_path = normalize_path("data/suspicious_registry.json")

    if not registry_path.exists():
        print("[ERROR] Registry文件不存在: {}".format(registry_path))
        return False

    # 加载当前数据
    with open(registry_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data)
    print(f"[INFO] 当前Registry记录数: {original_count}")

    if original_count < 3:
        print("[ERROR] 需要至少3条记录才能演示压缩，当前只有{}条".format(original_count))
        return False

    # 修改前3条记录为30天前删除状态
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    modified_count = 0

    for i, record in enumerate(data[:3]):
        record["file_exists"] = False
        record["deleted_at"] = thirty_days_ago
        record["marked_false_positive"] = False  # 确保不是误报
        modified_count += 1
        print(f"[MODIFY] 记录 {i + 1}: {Path(record['file_path']).name} -> 标记为30天前删除")

    # 保存修改后的数据
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] 已修改 {modified_count} 条记录")
    print(f"[INFO] 现在Registry中有 {modified_count} 条可清理记录（已删除30天）")
    print(f"[INFO] 剩余 {len(data) - modified_count} 条正常记录")

    return True


def generate_wal_for_replay():
    """生成用于重放测试的WAL文件"""
    print("\n" + "=" * 60)
    print("[STEP 2] 生成WAL重放测试数据")
    print("=" * 60)

    wal_path = normalize_path("data/registry_wal.log")
    wal_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成一些WAL操作记录
    # 注意：使用未来时间点确保这些记录还未被Registry同步
    future_time = (datetime.now() + timedelta(minutes=5)).isoformat()

    wal_entries = [
        {
            "timestamp": future_time,
            "operation": "ADD",
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\wal_test_1.php",
            "features": ["WAL_TEST_1", "YARA:Test_Rule(critical)"],
            "ip": None,
            "pid": os.getpid(),
            "thread_id": 12345,
            "wal_threshold_mb": 10
        },
        {
            "timestamp": future_time,
            "operation": "ADD",
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\wal_test_2.jsp",
            "features": ["WAL_TEST_2", "YARA:JSP_Test(high)"],
            "ip": None,
            "pid": os.getpid(),
            "thread_id": 12346,
            "wal_threshold_mb": 10
        },
        {
            "timestamp": future_time,
            "operation": "REMOVE",
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\wal_test_1.php",
            "features": [],
            "ip": None,
            "pid": os.getpid(),
            "thread_id": 12347,
            "wal_threshold_mb": 10
        }
    ]

    # 追加到WAL文件（模拟未同步的数据）
    with open(wal_path, 'a', encoding='utf-8') as f:
        for entry in wal_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[SUCCESS] WAL文件已生成: {wal_path}")
    print(f"[INFO] 添加3条操作记录:")
    print(f"  - ADD: wal_test_1.php")
    print(f"  - ADD: wal_test_2.jsp")
    print(f"  - REMOVE: wal_test_1.php (模拟删除)")
    print(f"[INFO] WAL重放后应恢复1条记录 (wal_test_2.jsp)")

    # 显示WAL文件大小
    size_mb = wal_path.stat().st_size / 1024 / 1024
    print(f"[INFO] 当前WAL文件大小: {size_mb:.2f} MB")

    return True


def ensure_registry_exists():
    """确保Registry文件存在，不存在则创建初始数据"""
    registry_path = normalize_path("data/suspicious_registry.json")

    if registry_path.exists():
        print(f"[INFO] Registry文件已存在: {registry_path}")
        return True

    print(f"[WARN] Registry文件不存在，正在创建初始测试数据...")

    # 创建初始测试数据（8条，与您的目录结构匹配）
    initial_data = [
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\webshelldection1.php",
            "detected_at": "2026-01-19T14:28:35.768919",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\dokidoki.php",
            "detected_at": "2026-01-19T14:28:35.764890",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\hello.jsp",
            "detected_at": "2026-01-19T14:28:35.759558",
            "features": ["YARA:JSP_Shell_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\evil.php",
            "detected_at": "2026-01-19T14:28:35.754577",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\unknown.php",
            "detected_at": "2026-01-19T14:28:35.750917",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\raw.php",
            "detected_at": "2026-01-19T14:28:35.746350",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\b64.php",
            "detected_at": "2026-01-19T14:28:35.741791",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        },
        {
            "file_path": "e:\\software\\phpstudy_pro\\www\\test\\kami.php",
            "detected_at": "2026-01-19T14:28:35.737266",
            "features": ["YARA:Custom_Eval_Generic(critical)"],
            "alerted": False,
            "file_exists": True,
            "first_seen_ip": None,
            "communication_count": 0,
            "deleted_at": None,
            "marked_false_positive": False,
            "false_positive_reason": "",
            "false_positive_at": None
        }
    ]

    # 确保目录存在
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Registry文件已创建: {registry_path}")
    print(f"[INFO] 初始记录数: {len(initial_data)}条")
    return True


def verify_setup():
    """验证测试环境准备就绪"""
    print("\n" + "=" * 60)
    print("[STEP 3] 验证测试环境")
    print("=" * 60)

    # 检查Registry
    registry_path = normalize_path("data/suspicious_registry.json")
    if registry_path.exists():
        with open(registry_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        deletable = [r for r in data if not r.get("file_exists", True)]
        print(f"[VERIFY] Registry文件: ✓ (共{len(data)}条，可清理{len(deletable)}条)")
    else:
        print(f"[ERROR] Registry文件不存在: {registry_path}")
        return False

    # 检查WAL
    wal_path = normalize_path("data/registry_wal.log")
    if wal_path.exists():
        with open(wal_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"[VERIFY] WAL文件: ✓ (共{len(lines)}条操作记录)")
    else:
        print(f"[ERROR] WAL文件不存在: {wal_path}")
        return False

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("Trident v1.7.6 Registry压缩和WAL重放测试数据生成工具")
    print("=" * 60)

    try:
        # 初始化配置
        ConfigRegistry.initialize()
    except RuntimeError:
        pass

    ensure_registry_exists()

    # 步骤1: 备份
    backup_path = backup_registry()

    try:
        # 步骤2: 制造可压缩数据
        success1 = create_compressible_records()

        # 步骤3: 生成WAL数据
        success2 = generate_wal_for_replay()

        # 步骤4: 验证
        success3 = verify_setup()

        if success1 and success2 and success3:
            print("\n" + "=" * 60)
            print("[SUCCESS] 测试数据生成完成！")
            print("=" * 60)
            print("\n接下来您可以：")
            print("1. 启动Trident: python app.py")
            print("2. 访问管理后台: http://127.0.0.1:8080/admin")
            print("3. 进入系统管理页面")
            print("4. 点击[手动压缩Registry]按钮")
            print("   - 预期: 记录数从8条变为5条")
            print("   - 日志: 应显示'清理 3 条过期记录'")
            print("5. 点击[手动重放WAL]按钮")
            print("   - 预期: 可疑清单新增1条记录 (wal_test_2.jsp)")
            print("   - 日志: 应显示'WAL重放完成，恢复 1 条记录'")
            print("\n如果出现问题，备份文件在: {}".format(backup_path))

            return 0
        else:
            print("\n[ERROR] 测试数据生成失败！")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())