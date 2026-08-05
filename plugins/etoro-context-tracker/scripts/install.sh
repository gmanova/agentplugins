#!/usr/bin/env bash
# Cross-platform entrypoint (macOS / Linux). Windows: use install.ps1 or call install.py.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Need python3 on PATH" >&2
  exit 1
fi
exec "$PY" "$ROOT/install.py" "$@"
