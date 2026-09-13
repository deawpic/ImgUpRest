import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

# Force offscreen platform for headless CI / automated tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_batch_queue_table(qapp, tmp_path: Path):
    from src.gui.components.drop_zone import BatchQueueTable

    table = BatchQueueTable()
    assert table.table.alternatingRowColors() is False

    # Create dummy images
    img1 = tmp_path / "img1.jpg"
    img2 = tmp_path / "img2.png"
    img1.write_bytes(b"dummy")
    img2.write_bytes(b"dummy")

    table.add_paths([img1, img2])
    assert len(table.get_files()) == 2
    assert table.table.rowCount() == 2

    # Test status update
    table.set_file_status(str(img1), "Done")
    item_status = table.table.item(0, 3)
    assert item_status.text() == "Done"

    # Test clear
    table.clear_all()
    assert len(table.get_files()) == 0
    assert table.table.rowCount() == 0


def test_control_panel_config(qapp):
    from src.gui.components.control_panel import ControlPanel

    panel = ControlPanel()
    config = panel.get_config()

    assert config.scale == 4
    assert config.model == "x4plus"
    assert config.quality == 92
    assert config.tile_size == 0
    assert config.enable_gpu is True
    assert config.denoise_strength == 0
    assert config.grain_strength == 0
    assert config.enable_face_enhance is False
    assert config.face_model == "gfpgan"
    assert abs(config.face_fidelity - 0.8) < 1e-4
    assert config.mask_mouth is False

    # Test selecting a preset
    idx_portrait = panel.cmb_preset.findData("portrait")
    panel.cmb_preset.setCurrentIndex(idx_portrait)
    portrait_cfg = panel.get_config()
    assert portrait_cfg.grain_strength == 2
    assert portrait_cfg.enable_face_enhance is True
    assert portrait_cfg.face_model == "gfpgan"
    assert abs(portrait_cfg.face_fidelity - 0.80) < 1e-4
    assert portrait_cfg.mask_mouth is True

    # Test manual adjustment resets preset to custom
    panel.slider_grain.setValue(8)
    assert panel.cmb_preset.currentData() == "custom"
    assert panel.get_config().grain_strength == 8

    # Test changing other values
    panel.chk_face_enhance.setChecked(True)
    panel.chk_mask_mouth.setChecked(True)
    panel.slider_denoise.setValue(40)
    panel.slider_fidelity.setValue(85)
    updated_cfg = panel.get_config()
    assert updated_cfg.enable_face_enhance is True
    assert updated_cfg.mask_mouth is True
    assert updated_cfg.denoise_strength == 40
    assert abs(updated_cfg.face_fidelity - 0.85) < 1e-4


def test_comparison_viewer_split_and_zoom(qapp):
    from PySide6.QtCore import QPoint

    from src.gui.components.comparison_viewer import ComparisonViewer

    viewer = ComparisonViewer()
    canvas = viewer.canvas
    assert canvas._split_ratio == 0.5
    assert canvas._zoom == 1.0
    assert canvas._pan_offset == QPoint(0, 0)

    # Test split update
    canvas._update_split(100)
    assert 0.0 < canvas._split_ratio < 1.0

    # Test zoom & pan reset
    canvas._zoom = 3.0
    canvas._pan_offset = QPoint(50, -30)
    canvas.reset_view()
    assert canvas._zoom == 1.0
    assert canvas._pan_offset == QPoint(0, 0)


def test_progress_panel_state(qapp):
    from src.gui.components.progress_panel import ProgressPanel

    panel = ProgressPanel()
    panel.update_progress(completed=5, total=10, speed=2.5, eta=2.0)
    assert panel.progress_bar.value() == 50
    assert "5/10" in panel.lbl_status.text()
    assert "2.5 img/s" in panel.lbl_telemetry.text()

    panel.set_running_state(True)
    assert not panel.btn_start.isEnabled()
    assert panel.btn_cancel.isEnabled()

    panel.set_finished_state(completed=10, total=10, cancelled=False)
    assert panel.btn_start.isEnabled()
    assert not panel.btn_cancel.isEnabled()
    assert panel.progress_bar.value() == 100


def test_theme_toggle(qapp):
    from src.gui.main_window import MainWindow

    win = MainWindow()
    assert win._is_dark is False
    assert "Dark Mode" in win.btn_theme.text()

    # Click toggle -> should switch to Dark
    win.btn_theme.click()
    assert win._is_dark is True
    assert "Light Mode" in win.btn_theme.text()

    # Click toggle again -> should switch back to Light
    win.btn_theme.click()
    assert win._is_dark is False
    assert "Dark Mode" in win.btn_theme.text()


def test_main_window_close_event(qapp, mocker):
    from PySide6.QtGui import QCloseEvent

    from src.gui.main_window import MainWindow

    win = MainWindow()
    mock_worker = mocker.MagicMock()
    mock_worker.isRunning.return_value = True
    win._worker_thread = mock_worker

    mock_preview = mocker.MagicMock()
    mock_preview.isRunning.return_value = True
    win._preview_worker = mock_preview

    evt = QCloseEvent()
    win.closeEvent(evt)

    assert evt.isAccepted()
    mock_worker.cancel.assert_called_once()
    mock_worker.wait.assert_called_once()
    mock_preview.wait.assert_called_once()


