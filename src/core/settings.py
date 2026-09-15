"""Application settings persistence module.

Saves and loads user preferences (Control Panel settings, UI theme, etc.)
to a JSON file located in the user's platform-specific app data directory.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from src.core.face_enhancer import get_default_weights_dir

logger = logging.getLogger(__name__)


def get_settings_file_path() -> Path:
    """Returns the persistent settings file path in user app data."""
    env_override = os.environ.get("REAL_ESRGAN_SETTINGS_PATH")
    if env_override:
        p = Path(env_override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    app_dir = get_default_weights_dir().parent
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / "settings.json"


def save_app_settings(settings: dict, path: Path | None = None) -> Path:
    """Saves settings dictionary to JSON file atomically."""
    target_path = path or get_settings_file_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = target_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        temp_path.replace(target_path)
        logger.debug("Saved app settings to %s", target_path)
        return target_path
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        logger.warning("Failed to save app settings to %s: %s", target_path, exc)
        raise


def load_app_settings(path: Path | None = None) -> dict:
    """Loads settings dictionary from JSON file. Returns empty dict if missing or corrupted."""
    target_path = path or get_settings_file_path()
    if not target_path.is_file():
        return {}

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception as exc:
        logger.warning("Failed to load app settings from %s: %s", target_path, exc)
        return {}
