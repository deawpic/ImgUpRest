"""Adjustable image denoising module with edge and natural texture preservation."""

from __future__ import annotations

import cv2
import numpy as np


def apply_denoise(image: np.ndarray, strength: int = 0) -> np.ndarray:
    """Applies adaptive edge-preserving denoising.

    Photography / Perception rationale:
    - strength = 0: Disables denoising entirely, keeping 100% of the natural
      film grain, sensor micro-noise, and skin texture.
    - strength > 0: Applies bilateral filtering that smooths out digital noise
      and chromatic artifacts while preserving high-contrast edges (eyes, hair, lines).

    Args:
        image: Input image array (H, W, C) in BGR uint8 format.
        strength: Denoise level from 0 (off, preserve 100% natural grain)
                  to 100 (maximum smooth).

    Returns:
        Denoised image array in BGR uint8 format.
    """
    if strength <= 0:
        return image

    strength = min(100, max(0, strength))

    # Adaptive diameter based on strength
    if strength <= 30:
        d = 5
    elif strength <= 70:
        d = 7
    else:
        d = 9

    sigma_color = float(strength) * 0.8
    sigma_space = float(strength) * 0.8

    filtered = cv2.bilateralFilter(
        image, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space
    )

    alpha = float(strength) / 100.0
    if alpha < 1.0:
        return cv2.addWeighted(filtered, alpha, image, 1.0 - alpha, 0.0)
    return filtered
