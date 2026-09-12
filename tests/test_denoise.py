import numpy as np

from src.core.denoise import apply_denoise


def test_denoise_zero_strength_identity():
    """Strength 0 must preserve 100% of original image texture and grain."""
    img = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    out = apply_denoise(img, strength=0)
    np.testing.assert_array_equal(out, img)


def test_denoise_positive_strength():
    img = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    out = apply_denoise(img, strength=50)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_denoise_boundary_values():
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    out_neg = apply_denoise(img, strength=-10)
    np.testing.assert_array_equal(out_neg, img)

    out_high = apply_denoise(img, strength=150)
    assert out_high.shape == img.shape
