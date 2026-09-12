from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core import EngineResult, UpscaleConfig, UpscaleEngine
from src.gui.components.comparison_viewer import ComparisonViewer
from src.gui.components.control_panel import ControlPanel
from src.gui.components.drop_zone import BatchQueueTable
from src.gui.components.log_viewer import LogViewer
from src.gui.components.progress_panel import ProgressPanel
from src.gui.theme import DARK_THEME, LIGHT_THEME
from src.gui.worker_thread import UpscaleWorkerThread


class PreviewWorker(QThread):
    """Generates an instant upscaled preview for a single image."""

    preview_done = Signal(str, str)  # (in_file, out_file)
    preview_failed = Signal(str, str)  # (in_file, error)

    def __init__(self, in_file: Path, config: UpscaleConfig, parent=None):
        super().__init__(parent)
        self.in_file = in_file
        self.config = config

    def run(self):
        try:
            preview_dir = Path.cwd() / "output" / ".preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            out_file = (
                preview_dir / f"preview_{self.in_file.stem}_x{self.config.scale}.jpg"
            )

            engine = UpscaleEngine()
            engine.process_single_image(
                img_path=self.in_file,
                output_file=out_file,
                scale=self.config.scale,
                model=self.config.model,
                tile_size=self.config.tile_size,
                quality=self.config.quality,
                gpuid=self.config.gpuid if self.config.enable_gpu else -1,
                output_format="jpg",
                denoise_strength=self.config.denoise_strength,
                grain_strength=self.config.grain_strength,
                enable_face_enhance=self.config.enable_face_enhance,
                face_model=self.config.face_model,
                face_fidelity=self.config.face_fidelity,
                mask_mouth=self.config.mask_mouth,
            )
            self.preview_done.emit(str(self.in_file), str(out_file))
        except Exception as e:
            self.preview_failed.emit(str(self.in_file), str(e))


