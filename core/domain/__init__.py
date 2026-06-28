# -*- coding: utf-8 -*-
"""
Trident v2.0-alpha: Domain Layer

Core business entities and value objects.
Pure Python — no infrastructure dependencies.
"""
from core.domain.entities import FileRecord, DetectionSource, ScanResult, QuarantineRecord

__all__ = ["FileRecord", "DetectionSource", "ScanResult", "QuarantineRecord"]
