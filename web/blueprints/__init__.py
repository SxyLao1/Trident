# -*- coding: utf-8 -*-
"""
@Time: 1/11/2026 9:59 PM
@Auth: SxyLao1
@File: __init__.py.py
@IDE: PyCharm
@Motto: HACK THE REAL
Blueprint统一注册
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def register_blueprints(app: 'Flask'):
    """注册所有Blueprint"""
    # 注册Metrics Blueprint
    from web.blueprints.metrics import metrics_bp
    app.register_blueprint(metrics_bp)

    # 注册Admin Blueprint
    from web.blueprints.admin_bp import admin_bp
    app.register_blueprint(admin_bp)

    # 注册YARA Blueprint
    from web.blueprints.yara_bp import yara_bp
    app.register_blueprint(yara_bp)

    # v1.7.9: 注册Quarantine Blueprint
    from web.blueprints.quarantine_bp import quarantine_bp
    app.register_blueprint(quarantine_bp)