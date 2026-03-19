#!/bin/bash
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
