#!/bin/bash

# Exit on any error
set -e

# Help / usage
show_help() {
    echo "Usage: ./install.sh [codex|github-copilot|agy|claude-code]"
    echo ""
    echo "This script builds the MCP server into a standalone binary,"
    echo "copies it to \$HOME/.local/bin/code-generator-mcp, and configures"
    echo "the specified coding agent to use it."
    exit 1
}

if [ "$#" -ne 1 ]; then
    show_help
fi

AGENT=$1

case "$AGENT" in
    codex|github-copilot|agy|claude-code)
        ;;
    *)
        echo "Error: Invalid agent type '$AGENT'."
        show_help
        ;;
esac

echo "Step 1: Preparing virtual environment..."
if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found. Creating one..."
    if ! python3 -m venv .venv 2>/dev/null; then
        echo "Error: Failed to create virtual environment."
        echo "This is typically caused by a missing 'python3-venv' package."
        echo "Please install it using: sudo apt update && sudo apt install python3-venv"
        exit 1
    fi
fi

source .venv/bin/activate

echo "Step 2: Installing dependencies & PyInstaller..."
pip install -r requirements.txt
pip install pyinstaller

echo "Step 3: Building standalone executable using PyInstaller..."
pyinstaller --onefile --name code-generator-mcp --clean src/code_generator_mcp/server.py

# Check if build succeeded
if [ ! -f "dist/code-generator-mcp" ]; then
    echo "Error: Build failed. Standalone executable not found in dist/."
    exit 1
fi

echo "Step 4: Installing executable to \$HOME/.local/bin..."
mkdir -p "$HOME/.local/bin"
cp dist/code-generator-mcp "$HOME/.local/bin/code-generator-mcp"
chmod +x "$HOME/.local/bin/code-generator-mcp"

echo "Step 5: Configuring agent '$AGENT'..."
python3 scripts/configure_agent.py "$AGENT" "$HOME/.local/bin/code-generator-mcp"

echo ""
echo "=========================================================="
echo "Installation and configuration complete!"
echo "Binary installed at: $HOME/.local/bin/code-generator-mcp"
echo "Agent configured: $AGENT"
echo "=========================================================="
