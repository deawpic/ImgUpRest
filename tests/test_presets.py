from src.core.config import UpscaleConfig
from src.core.presets import PRESETS, Preset


def test_preset_definitions():
    expected = {"portrait", "vintage_film", "landscape", "anime", "low_light"}
    assert set(PRESETS.keys()) == expected

    for key, preset in PRESETS.items():
        assert isinstance(preset, Preset)
        assert preset.key == key
        assert preset.scale in (2, 4)
        assert 0 <= preset.denoise_strength <= 100
        assert 0 <= preset.grain_strength <= 10
        assert preset.face_model in ("codeformer", "gfpgan")
        assert 0.0 <= preset.face_fidelity <= 1.0


def test_apply_preset_to_config():
    cfg = UpscaleConfig()
    portrait = PRESETS["portrait"]
    portrait.apply_to_config(cfg)

    assert cfg.model == portrait.model
    assert cfg.scale == portrait.scale
    assert cfg.denoise_strength == 0
    assert cfg.grain_strength == 2
    assert cfg.enable_face_enhance is True
    assert cfg.face_model == "gfpgan"
    assert cfg.face_fidelity == 0.80
    assert cfg.mask_mouth is True

    cfg.validate()  # Should validate with 0 errors


def test_anime_preset_to_config():
    cfg = UpscaleConfig()
    anime = PRESETS["anime"]
    anime.apply_to_config(cfg)

    assert cfg.model == "x4plus-anime"
    assert cfg.denoise_strength == 40
    assert cfg.grain_strength == 0
    assert cfg.enable_face_enhance is False
    assert cfg.mask_mouth is False

    cfg.validate()
