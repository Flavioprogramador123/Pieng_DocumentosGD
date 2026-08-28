@echo off
setlocal EnableDelayedExpansion
color 0A
cls

REM ============================================
REM Sistema de Automacao Equatorial Energia
REM ============================================

echo.
echo   ===================================================
echo   ^|   Sistema de Automacao Equatorial Energia      ^|
echo   ===================================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [X] ERRO: Python nao encontrado
    echo   [!] Instale Python 3.10 ou superior
    echo.
    pause
    exit /b 1
)

REM Verificar Node.js
node --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [X] ERRO: Node.js nao encontrado
    echo   [!] Instale Node.js
    echo.
    pause
    exit /b 1
)

REM Barra de progresso animada
echo   Iniciando sistema...
echo.
echo   [                                        ] 0%%

REM Iniciar Backend
start /min "" cmd /k "%~dp0start_backend.bat"
timeout /T 1 /NOBREAK >nul
cls
echo.
echo   ===================================================
echo   ^|   Sistema de Automacao Equatorial Energia      ^|
echo   ===================================================
echo.
echo   Iniciando sistema...
echo.
echo   [##########                              ] 25%%
timeout /T 1 /NOBREAK >nul

REM Aguardar backend
cls
echo.
echo   ===================================================
echo   ^|   Sistema de Automacao Equatorial Energia      ^|
echo   ===================================================
echo.
echo   Iniciando sistema...
echo.
echo   [####################                    ] 50%%
timeout /T 2 /NOBREAK >nul

REM Iniciar Frontend
start /min "" cmd /k "%~dp0start_frontend.bat"
cls
echo.
echo   ===================================================
echo   ^|   Sistema de Automacao Equatorial Energia      ^|
echo   ===================================================
echo.
echo   Iniciando sistema...
echo.
echo   [##############################          ] 75%%
timeout /T 2 /NOBREAK >nul

REM Abrir navegador
start http://localhost:5173
cls
echo.
echo   ===================================================
echo   ^|   Sistema de Automacao Equatorial Energia      ^|
echo   ===================================================
echo.
echo   Iniciando sistema...
echo.
echo   [########################################] 100%%
timeout /T 1 /NOBREAK >nul

REM Tela final
cls
color 0A
echo.
echo   ===================================================
echo   ^|        Sistema Iniciado com Sucesso            ^|
echo   ===================================================
echo.
echo   Backend:   http://127.0.0.1:5000
echo   Frontend:  http://localhost:5173
echo.
echo   ===================================================
echo   Status da IA:
echo   * Gemini 3.6 Flash: Ativo
echo   * Ollama (opcional): Verificando...
echo   ===================================================
echo.
echo   [i] Para parar o sistema, feche as janelas do
echo       Backend e Frontend que foram abertas.
echo.
echo   Pressione qualquer tecla para sair deste console...
pause >nul
