from pathlib import Path

import pytest

from src.core.config import UpscaleConfig


def test_default_config():
    config = UpscaleConfig()
    assert config.scale == 4
    assert config.model == "x4plus"
    assert config.quality == 92
    assert config.tile_size == 0
    assert config.enable_gpu is True
    assert config.output_format == "jpg"
    assert config.cpu_workers >= 1
    assert config.denoise_strength == 0
    assert config.grain_strength == 0
    assert config.enable_face_enhance is False
    assert config.face_model == "gfpgan"
    assert abs(config.face_fidelity - 0.8) < 1e-4
    assert config.mask_mouth is False


def test_config_to_dict():
    config = UpscaleConfig(scale=4, model="x4plus", output_dir=Path("/tmp/out"))
    d = config.to_dict()
    assert isinstance(d, dict)
    assert d["scale"] == 4
    assert d["model"] == "x4plus"
    assert Path(d["output_dir"]) == Path("/tmp/out")
    assert "face_model" in d



def test_validation_valid():
    config = UpscaleConfig(
        scale=4,
        model="x4plus",
        quality=95,
        tile_size=200,
        cpu_workers=2,
        output_format="png",
    )
    config.validate()


def test_validation_invalid_scale():
    config = UpscaleConfig(scale=3)
    with pytest.raises(ValueError, match="Invalid scale"):
        config.validate()


def test_validation_invalid_model():
    config = UpscaleConfig(model="nonexistent_model")
    with pytest.raises(ValueError, match="Unknown model"):
        config.validate()


def test_validation_invalid_quality():
    config = UpscaleConfig(quality=105)
    with pytest.raises(ValueError, match="Quality must be between 1 and 100"):
        config.validate()


def test_validation_no_workers():
    config = UpscaleConfig(enable_gpu=False, cpu_workers=0)
    with pytest.raises(ValueError, match="Cannot disable GPU and have 0 CPU workers"):
        config.validate()


def test_validation_invalid_denoise():
    config = UpscaleConfig(denoise_strength=120)
    with pytest.raises(ValueError, match="Denoise strength must be between 0 and 100"):
        config.validate()


def test_validation_invalid_face_model():
    config = UpscaleConfig(face_model="unknown_model")
    with pytest.raises(ValueError, match="Unknown face model"):
        config.validate()


def test_validation_invalid_face_fidelity():
    config = UpscaleConfig(face_fidelity=1.5)
    with pytest.raises(ValueError, match="Face fidelity must be between 0.0 and 1.0"):
        config.validate()


def test_validation_invalid_grain():
    config = UpscaleConfig(grain_strength=15)
    with pytest.raises(ValueError, match="Grain strength must be between 0 and 10"):
        config.validate()

    config_neg = UpscaleConfig(grain_strength=-1)
    with pytest.raises(ValueError, match="Grain strength must be between 0 and 10"):
        config_neg.validate()


def test_resolve_files(tmp_path: Path):
    # Create test image files and non-image files
    img1 = tmp_path / "test1.jpg"
    img2 = tmp_path / "test2.PNG"
    txt = tmp_path / "notes.txt"

    img1.write_text("fake image 1")
    img2.write_text("fake image 2")
    txt.write_text("text file")

    config = UpscaleConfig(input_path=tmp_path)
    files = config.resolve_files()

    assert len(files) == 2
    assert img1 in files
    assert img2 in files
    assert txt not in files


def test_resolve_files_recursive_subfolders(tmp_path: Path):
    sub1 = tmp_path / "sub1"
    sub2 = tmp_path / "sub1" / "nested"
    sub1.mkdir()
    sub2.mkdir()

    img1 = tmp_path / "root.jpg"
    img2 = sub1 / "level1.png"
    img3 = sub2 / "level2.webp"
    doc = sub2 / "info.pdf"

    img1.write_text("1")
    img2.write_text("2")
    img3.write_text("3")
    doc.write_text("doc")

    config = UpscaleConfig(input_path=tmp_path)
    files = config.resolve_files()

    assert len(files) == 3
    assert img1 in files
    assert img2 in files
    assert img3 in files
    assert doc not in files
