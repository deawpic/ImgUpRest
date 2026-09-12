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
    assert config.face_model == "codeformer"
    assert abs(config.face_fidelity - 0.8) < 1e-4
    assert config.mask_mouth is False

    # Test selecting a preset
    idx_portrait = panel.cmb_preset.findData("portrait")
    panel.cmb_preset.setCurrentIndex(idx_portrait)
    portrait_cfg = panel.get_config()
    assert portrait_cfg.grain_strength == 2
    assert portrait_cfg.enable_face_enhance is True
    assert portrait_cfg.face_model == "codeformer"
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

