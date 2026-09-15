import os
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from src.core.settings import (
    get_settings_file_path,
    load_app_settings,
    save_app_settings,
)

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_save_and_load_app_settings(tmp_path: Path):
    target = tmp_path / "settings.json"
    data = {
        "theme": "dark",
        "prompt_on_add": False,
        "controls": {
            "model": "realesr-animevideov3-x2",
            "scale": 2,
            "denoise_strength": 15,
            "grain_strength": 20,
            "enable_face_enhance": True,
            "face_model": "codeformer",
            "face_fidelity": 0.75,
            "quality": 95,
            "output_format": "png",
            "cpu_workers": 2,
            "enable_gpu": True,
            "output_dir": str(tmp_path / "output"),
        },
    }
    saved_path = save_app_settings(data, path=target)
    assert saved_path.is_file()

    loaded = load_app_settings(path=target)
    assert loaded == data
    assert loaded["theme"] == "dark"
    assert loaded["controls"]["scale"] == 2
    assert loaded["controls"]["face_fidelity"] == 0.75


def test_load_non_existent_settings(tmp_path: Path):
    target = tmp_path / "does_not_exist.json"
    loaded = load_app_settings(path=target)
    assert loaded == {}


def test_load_corrupt_settings(tmp_path: Path):
    target = tmp_path / "corrupt.json"
    target.write_text("NOT VALID JSON {{{{", encoding="utf-8")
    loaded = load_app_settings(path=target)
    assert loaded == {}


def test_settings_file_path_env_override(tmp_path: Path):
    custom_path = tmp_path / "sub" / "custom_settings.json"
    with patch.dict("os.environ", {"REAL_ESRGAN_SETTINGS_PATH": str(custom_path)}):
        resolved = get_settings_file_path()
        assert resolved == custom_path


def test_control_panel_export_and_apply(qapp):
    from src.gui.components.control_panel import ControlPanel

    panel = ControlPanel()

    settings_to_apply = {
        "preset": "digital_art",
        "model": "realesr-animevideov3-x2",
        "scale": 2,
        "denoise_strength": 30,
        "grain_strength": 10,
        "enable_face_enhance": True,
        "face_model": "codeformer",
        "face_fidelity": 0.85,
        "mask_mouth": True,
        "tile_size": 256,
        "quality": 90,
        "output_format": "webp",
        "enable_gpu": False,
        "cpu_workers": 4,
        "output_dir": "/custom/output",
    }
    panel.apply_settings_dict(settings_to_apply)

    exported = panel.export_settings_dict()
    assert exported["scale"] == 2
    assert exported["denoise_strength"] == 30
    assert exported["grain_strength"] == 10
    assert exported["enable_face_enhance"] is True
    assert exported["face_model"] == "codeformer"
    assert exported["face_fidelity"] == 0.85
    assert exported["mask_mouth"] is True
    assert exported["tile_size"] == 256
    assert exported["quality"] == 90
    assert exported["output_format"] == "webp"
    assert exported["enable_gpu"] is False
    assert exported["cpu_workers"] == 4
    assert exported["output_dir"] == "/custom/output"