class MainWindow(QMainWindow):
    """Main application window coordinating all components and background inference."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-ESRGAN NCNN Upscaler — Hybrid GPU + CPU")
        self.resize(1150, 720)
        self.setMinimumSize(850, 560)

        self._is_dark: bool = False
        self._worker_thread: UpscaleWorkerThread | None = None
        self._preview_worker: PreviewWorker | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(6)

        # Header toolbar with App title and Theme Switcher
        header = QHBoxLayout()
        lbl_app = QLabel("⚡ Real-ESRGAN Upscaler (Hybrid GPU + CPU)")
        lbl_app.setStyleSheet("font-weight: bold; font-size: 15px;")
        header.addWidget(lbl_app)
        header.addStretch()

        self.btn_theme = QPushButton("🌙 Dark Mode")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.setToolTip("Toggle Light / Dark Theme")
        self.btn_theme.setStyleSheet(
            "padding: 4px 12px; font-size: 12px; font-weight: bold;"
        )
        header.addWidget(self.btn_theme)
        root_layout.addLayout(header)

        # Vertical Splitter: Top Section (Queue Table + Comparison Wiper) & Bottom Tabs
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setChildrenCollapsible(False)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(False)

        self.queue_table = BatchQueueTable()
        self.comparison_viewer = ComparisonViewer()

        top_splitter.addWidget(self.queue_table)
        top_splitter.addWidget(self.comparison_viewer)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 1)

        v_splitter.addWidget(top_splitter)

        # Bottom Area: Tabs (Control Panel & Logs)
        self.tabs = QTabWidget()
        self.control_panel = ControlPanel()
        self.log_viewer = LogViewer()

        self.tabs.addTab(self.control_panel, "⚙️ Settings & Hardware")
        self.tabs.addTab(self.log_viewer, "📜 Execution Logs")
        v_splitter.addWidget(self.tabs)

        # Set top section compact by default (~170px) and let tabs have comfortable room
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 2)
        v_splitter.setSizes([170, 390])

        root_layout.addWidget(v_splitter, stretch=1)

        # Progress and Action controls at bottom (compact height)
        self.progress_panel = ProgressPanel()
        root_layout.addWidget(self.progress_panel, stretch=0)

    def _connect_signals(self):
        # Theme toggle
        self.btn_theme.clicked.connect(self._toggle_theme)

        # File selection for preview
        self.queue_table.file_selected.connect(self.comparison_viewer.set_selected_file)
        self.comparison_viewer.request_preview.connect(self._on_generate_preview)

        # Execution actions
        self.progress_panel.start_clicked.connect(self._start_batch)
        self.progress_panel.cancel_clicked.connect(self._cancel_batch)

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        app = QApplication.instance()
        if self._is_dark:
            if app:
                app.setStyleSheet(DARK_THEME)
            self.btn_theme.setText("☀️ Light Mode")
        else:
            if app:
                app.setStyleSheet(LIGHT_THEME)
            self.btn_theme.setText("🌙 Dark Mode")

        self.queue_table.set_theme(self._is_dark)
        self.log_viewer.set_theme(self._is_dark)

    def _start_batch(self):
        files = self.queue_table.get_files()
        if not files:
            QMessageBox.warning(
                self,
                "No Files",
                "Please add at least one image file or folder to the queue.",
            )
            return

        config = self.control_panel.get_config()
        config.input_files = files

        try:
            config.validate()
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Configuration", str(e))
            return

        self.progress_panel.set_output_dir(config.output_dir)
        self.progress_panel.set_running_state(True)
        self.tabs.setCurrentIndex(1)  # Switch to Logs tab to monitor progress

        self.log_viewer.append_log(
            f"Starting upscale batch for {len(files)} files...", "INFO"
        )

        self._worker_thread = UpscaleWorkerThread(config=config, parent=self)
        self._worker_thread.progress_changed.connect(
            self.progress_panel.update_progress
        )
        self._worker_thread.item_completed.connect(self._on_item_completed)
        self._worker_thread.log_emitted.connect(self.log_viewer.append_log)
        self._worker_thread.finished_result.connect(self._on_batch_finished)
        self._worker_thread.start()

    def _cancel_batch(self):
        if self._worker_thread and self._worker_thread.isRunning():
            self.log_viewer.append_log("Cancellation requested...", "WARNING")
            self._worker_thread.cancel()

    def _on_item_completed(self, in_file: str, out_file: str, err: str):
        if err:
            self.queue_table.set_file_status(in_file, "Failed", err)
        else:
            self.queue_table.set_file_status(in_file, "Done")
            # If current file in preview matches, show after image
            if (
                self.comparison_viewer._current_file
                and str(self.comparison_viewer._current_file) == in_file
            ):
                self.comparison_viewer.set_upscaled_result(Path(out_file))

    def _on_batch_finished(self, result: EngineResult):
        self.progress_panel.set_finished_state(
            completed=result.completed,
            total=result.total,
            cancelled=result.cancelled,
        )
        if not result.cancelled:
            self.log_viewer.append_log(
                f"Batch completed! {result.completed}/{result.total} saved to {result.output_dir}",
                "SUCCESS",
            )

    def _on_generate_preview(self, file_path: str):
        config = self.control_panel.get_config()
        self.log_viewer.append_log(
            f"Generating preview for {Path(file_path).name}...", "INFO"
        )
        self.comparison_viewer.lbl_status.setText("Generating preview...")

        self._preview_worker = PreviewWorker(
            in_file=Path(file_path), config=config, parent=self
        )
        self._preview_worker.preview_done.connect(self._on_preview_done)
        self._preview_worker.preview_failed.connect(self._on_preview_failed)
        self._preview_worker.start()

    def _on_preview_done(self, in_file: str, out_file: str):
        self.comparison_viewer.lbl_status.setText(
            f"🔍 Preview Ready: {Path(in_file).name}"
        )
        self.comparison_viewer.set_upscaled_result(Path(out_file))
        self.log_viewer.append_log(
            f"Preview generated: {Path(out_file).name}", "SUCCESS"
        )

    def _on_preview_failed(self, in_file: str, error: str):
        self.comparison_viewer.lbl_status.setText(
            f"❌ Preview Failed: {Path(in_file).name}"
        )
        self.log_viewer.append_log(f"Preview generation failed: {error}", "ERROR")

    def closeEvent(self, event):
        """Cleanly terminates all background workers and processes upon closing the window."""
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.cancel()
            self._worker_thread.wait(1000)
            if self._worker_thread.isRunning():
                self._worker_thread.terminate()

        if self._preview_worker and self._preview_worker.isRunning():
            self._preview_worker.wait(500)
            if self._preview_worker.isRunning():
                self._preview_worker.terminate()

        event.accept()
