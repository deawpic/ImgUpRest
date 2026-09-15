from unittest.mock import MagicMock

import numpy as np

from src.core.face_enhancer import FaceEnhancer


def test_face_enhancer_align_face():
    enhancer = FaceEnhancer()
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # Dummy landmarks
    landmarks = np.array(
        [[50, 50], [100, 50], [75, 75], [60, 110], [90, 110]], dtype=np.float32
    )
    aligned, M = enhancer.align_face(img, landmarks)
    assert aligned.shape == (512, 512, 3)
    assert M.shape == (2, 3)


def test_create_mouth_mask():
    enhancer = FaceEnhancer()
    landmarks_512 = np.array(
        [[192, 240], [318, 240], [256, 314], [201, 371], [313, 371]], dtype=np.float32
    )
    mask = enhancer.create_mouth_mask(landmarks_512)
    assert mask.shape == (512, 512, 1)
    assert mask.dtype == np.float32
    assert 0.0 <= mask.min() and mask.max() <= 1.0
    # Mouth center should be close to 1.0
    assert mask[371, 257, 0] > 0.8
    # Forehead should be 0.0
    assert mask[100, 256, 0] == 0.0

    # Test fallback with None
    fallback_mask = enhancer.create_mouth_mask(None)
    assert fallback_mask.shape == (512, 512, 1)
    assert fallback_mask[371, 257, 0] > 0.8


def test_face_enhancer_with_mock_session():
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_input.type = "tensor(float)"
    mock_output = MagicMock()
    mock_output.name = "output"

    mock_session.get_inputs.return_value = [mock_input]
    mock_session.get_outputs.return_value = [mock_output]

    # Return dummy restored face tensor (1, 3, 512, 512)
    fake_out = np.zeros((1, 3, 512, 512), dtype=np.float32)
    mock_session.run.return_value = [fake_out]

    enhancer = FaceEnhancer(onnx_session=mock_session)
    enhancer._initialized = True

    aligned_face = np.ones((512, 512, 3), dtype=np.uint8) * 128
    res = enhancer.enhance_aligned_face(aligned_face)

    assert res.shape == (512, 512, 3)
    assert res.dtype == np.uint8
    mock_session.run.assert_called_once()


def test_face_enhancer_full_image_with_mock_detector():
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_output = MagicMock()
    mock_output.name = "output"
    mock_session.get_inputs.return_value = [mock_input]
    mock_session.get_outputs.return_value = [mock_output]
    mock_session.run.return_value = [np.zeros((1, 3, 512, 512), dtype=np.float32)]

    mock_detector = MagicMock()
    # Return 1 face detection: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
    dummy_face = np.array(
        [[20, 20, 60, 60, 35, 35, 65, 35, 50, 50, 40, 70, 60, 70, 0.95]],
        dtype=np.float32,
    )
    mock_detector.detect.return_value = (1, dummy_face)

    enhancer = FaceEnhancer(onnx_session=mock_session, detector=mock_detector)
    enhancer._initialized = True

    img = np.ones((100, 100, 3), dtype=np.uint8) * 100
    out = enhancer.enhance_image(img)

    assert out.shape == img.shape
    assert out.dtype == np.uint8
    mock_detector.detect.assert_called_once()
    mock_session.run.assert_called_once()


def test_ensure_face_enhancer_models_cached(tmp_path):
    from src.core.face_enhancer import ensure_face_enhancer_models

    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    # Create fake files with sizes above min_size
    yunet_f = weights_dir / "face_detection_yunet_2023mar.onnx"
    yunet_f.write_bytes(b"0" * 350_000)

    gfpgan_f = weights_dir / "GFPGANv1.4.onnx"
    gfpgan_f.write_bytes(b"0" * 310_000_000)

    y, g = ensure_face_enhancer_models(model_name="gfpgan", custom_dir=weights_dir)
    assert y == yunet_f
    assert g == gfpgan_f


