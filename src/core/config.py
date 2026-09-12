import os
from dataclasses import dataclass, field
from pathlib import Path

from src.core.models import MODEL_MAP, SUPPORTED_EXTS


def get_default_cpu_workers() -> int:
    """Calculate default CPU workers: Half of total logical cores or 3 (ideal for 6-core CPUs)."""
    count = os.cpu_count() or 4
    return max(1, count // 2)


@dataclass
class UpscaleConfig:
    input_path: Path | None = None
    input_files: list[Path] = field(default_factory=list)
    output_dir: Path = field(default_factory=lambda: Path("output"))
    scale: int = 4
    model: str = "x4plus"
    tile_size: int = 0
    quality: int = 92
    cpu_workers: int = field(default_factory=get_default_cpu_workers)
    enable_gpu: bool = True
    gpuid: int = 0
    output_format: str = "jpg"
    denoise_strength: int = 0
    enable_face_enhance: bool = False
    face_model: str = "codeformer"
    face_fidelity: float = 0.8
    grain_strength: int = 0
    mask_mouth: bool = False

    def resolve_files(self) -> list[Path]:
        """Resolves and returns all valid image files to process."""
        files: list[Path] = []
        if self.input_files:
            for p in self.input_files:
                resolved = Path(p).resolve()
                if resolved.is_file() and resolved.suffix.lower() in SUPPORTED_EXTS:
                    files.append(resolved)
        elif self.input_path:
            p = Path(self.input_path).resolve()
            if p.is_dir():
                for item in p.iterdir():
                    if item.is_file() and item.suffix.lower() in SUPPORTED_EXTS:
                        files.append(item)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)
        return sorted(set(files))

    def validate(self) -> None:
        """Validates configuration parameters, raising ValueError if invalid."""
        if self.scale not in (2, 4):
            raise ValueError(f"Invalid scale: {self.scale}. Must be 2 or 4.")

        if self.model not in MODEL_MAP:
            raise ValueError(
                f"Unknown model '{self.model}'. Choices: {list(MODEL_MAP.keys())}"
            )

        if not (1 <= self.quality <= 100):
            raise ValueError(f"Quality must be between 1 and 100. Got: {self.quality}")

        if self.tile_size < 0:
            raise ValueError(
                f"Tile size must be >= 0 (0 for auto). Got: {self.tile_size}"
            )

        if self.cpu_workers < 0:
            raise ValueError(f"CPU workers must be >= 0. Got: {self.cpu_workers}")

        if not self.enable_gpu and self.cpu_workers == 0:
            raise ValueError("Cannot disable GPU and have 0 CPU workers.")

        fmt = self.output_format.lower().lstrip(".")
        if fmt not in ("jpg", "jpeg", "png", "webp"):
            raise ValueError(
                f"Unsupported output format: '{self.output_format}'. "
                "Choices: 'jpg', 'png', 'webp'."
            )

        if not (0 <= self.denoise_strength <= 100):
            raise ValueError(
                f"Denoise strength must be between 0 and 100. Got: {self.denoise_strength}"
            )

        if self.face_model.lower() not in ("gfpgan", "codeformer"):
            raise ValueError(
                f"Unknown face model '{self.face_model}'. Choices: 'gfpgan', 'codeformer'."
            )

        if not (0.0 <= self.face_fidelity <= 1.0):
            raise ValueError(
                f"Face fidelity must be between 0.0 and 1.0. Got: {self.face_fidelity}"
            )

        if not (0 <= self.grain_strength <= 10):
            raise ValueError(
                f"Grain strength must be between 0 and 10. Got: {self.grain_strength}"
            )
