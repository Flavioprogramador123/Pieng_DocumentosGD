@echo off
setlocal
cd /d "%~dp0"

echo [*] Prototipo figura Maps (.temp) — nao altera o projeto principal
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [*] Criando venv local...
    python -m venv .venv
    if errorlevel 1 (
        echo [X] Python nao encontrado
        pause
        exit /b 1
    )
)

echo [*] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt

echo.
echo [*] Gerando figura — coordenadas exemplo Cleidimar / Parque Brasilia 2A
".venv\Scripts\python.exe" gerar_figura_maps.py --lat -16.326990 --lon -48.915934 --zoom 18 --raio 2

if errorlevel 1 (
    echo [X] Falha na geracao
    pause
    exit /b 1
)

echo.
echo [OK] Abra a pasta saida\ para ver a PNG
start "" "%~dp0saida"
pause
