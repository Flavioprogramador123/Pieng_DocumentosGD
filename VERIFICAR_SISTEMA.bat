@echo off
REM =====================================================================
REM  PIENG - Verificação de Saúde do Sistema
REM =====================================================================
title PIENG - Verificacao do Sistema
color 0B

echo.
echo ========================================
echo   PIENG - Verificacao do Sistema
echo ========================================
echo.

REM Verifica Python
echo [*] Verificando Python...
python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('python --version') do echo     [OK] %%i
) else (
    echo     [X] Python NAO encontrado
)

REM Verifica Node.js
echo [*] Verificando Node.js...
node --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('node --version') do echo     [OK] Node.js %%i
) else (
    echo     [X] Node.js NAO encontrado
)

REM Verifica pnpm
echo [*] Verificando pnpm...
pnpm --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('pnpm --version') do echo     [OK] pnpm v%%i
) else (
    echo     [X] pnpm NAO encontrado
)

REM Verifica backend
echo [*] Verificando backend (porta 5000)...
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo     [OK] Backend rodando
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/health' -UseBasicParsing -TimeoutSec 2; Write-Host '     [OK] API respondendo:' $r.StatusCode } catch { Write-Host '     [!] API nao responde' }"
) else (
    echo     [X] Backend NAO esta rodando
)

REM Verifica frontend
echo [*] Verificando frontend (porta 5173)...
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo     [OK] Frontend rodando
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2; Write-Host '     [OK] Frontend respondendo:' $r.StatusCode } catch { Write-Host '     [!] Frontend nao responde' }"
) else (
    echo     [X] Frontend NAO esta rodando
)

REM Verifica Google Drive
echo [*] Verificando Google Drive...
if exist "I:\Meu Drive" (
    echo     [OK] Google Drive montado
) else (
    echo     [!] Google Drive NAO encontrado (verifique Google Drive for Desktop)
)

REM Verifica arquivos .env
echo [*] Verificando configuracao...
if exist ".env" (
    echo     [OK] .env encontrado
) else (
    echo     [!] .env NAO encontrado
)

if exist "backend\.env" (
    echo     [OK] backend\.env encontrado
) else (
    echo     [!] backend\.env NAO encontrado
)

REM ODA File Converter (planta.dwg compacto)
echo [*] Verificando ODA File Converter...
set "ODA_FOUND="
for /f "delims=" %%F in ('dir /s /b "C:\Program Files\ODA\ODAFileConverter.exe" 2^>nul') do set "ODA_FOUND=%%F"
if defined ODA_FOUND (
    echo     [OK] ODA File Converter
    echo          %ODA_FOUND%
) else (
    echo     [!] ODA NAO instalado — planta sera entregue como .dxf (~25 MB)
    echo         Execute INSTALAR_ODA.bat ou instale pela primeira abertura do sistema
)

echo.
echo ========================================
echo   Verificacao concluida!
echo ========================================
echo.
pause
