#!/usr/bin/env bash
# Python Cache Cleaner (Unix/Linux/macOS)
# 默认当前目录，可传参指定目录，递归清理

set -euo pipefail

TARGET="${1:-$(pwd)}"
TARGET="$(cd "$TARGET" && pwd)"

echo "=========================================="
echo "  Python Cache Cleaner (Unix)"
echo "=========================================="
echo ""
echo "[INFO] 目标目录: $TARGET"

if [[ ! -d "$TARGET" ]]; then
    echo "[ERROR] 目录不存在: $TARGET"
    exit 1
fi

cd "$TARGET" || exit 1

echo ""
echo "[1/3] 递归清理 __pycache__ 目录 ..."
find . -type d -name "__pycache__" -print -exec rm -rf {} + 2>/dev/null || true

echo "[2/3] 递归清理 *.pyc / *.pyo 文件 ..."
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -print -delete 2>/dev/null || true

echo "[3/3] 递归清理 *.pyd / *.so 编译扩展 ..."
find . -type f \( -name "*.pyd" -o -name "*.so" \) -print -delete 2>/dev/null || true

echo ""
echo "=========================================="
echo "  清理完成"
echo "=========================================="
