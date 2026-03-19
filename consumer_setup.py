"""
DroxAI Review Reply Orchestrator - Consumer Package Creator
===========================================================

Creates a ready-to-distribute consumer package with:
- Simplified install scripts
- Only essential files
- Consumer-friendly README

Usage: python consumer_setup.py
"""

import os
import shutil
import sys

def create_consumer_package():
    """Create a consumer-ready distribution package."""
    
    print("=" * 60)
    print("  DroxAI Review Reply Orchestrator")
    print("  Consumer Package Creator")
    print("=" * 60)
    print()
    
    # Define package directory
    package_dir = "consumer_package"
    
    # Clean existing package
    if os.path.exists(package_dir):
        print(f"Cleaning existing {package_dir}/...")
        shutil.rmtree(package_dir)
    
    # Create package directory
    os.makedirs(package_dir)
    print(f"Created {package_dir}/")
    
    # Essential files to copy
    essential_files = [
        "app.py",
        "automation_service.py",
        "browser_automation.py",
        "monitor.py",
        "google_api.py",
        "config.json",
        "engine.env",
        "requirements.txt",
        "README.md",
    ]
    
    # Essential directories to copy
    essential_dirs = [
        "clients",
        "data",
        "logs",
        "outbox",
        "tokens",
    ]
    
    # Copy files
    print("\nCopying essential files...")
    for file in essential_files:
        if os.path.exists(file):
            shutil.copy2(file, package_dir)
            print(f"  ✓ {file}")
        else:
            print(f"  ⚠ {file} (not found, skipping)")
    
    # Copy directories
    print("\nCopying essential directories...")
    for dir_name in essential_dirs:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join(package_dir, dir_name))
            print(f"  ✓ {dir_name}/")
        else:
            os.makedirs(os.path.join(package_dir, dir_name))
            print(f"  ✓ {dir_name}/ (created empty)")
    
    # Create consumer install script (Windows)
    install_bat = """@echo off
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
"""
    
    with open(os.path.join(package_dir, "install.bat"), "w") as f:
        f.write(install_bat)
    print("\n✓ Created install.bat (Windows)")
    
    # Create consumer install script (Mac/Linux)
    install_sh = """#!/bin/bash
echo "========================================"
echo "  DroxAI Review Reply Orchestrator"
echo "  Consumer Installer"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed!"
    echo "Please install Python 3.9+ from https://python.org"
    exit 1
fi

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Failed to install dependencies"
    exit 1
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "To start the application:"
echo "  python3 app.py"
echo ""
echo "Then open your browser to:"
echo "  http://127.0.0.1:7363"
echo ""
"""
    
    with open(os.path.join(package_dir, "install.sh"), "w") as f:
        f.write(install_sh)
    print("✓ Created install.sh (Mac/Linux)")
    
    # Create consumer README
    consumer_readme = """# Review Reply Orchestrator - Consumer Edition

## What This Does

Automatically replies to your Google Business reviews using AI. Just enter your Google Business credentials once, and the software will:
- Check for new reviews every hour
- Generate professional, personalized replies
- Post them automatically to Google Business

## Quick Start (Windows)

1. Double-click `install.bat`
2. Wait for installation to complete
3. Run: `python app.py`
4. Open your browser to: http://127.0.0.1:7363

## Quick Start (Mac/Linux)

1. Open Terminal in this folder
2. Run: `chmod +x install.sh && ./install.sh`
3. Run: `python3 app.py`
4. Open your browser to: http://127.0.0.1:7363

## First-Time Setup

1. Open http://127.0.0.1:7363 in your browser
2. Enter your Google Business email and password
3. Click "Save & Start Automation"
4. That's it! The software will now automatically reply to reviews

## Requirements

- Python 3.9 or higher
- Google Chrome (for browser automation)
- Ollama (for AI - optional, install separately)

## Support

Email: droxai25@outlook.com
Website: https://droxai.com

---

Built by DroxAI LLC
"""
    
    with open(os.path.join(package_dir, "README_CONSUMER.md"), "w") as f:
        f.write(consumer_readme)
    print("✓ Created README_CONSUMER.md")
    
    # Create .gitkeep for empty directories
    for dir_name in essential_dirs:
        gitkeep = os.path.join(package_dir, dir_name, ".gitkeep")
        if not os.path.exists(gitkeep):
            with open(gitkeep, "w") as f:
                pass
    
    print("\n" + "=" * 60)
    print("  Consumer Package Created Successfully!")
    print("=" * 60)
    print(f"\n  Location: {os.path.abspath(package_dir)}/")
    print("\n  To distribute:")
    print("  1. Zip the consumer_package folder")
    print("  2. Send to customers")
    print("  3. They double-click install.bat (Windows)")
    print("     or run ./install.sh (Mac/Linux)")
    print()

if __name__ == "__main__":
    create_consumer_package()