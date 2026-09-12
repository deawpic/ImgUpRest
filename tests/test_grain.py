import numpy as np

from src.core.grain import apply_film_grain


def test_grain_strength_zero_identity():
    img = np.full((100, 100, 3), 128, dtype=np.uint8)
    res = apply_film_grain(img, strength=0)
    assert np.array_equal(res, img)


def test_grain_empty_or_none():
    assert apply_film_grain(None, strength=5) is None
    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    res = apply_film_grain(empty, strength=5)
    assert res.size == 0


def test_grain_adds_noise_and_preserves_shape():
    img = np.full((120, 120, 3), 128, dtype=np.uint8)
    res = apply_film_grain(img, strength=5)
    assert res.shape == img.shape
    assert res.dtype == np.uint8
    assert not np.array_equal(res, img)
    # Mean should be close to 128 because noise has zero mean
    assert abs(float(np.mean(res)) - 128.0) < 2.0


def test_grain_midtone_weighting():
    # Midtones (128) should have higher noise variance than near-white (250)
    img_mid = np.full((150, 150, 3), 128, dtype=np.uint8)
    img_white = np.full((150, 150, 3), 250, dtype=np.uint8)

    res_mid = apply_film_grain(img_mid, strength=8)
    res_white = apply_film_grain(img_white, strength=8)

    var_mid = np.var(res_mid.astype(np.float32) - 128.0)
    var_white = np.var(res_white.astype(np.float32) - 250.0)

    assert var_mid > var_white


def test_grain_bounds_clipping():
    img = np.full((50, 50, 3), 255, dtype=np.uint8)
    res = apply_film_grain(img, strength=10)
    assert np.all(res <= 255)
    assert np.all(res >= 0)

    img_zero = np.zeros((50, 50, 3), dtype=np.uint8)
    res_zero = apply_film_grain(img_zero, strength=10)
    assert np.all(res_zero >= 0)
    assert np.all(res_zero <= 255)
