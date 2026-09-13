"""Session management and queue persistence for Real-ESRGAN GUI."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from src.core.face_enhancer import get_default_weights_dir

logger = logging.getLogger(__name__)


@dataclass
class QueueItemData:
    """Represents the persistent state of an individual file in the batch queue."""

    file_path: str
    status: str = "Queued"  # "Queued", "Done", "Failed", "Skipped"
    resolution: str = "-"
    output_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QueueItemData":
        return cls(
            file_path=str(data.get("file_path", "")),
            status=str(data.get("status", "Queued")),
            resolution=str(data.get("resolution", "-")),
            output_path=data.get("output_path"),
            error=data.get("error"),
        )


@dataclass
class QueueSession:
    """Represents the complete serialized state of a batch session."""

    version: str = "1.0"
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    config: dict = field(default_factory=dict)
    items: list[QueueItemData] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "saved_at": self.saved_at,
            "config": self.config,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueueSession":
        raw_items = data.get("items", [])
        items = [QueueItemData.from_dict(item) for item in raw_items]
        return cls(
            version=str(data.get("version", "1.0")),
            saved_at=str(data.get("saved_at", datetime.now().isoformat())),
            config=dict(data.get("config", {})),
            items=items,
        )


def save_session(session: QueueSession, file_path: Path) -> None:
    """Saves a queue session to disk as formatted JSON using atomic replacement."""
    target = Path(file_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.parent / f"{target.name}.tmp"

    data = session.to_dict()
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    temp_path.replace(target)
    logger.info(f"Saved session with {len(session.items)} items to {target}")


def load_session(file_path: Path) -> QueueSession:
    """Loads and deserializes a queue session from disk."""
    target = Path(file_path).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"Session file not found: {target}")

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    return QueueSession.from_dict(data)


def get_auto_session_path() -> Path:
    """Returns the platform-standard file path for automatic session recovery."""
    base_dir = get_default_weights_dir().parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "last_session.json"


def auto_save_session(session: QueueSession) -> None:
    """Persists current session state to the default auto-save path safely."""
    try:
        path = get_auto_session_path()
        save_session(session, path)
    except Exception as exc:
        logger.warning(f"Failed to auto-save session: {exc}")


def auto_load_session() -> QueueSession | None:
    """Attempts to restore the previous session from disk. Returns None if absent or corrupt."""
    try:
        path = get_auto_session_path()
        if path.is_file() and path.stat().st_size > 0:
            return load_session(path)
    except Exception as exc:
        logger.warning(f"Failed to auto-load previous session: {exc}")
    return None
