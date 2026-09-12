from dataclasses import dataclass

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass(frozen=True)
class ModelInfo:
    id: int
    name: str
    display_name: str
    native_scale: int
    description: str
    recommended_for: str


MODELS: dict[str, ModelInfo] = {
    "animevideov3": ModelInfo(
        id=0,
        name="animevideov3",
        display_name="Anime Video v3",
        native_scale=2,
        description="Fastest model, low resource usage.",
        recommended_for="Anime, animations, cartoons, 2D art (Fast 2x)",
    ),
    "x4plus": ModelInfo(
        id=1,
        name="x4plus",
        display_name="Real-ESRGAN x4 Plus",
        native_scale=4,
        description="High parameter model, detailed textures.",
        recommended_for="General photography, real-world scenes, portraits (4x)",
    ),
    "x4plus-anime": ModelInfo(
        id=2,
        name="x4plus-anime",
        display_name="Real-ESRGAN x4 Anime",
        native_scale=4,
        description="Ultra-sharp line restoration, zero blur.",
        recommended_for="Digital art, manga, anime illustrations (High-res 4x)",
    ),
}

MODEL_MAP = {k: v.id for k, v in MODELS.items()}
