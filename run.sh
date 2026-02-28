#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Activate venv
source .venv/bin/activate

# Build frontend
echo "Building frontend..."
(cd frontend && npm install --silent && npm run build)

# Start server (pass through any args, e.g. --reload --no-browser)
echo "Starting TaleKeeper..."
exec talekeeper serve "$@"
