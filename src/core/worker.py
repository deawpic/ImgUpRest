import os
import queue
import time
from pathlib import Path

from PIL import Image

# Force OpenMP multi-threading
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"


def worker_process(
    task_queue,
    progress_queue,
    cancel_event,
    gpuid: int,
    model_id: int,
    tile_size: int,
    scale: int,
    quality: int,
    output_format: str,
    output_path: Path,
    denoise_strength: int = 0,
    grain_strength: int = 0,
    enable_face_enhance: bool = False,
    face_model: str = "codeformer",
    face_fidelity: float = 0.8,
    mask_mouth: bool = False,
    pause_event=None,
):
    """Worker process targeting either GPU (gpuid >= 0) or CPU (gpuid = -1)."""
    import cv2
    import numpy as np
    from realesrgan_ncnn_py import Realesrgan

    from src.core.denoise import apply_denoise
    from src.core.face_enhancer import FaceEnhancer
    from src.core.grain import apply_film_grain
    from src.core.metadata import extract_image_metadata, get_save_kwargs

    try:
        upsampler = Realesrgan(gpuid=gpuid, model=model_id, tilesize=tile_size)
    except Exception as e:
        # Report init failure to progress queue
        progress_queue.put((False, None, None, f"[Device {gpuid} Init Error]: {e}"))
        return

    face_enhancer = None
    if enable_face_enhance:
        try:
            face_enhancer = FaceEnhancer(
                model_name=face_model,
                fidelity_weight=face_fidelity,
                mask_mouth=mask_mouth,
            )
            if not face_enhancer.initialize():
                progress_queue.put(
                    (
                        False,
                        None,
                        None,
                        f"[Device {gpuid}]: Failed to initialize face enhancer for '{face_model}'.",
                    )
                )
                return
        except Exception as e:
            progress_queue.put(
                (
                    False,
                    None,
                    None,
                    f"[Device {gpuid}]: Face enhancer error: {e}",
                )
            )
            return

    fmt = output_format.lower().lstrip(".")
    if fmt == "jpeg":
        fmt = "jpg"

    while not cancel_event.is_set():
        if pause_event is not None and pause_event.is_set():
            time.sleep(0.15)
            continue

        try:
            item = task_queue.get(timeout=0.2)
        except queue.Empty:
            continue

        if item is None:
            # Poison pill received: shutdown worker
            break

        target_out_file: Path | None = None
        target_out_dir = output_path

        if isinstance(item, tuple):
            img_file = Path(item[0])
            if len(item) > 2 and item[2]:
                target_out_file = Path(item[2])
                target_out_dir = target_out_file.parent
            elif len(item) > 1 and item[1]:
                target_out_dir = Path(item[1])
        else:
            img_file = Path(item)

        if target_out_file is None:
            target_out_file = target_out_dir / f"{img_file.stem}_x{scale}.{fmt}"

        target_out_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with Image.open(img_file) as im:
                rgb_im = im.convert("RGB")
                orig_w, orig_h = rgb_im.size

                out_im = upsampler.process_pil(rgb_im)

                # If requested scale is 2x and model upscales to 4x, downscale
                if scale == 2:
                    out_im = out_im.resize(
                        (orig_w * 2, orig_h * 2), Image.Resampling.BILINEAR
                    )

                # Apply Face Enhancement, Denoise, and Film Grain if enabled
                if (
                    face_enhancer is not None
                    or denoise_strength > 0
                    or grain_strength > 0
                ):
                    np_bgr = cv2.cvtColor(np.array(out_im), cv2.COLOR_RGB2BGR)

                    if face_enhancer is not None:
                        np_bgr = face_enhancer.enhance_image(np_bgr)

                    if denoise_strength > 0:
                        np_bgr = apply_denoise(np_bgr, strength=denoise_strength)

                    if grain_strength > 0:
                        np_bgr = apply_film_grain(np_bgr, strength=grain_strength)

                    out_im = Image.fromarray(cv2.cvtColor(np_bgr, cv2.COLOR_BGR2RGB))

                out_file = target_out_file
                metadata = extract_image_metadata(img_file)
                save_kwargs = get_save_kwargs(metadata, fmt, quality=quality)
                out_im.save(out_file, **save_kwargs)


            progress_queue.put((True, str(img_file), str(out_file), None))
        except Exception as e:
            progress_queue.put((False, str(img_file), None, str(e)))
