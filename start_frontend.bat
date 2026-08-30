@echo off
title Frontend React - Equatorial Energia
color 0E

cd /d "%~dp0equatorial_automation_frontend"

call "%~dp0kill_port_5173.bat"

REM Verificar node_modules
if not exist "node_modules" (
    echo [*] Instalando dependencias do frontend...
    call pnpm install >nul 2>&1
    echo [OK] Dependencias instaladas
    echo.
) else (
    REM Verificar atualizacoes silenciosamente
    call pnpm install >nul 2>&1
)

REM Iniciar Vite
echo.
echo ============================================
echo   Frontend React - Equatorial Energia
echo ============================================
echo.

call pnpm run dev

pause
