#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

"$REPO_ROOT/.venv/bin/zensical" build
echo "Docs available at http://127.0.0.1:8080"
python3 -m http.server -d "$REPO_ROOT/site" 8080
