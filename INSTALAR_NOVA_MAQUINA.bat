@echo off
REM =====================================================================
REM  PIENG - Instalação em Nova Máquina
REM  Execute este arquivo COMO ADMINISTRADOR na primeira vez
REM =====================================================================
title PIENG - Instalacao
color 0E

echo.
echo ========================================
echo   PIENG - Instalacao em Nova Maquina
echo ========================================
echo.

cd /d "%~dp0"

REM Verifica se é administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [X] ERRO: Execute como Administrador!
    echo.
    echo Clique com botao direito no arquivo e selecione:
    echo "Executar como administrador"
    echo.
    pause
    exit /b 1
)

echo [1/7] Verificando dependencias...
echo.

REM Verifica Python
echo [*] Python...
python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('python --version') do echo     [OK] %%i
) else (
    echo     [X] Python NAO encontrado!
    echo     Instale Python 3.11+ de: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Verifica Node.js
echo [*] Node.js...
node --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('node --version') do echo     [OK] Node.js %%i
) else (
    echo     [X] Node.js NAO encontrado!
    echo     Instale Node.js 20+ de: https://nodejs.org/
    pause
    exit /b 1
)

REM Verifica/Instala pnpm
echo [*] pnpm...
pnpm --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('pnpm --version') do echo     [OK] pnpm v%%i
) else (
    echo     [!] pnpm nao encontrado. Instalando...
    npm install -g pnpm
    if %errorlevel% neq 0 (
        echo     [X] Falha ao instalar pnpm
        pause
        exit /b 1
    )
    echo     [OK] pnpm instalado
)

echo.
echo [2/7] Criando ambiente virtual Python...
cd backend
if exist ".venv" (
    echo     [!] Ambiente virtual ja existe
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo     [X] Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
    echo     [OK] Ambiente virtual criado
)

echo.
echo [3/7] Instalando dependencias Python...
call .venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo     [X] Falha ao instalar dependencias Python
    pause
    exit /b 1
)
echo     [OK] Dependencias Python instaladas
call deactivate

cd ..

echo.
echo [4/7] Instalando dependencias Node.js...
cd equatorial_automation_frontend
pnpm install
if %errorlevel% neq 0 (
    echo     [X] Falha ao instalar dependencias Node.js
    pause
    exit /b 1
)
echo     [OK] Dependencias Node.js instaladas

cd ..

echo.
echo [5/7] Configurando arquivos .env...
if not exist ".env" (
    echo     [*] Criando .env na raiz...
    copy ".env.example" ".env" >nul 2>&1
    echo     [!] IMPORTANTE: Edite o arquivo .env e configure suas chaves
)

if not exist "backend\.env" (
    echo     [*] Criando backend\.env...
    copy "backend\.env.example" "backend\.env" >nul 2>&1
    echo     [!] IMPORTANTE: Edite o arquivo backend\.env e configure suas chaves
)

echo     [OK] Arquivos .env criados

echo.
echo [6/7] Inicializando banco de dados...
cd backend
call .venv\Scripts\activate.bat
python -c "from catalog_db import init_db; init_db()"
if %errorlevel% neq 0 (
    echo     [!] Aviso: Banco de dados pode precisar de atencao
) else (
    echo     [OK] Banco de dados inicializado
)
call deactivate
cd ..

echo.
echo [7/7] Criando atalhos...

REM Cria atalho na área de trabalho usando PowerShell
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\PIENG - Automacao Equatorial.lnk'); $s.TargetPath = '%~dp0PIENG.vbs'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'PIENG - Sistema de Automacao Equatorial'; $s.Save()"

if %errorlevel%==0 (
    echo     [OK] Atalho criado na area de trabalho
) else (
    echo     [!] Nao foi possivel criar atalho automaticamente
)

echo.
echo ========================================
echo   Instalacao concluida!
echo ========================================
echo.
echo PROXIMOS PASSOS:
echo.
echo 1. Edite os arquivos .env e backend\.env com suas configuracoes
echo 2. Instale o Google Drive for Desktop
echo 3. Use o atalho "PIENG - Automacao Equatorial" na area de trabalho
echo.
echo Para mais informacoes, leia o arquivo LEIA-ME_INSTALACAO.md
echo.
pause
