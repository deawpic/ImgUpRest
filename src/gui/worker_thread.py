from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.core import EngineResult, UpscaleConfig, UpscaleEngine


class UpscaleWorkerThread(QThread):
    """QThread running UpscaleEngine to ensure the GUI remains completely non-blocking."""

    # Signals
    progress_changed = Signal(int, int, float, float)  # (completed, total, speed, eta)
    item_completed = Signal(str, str, str)  # (in_file, out_file, error)
    log_emitted = Signal(str, str)  # (message, level)
    finished_result = Signal(object)  # EngineResult

    def __init__(self, config: UpscaleConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.engine = UpscaleEngine()

    def cancel(self):
        """Requests cooperative engine cancellation."""
        self.engine.cancel()

    def run(self):
        """Executes the upscale engine in background thread."""
        try:

            def on_progress(completed, total, speed, eta):
                self.progress_changed.emit(completed, total, speed, eta)

            def on_item(in_file, out_file, err):
                self.item_completed.emit(in_file or "", out_file or "", err or "")

            def on_log(msg, level):
                self.log_emitted.emit(msg, level)

            def on_finish(result: EngineResult):
                self.finished_result.emit(result)

            self.engine.run(
                config=self.config,
                on_progress=on_progress,
                on_item_complete=on_item,
                on_log=on_log,
                on_finish=on_finish,
            )
        except Exception as e:
            self.log_emitted.emit(f"Worker thread error: {e}", "ERROR")
            err_result = EngineResult(
                total=0,
                completed=0,
                failed=0,
                elapsed_seconds=0.0,
                output_dir=Path(self.config.output_dir),
                cancelled=False,
            )
            self.finished_result.emit(err_result)
