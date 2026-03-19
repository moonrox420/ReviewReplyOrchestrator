#!/bin/bash
# Review Reply Orchestrator - Ollama Installer (Mac/Linux)
# Run this script to install Ollama and download the AI model
# Usage: chmod +x install_ollama.sh && ./install_ollama.sh

echo "========================================"
echo "  Review Reply Orchestrator"
echo "  Ollama AI Model Installer"
echo "========================================"
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Detected OS: $OS ($ARCH)"

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "Ollama is already installed!"
    echo "Location: $(which ollama)"
else
    echo "Installing Ollama..."
    
    if [ "$OS" = "Darwin" ]; then
        # macOS
        echo "macOS detected - downloading Ollama..."
        curl -fsSL https://ollama.com/download/Ollama-darwin.zip -o /tmp/ollama.zip
        
        if [ $? -ne 0 ]; then
            echo "Failed to download Ollama"
            echo "Please download manually from https://ollama.com"
            exit 1
        fi
        
        echo "Extracting..."
        unzip -q /tmp/ollama.zip -d /tmp/
        
        echo "Installing to Applications..."
        cp -r /tmp/Ollama.app /Applications/
        
        rm /tmp/ollama.zip
        rm -rf /tmp/Ollama.app
        
        echo "Ollama installed to /Applications/Ollama.app"
        echo "Please launch Ollama from Applications to complete setup"
        
    elif [ "$OS" = "Linux" ]; then
        # Linux
        echo "Linux detected - installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        
        if [ $? -ne 0 ]; then
            echo "Failed to install Ollama"
            echo "Please install manually from https://ollama.com"
            exit 1
        fi
        
        echo "Ollama installed successfully!"
    else
        echo "Unsupported OS: $OS"
        echo "Please install manually from https://ollama.com"
        exit 1
    fi
fi

# Wait for Ollama service to start
echo ""
echo "Waiting for Ollama service to start..."
sleep 5

# Check if Ollama is running
max_attempts=30
attempt=0
ollama_running=false

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://127.0.0.1:11434 > /dev/null 2>&1; then
        ollama_running=true
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ "$ollama_running" = false ]; then
    echo "Ollama service may not be running."
    echo "Try running: ollama serve"
else
    echo "Ollama service is running!"
fi

# Download the AI model
echo ""
echo "Downloading AI model (qwen2.5:7b-instruct)..."
echo "This may take a few minutes (approx. 4GB download)..."
echo ""

model_name="qwen2.5:7b-instruct"

ollama pull "$model_name"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  Installation Complete!"
    echo "========================================"
    echo ""
    echo "  Model: $model_name"
    echo "  Ollama URL: http://127.0.0.1:11434"
    echo ""
    echo "  You can now start the Review Reply Orchestrator:"
    echo "  python app.py"
    echo ""
else
    echo ""
    echo "Model download may have failed."
    echo "Try manually: ollama pull $model_name"
    echo ""
fi