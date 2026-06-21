"""Genera preview PNG desde las rutas en milímetros."""

from pathlib import Path

from PIL import Image, ImageDraw

from utils import ensure_dir
from svg_generator import flatten_paths


def write_preview(output_path, paths, config):
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    height_px = int(config.preview_height_px)
    width_px = max(64, int(round(height_px * film_w / film_h)))
    img = Image.new("RGB", (width_px, height_px), "white")
    draw = ImageDraw.Draw(img)
    points_mm = flatten_paths(paths)
    if len(points_mm) > 1:
        points_px = [
            (int(round((x / film_w) * (width_px - 1))), int(round((y / film_h) * (height_px - 1))))
            for x, y in points_mm
        ]
        draw.line(points_px, fill="black", width=max(1, int(config.preview_line_width_px)), joint="curve")
    draw.rectangle([0, 0, width_px - 1, height_px - 1], outline=(180, 180, 180), width=1)
    img.save(output_path)
    return {"preview_path": str(output_path), "preview_width_px": width_px, "preview_height_px": height_px}
