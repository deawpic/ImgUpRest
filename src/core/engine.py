import queue
import time
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing import Event, Process, Queue
from pathlib import Path

from PIL import Image

from src.core.config import UpscaleConfig
from src.core.models import MODEL_MAP
from src.core.worker import worker_process


@dataclass
class EngineResult:
    total: int
    completed: int
    failed: int
    elapsed_seconds: float
    output_dir: Path
    cancelled: bool = False


class UpscaleEngine:
    """Orchestrates multi-process hybrid GPU/CPU image upscaling with cancellation support."""

    def __init__(self):
        self._cancel_event = Event()
        self._is_running = False
        self._current_processes: list[Process] = []

    @property
    def is_running(self) -> bool:
        return self._is_running

    def cancel(self) -> None:
        """Signals all active workers to cancel processing cooperatively."""
        self._cancel_event.set()

    def process_single_image(
        self,
        img_path: Path,
        output_file: Path,
        scale: int = 4,
        model: str = "x4plus",
        tile_size: int = 0,
        quality: int = 92,
        gpuid: int = 0,
        output_format: str = "jpg",
        denoise_strength: int = 0,
        grain_strength: int = 0,
        enable_face_enhance: bool = False,
        face_model: str = "gfpgan",
        face_fidelity: float = 0.8,
        mask_mouth: bool = False,
        log_callback: Callable[[str, str], None] | None = None,
    ) -> Path:
        """Synchronously processes a single image. Ideal for GUI preview generation."""
        from realesrgan_ncnn_py import Realesrgan

        from src.core.metadata import extract_image_metadata, get_save_kwargs

        img_path = Path(img_path).resolve()
        output_file = Path(output_file).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        model_id = MODEL_MAP.get(model, 0)

        # Pre-flight check: ensure face model is ready before processing
        if enable_face_enhance:
            from src.core.face_enhancer import ensure_face_enhancer_models

            ensure_face_enhancer_models(model_name=face_model, log_callback=log_callback)

        upsampler = Realesrgan(gpuid=gpuid, model=model_id, tilesize=tile_size)

        with Image.open(img_path) as im:
            rgb_im = im.convert("RGB")
            orig_w, orig_h = rgb_im.size
            out_im = upsampler.process_pil(rgb_im)

            if scale == 2:
                out_im = out_im.resize(
                    (orig_w * 2, orig_h * 2), Image.Resampling.BILINEAR
                )

            # Apply Face Enhancement, Denoise, and Film Grain if enabled
            if enable_face_enhance or denoise_strength > 0 or grain_strength > 0:
                import cv2
                import numpy as np

                from src.core.denoise import apply_denoise
                from src.core.face_enhancer import FaceEnhancer
                from src.core.grain import apply_film_grain

                np_bgr = cv2.cvtColor(np.array(out_im), cv2.COLOR_RGB2BGR)

                if enable_face_enhance:
                    enhancer = FaceEnhancer(
                        model_name=face_model,
                        fidelity_weight=face_fidelity,
                        mask_mouth=mask_mouth,
                    )
                    np_bgr = enhancer.enhance_image(np_bgr)

                if denoise_strength > 0:
                    np_bgr = apply_denoise(np_bgr, strength=denoise_strength)

                if grain_strength > 0:
                    np_bgr = apply_film_grain(np_bgr, strength=grain_strength)

                out_im = Image.fromarray(cv2.cvtColor(np_bgr, cv2.COLOR_BGR2RGB))

            metadata = extract_image_metadata(img_path)
            save_kwargs = get_save_kwargs(metadata, output_format, quality=quality)
            out_im.save(output_file, **save_kwargs)

        return output_file

    def run(
        self,
        config: UpscaleConfig,
        on_progress: Callable[[int, int, float, float], None] | None = None,
        on_item_complete: Callable[[str, str | None, str | None], None] | None = None,
        on_log: Callable[[str, str], None] | None = None,
        on_finish: Callable[[EngineResult], None] | None = None,
    ) -> EngineResult:
        """Executes batch upscaling using multi-process workers."""
        config.validate()
        images = config.resolve_files()
        total_images = len(images)

        output_path = Path(config.output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        def log(msg: str, level: str = "INFO"):
            if on_log:
                on_log(msg, level)

        if total_images == 0:
            log("No supported image files found to process.", "WARNING")
            res = EngineResult(0, 0, 0, 0.0, output_path)
            if on_finish:
                on_finish(res)
            return res

        self._cancel_event.clear()
        self._is_running = True

        # Pre-flight check: ensure face enhancement model is ready BEFORE launching workers
        if config.enable_face_enhance:
            log(f"Verifying face restoration model '{config.face_model}'...", "INFO")
            try:
                from src.core.face_enhancer import ensure_face_enhancer_models

                ensure_face_enhancer_models(
                    model_name=config.face_model,
                    log_callback=log,
                )
                log(f"Face model '{config.face_model}' verified and ready.", "INFO")
            except Exception as exc:
                err_msg = f"Cannot proceed with face enhancement: {exc}"
                log(err_msg, "ERROR")
                res = EngineResult(
                    total=total_images,
                    completed=0,
                    failed=total_images,
                    elapsed_seconds=0.0,
                    output_dir=output_path,
                    cancelled=True,
                )
                if on_finish:
                    on_finish(res)
                return res

        num_cpu_workers = config.cpu_workers
        num_gpu_workers = 1 if config.enable_gpu else 0
        total_workers = num_gpu_workers + num_cpu_workers

        log(f"Found {total_images} images to upscale.")
        log(
            f"Launching: {num_gpu_workers}x GPU Worker (ID: {config.gpuid}) + "
            f"{num_cpu_workers}x CPU Workers. Model: {config.model}, Scale: {config.scale}x"
        )

        task_queue = Queue()
        progress_queue = Queue()

        for img in images:
            task_queue.put(img)

        # Send termination signals for all workers
        for _ in range(total_workers):
            task_queue.put(None)

        model_id = MODEL_MAP[config.model]
        processes: list[Process] = []

        # 1. Start GPU Worker
        if config.enable_gpu:
            p_gpu = Process(
                target=worker_process,
                args=(
                    task_queue,
                    progress_queue,
                    self._cancel_event,
                    config.gpuid,
                    model_id,
                    config.tile_size,
                    config.scale,
                    config.quality,
                    config.output_format,
                    output_path,
                    config.denoise_strength,
                    config.grain_strength,
                    config.enable_face_enhance,
                    config.face_model,
                    config.face_fidelity,
                    config.mask_mouth,
                ),
            )
            p_gpu.start()
            processes.append(p_gpu)

        # 2. Start CPU Workers
        for _ in range(num_cpu_workers):
            p_cpu = Process(
                target=worker_process,
                args=(
                    task_queue,
                    progress_queue,
                    self._cancel_event,
                    -1,
                    model_id,
                    config.tile_size,
                    config.scale,
                    config.quality,
                    config.output_format,
                    output_path,
                    config.denoise_strength,
                    config.grain_strength,
                    config.enable_face_enhance,
                    config.face_model,
                    config.face_fidelity,
                    config.mask_mouth,
                ),
            )
            p_cpu.start()
            processes.append(p_cpu)

        self._current_processes = processes

        completed = 0
        failed = 0
        processed_count = 0
        start_time = time.time()

        try:
            while processed_count < total_images and not self._cancel_event.is_set():
                try:
                    msg = progress_queue.get(timeout=0.5)
                except queue.Empty:
                    # Check if all processes died unexpectedly
                    if not any(p.is_alive() for p in processes):
                        log("All worker processes exited prematurely.", "ERROR")
                        break
                    continue

                success, in_file, out_file, err = msg
                if in_file is None and err:
                    log(err, "ERROR")
                    continue

                processed_count += 1
                if success:
                    completed += 1
                    log(f"Upscaled: {Path(in_file).name} -> {Path(out_file).name}")
                else:
                    failed += 1
                    log(f"Failed {Path(in_file).name}: {err}", "ERROR")

                if on_item_complete:
                    on_item_complete(in_file, out_file, err)

                now = time.time()
                elapsed = max(0.001, now - start_time)
                speed = processed_count / elapsed  # images/sec
                remaining_items = total_images - processed_count
                eta = remaining_items / speed if speed > 0 else 0.0

                if on_progress:
                    on_progress(processed_count, total_images, speed, eta)

        finally:
            self._is_running = False
            # Clean up processes
            for p in processes:
                if p.is_alive():
                    p.join(timeout=0.5)
                    if p.is_alive():
                        p.terminate()
                        p.join(timeout=0.5)

            # Close multiprocessing queues and cancel feeder join threads
            # to prevent hanging on interpreter shutdown
            try:
                task_queue.close()
                task_queue.cancel_join_thread()
            except Exception:
                pass
            try:
                progress_queue.close()
                progress_queue.cancel_join_thread()
            except Exception:
                pass

        total_elapsed = time.time() - start_time
        was_cancelled = self._cancel_event.is_set()

        if was_cancelled:
            log("Batch processing cancelled by user.", "WARNING")
        else:
            log(
                f"Processing finished in {total_elapsed:.2f}s. Completed: {completed}, Failed: {failed}"
            )

        result = EngineResult(
            total=total_images,
            completed=completed,
            failed=failed,
            elapsed_seconds=total_elapsed,
            output_dir=output_path,
            cancelled=was_cancelled,
        )

        if on_finish:
            on_finish(result)

        return result
