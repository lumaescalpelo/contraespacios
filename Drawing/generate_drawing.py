#!/usr/bin/env python3
"""
Generador principal de SVG para Contra Espacios.

Ejemplo:
python3 generate_drawing.py --session S01 --data-root /home/pi/data --film-width-mm 16 --film-height-mm 43

Imprime un JSON final en stdout para que Node-RED pueda procesarlo.
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from drawing_config import DEFAULT_CONFIG, DrawingConfig
from environment_analysis import analyze_environment
from image_analysis import analyze_photos
from preview_generator import write_preview
from session_loader import load_session
from svg_generator import build_drawing_paths, write_svg
from utils import load_json, now_iso, save_json


def update_session_json(session_json_path, session_id, metadata):
    session_json_path = Path(session_json_path)

    if session_json_path.exists():
        try:
            session_data = load_json(session_json_path)
        except Exception:
            session_data = {}
    else:
        session_data = {}

    session_data.setdefault("session_id", session_id)
    session_data["drawing_done"] = True
    session_data["updated_at"] = now_iso()
    session_data["status"] = "drawing_generated"
    session_data["output"] = {
        "drawing_svg": metadata["outputs"]["svg"],
        "preview_png": metadata["outputs"]["preview"],
        "metadata_json": metadata["outputs"]["metadata"],
        "generation_log_json": metadata["outputs"]["generation_log"],
    }

    save_json(session_json_path, session_data)


def build_config(args):
    cfg = DrawingConfig(
        film_width_mm=float(args.film_width_mm),
        film_height_mm=float(args.film_height_mm),
        margin_mm=float(args.margin_mm),
        image_process_height_px=int(args.image_process_height_px),
        max_photos=int(args.max_photos),
        max_paths=int(args.max_paths),
        max_points_per_path=int(args.max_points_per_path),
        min_points_per_path=DEFAULT_CONFIG.min_points_per_path,
        blur_size=DEFAULT_CONFIG.blur_size,
        canny_low=int(args.canny_low),
        canny_high=int(args.canny_high),
        contour_simplify_ratio=DEFAULT_CONFIG.contour_simplify_ratio,
        preview_height_px=int(args.preview_height_px),
        preview_line_width_px=DEFAULT_CONFIG.preview_line_width_px,
        stroke_width_mm=DEFAULT_CONFIG.stroke_width_mm,
        base_seed=DEFAULT_CONFIG.base_seed,
        algorithm_name=DEFAULT_CONFIG.algorithm_name,
    )
    return cfg


def run(args):
    started = now_iso()
    start_time = time.time()

    cfg = build_config(args)

    session = load_session(
        data_root=args.data_root,
        session_id=args.session,
        max_photos=cfg.max_photos
    )

    env_stats, visual = analyze_environment(session["environment"])

    cfg.stroke_width_mm = float(visual.get("stroke_width_mm", cfg.stroke_width_mm))

    image_paths, image_meta = analyze_photos(session["photos"], cfg)

    drawing_paths = build_drawing_paths(image_paths, visual, cfg)

    output_dir = session["paths"]["output"]
    output_dir.mkdir(parents=True, exist_ok=True)

    svg_path = output_dir / "drawing.svg"
    preview_path = output_dir / "preview.png"
    metadata_path = output_dir / "metadata.json"
    log_path = output_dir / "generation_log.json"

    svg_info = write_svg(svg_path, drawing_paths, cfg)
    preview_info = write_preview(preview_path, drawing_paths, cfg)

    finished = now_iso()
    duration = round(time.time() - start_time, 3)

    metadata = {
        "ok": True,
        "session_id": args.session,
        "algorithm": cfg.algorithm_name,
        "created_at": finished,
        "started_at": started,
        "duration_seconds": duration,

        "film": {
            "width_mm": cfg.film_width_mm,
            "height_mm": cfg.film_height_mm,
            "margin_mm": cfg.margin_mm,
            "coordinate_space": "millimeters",
            "continuous_path": True,
            "z_axis_required": False,
        },

        "inputs": {
            "photos_used": image_meta.get("photos_used", 0),
            "environment_readings_used": env_stats.get("readings_used", 0),
            "photo_files": image_meta.get("photo_files", []),
            "environment_files": [str(item["path"]) for item in session["environment"]],
        },

        "environment": env_stats,
        "visual_parameters": visual,
        "image_analysis": image_meta,
        "svg": svg_info,
        "preview": preview_info,

        "outputs": {
            "svg": str(svg_path),
            "preview": str(preview_path),
            "metadata": str(metadata_path),
            "generation_log": str(log_path),
        }
    }

    save_json(metadata_path, metadata)

    generation_log = {
        "ok": True,
        "message": "Dibujo generado correctamente",
        "session_id": args.session,
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": duration,
        "outputs": metadata["outputs"],
    }

    save_json(log_path, generation_log)
    update_session_json(session["paths"]["session_json"], args.session, metadata)

    result = {
        "ok": True,
        "type": "drawing_result",
        "session_id": args.session,
        "message": "Dibujo generado",
        "svg": str(svg_path),
        "preview": str(preview_path),
        "metadata": str(metadata_path),
        "generation_log": str(log_path),
        "photos_used": metadata["inputs"]["photos_used"],
        "environment_readings_used": metadata["inputs"]["environment_readings_used"],
        "duration_seconds": duration,
    }

    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Genera SVG de Contra Espacios desde una sesión.")

    parser.add_argument("--session", required=True, help="ID de sesión, por ejemplo S01")
    parser.add_argument("--data-root", default="/home/pi/data", help="Carpeta de datos persistentes")
    parser.add_argument("--film-width-mm", type=float, default=16.0, help="Ancho físico del área de dibujo")
    parser.add_argument("--film-height-mm", type=float, default=43.0, help="Alto físico del área de dibujo")
    parser.add_argument("--margin-mm", type=float, default=0.7, help="Margen interno")
    parser.add_argument("--max-photos", type=int, default=12, help="Máximo de fotos a procesar")
    parser.add_argument("--max-paths", type=int, default=80, help="Máximo de contornos")
    parser.add_argument("--max-points-per-path", type=int, default=220, help="Máximo de puntos por contorno")
    parser.add_argument("--image-process-height-px", type=int, default=640, help="Altura de procesamiento de imagen")
    parser.add_argument("--preview-height-px", type=int, default=1200, help="Altura del preview PNG")
    parser.add_argument("--canny-low", type=int, default=60, help="Umbral bajo Canny")
    parser.add_argument("--canny-high", type=int, default=150, help="Umbral alto Canny")

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        error = {
            "ok": False,
            "type": "drawing_result",
            "session_id": getattr(args, "session", None),
            "message": str(exc),
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(error, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
