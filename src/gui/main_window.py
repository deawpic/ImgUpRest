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
from src.core.session import (
    QueueSession,
    auto_load_session,
    auto_save_session,
    clear_auto_session,
)
from src.core.settings import load_app_settings, save_app_settings
from src.gui.components.comparison_viewer import ComparisonViewer
from src.gui.components.control_panel import ControlPanel
from src.gui.components.drop_zone import BatchQueueTable
from src.gui.components.log_viewer import LogViewer
from src.gui.components.progress_panel import ProgressPanel
from src.gui.theme import DARK_THEME, LIGHT_THEME
from src.gui.worker_thread import UpscaleWorkerThread


class PreviewWorker(QThread):
    """Generates an instant upscaled preview for a single image and saves it to real output."""

    preview_done = Signal(str, str)  # (in_file, out_file)
    preview_failed = Signal(str, str)  # (in_file, error)
    log_emitted = Signal(str, str)  # (message, level)

    def __init__(self, in_file: Path, config: UpscaleConfig, parent=None):
        super().__init__(parent)
        self.in_file = in_file
        self.config = config

    def run(self):
        try:
            output_dir = Path(self.config.output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            fmt = self.config.output_format.lower().lstrip(".")
            if fmt == "jpeg":
                fmt = "jpg"

            out_file = output_dir / f"{self.in_file.stem}_x{self.config.scale}.{fmt}"

            def log_callback(msg: str, level: str = "INFO"):
                self.log_emitted.emit(msg, level)

            engine = UpscaleEngine()
            engine.process_single_image(
                img_path=self.in_file,
                output_file=out_file,
                scale=self.config.scale,
                model=self.config.model,
                tile_size=self.config.tile_size,
                quality=self.config.quality,
                gpuid=self.config.gpuid if self.config.enable_gpu else -1,
                output_format=fmt,
                denoise_strength=self.config.denoise_strength,
                grain_strength=self.config.grain_strength,
                enable_face_enhance=self.config.enable_face_enhance,
                face_model=self.config.face_model,
                face_fidelity=self.config.face_fidelity,
                mask_mouth=self.config.mask_mouth,
                log_callback=log_callback,
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
        self._load_app_settings()
        self._auto_restore_session()

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

        # File selection for preview & auto output detection
        self.queue_table.file_selected.connect(self._on_file_selected)
        self.queue_table.session_saved.connect(self._on_session_saved)
        self.queue_table.session_loaded.connect(self._on_session_loaded)
        self.comparison_viewer.request_preview.connect(self._on_generate_preview)
        self.control_panel.config_changed.connect(self._on_config_changed)
        self.control_panel.txt_output_dir.textChanged.connect(
            self.queue_table.set_default_destination
        )
        self.queue_table.set_default_destination(
            self.control_panel.txt_output_dir.text()
        )
        self.queue_table.config_provider = (
            lambda: self.control_panel.get_config().to_dict()
        )

        # Execution actions
        self.progress_panel.start_clicked.connect(self._start_batch)
        self.progress_panel.pause_clicked.connect(self._on_pause_clicked)
        self.progress_panel.cancel_clicked.connect(self._cancel_batch)

    def _load_app_settings(self):
        """Loads and applies persistent settings on startup."""
        try:
            data = load_app_settings()
            if not data:
                return

            saved_theme = data.get("theme", "light")
            if (saved_theme == "dark" and not self._is_dark) or (
                saved_theme == "light" and self._is_dark
            ):
                self._toggle_theme()

            if "prompt_on_add" in data:
                self.queue_table.prompt_on_add = bool(data["prompt_on_add"])

            if "controls" in data and isinstance(data["controls"], dict):
                self.control_panel.apply_settings_dict(data["controls"])
                if (
                    "output_dir" in data["controls"]
                    and data["controls"]["output_dir"]
                ):
                    self.queue_table.set_default_destination(
                        data["controls"]["output_dir"]
                    )
        except Exception as exc:
            self.log_viewer.append_log(
                f"Note: Could not load user settings: {exc}", "WARNING"
            )

    def _auto_restore_session(self):
        """Attempts to restore the previously active queue session automatically."""
        try:
            session = auto_load_session()
            if session and session.items:
                self.queue_table.import_session_items(session.items)
                total = len(self.queue_table.get_files())
                if total > 0:
                    done = self.queue_table.get_completed_count()
                    pending = self.queue_table.get_pending_count()
                    self.log_viewer.append_log(
                        f"Auto-restored previous session: {total} files ({done} completed, {pending} pending).",
                        "INFO",
                    )
        except Exception as e:
            self.log_viewer.append_log(
                f"Note: Could not restore previous session: {e}", "WARNING"
            )

    def _on_session_saved(self, path: str):
        self.log_viewer.append_log(
            f"Queue session successfully saved to {Path(path).name}", "SUCCESS"
        )

    def _on_session_loaded(self, cfg: dict):
        total = len(self.queue_table.get_files())
        done = self.queue_table.get_completed_count()
        pending = self.queue_table.get_pending_count()
        if "output_dir" in cfg and cfg["output_dir"]:
            self.queue_table.set_default_destination(cfg["output_dir"])
        self.log_viewer.append_log(
            f"Queue session loaded: {total} files ({done} completed, {pending} pending).",
            "SUCCESS",
        )

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
        all_files = self.queue_table.get_files()
        if not all_files:
            QMessageBox.warning(
                self,
                "No Files",
                "Please add at least one image file or folder to the queue.",
            )
            return

        pending_files = self.queue_table.get_pending_files()
        if not pending_files:
            ans = QMessageBox.question(
                self,
                "All Items Completed",
                "All files in the queue are already marked as Done.\nWould you like to reset all items to Queued and re-run?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ans == QMessageBox.Yes:
                self.queue_table.reset_all_to_queued()
                pending_files = self.queue_table.get_files()
            else:
                return

        config = self.control_panel.get_config()
        config.input_files = pending_files
        config.file_destinations = {
            str(f): self.queue_table.get_file_destination(str(f))
            for f in pending_files
            if self.queue_table.get_file_destination(str(f))
        }

        try:
            config.validate()
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Configuration", str(e))
            return

        self.progress_panel.set_output_dir(config.output_dir)
        self.progress_panel.set_running_state(True)
        self.tabs.setCurrentIndex(1)  # Switch to Logs tab to monitor progress

        completed_count = len(all_files) - len(pending_files)
        if completed_count > 0:
            self.log_viewer.append_log(
                f"Smart Resume: Processing {len(pending_files)} pending files (skipping {completed_count} already completed)...",
                "INFO",
            )
        else:
            self.log_viewer.append_log(
                f"Starting upscale batch for {len(pending_files)} files...", "INFO"
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

    def _on_pause_clicked(self):
        if self._worker_thread and self._worker_thread.isRunning():
            if self._worker_thread.is_paused:
                self._worker_thread.resume()
                self.progress_panel.set_paused_state(False)
                self.log_viewer.append_log("▶️ Upscaling resumed.", "INFO")
            else:
                self._worker_thread.pause()
                self.progress_panel.set_paused_state(True)
                self.log_viewer.append_log("⏸️ Upscaling paused.", "INFO")

    def _on_file_selected(self, file_path: str):
        self.comparison_viewer.set_selected_file(file_path)
        self._check_existing_output_for_selected(file_path)

    def _on_config_changed(self):
        """Re-evaluates preview availability if settings change (e.g. scale or output folder)."""
        if self.comparison_viewer._current_file:
            self._check_existing_output_for_selected(
                str(self.comparison_viewer._current_file)
            )

    def _find_existing_output(
        self, in_file: Path, config: UpscaleConfig
    ) -> Path | None:
        """Checks whether an upscaled output file for this image already exists in output_dir or custom destination."""
        item_dest = self.queue_table.get_file_destination(str(in_file))
        dest_dir = Path(item_dest) if item_dest else Path(config.output_dir)
        dest_dir = dest_dir.resolve()
        if not dest_dir.is_dir():
            return None

        stem = in_file.stem
        scale = config.scale
        fmt = config.output_format.lower().lstrip(".")
        if fmt == "jpeg":
            fmt = "jpg"

        preferred = dest_dir / f"{stem}_x{scale}.{fmt}"
        if preferred.is_file():
            return preferred

        # Fallback to check other common image formats at requested scale
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = dest_dir / f"{stem}_x{scale}{ext}"
            if candidate.is_file():
                return candidate

        return None

    def _check_existing_output_for_selected(self, file_path: str):
        in_path = Path(file_path)
        config = self.control_panel.get_config()
        existing = self._find_existing_output(in_path, config)

        if existing:
            self.comparison_viewer.set_upscaled_result(existing)
            self.comparison_viewer.lbl_status.setText(
                f"🔍 Ready (Output exists): {existing.name}"
            )
            self.comparison_viewer.btn_preview.setText("🔄 Re-generate Preview")
            self.comparison_viewer.btn_preview.setEnabled(True)
            self.queue_table.set_file_status(file_path, "Done")
        else:
            self.comparison_viewer.clear_preview()
            self.comparison_viewer.lbl_status.setText(f"🔍 Inspecting: {in_path.name}")
            self.comparison_viewer.btn_preview.setText("⚡ Generate Preview")
            self.comparison_viewer.btn_preview.setEnabled(True)

    def _on_item_completed(self, in_file: str, out_file: str, err: str):
        if err:
            self.queue_table.set_file_status(in_file, "Failed", error=err)
        else:
            self.queue_table.set_file_status(in_file, "Done", output_path=out_file)
            # If current file in preview matches, show after image
            if (
                self.comparison_viewer._current_file
                and str(self.comparison_viewer._current_file) == in_file
            ):
                self.comparison_viewer.set_upscaled_result(Path(out_file))
                self.comparison_viewer.lbl_status.setText(
                    f"🔍 Ready (Output saved): {Path(out_file).name}"
                )
                self.comparison_viewer.btn_preview.setText("🔄 Re-generate Preview")

    def _on_batch_finished(self, result: EngineResult):
        self.progress_panel.set_finished_state(
            completed=result.completed,
            total=result.total,
            cancelled=result.cancelled,
        )
        if not result.cancelled:
            try:
                QApplication.beep()
            except Exception:
                pass
            self.log_viewer.append_log(
                f"Batch completed! {result.completed}/{result.total} saved to {result.output_dir}",
                "SUCCESS",
            )

    def _on_generate_preview(self, file_path: str):
        config = self.control_panel.get_config()
        item_dest = self.queue_table.get_file_destination(file_path)
        if item_dest:
            config.output_dir = item_dest
        self.log_viewer.append_log(
            f"Generating preview & saving real output to {config.output_dir} for {Path(file_path).name}...",
            "INFO",
        )
        self.comparison_viewer.lbl_status.setText(
            "⚡ Generating preview & saving output..."
        )
        self.comparison_viewer.btn_preview.setEnabled(False)

        self._preview_worker = PreviewWorker(
            in_file=Path(file_path), config=config, parent=self
        )
        self._preview_worker.preview_done.connect(self._on_preview_done)
        self._preview_worker.preview_failed.connect(self._on_preview_failed)
        self._preview_worker.log_emitted.connect(self.log_viewer.append_log)
        self._preview_worker.start()

    def _on_preview_done(self, in_file: str, out_file: str):
        out_path = Path(out_file)
        self.comparison_viewer.lbl_status.setText(
            f"🔍 Preview Ready: {out_path.name}"
        )
        self.comparison_viewer.set_upscaled_result(out_path)
        self.comparison_viewer.btn_preview.setText("🔄 Re-generate Preview")
        self.comparison_viewer.btn_preview.setEnabled(True)
        self.queue_table.set_file_status(in_file, "Done", output_path=out_file)
        self.log_viewer.append_log(
            f"Preview generated & saved as real output: {out_path.name}", "SUCCESS"
        )

    def _on_preview_failed(self, in_file: str, error: str):
        self.comparison_viewer.lbl_status.setText(
            f"❌ Preview Failed: {Path(in_file).name}"
        )
        self.comparison_viewer.btn_preview.setEnabled(True)
        self.log_viewer.append_log(f"Preview generation failed: {error}", "ERROR")

    def closeEvent(self, event):
        """Cleanly terminates all background workers and auto-saves the active session and settings."""
        try:
            settings_payload = {
                "controls": self.control_panel.export_settings_dict(),
                "theme": "dark" if self._is_dark else "light",
                "prompt_on_add": self.queue_table.prompt_on_add,
            }
            save_app_settings(settings_payload)
        except Exception:
            pass

        try:
            items = self.queue_table.export_session_items()
            if items:
                config = self.control_panel.get_config()
                cfg_dict = {
                    "scale": config.scale,
                    "model": config.model,
                    "output_dir": str(config.output_dir),
                    "preset": self.control_panel.cmb_preset.currentText(),
                }
                session = QueueSession(
                    config=cfg_dict,
                    items=items,
                )
                auto_save_session(session)
            else:
                clear_auto_session()
        except Exception:
            pass

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

