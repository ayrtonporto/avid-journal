#!/bin/bash
# AViD Journal - Setup Script
# Run this after cloning the repository

echo "=================================="
echo "AViD Journal - Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Error: Python 3.8+ required"
    exit 1
fi

echo "✓ Python version OK"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  venv already exists, skipping creation"
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directory structure..."
mkdir -p tests/golden_datasets
mkdir -p examples
mkdir -p cache
mkdir -p logs
echo "✓ Directories created"
echo ""

# Create .env template
if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    cat > .env << EOF
# AViD Journal - Environment Variables
# Copy this to .env and fill in your values

# Claude API (for LLM judge)
CLAUDE_API_KEY=your_api_key_here

# Optional: Semantic Scholar API
# (Not required for basic usage)
# SEMANTIC_SCHOLAR_API_KEY=

# Database
DATABASE_PATH=avid.db

# Paths
CACHE_DIR=./cache
LOG_DIR=./logs
EOF
    echo "✓ .env template created"
    echo "  → Edit .env with your API keys"
else
    echo "⚠️  .env already exists, skipping"
fi
echo ""

# Success message
echo "=================================="
echo "✅ Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run tests: pytest tests/"
echo "3. Try the parser: python src/parser/parse_tex.py examples/sample.tex"
echo ""
echo "For more info, see README.md"
echo ""
