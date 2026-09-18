#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " Building Real-ESRGAN GUI Standalone with Nuitka   "
echo " Target Runtime: Python 3.11 (Linux x86_64)       "
echo "=================================================="

# Ensure Python 3.11 is installed via uv
uv python install 3.11

# Ensure dependencies and Nuitka are installed
uv pip install -e ".[dev]"

# Run standalone build using Nuitka
uv run python -m nuitka \
  --standalone \
  --enable-plugin=pyside6 \
  --include-package=src \
  --include-package-data=realesrgan_ncnn_py \
  --include-package=realesrgan_ncnn_py \
  --include-package=PIL \
  --include-package=cv2 \
  --include-package-data=onnxruntime \
  --include-package=onnxruntime \
  --output-dir=dist \
  --output-filename=RealESRGAN_GUI \
  --assume-yes-for-downloads \
  --lto=no \
  src/gui/app.py

# Organize output folder
if [ -d "dist/app.dist" ]; then
  rm -rf dist/RealESRGAN_GUI_Linux
  mv dist/app.dist dist/RealESRGAN_GUI_Linux
fi

echo "=================================================="
echo " Build Completed!"
echo " Output directory: dist/RealESRGAN_GUI_Linux"
echo " Executable: dist/RealESRGAN_GUI_Linux/RealESRGAN_GUI"
echo "=================================================="
