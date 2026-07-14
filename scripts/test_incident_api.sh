#!/usr/bin/env bash
set -euo pipefail
curl -s -X POST http://localhost:8000/incidents/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "inc_checkout_001",
    "service": "checkout-api",
    "namespace": "demo",
    "symptoms": ["Pod is in CrashLoopBackOff"],
    "evidence": [
      {"source":"kubernetes.event","summary":"Back-off restarting failed container checkout-api"},
      {"source":"kubernetes.log","summary":"RuntimeError: Missing required environment variable REDIS_URL"},
      {"source":"git.diff","summary":"Latest commit changed environment variable mapping for checkout-api"}
    ]
  }' | python3 -m json.tool
