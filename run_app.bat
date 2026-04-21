@echo off
echo Starting Multimodal RAG Agent...
echo.

if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b
)

set "PYTHONPATH=%CD%;%CD%\src;%PYTHONPATH%"

echo Running setup check...
.venv\Scripts\python.exe verify_setup.py --mode quick
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Setup check failed.
    pause
    exit /b
)

echo.
echo Starting FastAPI backend on port 8000...
start "FastAPI Backend" cmd /k ".venv\Scripts\python.exe -m uvicorn api.server:app --reload --port 8000"

echo Starting Next.js frontend on port 3000...
cd frontend
start "Next.js Frontend" cmd /k "npm run dev"
cd ..

echo.
echo [READY] Backend: http://localhost:8000
echo [READY] Frontend: http://localhost:3000
echo.
pause
