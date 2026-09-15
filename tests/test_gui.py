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


@pytest.fixture(autouse=True)
def isolate_session(tmp_path, monkeypatch):
    dummy_session = tmp_path / "test_isolated_session.json"
    monkeypatch.setattr("src.core.session.get_auto_session_path", lambda: dummy_session)
    monkeypatch.setattr("src.gui.main_window.auto_load_session", lambda: None)



def test_batch_queue_table(qapp, tmp_path: Path):
    from src.gui.components.drop_zone import (
        COL_DEST,
        COL_NAME,
        COL_NUM,
        COL_RES,
        COL_STATUS,
        BatchQueueTable,
    )

    table = BatchQueueTable()
    assert table.table.alternatingRowColors() is False
    assert (COL_NUM, COL_NAME, COL_RES, COL_DEST, COL_STATUS) == (0, 1, 2, 3, 4)
    assert table.table.columnCount() == 5
    headers = [table.table.horizontalHeaderItem(i).text() for i in range(5)]
    assert headers == ["#", "Name", "Resolution", "Destination", "Status"]

    # Create dummy images
    img1 = tmp_path / "img1.jpg"
    img2 = tmp_path / "img2.png"
    img1.write_bytes(b"dummy")
    img2.write_bytes(b"dummy")

    table.add_paths([img1, img2])
    assert len(table.get_files()) == 2
    assert table.table.rowCount() == 2

    # Test custom destination
    custom_dest = tmp_path / "my_custom_folder"
    table.set_file_destination(str(img1), str(custom_dest))
    assert table.get_file_destination(str(img1)) == str(custom_dest.resolve())
    assert table.table.item(0, COL_DEST).text() == "my_custom_folder"

    # Test status update preserves destination
    table.set_file_status(str(img1), "Done")
    item_status = table.table.item(0, COL_STATUS)
    assert item_status.text() == "Done"
    assert table.get_file_destination(str(img1)) == str(custom_dest.resolve())

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

    # Test hardware toggle and worker setting
    assert portrait_cfg.cpu_workers == 0
    panel.chk_gpu.setChecked(False)
    assert panel.spin_cpu_workers.value() >= 1
    assert panel.get_config().enable_gpu is False
    assert panel.get_config().cpu_workers >= 1

    panel.chk_gpu.setChecked(True)
    panel.cmb_preset.setCurrentIndex(idx_portrait)
    assert panel.spin_cpu_workers.value() == 0


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
    from src.gui.components.drop_zone import COL_STATUS

    assert win.queue_table.table.item(0, COL_STATUS).text() == "Done"


def test_main_window_preview_done_marks_done(qapp, tmp_path):
    from PIL import Image

    from src.gui.components.drop_zone import COL_STATUS
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

    assert win.queue_table.table.item(0, COL_STATUS).text() == "Done"
    assert win.comparison_viewer.btn_preview.text() == "🔄 Re-generate Preview"
    assert "sample_x4.jpg" in win.comparison_viewer.lbl_status.text()


def test_batch_queue_table_session_save_load_and_smart_resume(qapp, tmp_path: Path):
    from PIL import Image

    from src.gui.components.drop_zone import COL_STATUS, BatchQueueTable

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
    assert table.table.item(1, COL_STATUS).text() == "Queued"
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
    assert table.table.item(0, COL_STATUS).text() == "Done"

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


def test_batch_queue_table_multi_session_append_and_fallback(
    qapp, tmp_path: Path
):
    from PIL import Image

    from src.core.session import QueueItemData, QueueSession, save_session
    from src.gui.components.drop_zone import BatchQueueTable

    # Create dummy images
    img1 = tmp_path / "f1.png"
    img2 = tmp_path / "f2.png"
    img3 = tmp_path / "f3.png"
    img4 = tmp_path / "f4.png"
    for img in (img1, img2, img3, img4):
        Image.new("RGB", (20, 20)).save(img)

    valid_dest = tmp_path / "valid_dest"
    valid_dest.mkdir()
    fallback_dest = tmp_path / "fallback_default"
    fallback_dest.mkdir()

    # Session 1: f1 with valid custom destination, f2 with None
    s1_path = tmp_path / "session1.json"
    sess1 = QueueSession(
        config={"output_dir": str(valid_dest)},
        items=[
            QueueItemData(file_path=str(img1), destination_dir=str(valid_dest)),
            QueueItemData(file_path=str(img2)),
        ],
    )
    save_session(sess1, s1_path)

    # Session 2: f3 with non-existent foreign destination, f4 with None
    s2_path = tmp_path / "session2.json"
    sess2 = QueueSession(
        config={"output_dir": "/nonexistent/drive_d/output"},
        items=[
            QueueItemData(
                file_path=str(img3),
                destination_dir="/nonexistent/drive_d/output",
            ),
            QueueItemData(file_path=str(img4)),
        ],
    )
    save_session(sess2, s2_path)

    table = BatchQueueTable()
    table.set_default_destination(str(fallback_dest))

    # Load session 1 (append=False)
    table.load_session_from_file(s1_path, append=False)
    assert len(table.get_files()) == 2
    assert table.get_file_destination(str(img1.resolve())) == str(valid_dest.resolve())

    # Load session 2 (append=True) -> merging queues
    table.load_session_from_file(s2_path, append=True)
    assert len(table.get_files()) == 4
    # img3 destination non-existent -> gracefully fallback to fallback_dest
    assert table.get_file_destination(str(img3.resolve())) == str(fallback_dest)


