from pathlib import Path

from PIL import Image

from src.core.metadata import extract_image_metadata, get_save_kwargs


def test_extract_empty_metadata(tmp_path: Path):
    p = tmp_path / "plain.jpg"
    im = Image.new("RGB", (50, 50), color="blue")
    im.save(p, format="JPEG")

    meta = extract_image_metadata(p)
    assert meta["exif"] is None
    assert meta["icc_profile"] is None


def test_save_kwargs_formats():
    kw_jpg = get_save_kwargs(None, "jpg", quality=90)
    assert kw_jpg["format"] == "JPEG"
    assert kw_jpg["quality"] == 90
    assert kw_jpg["subsampling"] == 0

    kw_png = get_save_kwargs(None, "png")
    assert kw_png["format"] == "PNG"
    assert kw_png["optimize"] is True

    kw_webp = get_save_kwargs(None, "webp", quality=85)
    assert kw_webp["format"] == "WEBP"
    assert kw_webp["quality"] == 85


def test_metadata_preservation(tmp_path: Path):
    p_in = tmp_path / "with_exif.jpg"
    im = Image.new("RGB", (60, 60), color="red")
    exif = im.getexif()
    exif[0x010F] = "TestCameraVendor"
    exif[0x0110] = "TestCameraModel"
    im.save(p_in, format="JPEG", exif=exif)

    meta = extract_image_metadata(p_in)
    assert meta["exif"] is not None

    p_out = tmp_path / "out.jpg"
    save_kw = get_save_kwargs(meta, "jpg")
    im.save(p_out, **save_kw)

    with Image.open(p_out) as out_im:
        out_exif = out_im.getexif()
        assert out_exif.get(0x010F) == "TestCameraVendor"
        assert out_exif.get(0x0110) == "TestCameraModel"
