@echo off
setlocal EnableDelayedExpansion
color 0A
cls

REM ============================================
REM Sistema de Automacao Equatorial Energia
REM Backend pronto ANTES do frontend e do browser
REM ============================================

echo.
echo   ===================================================
echo   ^|   Sistema de Automacao Equatorial Energia      ^|
echo   ===================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [X] ERRO: Python nao encontrado
    echo   [i] Instale Python 3.10 ou superior
    echo.
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [X] ERRO: Node.js nao encontrado
    echo   [i] Instale Node.js
    echo.
    pause
    exit /b 1
)

echo   [1/4] Preparando backend (venv + dependencias)...
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
    echo         Criando ambiente virtual Python...
    python -m venv .venv
    if errorlevel 1 (
        color 0C
        echo   [X] Falha ao criar .venv em backend\
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -q --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -q -r requirements_api.txt
) else (
    ".venv\Scripts\python.exe" -m pip install -q -r requirements_api.txt >nul 2>&1
)
cd /d "%~dp0"
echo         [OK] Backend preparado
echo.

echo   [2/4] Subindo backend e aguardando http://127.0.0.1:5000 ...
call "%~dp0kill_port_5000.bat"
start /min "" cmd /k "%~dp0start_backend.bat"

set "BACKEND_OK=0"
for /L %%i in (1,1,90) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "BACKEND_OK=1"
        goto :backend_ready
    )
    if %%i==30 echo         ... ainda aguardando backend - 30s
    if %%i==60 echo         ... ainda aguardando backend - 60s
    timeout /T 1 /NOBREAK >nul
)
:backend_ready

if "!BACKEND_OK!"=="0" (
    color 0C
    echo.
    echo   [X] Backend nao respondeu em http://127.0.0.1:5000/api/health
    echo       Verifique a janela minimizada "Backend API" ou rode kill_port_5000.bat
    echo.
    pause
    exit /b 1
)
echo         [OK] Backend online
echo.

echo   [3/4] Preparando frontend e subindo Vite...
cd /d "%~dp0equatorial_automation_frontend"
if not exist "node_modules" (
    echo         Instalando pnpm install - primeira vez...
    call pnpm install
    if errorlevel 1 (
        color 0C
        echo   [X] Falha no pnpm install
        cd /d "%~dp0"
        pause
        exit /b 1
    )
) else (
    call pnpm install >nul 2>&1
)
cd /d "%~dp0"
call "%~dp0kill_port_5173.bat"
start /min "" cmd /k "%~dp0start_frontend.bat"

set "FRONTEND_OK=0"
for /L %%i in (1,1,60) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        set "FRONTEND_OK=1"
        goto :frontend_ready
    )
    if %%i==20 echo         ... aguardando Vite - 20s
    if %%i==40 echo         ... aguardando Vite - 40s
    timeout /T 1 /NOBREAK >nul
)
:frontend_ready

if "!FRONTEND_OK!"=="0" (
    color 0E
    echo         [AVISO] Frontend ainda nao respondeu - tentando abrir mesmo assim
    color 0A
) else (
    echo         [OK] Frontend online
)
echo.

echo   [4/4] Abrindo navegador...
start http://127.0.0.1:5173
timeout /T 1 /NOBREAK >nul

cls
color 0A
echo.
echo   ===================================================
echo   ^|        Sistema Iniciado com Sucesso            ^|
echo   ===================================================
echo.
echo   Backend:   http://127.0.0.1:5000  - online
if "!FRONTEND_OK!"=="1" (
    echo   Frontend:  http://127.0.0.1:5173  - online
) else (
    echo   Frontend:  http://127.0.0.1:5173  - iniciando, aguarde a janela Vite
)
echo.
echo   ===================================================
echo   [i] Para parar, feche as janelas Backend e Frontend.
echo   ===================================================
echo.
echo   Pressione qualquer tecla para sair deste console...
pause >nul
