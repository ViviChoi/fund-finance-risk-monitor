#!/bin/bash
# Mac 双击启动器 — Fund Finance Facility Risk Monitor
# 自动建虚拟环境、装依赖、跑 run.py、打开文件夹。
# 任何报错都会保留终端，按任意键退出。

cd "$(dirname "$0")"

# trap: 无论怎么退都让用户先看到日志再关窗
trap 'echo ""; echo "按任意键退出（按完会打开文件夹）..."; read -n 1 -s -r; open . 2>/dev/null; exit' EXIT

# --- 1. 找 Python 3 ---
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[错误] 没找到 Python 3。"
    echo "        请去 https://www.python.org/downloads/ 装一个再重试。"
    exit 1
fi

# --- 2. 准备虚拟环境 ---
NEED_INSTALL=0
if [ ! -d ".venv" ]; then
    echo "[首次启动] 创建虚拟环境..."
    if ! "$PY" -m venv .venv; then
        echo "[错误] venv 创建失败。"
        exit 1
    fi
    NEED_INSTALL=1
fi

# --- 3. 验证依赖是否真的装好（不能只看 .venv 文件夹是否存在） ---
if ! .venv/bin/python -c "import numpy, matplotlib, pptx" >/dev/null 2>&1; then
    NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" = "1" ]; then
    echo "[安装依赖] 30-60 秒，需要联网..."
    .venv/bin/python -m pip install --upgrade pip --quiet 2>/dev/null || true
    if ! .venv/bin/pip install -r requirements.txt; then
        echo ""
        echo "[错误] 依赖安装失败 — 看上面的错误信息。"
        echo "        如果是网络问题，连上 VPN / 换网再重试。"
        exit 1
    fi
    echo "[完成] 依赖已就绪。"
    echo ""
fi

# --- 4. 跑报告 ---
echo "================================================================"
echo "  Fund Finance Facility Risk Monitor — 正在生成报告..."
echo "================================================================"
echo ""

if ! .venv/bin/python run.py; then
    echo ""
    echo "[错误] run.py 报错退出 — 看上面的 traceback。"
    echo "        最常见原因：sample_data/*.csv 被改坏了。"
    exit 1
fi

echo ""
echo "================================================================"
echo "  完成。"
echo "  图  -> figures/stress_chart.png + figures/reverse_stress.png"
echo "  PPT -> slides/FFRM-Deck.pptx（如果还没生成，双击「生成PPT.command」）"
echo "================================================================"
