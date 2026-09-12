#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " Building Real-ESRGAN GUI Standalone for Linux    "
echo " Target Runtime: Python 3.11                      "
echo "=================================================="

# Ensure Python 3.11 is installed via uv
uv python install 3.11

# Ensure pyinstaller is installed in the 3.11 environment
uv pip install --python 3.11 pyinstaller

# Run build strictly with Python 3.11
uv run --python 3.11 pyinstaller --noconfirm packaging/pyinstaller_linux.spec

echo "=================================================="
echo " Build Completed! Output in dist/RealESRGAN_GUI_Linux"
echo " To run: ./dist/RealESRGAN_GUI_Linux/RealESRGAN_GUI"
echo "=================================================="
