import multiprocessing
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.gui.theme import LIGHT_THEME

# Set environment before any native init
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"


def main():
    # Critical for Windows PyInstaller frozen binaries:
    # Must be called before anything else to intercept multiprocessing worker processes
    # and prevent recursively spawning multiple GUI windows!
    multiprocessing.freeze_support()

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.lastWindowClosed.connect(app.quit)
    app.setStyle("Fusion")
    app.setStyleSheet(LIGHT_THEME)

    window = MainWindow()
    window.show()

    exit_code = app.exec()

    # Flush standard streams and immediately terminate the process to prevent
    # hanging on lingering native C++ thread pools (e.g. OpenMP, Vulkan driver, ONNX Runtime)
    try:
        if sys.stdout is not None:
            sys.stdout.flush()
        if sys.stderr is not None:
            sys.stderr.flush()
    except Exception:
        pass
    os._exit(exit_code)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
