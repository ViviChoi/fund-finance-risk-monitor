@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM Windows 双击启动器 — Fund Finance Facility Risk Monitor

cd /d "%~dp0"

REM --- 1. 找 Python 3 ---
set "PY="
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py"
)
if not defined PY (
    echo.
    echo [ERROR] No Python 3 found.
    echo         Install from https://www.python.org/downloads/
    echo         IMPORTANT: tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

REM --- 2. 准备虚拟环境 ---
set "NEED_INSTALL=0"
if not exist ".venv" (
    echo [First run] Creating virtual environment...
    !PY! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv creation failed.
        pause
        exit /b 1
    )
    set "NEED_INSTALL=1"
)

REM --- 3. 验证依赖是否真的装好 ---
.venv\Scripts\python.exe -c "import numpy, matplotlib, pptx" >nul 2>&1
if errorlevel 1 set "NEED_INSTALL=1"

if "!NEED_INSTALL!"=="1" (
    echo [Installing] 30-60s, requires internet...
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency install failed - see errors above.
        echo         If a network issue, check your connection / VPN.
        pause
        exit /b 1
    )
    echo [Done] Dependencies installed.
    echo.
)

REM --- 4. 跑报告 ---
echo ================================================================
echo   Fund Finance Facility Risk Monitor - Generating report...
echo ================================================================
echo.

.venv\Scripts\python.exe run.py
set "RC=!ERRORLEVEL!"
echo.

if not "!RC!"=="0" (
    echo [ERROR] run.py exited with code !RC! - see traceback above.
    echo         Most common cause: a broken sample_data\*.csv file.
    pause
    exit /b !RC!
)

echo ================================================================
echo   Done.
echo   Charts -^> figures\stress_chart.png + figures\reverse_stress.png
echo   PPT    -^> slides\FFRM-Deck.pptx (run 生成PPT.bat to regenerate)
echo ================================================================
echo.
pause
explorer .
