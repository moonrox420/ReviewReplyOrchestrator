RUN:
  Start now:   "C:\Users\droxa\ReviewReplyOrchestrator\start-orchestrator.ps1"
  Test lead:   "C:\Users\droxa\ReviewReplyOrchestrator\test-lead.ps1"
  Test full:   "C:\Users\droxa\ReviewReplyOrchestrator\test-full.ps1"
  Health:      http://127.0.0.1:7364/healthz

CONFIG:
  Edit: C:\Users\droxa\ReviewReplyOrchestrator\engine.env
  SMTP: set SMTP_ENABLED=true and fill SMTP_* to send email; otherwise .eml files drop to C:\Users\droxa\ReviewReplyOrchestrator\outbox\

ENDPOINTS:
  POST /lead-intake      -> generates 5-sample PDF/DOCX + emails client
  POST /intake-submit    -> full run (up to 50) PDF/DOCX + emails client
  POST /generate_replies -> core engine
  POST /webhook/stripe   -> accepts checkout.session.completed (when forwarded)
  GET  /healthz          -> health

PORT:
  Using 7364 (dedicated). Override by setting ENGINE_PORT in C:\Users\droxa\ReviewReplyOrchestrator\engine.env and restart.
