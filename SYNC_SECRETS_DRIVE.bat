@echo off
REM Sincroniza configs sigilosas (gitignored) com Google Drive Desktop
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo [X] Ambiente Python nao encontrado. Execute INICIAR_SISTEMA.bat uma vez.
    exit /b 1
)

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=pull"

".venv\Scripts\python.exe" local_secrets_sync.py %ACTION%
exit /b %ERRORLEVEL%
