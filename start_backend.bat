@echo off
title Backend API - Equatorial Energia
color 0B

cd /d "%~dp0backend"

REM Verificar/criar ambiente virtual
if not exist ".venv\Scripts\python.exe" (
    echo [*] Preparando ambiente Python...
    python -m venv .venv >nul 2>&1
    echo [*] Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install -q --upgrade pip >nul 2>&1
    ".venv\Scripts\python.exe" -m pip install -q -r requirements_api.txt
    echo [OK] Ambiente configurado
    echo.
) else (
    ".venv\Scripts\python.exe" -m pip install -q -r requirements_api.txt >nul 2>&1
)

REM Iniciar servidor
echo.
echo ============================================
echo   Backend API - Equatorial Energia
echo ============================================
echo.

".venv\Scripts\python.exe" api_server.py

pause
