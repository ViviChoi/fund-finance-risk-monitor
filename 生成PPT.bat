@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY="
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py"
)
if not defined PY (
    echo [ERROR] No Python 3 found.
    pause
    exit /b 1
)

set "NEED_INSTALL=0"
if not exist ".venv" (
    echo [First run] Creating virtual environment...
    !PY! -m venv .venv
    if errorlevel 1 ( echo [ERROR] venv creation failed & pause & exit /b 1 )
    set "NEED_INSTALL=1"
)

.venv\Scripts\python.exe -c "import pptx, matplotlib, numpy" >nul 2>&1
if errorlevel 1 set "NEED_INSTALL=1"

if "!NEED_INSTALL!"=="1" (
    echo [Installing] 30-60s, needs internet...
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 ( echo [ERROR] install failed & pause & exit /b 1 )
    echo.
)

echo Generating PPT...
.venv\Scripts\python.exe scripts\build_deck.py
if errorlevel 1 ( echo [ERROR] PPT generation failed & pause & exit /b 1 )

echo.
echo Done. slides\FFRM-Deck.pptx is ready.
echo.
pause
explorer slides
