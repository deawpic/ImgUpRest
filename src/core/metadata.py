"""Metadata preservation module for EXIF camera tags and ICC color profiles.

Extracts binary metadata from input images and re-embeds it into upscaled outputs
using native Pillow features without external third-party dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


def extract_image_metadata(img_path: Path) -> dict[str, Any]:
    """Extracts EXIF and ICC Color Profile metadata from an image file.

    Args:
        img_path: Path to the source image.

    Returns:
        Dictionary containing binary 'exif' and 'icc_profile' if present.
    """
    metadata: dict[str, Any] = {
        "exif": None,
        "icc_profile": None,
    }
    try:
        with Image.open(img_path) as im:
            exif = im.info.get("exif")
            if exif:
                metadata["exif"] = exif
            icc = im.info.get("icc_profile")
            if icc:
                metadata["icc_profile"] = icc
    except Exception as exc:
        logger.debug("Failed to extract metadata from %s: %s", img_path, exc)

    return metadata


def get_save_kwargs(
    metadata: dict[str, Any] | None,
    output_format: str,
    quality: int = 92,
) -> dict[str, Any]:
    """Builds keyword arguments for PIL.Image.save preserving metadata and quality.

    Args:
        metadata: Dictionary from extract_image_metadata.
        output_format: 'jpg', 'jpeg', 'png', or 'webp'.
        quality: Compression quality (1-100).

    Returns:
        Dict of keyword arguments to unpack into out_im.save(output_file, **kwargs).
    """
    fmt = output_format.lower().lstrip(".")
    save_kwargs: dict[str, Any] = {}

    if fmt in ("jpg", "jpeg"):
        save_kwargs["format"] = "JPEG"
        save_kwargs["quality"] = quality
        save_kwargs["subsampling"] = 0
    elif fmt == "png":
        save_kwargs["format"] = "PNG"
        save_kwargs["optimize"] = True
    elif fmt == "webp":
        save_kwargs["format"] = "WEBP"
        save_kwargs["quality"] = quality

    if not metadata:
        return save_kwargs

    exif = metadata.get("exif")
    icc = metadata.get("icc_profile")

    if icc:
        save_kwargs["icc_profile"] = icc

    if exif and fmt in ("jpg", "jpeg", "webp", "png"):
        try:
            save_kwargs["exif"] = exif
        except Exception as exc:
            logger.debug("Could not assign EXIF bytes to format %s: %s", fmt, exc)

    return save_kwargs
