"""Photography and enhancement presets based on the Manual.md tuning matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.config import UpscaleConfig


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    description: str
    model: str
    scale: int
    denoise_strength: int
    grain_strength: int
    enable_face_enhance: bool
    face_model: str
    face_fidelity: float
    mask_mouth: bool = False

    def apply_to_config(self, config: UpscaleConfig) -> None:
        """Applies this preset parameters to an existing UpscaleConfig instance."""
        config.model = self.model
        config.scale = self.scale
        config.denoise_strength = self.denoise_strength
        config.grain_strength = self.grain_strength
        config.enable_face_enhance = self.enable_face_enhance
        config.face_model = self.face_model
        config.face_fidelity = self.face_fidelity
        config.mask_mouth = self.mask_mouth


PRESETS: dict[str, Preset] = {
    "portrait": Preset(
        key="portrait",
        name="📸 Portrait & Studio (ภาพบุคคล & สตูดิโอ)",
        description="GFPGAN v1.4 (0.80) + Denoise 0% + Grain 2% + Real Smile (Natural eyes, skin & real teeth)",
        model="x4plus",
        scale=4,
        denoise_strength=0,
        grain_strength=2,
        enable_face_enhance=True,
        face_model="gfpgan",
        face_fidelity=0.80,
        mask_mouth=True,
    ),
    "vintage_film": Preset(
        key="vintage_film",
        name="🎞️ Old / Scanned Film (ภาพเก่า & สแกนฟิล์ม)",
        description="GFPGAN v1.4 (0.75) + Denoise 20% + Grain 5% (Authentic 35mm grain)",
        model="x4plus",
        scale=4,
        denoise_strength=20,
        grain_strength=5,
        enable_face_enhance=True,
        face_model="gfpgan",
        face_fidelity=0.75,
        mask_mouth=False,
    ),
    "landscape": Preset(
        key="landscape",
        name="🏔️ Landscape & Nature (วิว & สถาปัตยกรรม)",
        description="x4plus + Denoise 0% + Face OFF (Max foliage & stone sharpness)",
        model="x4plus",
        scale=4,
        denoise_strength=0,
        grain_strength=0,
        enable_face_enhance=False,
        face_model="gfpgan",
        face_fidelity=0.80,
    ),
    "anime": Preset(
        key="anime",
        name="🎨 Anime & Digital Art (ภาพการ์ตูน & อาร์ต)",
        description="x4plus-anime + Denoise 40% + Face OFF (Crisp clean lines)",
        model="x4plus-anime",
        scale=4,
        denoise_strength=40,
        grain_strength=0,
        enable_face_enhance=False,
        face_model="gfpgan",
        face_fidelity=0.80,
    ),
    "low_light": Preset(
        key="low_light",
        name="🌃 Low-Light / High-ISO (ภาพกลางคืน & น้อยส์สูง)",
        description="GFPGAN v1.4 (0.70) + Denoise 30% + Grain 2% (Removes chroma noise)",
        model="x4plus",
        scale=4,
        denoise_strength=30,
        grain_strength=2,
        enable_face_enhance=True,
        face_model="gfpgan",
        face_fidelity=0.70,
    ),
}
