@echo off
echo ==================================================
echo  Building Real-ESRGAN GUI Standalone with Nuitka
echo  Target Runtime: Python 3.11 (Windows x64)
echo ==================================================

rem Ensure Python 3.11 is installed via uv
uv python install 3.11

rem Ensure dependencies and Nuitka are installed
uv pip install -e ".[dev]"

rem Run standalone build using Nuitka
uv run python -m nuitka ^
  --standalone ^
  --enable-plugin=pyside6 ^
  --include-package=src ^
  --include-package-data=realesrgan_ncnn_py ^
  --include-package=realesrgan_ncnn_py ^
  --include-package=PIL ^
  --include-package=cv2 ^
  --include-package-data=onnxruntime ^
  --include-package=onnxruntime ^
  --windows-console-mode=disable ^
  --output-dir=dist ^
  --output-filename=RealESRGAN_GUI.exe ^
  --assume-yes-for-downloads ^
  --msvc=latest ^
  --lto=no ^
  src\gui\app.py

rem Organize output folder
if exist dist\app.dist (
  if exist dist\RealESRGAN_GUI_Windows rd /s /q dist\RealESRGAN_GUI_Windows
  ren dist\app.dist RealESRGAN_GUI_Windows
)

echo ==================================================
echo  Build Completed!
echo  Output directory: dist\RealESRGAN_GUI_Windows
echo  Executable: dist\RealESRGAN_GUI_Windows\RealESRGAN_GUI.exe
echo ==================================================