def test_drop_zone_recursive_add_folder(qapp, tmp_path: Path, mocker):
    from PIL import Image

    from src.gui.components.drop_zone import BatchQueueTable

    root = tmp_path / "scan_test"
    sub1 = root / "sub1"
    sub2 = root / "sub1" / "nested"
    sub1.mkdir(parents=True)
    sub2.mkdir(parents=True)

    f1 = root / "top.png"
    f2 = sub1 / "mid.jpg"
    f3 = sub2 / "deep.webp"
    for f in (f1, f2, f3):
        Image.new("RGB", (16, 16)).save(f)

    default_out = tmp_path / "output"
    table = BatchQueueTable()
    table.prompt_on_add = False
    table.set_default_destination(str(default_out))
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        return_value=str(root),
    )
    table._on_add_folder()

    files = table.get_files()
    assert len(files) == 3
    assert f1.resolve() in files
    assert f2.resolve() in files
    assert f3.resolve() in files

    # Verify mirrored folder & subfolder destinations
    expected_dest_f1 = (default_out / "scan_test").resolve()
    expected_dest_f2 = (default_out / "scan_test" / "sub1").resolve()
    expected_dest_f3 = (default_out / "scan_test" / "sub1" / "nested").resolve()

    assert table.get_file_destination(str(f1.resolve())) == str(expected_dest_f1)
    assert table.get_file_destination(str(f2.resolve())) == str(expected_dest_f2)
    assert table.get_file_destination(str(f3.resolve())) == str(expected_dest_f3)

    # Check table COL_DEST display labels
    from src.gui.components.drop_zone import COL_DEST
    row_f1 = files.index(f1.resolve())
    row_f2 = files.index(f2.resolve())
    row_f3 = files.index(f3.resolve())
    assert table.table.item(row_f1, COL_DEST).text() == "scan_test"
    assert table.table.item(row_f2, COL_DEST).text() == str(Path("scan_test") / "sub1")
    assert table.table.item(row_f3, COL_DEST).text() == str(Path("scan_test") / "sub1" / "nested")



def test_batch_queue_table_bulk_destination_change(qapp, tmp_path: Path, mocker):
    from PIL import Image

    from src.gui.components.drop_zone import COL_DEST, BatchQueueTable

    # Create 3 images
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    img3 = tmp_path / "img3.png"
    for img in (img1, img2, img3):
        Image.new("RGB", (10, 10)).save(img)

    table = BatchQueueTable()
    table.add_paths([img1, img2, img3])
    assert len(table.get_files()) == 3

    # 1. Test set_files_destination programmatic API
    dest_a = tmp_path / "dest_a"
    dest_a.mkdir()
    table.set_files_destination([img1, img2], str(dest_a))
    assert table.get_file_destination(str(img1.resolve())) == str(dest_a.resolve())
    assert table.get_file_destination(str(img2.resolve())) == str(dest_a.resolve())
    assert table.table.item(0, COL_DEST).text() == "dest_a"
    assert table.table.item(1, COL_DEST).text() == "dest_a"

    # 2. Test selecting multiple rows and using btn_set_dest
    from PySide6.QtWidgets import QTableWidgetSelectionRange

    dest_b = tmp_path / "dest_b"
    dest_b.mkdir()
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        return_value=str(dest_b),
    )

    # Select rows 1 and 2
    table.table.setRangeSelected(QTableWidgetSelectionRange(1, 0, 2, 4), True)
    assert len(table.table.selectionModel().selectedRows()) == 2

    table.btn_set_dest.click()
    assert table.get_file_destination(str(img2.resolve())) == str(dest_b.resolve())
    assert table.get_file_destination(str(img3.resolve())) == str(dest_b.resolve())
    assert table.table.item(1, COL_DEST).text() == "dest_b"
    assert table.table.item(2, COL_DEST).text() == "dest_b"

    # 3. Test double-clicking COL_DEST with multiple selection
    dest_c = tmp_path / "dest_c"
    dest_c.mkdir()
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        return_value=str(dest_c),
    )
    # Select all rows
    table.table.selectAll()
    assert len(table.table.selectionModel().selectedRows()) == 3
    table._on_cell_double_clicked(0, COL_DEST)
    for img in (img1, img2, img3):
        assert table.get_file_destination(str(img.resolve())) == str(dest_c.resolve())


