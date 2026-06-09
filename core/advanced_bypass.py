# -*- coding: utf-8 -*-
"""
@Time: 1/11/2026 6:42 PM
@Auth: SxyLao1
@File: advanced_bypass.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""
from pathlib import Path
from typing import Optional
from core.models import ScanResult

class VMwareBypassDetector:
    """高级绕过手法检测（VMware Tools权限混淆等）"""

    @staticmethod
    def detect_permission_confusion(file_path: Path) -> Optional[ScanResult]:
        """检测权限混淆攻击"""
        try:
            import win32security
            sd = win32security.GetFileSecurity(
                str(file_path),
                win32security.OWNER_SECURITY_INFORMATION
            )
            owner_sid = sd.GetSecurityDescriptorOwner()
            sid_str = win32security.ConvertSidToStringSid(owner_sid)

            if sid_str.startswith("S-1-5-21-") and "Unknown" in str(owner_sid):
                return ScanResult(
                    file_path=file_path,
                    is_suspicious=True,
                    features=["PERMISSION_CONFUSION", "VMWARE_TOOLS_BYPASS"],
                    score=0.95,
                    engine="advanced_bypass"
                )
        except:
            pass
        return None