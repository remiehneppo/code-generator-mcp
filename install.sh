#!/bin/bash

# Exit on any error
set -e

# Help / usage
show_help() {
    echo "Usage: ./install.sh <agent_type> [global|local]"
    echo "Supported agent types: [claude-desktop|claude-code|cursor|github-copilot|codex|windsurf|zed|agy]"
    echo ""
    echo "This script builds the MCP server into a standalone binary,"
    echo "copies it to \$HOME/.local/bin/code-generator-mcp, and configures"
    echo "the specified coding agent to use it."
    exit 1
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    show_help
fi

AGENT=$1
SCOPE=${2:-global}

case "$AGENT" in
    claude-desktop|claude-code|cursor|github-copilot|codex|windsurf|zed|agy)
        ;;
    *)
        echo "Error: Invalid agent type '$AGENT'."
        show_help
        ;;
esac

case "$SCOPE" in
    global|local)
        ;;
    *)
        echo "Error: Invalid scope '$SCOPE'. Must be 'global' or 'local'."
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

echo "Step 5: Configuring agent '$AGENT' (Scope: $SCOPE)..."
python scripts/configure_agent.py "$AGENT" "$HOME/.local/bin/code-generator-mcp" --scope "$SCOPE"

echo ""
echo "=========================================================="
echo "Installation and configuration complete!"
echo "Binary installed at: $HOME/.local/bin/code-generator-mcp"
echo "Agent configured: $AGENT (Scope: $SCOPE)"
echo "=========================================================="