def test_batch_queue_table_save_appends_json_and_config_provider(
    qapp, tmp_path: Path, mocker
):
    from PIL import Image

    from src.core.config import UpscaleConfig
    from src.gui.components.drop_zone import BatchQueueTable

    img = tmp_path / "pic.png"
    Image.new("RGB", (10, 10)).save(img)

    table = BatchQueueTable()
    table.add_paths([img])
    config = UpscaleConfig(scale=4, model="x4plus")
    table.config_provider = lambda: config.to_dict()

    save_target = tmp_path / "my_custom_queue"  # intentionally omitting .json extension
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(str(save_target), "JSON Queue Files (*.json)"),
    )

    saved_paths = []
    table.session_saved.connect(saved_paths.append)

    table._on_save_queue()

    assert len(saved_paths) == 1
    assert saved_paths[0].endswith(".json")
    saved_file = Path(saved_paths[0])
    assert saved_file.is_file()
    assert saved_file.name == "my_custom_queue.json"


def test_clear_queue_removes_auto_session(qapp, tmp_path, monkeypatch):
    from PySide6.QtGui import QCloseEvent

    from src.core.session import QueueItemData, QueueSession, auto_save_session
    from src.gui.main_window import MainWindow

    auto_file = tmp_path / "last_session.json"
    monkeypatch.setattr("src.core.session.get_auto_session_path", lambda: auto_file)
    import src.core.session
    monkeypatch.setattr("src.gui.main_window.auto_load_session", src.core.session.auto_load_session)

    # 1. Simulate an existing auto-session file
    dummy_img = tmp_path / "img1.png"
    dummy_img.write_text("x")
    auto_save_session(
        QueueSession(
            config={"scale": 4},
            items=[
                QueueItemData(
                    file_path=str(dummy_img), status="Queued"
                )
            ],
        )
    )
    assert auto_file.is_file()

    # 2. Open MainWindow (which restores the session)
    win = MainWindow()
    assert len(win.queue_table.get_files()) == 1

    # 3. User clicks Clear All
    win.queue_table.clear_all()
    assert len(win.queue_table.get_files()) == 0
    # The file should be removed immediately
    assert not auto_file.is_file()

    # 4. User closes the app with empty queue
    evt = QCloseEvent()
    win.closeEvent(evt)
    assert evt.isAccepted()
    assert not auto_file.is_file()

    # 5. Reopening MainWindow must NOT restore the cleared session
    win2 = MainWindow()
    assert len(win2.queue_table.get_files()) == 0


