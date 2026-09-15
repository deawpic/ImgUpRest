"""Face enhancement module using ONNX models (GFPGAN / CodeFormer) and OpenCV YuNet.

Runs lightweight ONNX Runtime inference without requiring PyTorch.
"""

from __future__ import annotations

import io
import logging
import os
import platform
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Standard 5-point landmark template for 512x512 aligned face crops (ArcFace / FFHQ standard)
CANONICAL_512 = np.array(
    [
        [192.98138, 239.94708],  # Left eye
        [318.45563, 240.01953],  # Right eye
        [256.00000, 314.01935],  # Nose tip
        [201.26117, 371.41043],  # Left mouth corner
        [313.08905, 371.15118],  # Right mouth corner
    ],
    dtype=np.float32,
)

MODEL_URLS = {
    "yunet": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "gfpgan": "https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/GFPGANv1.4.onnx",
    "codeformer": "https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/codeformer.onnx",
}

MODEL_FILENAMES = {
    "yunet": "face_detection_yunet_2023mar.onnx",
    "gfpgan": "GFPGANv1.4.onnx",
    "codeformer": "codeformer.onnx",
}

# Minimum expected file sizes to detect truncated or corrupted downloads
MODEL_MIN_SIZES = {
    "yunet": 200_000,  # Real size: 232,589 bytes (~227 KB)
    "gfpgan": 300_000_000,  # Real size: ~340 MB
    "codeformer": 300_000_000,  # Real size: ~376 MB
}


def get_default_weights_dir() -> Path:
    """Returns platform-standard directory for storing persistent ONNX model weights.

    Priority:
    1. Custom Environment Variable: `REAL_ESRGAN_WEIGHTS_DIR`
    2. Portable mode: `./weights` directory next to executable or in current working directory
    3. Platform-standard persistent data directory:
       - Windows: %LOCALAPPDATA%/real_esrgan_gui/weights
       - macOS: ~/Library/Application Support/real_esrgan_gui/weights
       - Linux: $XDG_DATA_HOME/real_esrgan_gui/weights (default: ~/.local/share/real_esrgan_gui/weights)
    """
    # 1. Environment variable override
    env_dir = os.environ.get("REAL_ESRGAN_WEIGHTS_DIR")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 2. Portable mode: next to standalone executable or in working directory
    if getattr(sys, "frozen", False):
        exe_weights = Path(sys.executable).parent / "weights"
        if exe_weights.is_dir():
            return exe_weights

    cwd_weights = Path.cwd() / "weights"
    if cwd_weights.is_dir():
        return cwd_weights

    # 3. Platform-standard persistent data directory
    system = platform.system()
    if system == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        base = (
            Path(local_appdata)
            if local_appdata
            else (Path.home() / "AppData" / "Local")
        )
        p = base / "real_esrgan_gui" / "weights"
    elif system == "Darwin":
        p = (
            Path.home()
            / "Library"
            / "Application Support"
            / "real_esrgan_gui"
            / "weights"
        )
    else:
        # Linux / BSD / Unix (XDG Data Home standard)
        xdg_data = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
        p = base / "real_esrgan_gui" / "weights"

    p.mkdir(parents=True, exist_ok=True)
    return p


def find_weight_file(model_key: str, custom_dir: Path | None = None) -> Path | None:
    """Searches for model weights across custom dirs, portable folders, OS data dirs, and legacy cache.

    Priority order:
    1. Explicit custom directory argument
    2. REAL_ESRGAN_WEIGHTS_DIR environment variable
    3. Portable executable directory (if frozen)
    4. Current working directory / project root (`./weights` or `./models`)
    5. Platform-standard persistent data directory (`get_default_weights_dir()`)
    6. Backward-compatibility legacy caches (e.g. `~/.cache/real_esrgan_gui/weights`)
    """
    filename = MODEL_FILENAMES.get(model_key)
    if not filename:
        return None

    min_size = MODEL_MIN_SIZES.get(model_key, 1000)

    # Collect candidate search directories
    candidates: list[Path | None] = [custom_dir]

    if env_dir := os.environ.get("REAL_ESRGAN_WEIGHTS_DIR"):
        candidates.append(Path(env_dir).expanduser().resolve())

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.extend([exe_dir / "weights", exe_dir / "models", exe_dir])

    # Project / cwd locations
    candidates.extend(
        [
            Path.cwd() / "weights",
            Path.cwd() / "models",
            Path(__file__).resolve().parents[2] / "weights",
            Path(__file__).resolve().parents[2] / "models",
        ]
    )

    # Platform standard data directory
    try:
        candidates.append(get_default_weights_dir())
    except Exception:
        pass

    # Backward-compatible legacy cache locations (so existing users don't need to re-download)
    candidates.extend(
        [
            Path.home() / ".local" / "share" / "real_esrgan_gui" / "weights",
            Path.home() / ".cache" / "real_esrgan_gui" / "weights",
            Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            / "real_esrgan_gui"
            / "weights",
            Path.home() / "AppData" / "Local" / "real_esrgan_gui" / "weights",
            Path.home() / "AppData" / "Roaming" / "real_esrgan_gui" / "weights",
            Path.home()
            / "Library"
            / "Application Support"
            / "real_esrgan_gui"
            / "weights",
            Path.home() / "Library" / "Caches" / "real_esrgan_gui" / "weights",
        ]
    )

    seen: set[Path] = set()
    for d in candidates:
        if d is None:
            continue
        try:
            resolved = d.resolve()
        except Exception:
            resolved = d
        if resolved in seen:
            continue
        seen.add(resolved)

        target_file = resolved / filename
        if target_file.exists() and target_file.stat().st_size >= min_size:
            return target_file

    return None


