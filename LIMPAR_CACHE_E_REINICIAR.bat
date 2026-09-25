@echo off
chcp 65001 >nul
title PIENG - Limpeza de Cache e Reinício

echo ========================================
echo   PIENG - Limpeza de Cache
echo ========================================
echo.

REM Parar todos os processos
echo [1/5] Parando processos...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5180" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo [OK] Processos parados

REM Limpar cache do Vite
echo.
echo [2/5] Limpando cache do Vite...
cd /d "%~dp0equatorial_automation_frontend"
if exist "node_modules\.vite" (
    rmdir /s /q "node_modules\.vite" >nul 2>&1
)
if exist ".vite" (
    rmdir /s /q ".vite" >nul 2>&1
)
echo [OK] Cache do Vite limpo

REM Limpar dist
echo.
echo [3/5] Limpando build anterior...
if exist "dist" (
    rmdir /s /q "dist" >nul 2>&1
)
echo [OK] Build anterior removido

REM Reinstalar dependências (rápido com pnpm)
echo.
echo [4/5] Verificando dependências...
call pnpm install >nul 2>&1
echo [OK] Dependências verificadas

REM Voltar ao diretório raiz
cd /d "%~dp0"

echo.
echo [5/5] Iniciando sistema...
echo.
echo ========================================
echo   IMPORTANTE!
echo ========================================
echo.
echo No navegador, quando a página abrir:
echo.
echo   1. Pressione: Ctrl + Shift + Del
echo   2. Marque: "Imagens e arquivos em cache"
echo   3. Clique em "Limpar dados"
echo.
echo   OU simplesmente pressione:
echo   Ctrl + Shift + R (reload forçado)
echo.
echo ========================================
echo.

REM Iniciar sistema
start "" /min cmd /c "%~dp0start_backend.bat"
timeout /t 3 /nobreak >nul
start "" cmd /c "%~dp0equatorial_automation_frontend\start_frontend.bat"

timeout /t 5 /nobreak >nul
start http://127.0.0.1:5180

echo.
echo [OK] Sistema iniciado!
echo.
echo A página irá abrir automaticamente.
echo Lembre-se de limpar o cache do navegador!
echo.
pause
