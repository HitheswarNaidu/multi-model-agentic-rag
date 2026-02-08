@echo off
if not exist .venv (
    echo [ERROR] .venv directory not found!
    echo Please run: python -m venv .venv
    pause
    exit /b
)

call .venv\Scripts\activate
python src/cli.py %*
