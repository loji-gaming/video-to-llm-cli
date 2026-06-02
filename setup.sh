#!/bin/bash
# Setup script for video-to-context pipeline
# Creates the Python 3.11 venv and installs all dependencies

set -e

VENV_DIR="${VENV_DIR:-$HOME/.local/share/whisperx-pipeline}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== video-to-context setup ==="
echo "Venv location: $VENV_DIR"

# Check for uv
if ! command -v uv &>/dev/null; then
    echo "Error: 'uv' is required. Install it from https://docs.astral.sh/uv/"
    exit 1
fi

# Create venv with Python 3.11
echo "[1/3] Creating Python 3.11 venv..."
uv venv --python 3.11 "$VENV_DIR"

# Install dependencies
echo "[2/3] Installing dependencies..."
source "$VENV_DIR/bin/activate"
uv pip install whisperx transformers accelerate qwen-vl-utils bitsandbytes Pillow easyocr

# Install script
echo "[3/3] Installing video-to-context script..."
mkdir -p "$HOME/.local/bin"
cp "$SCRIPT_DIR/video-to-context" "$HOME/.local/bin/video-to-context"
chmod +x "$HOME/.local/bin/video-to-context"

echo ""
echo "✅ Setup complete!"
echo "   Activate:  source $VENV_DIR/bin/activate"
echo "   Run:       video-to-context your_video.mkv --language en"
echo "   Help:      video-to-context --help"
