@echo off
echo Starting Multimodal RAG Agent...
echo.

if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b
)

if not exist .venv (
    echo [ERROR] .venv directory not found!
    echo Please run: python -m venv .venv
    pause
    exit /b
)

set "RUN_CHECK=0"
if /I "%~1"=="--check" set "RUN_CHECK=1"

set "PYTHONPATH=%CD%;%CD%\src;%PYTHONPATH%"

if "%RUN_CHECK%"=="1" (
    echo Running full setup check...
    .venv\Scripts\python.exe verify_setup.py --mode full
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Full setup check failed.
        pause
        exit /b
    )
) else (
    echo Running quick setup check...
    .venv\Scripts\python.exe verify_setup.py --mode quick
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Quick setup check failed. Run run_app.bat --check for details.
        pause
        exit /b
    )
)

echo Launching Streamlit...
.venv\Scripts\python.exe -m streamlit run app/main.py
pause
