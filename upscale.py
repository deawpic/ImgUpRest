import argparse
import os
import sys
from pathlib import Path

# Set OpenMP environment variables before importing native modules
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

from tqdm import tqdm

from src.core import MODEL_MAP, PRESETS, UpscaleConfig, UpscaleEngine


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Core Hybrid GPU + CPU Upscaler")
    parser.add_argument(
        "--input_dir", "-i", type=str, required=True, help="Input directory"
    )
    parser.add_argument(
        "--output_dir", "-o", type=str, required=True, help="Output directory"
    )
    parser.add_argument(
        "--preset",
        "-p",
        type=str,
        default=None,
        choices=list(PRESETS.keys()),
        help=f"1-Click photography preset: {list(PRESETS.keys())}",
    )
    parser.add_argument(
        "--scale",
        "-s",
        type=int,
        choices=[2, 4],
        default=4,
        help="Scale factor (default: 4)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="x4plus",
        choices=list(MODEL_MAP.keys()),
        help="AI Model (default: x4plus)",
    )
    parser.add_argument(
        "--tile_size",
        "-t",
        type=int,
        default=0,
        help="Tile size (0 for fastest)",
    )
    parser.add_argument(
        "--quality",
        "-q",
        type=int,
        default=92,
        help="JPG quality 1-100 (default: 92)",
    )
    parser.add_argument(
        "--cpu_workers",
        "-c",
        type=int,
        default=3,
        help="Number of CPU workers (default: 3)",
    )
    parser.add_argument(
        "--denoise",
        "-d",
        type=int,
        default=0,
        help="Denoise level 0-100 (default: 0, preserves natural grain & skin texture)",
    )
    parser.add_argument(
        "--grain",
        "-g",
        type=int,
        default=None,
        help="Film grain strength 0-10 (default: 0)",
    )
    parser.add_argument(
        "--face_enhance",
        "-f",
        action="store_true",
        help="Enable face enhancement (GFPGAN / CodeFormer ONNX)",
    )
    parser.add_argument(
        "--face_model",
        type=str,
        default="codeformer",
        choices=["codeformer", "gfpgan"],
        help="Face enhancement model (default: codeformer)",
    )
    parser.add_argument(
        "--face_fidelity",
        type=float,
        default=0.8,
        help="Face fidelity weight 0.0-1.0 (default: 0.8)",
    )
    parser.add_argument(
        "--mask_mouth",
        "-mm",
        action="store_true",
        help="Preserve natural mouth and teeth without AI alteration",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_dir).resolve()
    output_path = Path(args.output_dir).resolve()

    if not input_path.is_dir():
        print(f"[Error] Input directory not found: {input_path}")
        sys.exit(1)

    config = UpscaleConfig(
        input_path=input_path,
        output_dir=output_path,
        scale=args.scale,
        model=args.model,
        tile_size=args.tile_size,
        quality=args.quality,
        cpu_workers=args.cpu_workers,
        enable_gpu=True,
        gpuid=0,
        denoise_strength=args.denoise,
        grain_strength=args.grain if args.grain is not None else 0,
        enable_face_enhance=args.face_enhance,
        face_model=args.face_model,
        face_fidelity=args.face_fidelity,
        mask_mouth=args.mask_mouth,
    )

    if args.preset and args.preset in PRESETS:
        preset = PRESETS[args.preset]
        preset.apply_to_config(config)
        if args.grain is not None:
            config.grain_strength = args.grain
        if args.mask_mouth:
            config.mask_mouth = True
        print(f"[Preset] Applied '{args.preset}': {preset.description}")

    images = config.resolve_files()
    if not images:
        print(f"[Info] No supported images found in {input_path}")
        return

    engine = UpscaleEngine()

    with tqdm(total=len(images), desc="Upscaling") as pbar:

        def on_progress(completed, total, speed, eta):
            pbar.n = completed
            pbar.set_postfix({"speed": f"{speed:.1f} img/s", "eta": f"{eta:.1f}s"})
            pbar.refresh()

        result = engine.run(
            config=config,
            on_progress=on_progress,
            on_log=lambda msg, level: (
                print(f"[{level}] {msg}") if level != "INFO" else None
            ),
        )

    if result.cancelled:
        print("\n[Cancelled] Processing was stopped early.")
    else:
        print(
            f"\n[Success] Completed {result.completed}/{result.total} images saved to: {output_path}"
        )


if __name__ == "__main__":
    main()
