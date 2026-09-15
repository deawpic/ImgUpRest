from pathlib import Path

from src.core.config import UpscaleConfig
from src.core.engine import EngineResult, UpscaleEngine


def test_engine_init():
    engine = UpscaleEngine()
    assert not engine.is_running
    engine.cancel()
    assert engine._cancel_event.is_set()


def test_engine_empty_input(tmp_path: Path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    out_dir = tmp_path / "out"

    config = UpscaleConfig(input_path=empty_dir, output_dir=out_dir)
    engine = UpscaleEngine()

    result = engine.run(config)
    assert result.total == 0
    assert result.completed == 0
    assert result.failed == 0
    assert not result.cancelled


def test_engine_callbacks_on_empty(tmp_path: Path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    out_dir = tmp_path / "out"

    config = UpscaleConfig(input_path=empty_dir, output_dir=out_dir)
    engine = UpscaleEngine()

    logs = []
    finish_called = []

    def on_log(msg, level):
        logs.append((level, msg))

    def on_finish(res: EngineResult):
        finish_called.append(res)

    _ = engine.run(config, on_log=on_log, on_finish=on_finish)
    assert len(finish_called) == 1
    assert any(level == "WARNING" for level, _ in logs)


def test_cli_folder_and_subfolder_mirroring(tmp_path: Path, monkeypatch):
    import sys

    from PIL import Image

    import upscale

    # Setup source directory structure: Album1 with top-level and subfolder
    input_dir = tmp_path / "Album1"
    sub_dir = input_dir / "day1"
    sub_dir.mkdir(parents=True)
    f1 = input_dir / "pic1.png"
    f2 = sub_dir / "pic2.png"
    Image.new("RGB", (10, 10)).save(f1)
    Image.new("RGB", (10, 10)).save(f2)

    output_dir = tmp_path / "output"

    captured_configs = []

    class DummyEngine:
        def run(self, config, on_progress=None, on_log=None):
            captured_configs.append(config)
            return EngineResult(
                total=2,
                completed=2,
                failed=0,
                elapsed_seconds=0.1,
                output_dir=output_dir,
                cancelled=False,
            )

    monkeypatch.setattr(upscale, "UpscaleEngine", DummyEngine)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "upscale.py",
            "-i",
            str(input_dir),
            "-o",
            str(output_dir),
            "-c",
            "1",
        ],
    )

    upscale.main()

    assert len(captured_configs) == 1
    cfg = captured_configs[0]
    expected_dest_f1 = str((output_dir / "Album1").resolve())
    expected_dest_f2 = str((output_dir / "Album1" / "day1").resolve())

    assert cfg.file_destinations[str(f1.resolve())] == expected_dest_f1
    assert cfg.file_destinations[str(f2.resolve())] == expected_dest_f2


def test_engine_pause_resume():
    from src.gui.worker_thread import UpscaleWorkerThread

    engine = UpscaleEngine()
    assert not engine.is_paused

    engine.pause()
    assert engine.is_paused
    assert engine._pause_event.is_set()

    engine.resume()
    assert not engine.is_paused
    assert not engine._pause_event.is_set()

    # Verify cancel clears pause
    engine.pause()
    assert engine.is_paused
    engine.cancel()
    assert not engine.is_paused
    assert engine._cancel_event.is_set()

    # Verify UpscaleWorkerThread proxy
    cfg = UpscaleConfig(output_dir=Path("/tmp"))
    thread = UpscaleWorkerThread(config=cfg)
    assert not thread.is_paused
    thread.pause()
    assert thread.is_paused
    thread.resume()
    assert not thread.is_paused


