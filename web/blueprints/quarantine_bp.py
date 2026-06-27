from datetime import datetime
# -*- coding: utf-8 -*-
"""
@Time: 2026-06-09
@Auth: SxyLao1
@File: quarantine_bp.py
@IDE: PyCharm
@Motto: HACK THE REAL

v1.7.9 新增：隔离管理后台蓝图
"""
from flask import Blueprint, render_template, request, jsonify, current_app

from core.quarantine import (
    get_quarantine_list, get_quarantine_detail, get_quarantine_stats,
    restore_file, delete_quarantine
)
from config.registry import ConfigRegistry
from web.auth import require_auth

quarantine_bp = Blueprint('quarantine', __name__, url_prefix='/admin')


@quarantine_bp.route('/quarantine', methods=['GET'])
@require_auth
def quarantine_list():
    """隔离文件列表"""
    try:
        status = request.args.get('status', 'quarantined')
        page_str = request.args.get('page', '1')
        try:
            page = max(1, int(page_str))
        except (ValueError, TypeError):
            page = 1

        config = ConfigRegistry.get_raw_config()
        per_page = config.get("web_admin", {}).get("items_per_page", 20)

        all_records = get_quarantine_list(status=status if status != 'all' else None)

        # v1.8.4: 搜索过滤
        q = request.args.get('q', '').lower()
        if q:
            all_records = [r for r in all_records
                if q in r.get('quarantine_id', '').lower()
                or q in r.get('original_path', '').lower()
                or q in r.get('quarantine_path', '').lower()
                or q in r.get('rule_name', '').lower()]

        total = len(all_records)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)

        start = (page - 1) * per_page
        end = start + per_page
        paginated = all_records[start:end]

        stats = get_quarantine_stats()

        compact = request.args.get('compact') == '1'
        if request.headers.get('HX-Request'):
            return render_template(
                'admin/quarantine_list.html',
                records=paginated,
                stats=stats,
                page=page,
                total_pages=total_pages,
                total=total,
                per_page=per_page,
                current_status=status,
                compact=compact
            )
        else:
            return render_template(
                'admin/quarantine.html',
                records=paginated,
                stats=stats,
                page=page,
                total_pages=total_pages,
                total=total,
                per_page=per_page,
                current_status=status
            )

    except Exception as e:
        current_app.logger.error(f"[QUARANTINE][LIST] 错误: {e}", exc_info=True)
        return render_template('admin/error.html', error=str(e)), 500


@quarantine_bp.route('/quarantine/detail', methods=['GET'])
@require_auth
def quarantine_detail():
    """隔离详情"""
    try:
        qid = request.args.get('qid', '')
        if not qid:
            return jsonify({"error": "缺少 qid 参数"}), 400

        record = get_quarantine_detail(qid)
        if not record:
            return jsonify({"error": "记录不存在"}), 404

        if request.headers.get('HX-Request'):
            return render_template('admin/quarantine_detail.html', record=record)
        else:
            return jsonify(record)

    except Exception as e:
        current_app.logger.error(f"[QUARANTINE][DETAIL] 错误: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def _render_quarantine_list(status=None):
    """v1.7.9: 渲染隔离列表片段，供 restore/delete 后刷新用"""
    config = ConfigRegistry.get_raw_config()
    per_page = config.get("web_admin", {}).get("items_per_page", 20)
    all_records = get_quarantine_list(status=status)
    total = len(all_records)
    total_pages = max(1, (total + per_page - 1) // per_page)
    paginated = all_records[:per_page]
    stats = get_quarantine_stats()
    return render_template('admin/quarantine_list.html',
        records=paginated, stats=stats, page=1, total_pages=total_pages,
        total=total, per_page=per_page, current_status=status or 'all')


@quarantine_bp.route('/quarantine/restore', methods=['POST'])
@require_auth
def quarantine_restore():
    """恢复隔离文件 — v1.7.9: 返回刷新后的列表HTML"""
    try:
        qid = request.form.get('qid', '') or request.args.get('qid', '')
        if not qid:
            return jsonify({"error": "缺少 qid 参数"}), 400

        result = restore_file(qid)
        # 返回刷新后的列表，保留当前筛选状态
        status = request.args.get('status', 'quarantined')
        return _render_quarantine_list(status=None)  # 显示全部，包含刚恢复的

    except Exception as e:
        current_app.logger.error(f"[QUARANTINE][RESTORE] 错误: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@quarantine_bp.route('/quarantine/delete', methods=['POST'])
@require_auth
def quarantine_delete():
    """永久删除隔离文件 — v1.7.9: 返回刷新后的列表HTML"""
    try:
        qid = request.form.get('qid', '') or request.args.get('qid', '')
        if not qid:
            return jsonify({"error": "缺少 qid 参数"}), 400

        delete_quarantine(qid)
        return _render_quarantine_list(status=None)

    except Exception as e:
        current_app.logger.error(f"[QUARANTINE][DELETE] 错误: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