def test_freeze_support_invoked(mocker):
    import multiprocessing

    import src.gui.app as gui_app

    mock_freeze = mocker.patch.object(multiprocessing, "freeze_support")
    mocker.patch("PySide6.QtWidgets.QApplication.exec", return_value=0)
    mocker.patch("PySide6.QtWidgets.QWidget.show")
    mocker.patch("os._exit")

    gui_app.main()
    mock_freeze.assert_called_once()


def test_main_window_auto_detects_existing_output(qapp, tmp_path):
    from PIL import Image

    from src.gui.main_window import MainWindow

    # Setup dummy input and output directories
    in_img = tmp_path / "photo1.png"
    Image.new("RGB", (50, 50), color="red").save(in_img)

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    out_img = out_dir / "photo1_x4.jpg"
    Image.new("RGB", (200, 200), color="blue").save(out_img)

    win = MainWindow()
    win.control_panel.txt_output_dir.setText(str(out_dir))
    win.queue_table.add_paths([in_img])

    # Select the file row in the queue table
    win._on_file_selected(str(in_img))

    # Should detect existing output in out_dir
    assert win.comparison_viewer.btn_preview.text() == "🔄 Re-generate Preview"
    assert "Output exists" in win.comparison_viewer.lbl_status.text()
    assert win.comparison_viewer.canvas._pix_after is not None
    # Table status should be marked Done
    assert win.queue_table.table.item(0, 3).text() == "Done"


def test_main_window_preview_done_marks_done(qapp, tmp_path):
    from PIL import Image

    from src.gui.main_window import MainWindow

    in_img = tmp_path / "sample.png"
    Image.new("RGB", (50, 50), color="green").save(in_img)
    out_img = tmp_path / "sample_x4.jpg"
    Image.new("RGB", (200, 200), color="yellow").save(out_img)

    win = MainWindow()
    win.queue_table.add_paths([in_img])
    win.comparison_viewer.set_selected_file(str(in_img))

    # Simulate preview completed
    win._on_preview_done(str(in_img), str(out_img))

    assert win.queue_table.table.item(0, 3).text() == "Done"
    assert win.comparison_viewer.btn_preview.text() == "🔄 Re-generate Preview"
    assert "sample_x4.jpg" in win.comparison_viewer.lbl_status.text()


def test_batch_queue_table_session_save_load_and_smart_resume(qapp, tmp_path: Path):
    from PIL import Image

    from src.gui.components.drop_zone import BatchQueueTable

    table = BatchQueueTable()

    # Create dummy images
    img1 = tmp_path / "img1.jpg"
    img2 = tmp_path / "img2.jpg"
    img3 = tmp_path / "img3.jpg"
    for img in (img1, img2, img3):
        Image.new("RGB", (100, 100)).save(img)

    table.add_paths([img1, img2, img3])
    assert len(table.get_files()) == 3

    # Mark statuses
    table.set_file_status(str(img1), "Done", output_path="/tmp/img1_out.png")
    table.set_file_status(str(img2), "Failed", error="CUDA OOM")

    assert table.get_completed_count() == 1
    assert table.get_pending_count() == 2
    pending = table.get_pending_files()
    assert len(pending) == 2
    assert img1 not in pending
    assert img2 in pending
    assert img3 in pending

    # Test retry failed
    table.retry_failed()
    assert table.table.item(1, 3).text() == "Queued"
    assert table.get_pending_count() == 2

    # Save session to file
    session_file = tmp_path / "test_queue.json"
    table.save_session_to_file(session_file, config_dict={"scale": 4})
    assert session_file.is_file()

    # Clear and reload from file
    table.clear_all()
    assert len(table.get_files()) == 0
    loaded_cfg = table.load_session_from_file(session_file)
    assert loaded_cfg.get("scale") == 4
    assert len(table.get_files()) == 3
    assert table.table.item(0, 3).text() == "Done"

    # Test clear completed
    table.clear_completed()
    assert len(table.get_files()) == 2
    assert table.get_completed_count() == 0


def test_main_window_smart_resume_skips_done(qapp, tmp_path: Path, mocker):
    from PIL import Image

    from src.gui.main_window import MainWindow

    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    Image.new("RGB", (50, 50)).save(img1)
    Image.new("RGB", (50, 50)).save(img2)

    win = MainWindow()
    win.queue_table.add_paths([img1, img2])
    win.queue_table.set_file_status(str(img1), "Done")

    # Mock UpscaleWorkerThread to inspect config passed to it
    captured_config = []

    class DummyWorkerThread:
        def __init__(self, config, parent=None):
            captured_config.append(config)
            self.progress_changed = mocker.MagicMock()
            self.item_completed = mocker.MagicMock()
            self.log_emitted = mocker.MagicMock()
            self.finished_result = mocker.MagicMock()

        def start(self):
            pass

        def isRunning(self):
            return False

    mocker.patch("src.gui.main_window.UpscaleWorkerThread", DummyWorkerThread)

    win._start_batch()
    assert len(captured_config) == 1
    # Only pending img2 should be submitted
    assert captured_config[0].input_files == [img2]



