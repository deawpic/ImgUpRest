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
