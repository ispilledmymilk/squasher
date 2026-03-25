#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
if [ ! -d "venv" ]; then
    echo "Run scripts/setup.sh first."
    exit 1
fi
source venv/bin/activate
echo "Starting CodeDecay backend..."
exec python -m api.main
