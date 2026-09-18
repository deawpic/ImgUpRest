@echo off
echo ==================================================
echo  Building Real-ESRGAN GUI Standalone for Windows (PyInstaller onedir)
echo  Target Runtime: Python 3.11 (Windows x64)
echo ==================================================

rem Ensure Python 3.11 is installed via uv
uv python install 3.11

rem Ensure dependencies and PyInstaller are installed
uv pip install -e ".[dev]" pyinstaller

rem Run build strictly with Python 3.11 using PyInstaller (onedir)
uv run --python 3.11 pyinstaller --noconfirm "%~dp0pyinstaller_windows.spec"

echo ==================================================
echo  Build Completed! Output directory: dist\RealESRGAN_GUI_Windows
echo  Executable: dist\RealESRGAN_GUI_Windows\RealESRGAN_GUI.exe
echo ==================================================
