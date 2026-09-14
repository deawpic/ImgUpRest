"""Unit tests for queue session management and persistence."""

from pathlib import Path

from src.core.session import (
    QueueItemData,
    QueueSession,
    auto_load_session,
    auto_save_session,
    clear_auto_session,
    get_auto_session_path,
    load_session,
    save_session,
)


def test_session_dataclass_roundtrip():
    item = QueueItemData(
        file_path="/path/to/img.jpg",
        status="Done",
        resolution="1920×1080",
        output_path="/path/to/img_x4.png",
        error=None,
    )
    d = item.to_dict()
    reconstructed = QueueItemData.from_dict(d)
    assert reconstructed.file_path == "/path/to/img.jpg"
    assert reconstructed.status == "Done"
    assert reconstructed.resolution == "1920×1080"
    assert reconstructed.output_path == "/path/to/img_x4.png"
    assert reconstructed.error is None

    session = QueueSession(
        config={"scale": 4, "model": "x4plus"},
        items=[reconstructed],
    )
    sess_dict = session.to_dict()
    sess_reconstructed = QueueSession.from_dict(sess_dict)
    assert sess_reconstructed.version == "1.0"
    assert sess_reconstructed.config["scale"] == 4
    assert len(sess_reconstructed.items) == 1
    assert sess_reconstructed.items[0].file_path == "/path/to/img.jpg"


def test_save_and_load_session(tmp_path: Path):
    target_file = tmp_path / "test_session.json"
    items = [
        QueueItemData(file_path="/tmp/a.jpg", status="Done"),
        QueueItemData(file_path="/tmp/b.jpg", status="Queued"),
        QueueItemData(file_path="/tmp/c.jpg", status="Failed", error="CUDA OOM"),
    ]
    session = QueueSession(
        config={"preset": "portrait", "scale": 4},
        items=items,
    )

    save_session(session, target_file)
    assert target_file.is_file()

    loaded = load_session(target_file)
    assert loaded.config["preset"] == "portrait"
    assert len(loaded.items) == 3
    assert loaded.items[0].status == "Done"
    assert loaded.items[1].status == "Queued"
    assert loaded.items[2].status == "Failed"
    assert loaded.items[2].error == "CUDA OOM"


def test_auto_save_and_auto_load_lifecycle(tmp_path: Path, monkeypatch):
    auto_file = tmp_path / "last_session.json"
    monkeypatch.setattr("src.core.session.get_auto_session_path", lambda: auto_file)

    # Before saving, should return None
    assert auto_load_session() is None

    # Save session
    session = QueueSession(
        config={"scale": 2},
        items=[QueueItemData(file_path="/tmp/sample.png", status="Done")],
    )
    auto_save_session(session)
    assert auto_file.is_file()

    # Load session
    restored = auto_load_session()
    assert restored is not None
    assert len(restored.items) == 1
    assert restored.items[0].status == "Done"

    # Corrupt file should safely return None without crashing
    auto_file.write_text("{corrupted-json")
    assert auto_load_session() is None

    # clear_auto_session should delete the file safely
    auto_file.write_text("{}")
    assert auto_file.is_file()
    clear_auto_session()
    assert not auto_file.is_file()
    # Calling clear again when file does not exist should not raise error
    clear_auto_session()



def test_get_auto_session_path():
    path = get_auto_session_path()
    assert isinstance(path, Path)
    assert path.name == "last_session.json"


def test_session_destination_dir_roundtrip(tmp_path: Path):
    target_file = tmp_path / "dest_session.json"
    item1 = QueueItemData(
        file_path="/tmp/pic1.png",
        status="Queued",
        destination_dir="/tmp/custom_out",
    )
    item2 = QueueItemData(
        file_path="/tmp/pic2.png",
        status="Done",
        destination_dir=None,
    )
    session = QueueSession(
        config={"output_dir": "/tmp/default_out"},
        items=[item1, item2],
    )
    save_session(session, target_file)

    loaded = load_session(target_file)
    assert len(loaded.items) == 2
    assert loaded.items[0].destination_dir == "/tmp/custom_out"
    # When None, from_dict falls back to config["output_dir"]
    assert loaded.items[1].destination_dir == "/tmp/default_out"


def test_session_backward_compatibility_fallback():
    # Legacy session payload without destination_dir
    legacy_dict = {
        "version": "1.0",
        "saved_at": "2026-09-01T00:00:00",
        "config": {"output_dir": "/home/user/Upscaled"},
        "items": [
            {"file_path": "/home/user/photo.jpg", "status": "Queued"},
        ],
    }
    session = QueueSession.from_dict(legacy_dict)
    assert len(session.items) == 1
    assert session.items[0].destination_dir == "/home/user/Upscaled"


def test_save_session_auto_appends_json_extension(tmp_path: Path):
    target = tmp_path / "custom_queue_no_ext"
    session = QueueSession(config={"scale": 4})
    saved = save_session(session, target)
    assert saved.suffix == ".json"
    assert (tmp_path / "custom_queue_no_ext.json").is_file()

    # And loading without .json finds it
    loaded = load_session(target)
    assert loaded.config["scale"] == 4


