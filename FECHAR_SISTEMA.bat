@echo off
REM =====================================================================
REM  PIENG - Fechar Sistema
REM =====================================================================
title PIENG - Encerrando Sistema
color 0C

echo.
echo ========================================
echo   PIENG - Encerrando Sistema
echo ========================================
echo.

echo [*] Encerrando backend (porta 5000)...
call "%~dp0kill_port_5000.bat"

echo [*] Encerrando frontend (porta 5180)...
call "%~dp0kill_port_5180.bat"

echo.
echo [OK] Sistema encerrado com sucesso!
echo.
timeout /t 3 /nobreak >nul
exit
