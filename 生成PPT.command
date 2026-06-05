#!/bin/bash
# Mac 双击 — 重新生成 slides/FFRM-Deck.pptx
# 如果 .venv 还没建好会自动建好，跟「启动报告.command」一样。

cd "$(dirname "$0")"
trap 'echo ""; echo "按任意键退出（按完会打开 slides 文件夹）..."; read -n 1 -s -r; open slides 2>/dev/null; exit' EXIT

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[错误] 没找到 Python 3。先去 https://www.python.org/downloads/ 装。"
    exit 1
fi

NEED_INSTALL=0
if [ ! -d ".venv" ]; then
    echo "[首次启动] 创建虚拟环境..."
    "$PY" -m venv .venv || { echo "[错误] venv 创建失败"; exit 1; }
    NEED_INSTALL=1
fi
if ! .venv/bin/python -c "import pptx, matplotlib, numpy" >/dev/null 2>&1; then
    NEED_INSTALL=1
fi
if [ "$NEED_INSTALL" = "1" ]; then
    echo "[安装依赖] 30-60 秒..."
    .venv/bin/python -m pip install --upgrade pip --quiet 2>/dev/null || true
    if ! .venv/bin/pip install -r requirements.txt; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
    echo ""
fi

echo "正在生成 PPT..."
if ! .venv/bin/python scripts/build_deck.py; then
    echo "[错误] PPT 生成失败 — 看上面的错误信息"
    exit 1
fi
echo ""
echo "完成。slides/FFRM-Deck.pptx 已就绪。"
