#!/bin/bash
set -e
echo "Setting up CodeDecay..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.10+"
    exit 1
fi
echo "✓ Python $(python3 --version) found"

# Check Node.js (optional for extension)
if command -v node &> /dev/null; then
    echo "✓ Node.js $(node --version) found"
else
    echo "Node.js not found. Install for VS Code extension development."
fi

# Project root = parent of scripts/
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Backend venv
echo "Setting up Python backend..."
mkdir -p backend
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate
pip install --upgrade pip
pip install -r ../requirements.txt
echo "✓ Backend dependencies installed"

# .env
cd "$ROOT"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env. Add OPENAI_API_KEY if you use LLM features."
fi

# Data dirs
mkdir -p data/vectordb data/models
echo "✓ Data directories created"

# Extension
if [ -d "extension" ] && command -v npm &> /dev/null; then
    echo "Setting up VS Code extension..."
    cd extension && npm install && cd "$ROOT"
    echo "✓ Extension dependencies installed"
fi

echo ""
echo "Setup complete."
echo "Next:"
echo "  1. Start backend: cd backend && source venv/bin/activate && python -m api.main"
echo "  2. (Optional) Seed vector DB: python scripts/seed_data.py"
echo "  3. Open extension/ in VS Code and press F5 to run the extension"
