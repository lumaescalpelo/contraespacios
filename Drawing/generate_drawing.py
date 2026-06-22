#!/usr/bin/env python3
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from drawing_config import DrawingConfig, DEFAULT_CONFIG
from environment_analysis import analyze_environment
from image_analysis import analyze_photos
from preview_generator import write_preview
from process_steps import save_process_steps
from session_loader import load_session
from svg_generator import build_drawing_paths, write_svg
from utils import load_json, now_iso, save_json


def update_session_json(session_json_path, session_id, metadata):
    path = Path(session_json_path)
    if path.exists():
        try:
            data = load_json(path)
        except Exception:
            data = {}
    else:
        data = {}
    data.setdefault("session_id", session_id)
    data["drawing_done"] = True
    data["updated_at"] = now_iso()
    data["status"] = "drawing_generated"
    data["output"] = {
        "drawing_svg": metadata["outputs"]["svg"],
        "preview_png": metadata["outputs"]["preview"],
        "metadata_json": metadata["outputs"]["metadata"],
        "generation_log_json": metadata["outputs"]["generation_log"],
    }
    save_json(path, data)


def build_config(args):
    return DrawingConfig(
        film_width_mm=float(args.film_width_mm),
        film_height_mm=float(args.film_height_mm),
        margin_mm=float(args.margin_mm),
        image_process_height_px=int(args.image_process_height_px),
        max_photos=int(args.max_photos),
        quantization_levels=int(args.quantization_levels),
        blur_size=int(args.blur_size),
        max_contours=int(args.max_contours),
        max_points_per_contour=int(args.max_points_per_contour),
        min_points_per_contour=DEFAULT_CONFIG.min_points_per_contour,
        contour_simplify_ratio=float(args.contour_simplify_ratio),
        min_contour_area_ratio=float(args.min_contour_area_ratio),
        landscape_bands=int(args.landscape_bands),
        band_samples=int(args.band_samples),
        band_dark_threshold=float(args.band_dark_threshold),
        band_amplitude_mm=float(args.band_amplitude_mm),
        band_min_length_ratio=float(args.band_min_length_ratio),
        internal_lines=int(args.internal_lines),
        internal_samples=int(args.internal_samples),
        internal_dark_threshold=float(args.internal_dark_threshold),
        internal_amplitude_mm=float(args.internal_amplitude_mm),
        stroke_width_mm=DEFAULT_CONFIG.stroke_width_mm,
        preview_height_px=int(args.preview_height_px),
        preview_line_width_px=DEFAULT_CONFIG.preview_line_width_px,
        algorithm_name=DEFAULT_CONFIG.algorithm_name,
    )


def run(args):
    started = now_iso()
    t0 = time.time()
    config = build_config(args)
    session = load_session(args.data_root, args.session, max_photos=config.max_photos)
    env_stats, visual = analyze_environment(session["environment"])
    config.stroke_width_mm = float(visual.get("stroke_width_mm", config.stroke_width_mm))
    image_analysis = analyze_photos(session["photos"], config)
    paths, drawing_meta = build_drawing_paths(image_analysis, visual, config)

    output_dir = session["paths"]["output"]
    svg_path = output_dir / "drawing.svg"
    preview_path = output_dir / "preview.png"
    metadata_path = output_dir / "metadata.json"
    log_path = output_dir / "generation_log.json"

    svg_info = write_svg(svg_path, paths, config)
    preview_info = write_preview(preview_path, paths, config)
    process_info = save_process_steps(session, image_analysis, env_stats, visual, config, output_dir)
    duration = round(time.time() - t0, 3)
    finished = now_iso()

    metadata = {
        "ok": True,
        "session_id": args.session,
        "algorithm": config.algorithm_name,
        "started_at": started,
        "created_at": finished,
        "duration_seconds": duration,
        "film": {
            "width_mm": config.film_width_mm,
            "height_mm": config.film_height_mm,
            "margin_mm": config.margin_mm,
            "orientation": "horizontal" if config.film_width_mm >= config.film_height_mm else "vertical",
            "coordinate_space": "millimeters",
            "continuous_path": True,
            "z_axis_required": False,
        },
        "inputs": {
            "photos_used": image_analysis["meta"]["photos_used"],
            "environment_readings_used": env_stats["readings_used"],
            "photo_files": image_analysis["meta"]["photo_files"],
            "environment_files": [str(x["path"]) for x in session["environment"]],
        },
        "environment": env_stats,
        "visual_parameters": visual,
        "image_analysis": image_analysis["meta"],
        "drawing_analysis": drawing_meta,
        "svg": svg_info,
        "preview": preview_info,
        "outputs": {
            "svg": str(svg_path),
            "preview": str(preview_path),
            "metadata": str(metadata_path),
            "generation_log": str(log_path),
            "process_steps_dir": process_info["steps_dir"],
            "process_manifest": process_info["manifest"],
        },
        "process_steps": process_info,
    }

    save_json(metadata_path, metadata)
    save_json(log_path, {
        "ok": True,
        "message": "Dibujo generado correctamente",
        "session_id": args.session,
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": duration,
        "outputs": metadata["outputs"],
    })
    update_session_json(session["paths"]["session_json"], args.session, metadata)

    return {
        "ok": True,
        "type": "drawing_result",
        "session_id": args.session,
        "message": "Dibujo generado",
        "svg": str(svg_path),
        "preview": str(preview_path),
        "metadata": str(metadata_path),
        "generation_log": str(log_path),
        "process_steps_dir": process_info["steps_dir"],
        "process_manifest": process_info["manifest"],
        "photos_used": metadata["inputs"]["photos_used"],
        "environment_readings_used": metadata["inputs"]["environment_readings_used"],
        "duration_seconds": duration,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Genera SVG v4 legible 30x32 mm para Contra Espacios.")
    p.add_argument("--session", required=True)
    p.add_argument("--data-root", default="/home/pi/data")
    p.add_argument("--film-width-mm", type=float, default=30.0)
    p.add_argument("--film-height-mm", type=float, default=32.0)
    p.add_argument("--margin-mm", type=float, default=0.8)
    p.add_argument("--max-photos", type=int, default=12)
    p.add_argument("--image-process-height-px", type=int, default=420)
    p.add_argument("--quantization_levels", type=int, default=5)
    p.add_argument("--blur-size", type=int, default=7)
    p.add_argument("--max-contours", type=int, default=8)
    p.add_argument("--max-points-per-contour", type=int, default=100)
    p.add_argument("--contour-simplify-ratio", type=float, default=0.012)
    p.add_argument("--min-contour-area-ratio", type=float, default=0.0025)
    p.add_argument("--landscape-bands", type=int, default=5)
    p.add_argument("--band-samples", type=int, default=90)
    p.add_argument("--band-dark-threshold", type=float, default=0.55)
    p.add_argument("--band-amplitude-mm", type=float, default=0.75)
    p.add_argument("--band-min-length-ratio", type=float, default=0.08)
    p.add_argument("--internal-lines", type=int, default=3)
    p.add_argument("--internal-samples", type=int, default=80)
    p.add_argument("--internal-dark-threshold", type=float, default=0.46)
    p.add_argument("--internal-amplitude-mm", type=float, default=0.42)
    p.add_argument("--preview-height-px", type=int, default=700)
    return p.parse_args()


def main():
    args = parse_args()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "type": "drawing_result",
            "session_id": getattr(args, "session", None),
            "message": str(exc),
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
