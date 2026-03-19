# Review Reply Orchestrator - Ollama Installer (Windows)
# Run this script to install Ollama and download the AI model
# Usage: .\install_ollama.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Review Reply Orchestrator" -ForegroundColor Cyan
Write-Host "  Ollama AI Model Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script requires Administrator privileges." -ForegroundColor Yellow
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Ollama is already installed
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue

if ($ollamaPath) {
    Write-Host "Ollama is already installed!" -ForegroundColor Green
    Write-Host "Location: $($ollamaPath.Source)" -ForegroundColor Gray
} else {
    Write-Host "Downloading Ollama..." -ForegroundColor Yellow
    
    # Create temp directory
    $tempDir = "$env:TEMP\ollama_install"
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    
    # Download Ollama installer
    $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
    $installerPath = "$tempDir\OllamaSetup.exe"
    
    try {
        Invoke-WebRequest -Uri $ollamaUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "Download complete!" -ForegroundColor Green
    } catch {
        Write-Host "Failed to download Ollama: $_" -ForegroundColor Red
        Write-Host "Please download manually from https://ollama.com" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Run installer
    Write-Host "Installing Ollama..." -ForegroundColor Yellow
    Write-Host "Please follow the installer prompts..." -ForegroundColor Gray
    
    Start-Process -FilePath $installerPath -Wait
    
    # Clean up
    Remove-Item -Recurse -Force $tempDir
    
    Write-Host "Ollama installed successfully!" -ForegroundColor Green
}

# Wait for Ollama service to start
Write-Host ""
Write-Host "Waiting for Ollama service to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if Ollama is running
$maxAttempts = 30
$attempt = 0
$ollamaRunning = $false

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434" -UseBasicParsing -TimeoutSec 2
        $ollamaRunning = $true
        break
    } catch {
        $attempt++
        Start-Sleep -Seconds 2
    }
}

if (-not $ollamaRunning) {
    Write-Host "Ollama service may not be running." -ForegroundColor Yellow
    Write-Host "Try running: ollama serve" -ForegroundColor Yellow
} else {
    Write-Host "Ollama service is running!" -ForegroundColor Green
}

# Download the AI model
Write-Host ""
Write-Host "Downloading AI model (qwen2.5:7b-instruct)..." -ForegroundColor Yellow
Write-Host "This may take a few minutes (approx. 4GB download)..." -ForegroundColor Gray
Write-Host ""

$modelName = "qwen2.5:7b-instruct"

try {
    & ollama pull $modelName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Installation Complete!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Model: $modelName" -ForegroundColor White
        Write-Host "  Ollama URL: http://127.0.0.1:11434" -ForegroundColor White
        Write-Host ""
        Write-Host "  You can now start the Review Reply Orchestrator:" -ForegroundColor Cyan
        Write-Host "  python app.py" -ForegroundColor Yellow
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "Model download may have failed." -ForegroundColor Yellow
        Write-Host "Try manually: ollama pull $modelName" -ForegroundColor Yellow
        Write-Host ""
    }
} catch {
    Write-Host ""
    Write-Host "Could not download model: $_" -ForegroundColor Yellow
    Write-Host "Try manually: ollama pull $modelName" -ForegroundColor Yellow
    Write-Host ""
}

Read-Host "Press Enter to exit"