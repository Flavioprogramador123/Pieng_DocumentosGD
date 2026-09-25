@echo off
REM =====================================================================
REM  PIENG - Sistema de Automação Equatorial
REM  Inicialização Rápida Otimizada
REM =====================================================================
title PIENG - Automacao Equatorial
color 0A

REM Muda para o diretório do script
cd /d "%~dp0"

REM Verifica se já está rodando (frontend + backend atualizado)
echo [*] Verificando se sistema ja esta rodando...
set "SYS_OK=0"
netstat -ano | findstr ":5180" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
    if not errorlevel 1 (
        powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:5000/api/health' -TimeoutSec 2; if ($r.capabilities.output_open) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 set "SYS_OK=1"
    )
)
if "%SYS_OK%"=="1" (
    echo [OK] Sistema ja esta rodando!
    echo [*] Abrindo navegador...
    start http://127.0.0.1:5180
    timeout /t 2 /nobreak >nul
    exit
)

netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [!] Backend antigo detectado — reiniciando pilha completa...
    call "%~dp0kill_port_5000.bat" >nul 2>&1
)
netstat -ano | findstr ":5180" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    call "%~dp0kill_port_5180.bat" >nul 2>&1
)

REM Sistema não está rodando (ou foi reiniciado), iniciar tudo
echo.
echo ========================================
echo   PIENG - Automacao Equatorial
echo   Iniciando sistema...
echo ========================================
echo.

REM Mata processos antigos se existirem
call "%~dp0kill_port_5000.bat" >nul 2>&1
call "%~dp0kill_port_5180.bat" >nul 2>&1

REM Configs sigilosas: puxa do Google Drive (se montado) antes do backend
echo [0/2] Sincronizando configs do Google Drive...
call "%~dp0SYNC_SECRETS_DRIVE.bat" pull >nul 2>&1

REM Inicia backend em janela minimizada
echo [1/2] Iniciando backend Python...
start /min "PIENG Backend" cmd /k "%~dp0start_backend.bat"

REM Aguarda backend ficar online (máximo 20 segundos)
set "BACKEND_OK=0"
for /L %%i in (1,1,20) do (
    timeout /t 1 /nobreak >nul
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "BACKEND_OK=1"
        goto :backend_ready
    )
)
:backend_ready

if "%BACKEND_OK%"=="0" (
    echo [X] Backend nao respondeu. Verifique a janela minimizada.
    pause
    exit /b 1
)

echo [OK] Backend online

REM Inicia frontend em janela minimizada
echo [2/2] Iniciando frontend React...
start /min "PIENG Frontend" cmd /k "%~dp0start_frontend.bat"

REM Aguarda frontend ficar online (máximo 15 segundos)
set "FRONTEND_OK=0"
for /L %%i in (1,1,15) do (
    timeout /t 1 /nobreak >nul
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5180/' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "FRONTEND_OK=1"
        goto :frontend_ready
    )
)
:frontend_ready

if "%FRONTEND_OK%"=="0" (
    echo [!] Frontend nao respondeu. Verifique a janela minimizada.
    pause
    exit /b 1
)

echo [OK] Frontend online
echo.
echo ========================================
echo   Sistema pronto!
echo   Abrindo navegador...
echo ========================================
echo.

REM Abre o navegador
start http://127.0.0.1:5180

REM Aguarda 2 segundos e fecha esta janela
timeout /t 2 /nobreak >nul
exit