def download_weight_file(
    model_key: str,
    dest_dir: Path,
    log_callback: Callable[[str, str], None] | None = None,
) -> Path:
    """Downloads model weights with atomic temp file writing and progress reporting.

    Raises RuntimeError if download fails or result is incomplete.
    """
    filename = MODEL_FILENAMES.get(model_key)
    url = MODEL_URLS.get(model_key)
    min_size = MODEL_MIN_SIZES.get(model_key, 1000)
    if not filename or not url:
        raise ValueError(f"Unknown model key: {model_key}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / filename

    if dest_file.exists():
        if dest_file.stat().st_size >= min_size:
            return dest_file
        dest_file.unlink(missing_ok=True)

    def log(msg: str, level: str = "INFO"):
        logger.info(msg)
        if log_callback:
            log_callback(msg, level)

    temp_file = dest_dir / f"{filename}.tmp"
    if temp_file.exists():
        temp_file.unlink(missing_ok=True)

    if sys.stdout is not None:
        try:
            print(f"\n[AI Model] Downloading {model_key} weights ({filename})...")
        except Exception:
            pass
    log(f"Downloading {model_key} weights ({filename}) from {url}...")

    try:
        from tqdm import tqdm

        has_stream = sys.stderr is not None and hasattr(sys.stderr, "write")
        out_stream = sys.stderr if has_stream else io.StringIO()
        disable_pbar = not has_stream

        with tqdm(
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            miniters=1,
            desc=filename,
            file=out_stream,
            disable=disable_pbar,
        ) as pbar:
            last_logged_pct = [-15]

            def reporthook(blocknum, blocksize, totalsize):
                if totalsize > 0:
                    if not disable_pbar:
                        pbar.total = totalsize
                    pct = int((blocknum * blocksize / totalsize) * 100)
                    if pct >= last_logged_pct[0] + 15:
                        last_logged_pct[0] = pct
                        mb_done = (blocknum * blocksize) / (1024 * 1024)
                        mb_tot = totalsize / (1024 * 1024)
                        log(
                            f"Downloading {filename}: {mb_done:.1f} / {mb_tot:.1f} MB ({pct}%)",
                            "INFO",
                        )
                if not disable_pbar:
                    pbar.update(blocksize)

            urllib.request.urlretrieve(url, temp_file, reporthook=reporthook)

        actual_size = temp_file.stat().st_size
        if actual_size < min_size:
            temp_file.unlink(missing_ok=True)
            raise RuntimeError(
                f"Downloaded file {filename} is incomplete ({actual_size} bytes, expected >= {min_size} bytes)"
            )

        # Atomic rename once verified
        temp_file.replace(dest_file)
        if sys.stdout is not None:
            try:
                print(f"[AI Model] Successfully downloaded {filename} to {dest_file}\n")
            except Exception:
                pass
        log(
            f"Successfully downloaded {filename} ({actual_size / (1024 * 1024):.1f} MB)"
        )
        return dest_file
    except Exception as exc:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
        if sys.stderr is not None:
            try:
                print(f"[Warning] Failed to download {filename}: {exc}")
            except Exception:
                pass
        log(f"Failed to download {filename}: {exc}", "ERROR")
        raise RuntimeError(
            f"Failed to download {model_key} weights ({filename}): {exc}"
        ) from exc


def ensure_face_enhancer_models(
    model_name: str = "gfpgan",
    custom_dir: Path | None = None,
    log_callback: Callable[[str, str], None] | None = None,
) -> tuple[Path, Path]:
    """Pre-flight check: ensures face detector and model weights exist before inference starts.

    Downloads missing weights sequentially in the main process to prevent race conditions.
    Raises RuntimeError if models cannot be verified or downloaded.
    """
    weights_dir = custom_dir or get_default_weights_dir()

    def log(msg: str, level: str = "INFO"):
        logger.info(msg)
        if log_callback:
            log_callback(msg, level)

    # 1. Detector
    yunet_file = find_weight_file("yunet", weights_dir)
    if not yunet_file:
        log("Face detector (YuNet) not found locally. Downloading...", "INFO")
        yunet_file = download_weight_file(
            "yunet", weights_dir, log_callback=log_callback
        )

    # 2. Face restoration model
    model_file = find_weight_file(model_name, weights_dir)
    if not model_file:
        filename = MODEL_FILENAMES.get(model_name, model_name)
        log(
            f"Face model '{model_name}' ({filename}) not found. Downloading (~340-380MB)...",
            "INFO",
        )
        model_file = download_weight_file(
            model_name, weights_dir, log_callback=log_callback
        )

    return yunet_file, model_file


class FaceEnhancer:
    """Performs face detection, affine alignment, ONNX restoration, and seamless blending."""

    def __init__(
        self,
        model_name: str = "gfpgan",
        fidelity_weight: float = 0.8,
        mask_mouth: bool = False,
        weights_dir: Path | None = None,
        onnx_session: Any | None = None,
        detector: Any | None = None,
    ):
        self.model_name = model_name.lower()
        self.fidelity_weight = float(np.clip(fidelity_weight, 0.0, 1.0))
        self.mask_mouth = mask_mouth
        self.weights_dir = weights_dir or get_default_weights_dir()

        self._session = onnx_session
        self._detector = detector
        self._initialized = False

    def initialize(self) -> bool:
        """Initializes detector and ONNX session."""
        if self._initialized:
            return True

        # Initialize detector if not provided
        if self._detector is None:
            yunet_file = find_weight_file("yunet", self.weights_dir)
            if not yunet_file:
                yunet_file = download_weight_file("yunet", self.weights_dir)

            if yunet_file and yunet_file.exists():
                try:
                    if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
                        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)

                    self._detector = cv2.FaceDetectorYN.create(
                        str(yunet_file),
                        "",
                        (320, 320),
                        score_threshold=0.6,
                        nms_threshold=0.3,
                        top_k=50,
                    )
                except Exception as exc:
                    logger.warning("Failed to create YuNet face detector: %s", exc)
            else:
                logger.warning("YuNet detector model not available.")

        # Initialize ONNX inference session if not provided
        if self._session is None:
            model_file = find_weight_file(self.model_name, self.weights_dir)
            if not model_file:
                model_file = download_weight_file(self.model_name, self.weights_dir)

            if model_file and model_file.exists():
                try:
                    import onnxruntime as ort

                    opts = ort.SessionOptions()
                    opts.graph_optimization_level = (
                        ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    )
                    self._session = ort.InferenceSession(
                        str(model_file),
                        sess_options=opts,
                        providers=["CPUExecutionProvider"],
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to load ONNX model %s: %s", self.model_name, exc
                    )
            else:
                logger.warning(
                    "Face model %s not available at %s", self.model_name, model_file
                )

        self._initialized = self._session is not None
        return self._initialized

    def detect_faces(self, img: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
        """Detects faces in BGR image.

        Returns:
            List of tuples: (bbox [x, y, w, h], landmarks_5 [5, 2])
        """
        if self._detector is None:
            return []

        h, w = img.shape[:2]
        self._detector.setInputSize((w, h))
        _, faces = self._detector.detect(img)

        results = []
        if faces is not None:
            for face in faces:
                bbox = face[0:4]
                # Landmarks: right_eye, left_eye, nose_tip, right_mouth, left_mouth
                landmarks = np.array(
                    [
                        [face[4], face[5]],
                        [face[6], face[7]],
                        [face[8], face[9]],
                        [face[10], face[11]],
                        [face[12], face[13]],
                    ],
                    dtype=np.float32,
                )
                results.append((bbox, landmarks))
        return results

    def align_face(
        self, img: np.ndarray, landmarks: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Aligns face to standard 512x512 coordinate frame using similarity transform."""
        M, _ = cv2.estimateAffinePartial2D(landmarks, CANONICAL_512)
        if M is None:
            # Fallback identity scale transform
            M = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
        aligned = cv2.warpAffine(img, M, (512, 512), borderMode=cv2.BORDER_REFLECT)
        return aligned, M

    def enhance_aligned_face(self, aligned_face: np.ndarray) -> np.ndarray:
        """Runs ONNX inference on a 512x512 aligned face."""
        if self._session is None:
            return aligned_face

        # Preprocess: BGR -> RGB, float32, normalized to [-1.0, 1.0]
        rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        tensor = (rgb.astype(np.float32) / 127.5) - 1.0
        tensor = np.transpose(tensor, (2, 0, 1))[np.newaxis, ...]  # (1, 3, 512, 512)

        input_names = [inp.name for inp in self._session.get_inputs()]
        feed_dict = {input_names[0]: tensor}

        # CodeFormer takes fidelity weight as second input if supported
        if len(input_names) > 1:
            w_input = self._session.get_inputs()[1]
            if "double" in w_input.type:
                feed_dict[input_names[1]] = np.array(
                    [self.fidelity_weight], dtype=np.float64
                )
            else:
                feed_dict[input_names[1]] = np.array(
                    [self.fidelity_weight], dtype=np.float32
                )

        output_name = self._session.get_outputs()[0].name
        out = self._session.run([output_name], feed_dict)[0]

        # Postprocess: [-1.0, 1.0] -> uint8 BGR
        out_face = out[0].transpose(1, 2, 0)
        out_face = np.clip((out_face + 1.0) * 127.5, 0, 255).astype(np.uint8)
        bgr_face = cv2.cvtColor(out_face, cv2.COLOR_RGB2BGR)

        # CodeFormer handles fidelity weight natively inside its neural network via latent codebook lookup.
        # Only apply post-blend for models like GFPGAN that lack native fidelity input.
        if len(input_names) == 1 and self.fidelity_weight < 1.0:
            bgr_face = cv2.addWeighted(
                bgr_face,
                self.fidelity_weight,
                aligned_face,
                1.0 - self.fidelity_weight,
                0.0,
            )

        return bgr_face

    @staticmethod
    def create_mouth_mask(
        landmarks_512: np.ndarray | None, feather_size: int = 35
    ) -> np.ndarray:
        """Creates a smooth feathered mask covering the mouth and teeth region in 512x512 space.

        Args:
            landmarks_512: 5-point landmarks in 512x512 aligned coordinate frame.
            feather_size: Gaussian blur kernel size (odd integer).

        Returns:
            Float32 mask of shape (512, 512, 1) with values in [0.0, 1.0].
        """
        if landmarks_512 is None or len(landmarks_512) < 5:
            center = (257.0, 371.0)
            width = 112.0
            angle = 0.0
        else:
            m1 = landmarks_512[3]
            m2 = landmarks_512[4]
            center = (float(m1[0] + m2[0]) / 2.0, float(m1[1] + m2[1]) / 2.0)
            width = float(np.linalg.norm(m2 - m1))
            angle = float(np.degrees(np.arctan2(m2[1] - m1[1], m2[0] - m1[0])))

        rx = int(max(40.0, width * 0.70))
        ry = int(max(25.0, width * 0.40))

        mouth_mask = np.zeros((512, 512), dtype=np.float32)
        cv2.ellipse(
            mouth_mask,
            (int(round(center[0])), int(round(center[1]))),
            (rx, ry),
            angle,
            0,
            360,
            1.0,
            -1,
        )

        k = feather_size if feather_size % 2 == 1 else feather_size + 1
        mouth_mask = cv2.GaussianBlur(mouth_mask, (k, k), 0)
        return mouth_mask[:, :, np.newaxis]

    def enhance_image(
        self, img: np.ndarray, mask_mouth: bool | None = None
    ) -> np.ndarray:
        """Detects and enhances all faces in the image, seamlessly blending results."""
        if not self.initialize():
            return img

        faces = self.detect_faces(img)
        if not faces:
            return img

        do_mask_mouth = self.mask_mouth if mask_mouth is None else mask_mouth
        h, w = img.shape[:2]
        result = img.copy().astype(np.float32)

        # Base 512x512 soft feather mask
        mask = np.zeros((512, 512), dtype=np.float32)
        cv2.ellipse(mask, (256, 256), (170, 220), 0, 0, 360, 1.0, -1)
        mask = cv2.GaussianBlur(mask, (51, 51), 0)[:, :, np.newaxis]

        for _, landmarks in faces:
            aligned, M = self.align_face(img, landmarks)
            enhanced_face = self.enhance_aligned_face(aligned)

            if do_mask_mouth:
                pts_512 = cv2.transform(landmarks.reshape(1, -1, 2), M)[0]
                m_mask = self.create_mouth_mask(pts_512)
                # Keep real/upscaled mouth & teeth where m_mask is 1.0, use AI face elsewhere
                enhanced_face = (
                    enhanced_face.astype(np.float32) * (1.0 - m_mask)
                    + aligned.astype(np.float32) * m_mask
                ).clip(0, 255).astype(np.uint8)

            # Invert transform
            M_inv = cv2.invertAffineTransform(M)
            inv_face = cv2.warpAffine(
                enhanced_face, M_inv, (w, h), borderMode=cv2.BORDER_REFLECT
            )
            inv_mask = cv2.warpAffine(
                mask, M_inv, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=0
            )
            if inv_mask.ndim == 2:
                inv_mask = inv_mask[:, :, np.newaxis]

            # Seamless blending
            result = result * (1.0 - inv_mask) + inv_face.astype(np.float32) * inv_mask

        return np.clip(result, 0, 255).astype(np.uint8)
