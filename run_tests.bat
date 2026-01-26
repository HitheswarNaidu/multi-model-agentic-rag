@echo off
echo Running Multimodal RAG Tests...
echo.

if not exist .venv (
    echo [ERROR] .venv directory not found!
    echo Please run: python -m venv .venv
    pause
    exit /b
)

call .venv\Scripts\activate

echo 1. Running Real Logic Tests (Chunking, Intent, BM25)...
python -m pytest tests/test_real_logic.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo.
echo 2. Running Validator Tests (Numeric, Currency, Robustness)...
python -m pytest tests/test_validator_logic.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo.
echo 3. Running Full Architecture Mock Tests...
python -m pytest tests/test_full_architecture.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo.
echo 4. Running Existing Test Suite...
python -m pytest tests/test_e2e.py
if %ERRORLEVEL% NEQ 0 goto :fail

echo.
echo [SUCCESS] All tests passed!
pause
exit /b 0

:fail
echo.
echo [FAILURE] Tests failed. See output above.
pause
exit /b 1
