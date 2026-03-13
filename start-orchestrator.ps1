# start-orchestrator.ps1
$ErrorActionPreference = 'Stop'
cd 'C:\Users\droxa\ReviewReplyOrchestrator'
$env:PYTHONIOENCODING='utf-8'

# Ensure required directories exist
New-Item -ItemType Directory -Force -Path 'C:\Users\droxa\ReviewReplyOrchestrator\tokens' | Out-Null
New-Item -ItemType Directory -Force -Path 'C:\Users\droxa\ReviewReplyOrchestrator\data' | Out-Null
New-Item -ItemType Directory -Force -Path 'C:\Users\droxa\ReviewReplyOrchestrator\logs' | Out-Null

& 'C:\Users\droxa\ReviewReplyOrchestrator\.venv\Scripts\python.exe' -m uvicorn app:app --host 127.0.0.1 --port 7363 --log-level info
