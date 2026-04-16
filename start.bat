@echo off
echo ========================================
echo   Locadora Dashboard - Iniciando...
echo ========================================

:: Backend
echo [1/2] Iniciando backend FastAPI na porta 8000...
start "Locadora Backend" cmd /k "cd /d %~dp0backend && python -m pip install -r requirements.txt -q && python -m uvicorn main:app --reload --port 8000"

:: Aguarda o backend subir
timeout /t 4 /nobreak >nul

:: Frontend
echo [2/2] Iniciando frontend React na porta 5173...
start "Locadora Frontend" cmd /k "cd /d %~dp0frontend && npm install --silent && npm run dev"

echo.
echo ========================================
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo ========================================
timeout /t 6 /nobreak >nul
start http://localhost:5173
