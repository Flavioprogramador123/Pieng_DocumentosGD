@echo off
echo ========================================
echo  Sistema Completo - Automacao Equatorial
echo ========================================
echo.
echo Iniciando Backend e Frontend...
echo Backend:  http://127.0.0.1:5000
echo Frontend: http://localhost:5173
echo.

start "Backend API - Equatorial" cmd /k "%~dp0start_backend.bat"
timeout /t 3 /nobreak >nul
start "Frontend React - Equatorial" cmd /k "%~dp0start_frontend.bat"

echo.
echo Aguarde alguns segundos e acesse http://localhost:5173
echo.
pause
