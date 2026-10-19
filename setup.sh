#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3.13 -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r backend/requirements.txt
(cd frontend && npm ci && npm run build)
printf '%s\n' 'Setup complete. Run sh start.sh to start SuperHot.'
