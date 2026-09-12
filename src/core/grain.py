"""Natural monochromatic film grain generator.

Simulates 35mm analog silver halide grain with midtone luminance weighting.
Uses OpenCV C++ SIMD routines for fast vectorized execution.
"""

from __future__ import annotations

import cv2
import numpy as np


def apply_film_grain(bgr: np.ndarray, strength: int = 0) -> np.ndarray:
    """Applies realistic monochromatic film grain to a BGR image.

    Args:
        bgr: Input image in BGR format (uint8, shape [H, W, 3]).
        strength: Grain strength from 0 (disabled) to 10 (pronounced 35mm grain).

    Returns:
        Processed BGR image (uint8) with organic film micro-texture.
    """
    if strength <= 0 or bgr is None or bgr.size == 0:
        return bgr

    strength = int(np.clip(strength, 0, 10))
    h, w = bgr.shape[:2]

    # Generate monochromatic Gaussian noise (single channel) using fast OpenCV C++ SIMD
    sigma = float(strength) * 0.45
    noise = np.empty((h, w), dtype=np.float32)
    cv2.randn(noise, 0.0, sigma)

    # Estimate luminance using fast grayscale conversion in [0.0, 1.0]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    # Quadratic bell-curve weight: peak at midtones (0.5), gentle rolloff in deep shadows and bright highlights
    weight = np.clip(4.0 * gray * (1.0 - gray), 0.20, 1.0)
    weighted_noise = (noise * weight)[:, :, np.newaxis]

    # Vectorized addition across B, G, R channels
    result = bgr.astype(np.float32) + weighted_noise
    return np.clip(result, 0.0, 255.0).astype(np.uint8)
