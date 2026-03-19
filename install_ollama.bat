@echo off
REM Review Reply Orchestrator - Ollama Installer (Windows Batch)
REM Run this script to install Ollama and download the AI model
REM Usage: install_ollama.bat

echo ========================================
echo   Review Reply Orchestrator
echo   Ollama AI Model Installer
echo ========================================
echo.

REM Check if Ollama is already installed
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama is already installed!
    where ollama
    goto :download_model
)

echo Downloading Ollama...
echo.

REM Create temp directory
if not exist "%TEMP%\ollama_install" mkdir "%TEMP%\ollama_install"

REM Download Ollama using curl (available on Windows 10+)
curl -L -o "%TEMP%\ollama_install\OllamaSetup.exe" https://ollama.com/download/OllamaSetup.exe

if %errorlevel% neq 0 (
    echo Failed to download Ollama
    echo Please download manually from https://ollama.com
    pause
    exit /b 1
)

echo Download complete!
echo.
echo Installing Ollama...
echo Please follow the installer prompts...
echo.

REM Run installer
"%TEMP%\ollama_install\OllamaSetup.exe"

REM Clean up
rmdir /s /q "%TEMP%\ollama_install"

echo Ollama installed successfully!

:download_model
echo.
echo Waiting for Ollama service to start...
timeout /t 5 /nobreak >nul

REM Check if Ollama is running
curl -s http://127.0.0.1:11434 >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama service may not be running.
    echo Try running: ollama serve
) else (
    echo Ollama service is running!
)

echo.
echo Downloading AI model (qwen2.5:7b-instruct)...
echo This may take a few minutes (approx. 4GB download)...
echo.

ollama pull qwen2.5:7b-instruct

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Installation Complete!
    echo ========================================
    echo.
    echo   Model: qwen2.5:7b-instruct
    echo   Ollama URL: http://127.0.0.1:11434
    echo.
    echo   You can now start the Review Reply Orchestrator:
    echo   python app.py
    echo.
) else (
    echo.
    echo Model download may have failed.
    echo Try manually: ollama pull qwen2.5:7b-instruct
    echo.
)

pause