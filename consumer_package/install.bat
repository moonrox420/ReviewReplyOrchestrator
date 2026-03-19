@echo off
echo ========================================
echo   DroxAI Review Reply Orchestrator
echo   Consumer Installer
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed!
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo Installing Python dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To start the application:
echo   python app.py
echo.
echo Then open your browser to:
echo   http://127.0.0.1:7363
echo.
pause
