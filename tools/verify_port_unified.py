# -*- coding: utf-8 -*-
"""
@Time: 1/11/2026 10:08 PM
@Auth: SxyLao1
@File: verify_port_unified.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.0验证工具：确认8080端口单一服务
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import sys
import time
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def verify_port_unified():
    """验证8080端口统一服务"""
    print("=" * 60)
    print("v1.7.0端口统一验证")
    print("=" * 60)

    # 启动主应用
    print("[INFO] 正在启动Trident...")
    proc = __import__('subprocess').Popen(
        [sys.executable, "app.py"],
        cwd=PROJECT_ROOT,
        stdout=__import__('subprocess').PIPE,
        stderr=__import__('subprocess').PIPE,
        text=True
    )

    # 等待启动
    time.sleep(3)

    try:
        # 检查端口占用
        import psutil
        connections = [c for c in psutil.net_connections() if c.status == 'LISTEN' and c.laddr.port == 8080]

        print(f"[INFO] 8080端口监听进程数: {len(connections)}")

        if len(connections) == 0:
            print("[✗] 失败: 8080端口无监听")
            return False
        elif len(connections) > 1:
            print("[✗] 失败: 发现多个进程监听8080端口")
            for conn in connections:
                try:
                    proc = psutil.Process(conn.pid)
                    print(f"  - PID {conn.pid}: {proc.name()} ({proc.cmdline()})")
                except:
                    print(f"  - PID {conn.pid}: 无法获取进程信息")
            return False

        # 验证健康检查
        try:
            response = requests.get("http://127.0.0.1:8080/api/v1/health", timeout=5)
            if response.status_code == 200:
                print("[✓] 健康检查API正常")
            else:
                print(f"[✗] 健康检查返回状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"[✗] 健康检查失败: {e}")
            return False

        # 验证管理后台
        try:
            response = requests.get("http://127.0.0.1:8080/admin", timeout=5)
            if response.status_code == 401:  # 需要认证
                print("[✓] 管理后台正常（返回401认证要求）")
            elif response.status_code == 500:
                print("[✗] 管理后台500错误，需要修复")
                return False
            else:
                print(f"[✓] 管理后台可访问（状态码: {response.status_code}）")
        except Exception as e:
            print(f"[✗] 管理后台访问失败: {e}")
            return False

        print("[✓] 验证通过！8080端口单一服务运行正常")
        return True

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    success = verify_port_unified()
    sys.exit(0 if success else 1)