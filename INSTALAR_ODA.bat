@echo off
chcp 65001 >nul
REM =====================================================================
REM  PIENG - ODA File Converter (DXF para DWG compacto)
REM  Converte planta.dxf (~25 MB) em planta.dwg (~2 MB)
REM =====================================================================
title PIENG - Instalar ODA File Converter
color 0B

cd /d "%~dp0"

REM Auto-elevar para administrador (MSI exige)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissao de administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ========================================
echo   PIENG - ODA File Converter
echo ========================================
echo.
echo Necessario para entregar planta.dwg (~2 MB)
echo em vez de planta.dxf (~25 MB) ao cliente.
echo.

REM Ja instalado?
for /f "delims=" %%F in ('dir /s /b "C:\Program Files\ODA\ODAFileConverter.exe" 2^>nul') do (
    echo [OK] ODA ja instalado:
    echo      %%F
    echo.
    pause
    exit /b 0
)

echo [*] ODA nao encontrado. Baixando instalador...
set "MSI=%TEMP%\ODAFileConverter_27.1.msi"

powershell -NoProfile -Command ^
  "try { Invoke-WebRequest -Uri 'https://www.opendesign.com/guestfiles/get?filename=ODAFileConverter_QT6_vc16_amd64dll_27.1.msi' -OutFile '%MSI%' -UseBasicParsing; exit 0 } catch { exit 1 }"

if not exist "%MSI%" (
    color 0C
    echo [X] Falha no download.
    echo     Baixe manualmente em:
    echo     https://www.opendesign.com/guestfiles/oda_file_converter
    echo.
    pause
    exit /b 1
)

echo [OK] Download concluido
echo [*] Instalando (aguarde)...
msiexec /i "%MSI%" /qn /norestart
if %errorlevel% neq 0 (
    color 0C
    echo [X] Falha na instalacao MSI (codigo %errorlevel%)
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul

for /f "delims=" %%F in ('dir /s /b "C:\Program Files\ODA\ODAFileConverter.exe" 2^>nul') do (
    color 0A
    echo.
    echo [OK] ODA File Converter instalado:
    echo      %%F
    echo.
    echo Reinicie a geracao de documentos na web para usar planta.dwg.
    echo.
    pause
    exit /b 0
)

color 0E
echo [!] Instalacao concluida, mas executavel nao localizado.
echo     Verifique em C:\Program Files\ODA\
echo.
pause
exit /b 1
