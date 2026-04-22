#!/bin/sh
set -e

case "$DEPLOY_MODE" in
  lambda)
    exec python -m awslambdaric "$@"
    ;;
  local)
    exec python entrypoints/local.py
    ;;
  cli)
    exec python entrypoints/cli.py
    ;;
  *)
    exec python -m uvicorn entrypoints.fastapi_app:app --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
esac