def test_engine_aborts_when_face_download_fails(monkeypatch, tmp_path):
    from src.core.config import UpscaleConfig
    from src.core.engine import UpscaleEngine

    # Dummy input file
    in_dir = tmp_path / "inputs"
    in_dir.mkdir()
    (in_dir / "test.jpg").write_bytes(b"fake_jpg_content")

    out_dir = tmp_path / "output"

    config = UpscaleConfig(
        input_path=in_dir,
        output_dir=out_dir,
        enable_face_enhance=True,
        face_model="gfpgan",
    )

    # Mock ensure_face_enhancer_models to raise error (simulating network failure)
    def mock_ensure(*args, **kwargs):
        raise RuntimeError("No internet connection")

    monkeypatch.setattr(
        "src.core.face_enhancer.ensure_face_enhancer_models",
        mock_ensure,
    )

    engine = UpscaleEngine()
    logs = []
    result = engine.run(config=config, on_log=lambda msg, lvl: logs.append((msg, lvl)))

    assert result.cancelled is True
    assert result.completed == 0
    assert any("Cannot proceed with face enhancement" in m for m, _ in logs)


def test_get_default_weights_dir_env_override(monkeypatch, tmp_path):
    from src.core.face_enhancer import get_default_weights_dir

    custom_dir = tmp_path / "custom_weights"
    monkeypatch.setenv("REAL_ESRGAN_WEIGHTS_DIR", str(custom_dir))

    res = get_default_weights_dir()
    assert res == custom_dir
    assert res.is_dir()


def test_get_default_weights_dir_platforms(monkeypatch, tmp_path):
    import platform

    from src.core.face_enhancer import get_default_weights_dir

    monkeypatch.delenv("REAL_ESRGAN_WEIGHTS_DIR", raising=False)

    # Windows simulation
    fake_localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(fake_localappdata))

    win_dir = get_default_weights_dir()
    assert win_dir == fake_localappdata / "real_esrgan_gui" / "weights"
    assert win_dir.is_dir()

    # Linux simulation
    fake_xdg = tmp_path / ".local" / "share"
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(fake_xdg))

    linux_dir = get_default_weights_dir()
    assert linux_dir == fake_xdg / "real_esrgan_gui" / "weights"
    assert linux_dir.is_dir()


def test_find_weight_file_legacy_cache_fallback(monkeypatch, tmp_path):
    from pathlib import Path

    from src.core.face_enhancer import find_weight_file

    monkeypatch.delenv("REAL_ESRGAN_WEIGHTS_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Place a dummy weight file in the legacy cache directory
    legacy_dir = tmp_path / ".cache" / "real_esrgan_gui" / "weights"
    legacy_dir.mkdir(parents=True)
    fake_yunet = legacy_dir / "face_detection_yunet_2023mar.onnx"
    fake_yunet.write_bytes(b"x" * 250_000)

    found = find_weight_file("yunet")
    assert found is not None
    assert found == fake_yunet


def test_download_weight_file_with_none_stdout_stderr(monkeypatch, tmp_path):
    """Verifies download succeeds even when sys.stdout and sys.stderr are None (GUI/PyInstaller windowed mode)."""
    import sys
    import urllib.request

    from src.core.face_enhancer import download_weight_file

    dest_dir = tmp_path / "weights"

    # Simulate GUI environment where stdout and stderr are None
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    # Mock urllib.request.urlretrieve to write dummy file and trigger reporthook
    def mock_urlretrieve(url, filename, reporthook=None):
        with open(filename, "wb") as f:
            f.write(b"0" * 300_000)
        if reporthook:
            reporthook(1, 100_000, 300_000)
            reporthook(3, 100_000, 300_000)

    monkeypatch.setattr(urllib.request, "urlretrieve", mock_urlretrieve)

    logged = []
    out = download_weight_file(
        "yunet",
        dest_dir=dest_dir,
        log_callback=lambda msg, lvl: logged.append((msg, lvl)),
    )
    assert out.exists()
    assert out.stat().st_size >= 200_000
    assert any("Successfully downloaded" in m for m, _ in logged)