def test_drop_zone_drag_drop_mix_folder_and_file(qapp, tmp_path: Path):
    from PIL import Image
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent

    from src.gui.components.drop_zone import COL_DEST, BatchQueueTable

    # Create folder with subfolder
    album = tmp_path / "Album1"
    album_day1 = album / "day1"
    album_day1.mkdir(parents=True)
    f_album = album / "photo1.png"
    f_sub = album_day1 / "photo2.png"

    # Standalone file
    f_single = tmp_path / "single.jpg"

    for f in (f_album, f_sub, f_single):
        Image.new("RGB", (16, 16)).save(f)

    out_base = tmp_path / "my_output"
    table = BatchQueueTable()
    table.prompt_on_add = False
    table.set_default_destination(str(out_base))

    # Mock drop event with QMimeData
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(album)), QUrl.fromLocalFile(str(f_single))])

    event = QDropEvent(
        QPointF(0, 0),
        Qt.CopyAction,
        mime_data,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    table.dropEvent(event)

    files = table.get_files()
    assert len(files) == 3
    assert f_album.resolve() in files
    assert f_sub.resolve() in files
    assert f_single.resolve() in files

    # Verify single file uses default output
    assert table.get_file_destination(str(f_single.resolve())) == str(out_base.resolve())

    # Verify folder files mirror folder and subfolders
    assert table.get_file_destination(str(f_album.resolve())) == str((out_base / "Album1").resolve())
    assert table.get_file_destination(str(f_sub.resolve())) == str((out_base / "Album1" / "day1").resolve())

    # Verify COL_DEST text
    row_album = files.index(f_album.resolve())
    row_sub = files.index(f_sub.resolve())
    row_single = files.index(f_single.resolve())

    assert table.table.item(row_album, COL_DEST).text() == "Album1"
    assert table.table.item(row_sub, COL_DEST).text() == str(Path("Album1") / "day1")
    assert table.table.item(row_single, COL_DEST).text() == "my_output"


def test_destination_prompt_dialog_interactions(qapp, tmp_path: Path, mocker):
    from PySide6.QtWidgets import QDialog

    from src.gui.components.drop_zone import DestinationPromptDialog

    default_dest = tmp_path / "default_out"
    custom_dest = tmp_path / "custom_out"

    # 1. Test confirm with custom path
    dlg1 = DestinationPromptDialog(
        default_destination=str(default_dest), count=5, has_folders=True, folder_names=["Album1"]
    )
    dlg1.txt_dest.setText(str(custom_dest))
    dlg1.btn_confirm.click()
    assert dlg1.result() == QDialog.Accepted
    assert dlg1.chosen_destination == str(custom_dest)
    assert dlg1.dont_ask_again is False

    # 2. Test Use Default button
    dlg2 = DestinationPromptDialog(
        default_destination=str(default_dest), count=2, has_folders=False
    )
    dlg2.btn_default.click()
    assert dlg2.result() == QDialog.Accepted
    assert dlg2.chosen_destination == str(default_dest)

    # 3. Test Cancel button
    dlg3 = DestinationPromptDialog(
        default_destination=str(default_dest), count=2
    )
    dlg3.btn_cancel.click()
    assert dlg3.result() == QDialog.Rejected
    assert dlg3.chosen_destination is None

    # 4. Test "Don't ask again" checkbox
    dlg4 = DestinationPromptDialog(
        default_destination=str(default_dest), count=1
    )
    dlg4.chk_dont_ask.setChecked(True)
    dlg4.btn_confirm.click()
    assert dlg4.dont_ask_again is True


def test_add_actions_destination_prompt_flow(qapp, tmp_path: Path, mocker):
    from PIL import Image
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent

    from src.gui.components.drop_zone import BatchQueueTable

    # Create dummy images
    f1 = tmp_path / "photo1.jpg"
    f2 = tmp_path / "photo2.png"
    Image.new("RGB", (10, 10)).save(f1)
    Image.new("RGB", (10, 10)).save(f2)

    folder = tmp_path / "Vacation"
    folder.mkdir()
    f3 = folder / "beach.jpg"
    Image.new("RGB", (10, 10)).save(f3)

    custom_dir = tmp_path / "my_custom_destination"

    # 1. Add Files with custom destination confirmed
    table = BatchQueueTable()
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(f1)], ""),
    )
    mocker.patch.object(
        table, "_prompt_add_destination_dialog", return_value=str(custom_dir)
    )
    table._on_add_files()
    assert len(table.get_files()) == 1
    assert table.get_file_destination(str(f1.resolve())) == str(custom_dir.resolve())

    # 2. Add Files with dialog cancelled (returns None) -> should NOT add
    mocker.patch.object(
        table, "_prompt_add_destination_dialog", return_value=None
    )
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(f2)], ""),
    )
    table._on_add_files()
    assert len(table.get_files()) == 1  # Still 1, f2 was not added

    # 3. Add Folder with custom destination confirmed
    mocker.patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        return_value=str(folder),
    )
    mocker.patch.object(
        table, "_prompt_add_destination_dialog", return_value=str(custom_dir)
    )
    table._on_add_folder()
    assert len(table.get_files()) == 2
    expected_beach_dest = str((custom_dir / "Vacation").resolve())
    assert table.get_file_destination(str(f3.resolve())) == expected_beach_dest

    # 4. Drag and Drop with dialog cancelled -> should NOT add
    f4 = tmp_path / "dropped.png"
    Image.new("RGB", (10, 10)).save(f4)
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(f4))])
    event = QDropEvent(QPointF(0, 0), Qt.CopyAction, mime_data, Qt.LeftButton, Qt.NoModifier)

    mocker.patch.object(table, "_prompt_add_destination_dialog", return_value=None)
    table.dropEvent(event)
    assert len(table.get_files()) == 2  # Still 2, f4 was not added


