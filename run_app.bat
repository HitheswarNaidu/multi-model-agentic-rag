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

call .venv\Scripts\activate
echo Environment activated.

echo Checking setup...
python verify_setup.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Setup check failed.
    pause
    exit /b
)

echo.
echo Launching Streamlit...
streamlit run app/main.py
pause
