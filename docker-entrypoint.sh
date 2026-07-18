#!/bin/bash
set -e -x

echo "[entrypoint] START"
echo "[entrypoint] PORT=$PORT TRADINGAGENTS_DATA_DIR=$TRADINGAGENTS_DATA_DIR"

mkdir -p "$TRADINGAGENTS_DATA_DIR" 2>/dev/null || true

echo "[entrypoint] Starting uvicorn..."
exec .venv/bin/python -m uvicorn web.server.app:create_app --host 0.0.0.0 --port "$PORT"
