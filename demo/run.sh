#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
runtime="${VIRTUAL_ENV:-$PWD/.venv}"
if [[ ! -x "$runtime/bin/python" ]]; then python3 -m venv "$runtime"; fi
if ! "$runtime/bin/python" -c 'import uvicorn,fastapi,httpx' 2>/dev/null; then
  "$runtime/bin/python" -m pip install -r requirements.txt
fi
npm ci --no-audit --no-fund
npm run build
exec "$runtime/bin/python" -m uvicorn server:app --host 127.0.0.1 --port "${PORT:-8765}"
