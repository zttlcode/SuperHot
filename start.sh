#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ -n "${SUPERHOT_PYTHON:-}" ]; then
  exec "$SUPERHOT_PYTHON" scripts/run.py
elif [ -x .venv/bin/python ]; then
  exec .venv/bin/python scripts/run.py
else
  exec python3 scripts/run.py
fi
