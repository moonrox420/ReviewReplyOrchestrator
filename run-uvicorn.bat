@echo off
cd /d "C:\Users\droxa\ReviewReplyOrchestrator"
"C:\Users\droxa\ReviewReplyOrchestrator\.venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 7363 --log-level info
