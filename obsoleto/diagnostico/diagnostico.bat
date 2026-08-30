@echo off
echo ========================================
echo  Diagnostico do Sistema
echo ========================================
echo.

echo [1/6] Python
python --version 2>nul || echo   ERRO: Python nao encontrado
echo.

echo [2/6] Node.js
node --version 2>nul || echo   ERRO: Node.js nao encontrado
echo.

echo [3/6] pnpm
pnpm --version 2>nul || echo   ERRO: pnpm nao encontrado
echo.

echo [4/6] Estrutura
if exist "backend\api_server.py" (echo   OK: backend\api_server.py) else (echo   ERRO: backend ausente)
if exist "backend\gerar_documentos.py" (echo   OK: backend\gerar_documentos.py) else (echo   ERRO: gerador ausente)
if exist "equatorial_automation_frontend\package.json" (echo   OK: frontend) else (echo   ERRO: frontend ausente)
if exist "templates\modelo_procuracao_marcadores.docx" (echo   OK: templates) else (echo   ERRO: templates ausentes)
echo.

echo [5/6] venv do backend
if exist "backend\.venv\Scripts\python.exe" (
    echo   OK: backend\.venv
) else (
    echo   AVISO: rode start_backend.bat para criar o venv
)
echo.

echo [6/6] node_modules do frontend
if exist "equatorial_automation_frontend\node_modules" (
    echo   OK: dependencias instaladas
) else (
    echo   AVISO: rode pnpm install em equatorial_automation_frontend
)
echo.

echo ========================================
echo  Diagnostico concluido
echo ========================================
pause
