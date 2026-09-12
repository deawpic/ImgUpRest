import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Set environment before any native init
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

from src.gui.main_window import MainWindow
from src.gui.theme import LIGHT_THEME


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
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
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(exit_code)


if __name__ == "__main__":
    main()
