@echo off
setlocal EnableDelayedExpansion
REM Libera a porta 5173 (Vite) antes de subir de novo.
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo [*] Encerrando PID %%a na porta 5173...
    taskkill /F /PID %%a >nul 2>&1
)
if "!FOUND!"=="0" (
    echo [OK] Porta 5173 livre.
) else (
    ping -n 2 127.0.0.1 >nul
    echo [OK] Porta 5173 liberada.
)
endlocal
