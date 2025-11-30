#!/bin/bash
# Script to run all tests

set -e

echo "🧪 Running TabSage tests"
echo ""

# Install test dependencies if needed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "📦 Installing pytest..."
    pip install pytest pytest-asyncio
fi

# Run tests
echo "🚀 Running tests..."
python3 -m pytest tests/ -v --tb=short

echo ""
echo "✅ Tests completed!"

