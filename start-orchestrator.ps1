# start-orchestrator.ps1
$ErrorActionPreference = 'Stop'
cd 'C:\Users\droxa\ReviewReplyOrchestrator'
$env:PYTHONIOENCODING='utf-8'
& 'C:\Users\droxa\ReviewReplyOrchestrator\.venv\Scripts\python.exe' -m uvicorn app:app --host 127.0.0.1 --port 7363 --log-level info
