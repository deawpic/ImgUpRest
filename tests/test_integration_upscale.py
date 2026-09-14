from pathlib import Path

from PIL import Image

from src.core.config import UpscaleConfig
from src.core.engine import UpscaleEngine


def test_real_upscale_single_image(tmp_path: Path):
    """Verifies actual inference using real-esrgan-ncnn-py."""
    # 1. Create a 32x32 test image with gradient
    in_img = tmp_path / "test_input.png"
    im = Image.new("RGB", (32, 32), color=(120, 50, 200))
    im.save(in_img)

    out_img = tmp_path / "test_output.jpg"

    engine = UpscaleEngine()
    # Use CPU worker (-1) for guaranteed environment testability
    res_path = engine.process_single_image(
        img_path=in_img,
        output_file=out_img,
        scale=2,
        model="animevideov3",
        tile_size=0,
        quality=90,
        gpuid=-1,
        output_format="jpg",
    )

    assert res_path.exists()
    with Image.open(res_path) as out_im:
        assert out_im.size == (64, 64)


def test_batch_upscale_and_cancellation(tmp_path: Path):
    """Verifies batch run and cooperative cancellation."""
    img_dir = tmp_path / "inputs"
    img_dir.mkdir()
    out_dir = tmp_path / "outputs"

    # Create 4 test images
    for i in range(4):
        im = Image.new("RGB", (16, 16), color=(i * 40, 100, 200))
        im.save(img_dir / f"img_{i}.png")

    config = UpscaleConfig(
        input_path=img_dir,
        output_dir=out_dir,
        scale=2,
        model="animevideov3",
        cpu_workers=2,
        enable_gpu=False,  # CPU for test reliability
    )

    engine = UpscaleEngine()

    # Cancel immediately after first progress update
    def on_progress(completed, total, speed, eta):
        if completed >= 1:
            engine.cancel()

    result = engine.run(config, on_progress=on_progress)
    assert result.total == 4
    # At least one was completed before cancellation took effect
    assert result.completed >= 1
    assert result.cancelled is True


def test_batch_upscale_subfolders_and_collision_prevention(tmp_path: Path):
    """Verifies recursive subfolders, collision detection, and per-item destination routing."""
    sub_a = tmp_path / "sub_a"
    sub_b = tmp_path / "sub_b"
    sub_a.mkdir()
    sub_b.mkdir()

    img_a = sub_a / "photo.png"
    img_b = sub_b / "photo.png"
    Image.new("RGB", (16, 16), color=(255, 0, 0)).save(img_a)
    Image.new("RGB", (16, 16), color=(0, 255, 0)).save(img_b)

    custom_out = tmp_path / "custom_outputs"
    default_out = tmp_path / "default_outputs"

    config = UpscaleConfig(
        input_files=[img_a, img_b],
        output_dir=default_out,
        file_destinations={
            str(img_b): str(custom_out),
        },
        scale=2,
        model="animevideov3",
        cpu_workers=2,
        enable_gpu=False,
    )

    engine = UpscaleEngine()
    result = engine.run(config)

    assert result.total == 2
    assert result.completed == 2
    assert result.failed == 0

    # img_a went to default_out: photo_x2.jpg
    expected_a = default_out / "photo_x2.jpg"
    assert expected_a.exists()

    # img_b went to custom_out: photo_x2.jpg
    expected_b = custom_out / "photo_x2.jpg"
    assert expected_b.exists()

    # Now test collision in the same output directory:
    img_c = tmp_path / "photo.png"
    Image.new("RGB", (16, 16), color=(0, 0, 255)).save(img_c)

    config_collision = UpscaleConfig(
        input_files=[img_a, img_c],  # both named photo.png
        output_dir=default_out,
        scale=2,
        model="animevideov3",
        cpu_workers=2,
        enable_gpu=False,
    )
    result_collision = engine.run(config_collision)
    assert result_collision.completed == 2
    # One will be photo_x2.jpg, the other will be photo_1_x2.jpg
    file_1 = default_out / "photo_x2.jpg"
    file_2 = default_out / "photo_1_x2.jpg"
    assert file_1.exists()
    assert file_2.exists()
