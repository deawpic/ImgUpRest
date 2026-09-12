# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files("realesrgan_ncnn_py")
binaries = collect_dynamic_libs("realesrgan_ncnn_py")

project_root = os.path.abspath(os.path.join(SPECPATH, ".."))
entry_point = os.path.join(project_root, "src", "gui", "app.py")

a = Analysis(
    [entry_point],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "realesrgan_ncnn_py",
        "PIL",
        "cv2",
        "onnxruntime",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtPdf",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3D",
        "PySide6.QtMultimedia",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtXml",
        "tkinter",
        "matplotlib",
        "scipy",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RealESRGAN_GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="RealESRGAN_GUI_Linux",
)
