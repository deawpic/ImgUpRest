import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProgressPanel(QWidget):
    """Execution control panel with real-time speed, ETA, and progress bar."""

    start_clicked = Signal()
    pause_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_dir: Path = Path.cwd() / "output"
        self._last_completed: int = 0
        self._last_total: int = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Telemetry info line
        info_layout = QHBoxLayout()
        self.lbl_status = QLabel("Ready (0 / 0 items)")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.lbl_telemetry = QLabel("Speed: -- img/s  |  ETA: --  |  Elapsed: --")
        self.lbl_telemetry.setStyleSheet("color: #64748b; font-size: 12px;")
        info_layout.addWidget(self.lbl_status)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_telemetry)
        layout.addLayout(info_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                height: 16px;
                font-size: 11px;
                background-color: #e2e8f0;
                color: #0f172a;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 3px;
            }
            """
        )
        layout.addWidget(self.progress_bar)

        # Button controls
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Start Upscaling")
        self.btn_start.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 5px 16px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            """
        )

        self.btn_pause = QPushButton("⏸️ Pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet(
            """
            QPushButton {
                background-color: #d97706;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 5px 16px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #b45309;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            """
        )

        self.btn_cancel = QPushButton("⏹️ Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(
            """
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 5px 16px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            """
        )

        self.btn_open_folder = QPushButton("📂 Open Output Folder")
        self.btn_open_folder.setStyleSheet(
            """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                color: #1e293b;
                font-size: 12px;
                font-weight: 500;
                padding: 5px 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
            }
            """
        )

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_open_folder)
        layout.addLayout(btn_layout)

        # Signals
        self.btn_start.clicked.connect(self.start_clicked.emit)
        self.btn_pause.clicked.connect(self.pause_clicked.emit)
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        self.btn_open_folder.clicked.connect(self._open_output_folder)

    def set_output_dir(self, path: Path):
        self._output_dir = Path(path).resolve()

    def update_progress(self, completed: int, total: int, speed: float, eta: float):
        self._last_completed = completed
        self._last_total = total
        if total > 0:
            percent = int((completed / total) * 100)
            self.progress_bar.setValue(percent)
            self.lbl_status.setText(f"Upscaling ({completed}/{total} - {percent}%)")
        else:
            self.progress_bar.setValue(0)
            self.lbl_status.setText("Processing...")

        eta_str = f"{int(eta)}s" if eta < 60 else f"{int(eta // 60)}m {int(eta % 60)}s"
        self.lbl_telemetry.setText(f"Speed: {speed:.1f} img/s  |  ETA: {eta_str}")

    def set_running_state(self, is_running: bool):
        self.btn_start.setEnabled(not is_running)
        self.btn_cancel.setEnabled(is_running)
        self.btn_pause.setEnabled(is_running)
        self.btn_pause.setText("⏸️ Pause")

    def set_paused_state(self, is_paused: bool):
        if is_paused:
            self.btn_pause.setText("▶️ Resume")
            self.lbl_status.setText(f"⏸️ Paused ({self._last_completed}/{self._last_total})")
            self.lbl_telemetry.setText("Processing suspended. Click Resume to continue.")
        else:
            self.btn_pause.setText("⏸️ Pause")
            if self._last_total > 0:
                pct = int((self._last_completed / self._last_total) * 100)
                self.lbl_status.setText(f"Upscaling ({self._last_completed}/{self._last_total} - {pct}%)")

    def set_finished_state(self, completed: int, total: int, cancelled: bool):
        self.set_running_state(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸️ Pause")
        if cancelled:
            self.lbl_status.setText(f"⚠️ Cancelled ({completed}/{total} completed)")
            self.lbl_telemetry.setText("Batch cancelled by user.")
        else:
            self.progress_bar.setValue(100)
            self.lbl_status.setText(f"✅ Finished! ({completed}/{total} upscaled)")
            self.lbl_telemetry.setText("All tasks completed successfully.")

    def _open_output_folder(self):
        folder = str(self._output_dir)
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
