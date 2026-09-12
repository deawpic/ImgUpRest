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