def test_progress_panel_pause_button(qapp):
    from src.gui.components.progress_panel import ProgressPanel

    panel = ProgressPanel()
    assert not panel.btn_pause.isEnabled()

    clicked = []
    panel.pause_clicked.connect(lambda: clicked.append(True))

    panel.set_running_state(True)
    assert panel.btn_pause.isEnabled()
    assert "Pause" in panel.btn_pause.text()

    panel.btn_pause.click()
    assert len(clicked) == 1

    panel.set_paused_state(True)
    assert "Resume" in panel.btn_pause.text()
    assert "Paused" in panel.lbl_status.text()

    panel.set_paused_state(False)
    assert "Pause" in panel.btn_pause.text()

    panel.set_finished_state(completed=5, total=5, cancelled=False)
    assert not panel.btn_pause.isEnabled()
    assert "Pause" in panel.btn_pause.text()


def test_table_sorting_and_row_mapping(qapp, tmp_path: Path):
    from PIL import Image
    from PySide6.QtCore import Qt

    from src.gui.components.drop_zone import COL_NAME, COL_NUM, BatchQueueTable

    img_b = tmp_path / "b_file.png"
    img_a = tmp_path / "a_file.png"
    img_c = tmp_path / "c_file.png"
    for p in (img_b, img_a, img_c):
        Image.new("RGB", (20, 20)).save(p)

    table = BatchQueueTable()
    table.prompt_on_add = False
    table.add_paths([img_b, img_a, img_c])

    assert table.table.isSortingEnabled()

    # Sort ascending by Name (COL_NAME = 1)
    table.table.sortItems(COL_NAME, Qt.AscendingOrder)
    assert table.table.item(0, COL_NAME).text() == "a_file.png"
    assert table.table.item(1, COL_NAME).text() == "b_file.png"
    assert table.table.item(2, COL_NAME).text() == "c_file.png"

    # Verify get_files returns sorted order
    files = table.get_files()
    assert files[0].name == "a_file.png"
    assert files[1].name == "b_file.png"
    assert files[2].name == "c_file.png"

    # Verify status update accurately matches even when sorted
    table.set_file_status(str(img_b), "Done")
    assert table._get_row_status(1) == "Done"
    assert table._get_row_status(0) == "Queued"

    # Sort by COL_NUM (index 0) to verify numeric sorting
    table.table.sortItems(COL_NUM, Qt.AscendingOrder)
    assert table.table.item(0, COL_NAME).text() == "b_file.png"


def test_context_menu_open_destination_and_view_output(qapp, tmp_path: Path, mocker):
    from PIL import Image
    from PySide6.QtGui import QDesktopServices

    from src.gui.components.drop_zone import BatchQueueTable

    img = tmp_path / "photo.png"
    out_img = tmp_path / "output" / "photo_x4.png"
    out_img.parent.mkdir(parents=True)
    Image.new("RGB", (30, 30)).save(img)
    Image.new("RGB", (120, 120)).save(out_img)

    table = BatchQueueTable()
    table.prompt_on_add = False
    table.set_default_destination(str(tmp_path / "output"))
    table.add_paths([img])

    table.set_file_status(str(img), "Done", output_path=str(out_img))

    opened_urls = []
    mocker.patch.object(
        QDesktopServices,
        "openUrl",
        side_effect=lambda url: opened_urls.append(url.toLocalFile()) or True,
    )

    # 1. Open Destination Folder
    table._open_selected_destination([0])
    assert len(opened_urls) == 1
    assert Path(opened_urls[0]).resolve() == (tmp_path / "output").resolve()

    # 2. View Output Image
    table._view_selected_output(0)
    assert len(opened_urls) == 2
    assert Path(opened_urls[1]).resolve() == out_img.resolve()


def test_main_window_audio_alert_and_settings_persistence(qapp, tmp_path: Path, mocker):
    from PySide6.QtWidgets import QApplication

    from src.core.engine import EngineResult
    from src.core.settings import load_app_settings
    from src.gui.main_window import MainWindow

    settings_file = tmp_path / "test_settings.json"
    mocker.patch(
        "src.core.settings.get_settings_file_path", return_value=settings_file
    )

    beep_called = []
    mocker.patch.object(QApplication, "beep", side_effect=lambda: beep_called.append(True))

    win = MainWindow()
    # Test beep on finish
    res = EngineResult(
        total=1,
        completed=1,
        failed=0,
        elapsed_seconds=0.5,
        output_dir=tmp_path,
        cancelled=False,
    )
    win._on_batch_finished(res)
    assert len(beep_called) == 1

    # Modify some settings
    win.control_panel.slider_denoise.setValue(45)
    win.queue_table.prompt_on_add = False

    # Close window and verify saved settings
    event = mocker.MagicMock()
    win.closeEvent(event)

    saved = load_app_settings(path=settings_file)
    assert saved["prompt_on_add"] is False
    assert saved["controls"]["denoise_strength"] == 45










