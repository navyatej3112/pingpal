#!/bin/bash
# Helper script to run PingPal collector

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

# Check for virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Warning: No virtual environment found (venv or .venv)"
    echo "Make sure dependencies are installed: pip install -r requirements.txt"
    echo ""
fi

# Run collector
python collector.py

