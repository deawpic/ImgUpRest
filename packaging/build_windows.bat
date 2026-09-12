@echo off
echo ==================================================
echo  Building Real-ESRGAN GUI Standalone for Windows
echo  Target Runtime: Python 3.11
echo ==================================================

rem Ensure Python 3.11 is installed via uv
uv python install 3.11

rem Ensure pyinstaller is installed in the 3.11 environment
uv pip install --python 3.11 pyinstaller

rem Run build strictly with Python 3.11
uv run --python 3.11 pyinstaller --noconfirm packaging\pyinstaller_windows.spec

echo ==================================================
echo  Build Completed! Output in dist\RealESRGAN_GUI_Windows
echo  To run: dist\RealESRGAN_GUI_Windows\RealESRGAN_GUI.exe
echo ==================================================
