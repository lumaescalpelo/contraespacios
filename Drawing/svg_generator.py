"""Generación SVG v2: raster serpentino + contornos."""

from pathlib import Path

import svgwrite
import numpy as np

from utils import clamp, ensure_dir


def _map_norm_to_mm(xn, yn, film_w, film_h, margin):
    draw_w = max(0.1, film_w - margin * 2)
    draw_h = max(0.1, film_h - margin * 2)
    return margin + xn * draw_w, margin + yn * draw_h


def _nearest_order(paths):
    if not paths:
        return []
    remaining = [list(p) for p in paths if len(p) > 1]
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1][-1]
        best_i = 0
        best_rev = False
        best_d = None
        for i, path in enumerate(remaining):
            d0 = (path[0][0] - last[0]) ** 2 + (path[0][1] - last[1]) ** 2
            d1 = (path[-1][0] - last[0]) ** 2 + (path[-1][1] - last[1]) ** 2
            if best_d is None or d0 < best_d:
                best_d = d0
                best_i = i
                best_rev = False
            if d1 < best_d:
                best_d = d1
                best_i = i
                best_rev = True
        chosen = remaining.pop(best_i)
        if best_rev:
            chosen = list(reversed(chosen))
        ordered.append(chosen)
    return ordered


def _sample_row(arr, y_idx, sample_count):
    h, w = arr.shape[:2]
    xs = np.linspace(0, w - 1, sample_count)
    row = []
    y = int(np.clip(y_idx, 0, h - 1))
    for x in xs:
        xi = int(np.clip(round(float(x)), 0, w - 1))
        row.append(float(arr[y, xi]))
    return xs, np.array(row, dtype=np.float32)


def _build_scanline_path(gray, edges, visual, config):
    h, w = gray.shape[:2]
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    margin = float(config.margin_mm)
    draw_w = film_w - margin * 2
    draw_h = film_h - margin * 2

    density = float(visual.get("density", 0.85))
    scan_factor = float(visual.get("scanline_factor", 1.0))
    amp_factor = float(visual.get("scan_amplitude_factor", 1.0))
    edge_weight = float(visual.get("edge_weight", 0.95))
    tone_gamma = float(visual.get("tone_gamma", 0.95))

    scanlines = int(round(config.base_scanlines * density * scan_factor))
    scanlines = max(26, min(int(config.max_scanlines), scanlines))
    samples = max(60, int(config.samples_per_scanline))
    amp_mm = clamp(config.base_amplitude_mm * amp_factor, config.base_amplitude_mm * 0.8, config.max_amplitude_mm)

    # Normalizaciones.
    gray_n = gray.astype(np.float32) / 255.0
    edges_n = edges.astype(np.float32) / 255.0

    points = []
    ys = np.linspace(0, h - 1, scanlines)

    for i, y_img in enumerate(ys):
        base_y_mm = margin + (i / max(1, scanlines - 1)) * draw_h
        xs_img, row_g = _sample_row(gray_n, y_img, samples)
        _, row_e = _sample_row(edges_n, y_img, samples)

        darkness = 1.0 - row_g
        darkness = np.power(np.clip(darkness, 0.0, 1.0), tone_gamma)
        emphasis = np.clip(darkness * config.tonal_gain + row_e * config.edge_gain * edge_weight, 0.0, 1.4)

        row_points = []
        for j, x_img in enumerate(xs_img):
            xn = float(x_img) / max(1.0, w - 1)
            x_mm = margin + xn * draw_w

            # Desplazamiento vertical proporcional al tono + borde.
            offset = emphasis[j] * amp_mm
            y_mm = base_y_mm + offset
            y_mm = clamp(y_mm, margin, film_h - margin)
            row_points.append((x_mm, y_mm))

        if i % 2 == 1:
            row_points.reverse()

        points.extend(row_points)

    return points, {
        "scanlines_used": scanlines,
        "samples_per_scanline": samples,
        "scanline_amplitude_mm": round(amp_mm, 4),
    }


def _build_contour_paths(contours, visual, config):
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    margin = float(config.margin_mm)
    keep_ratio = float(visual.get("contour_weight", 0.75))
    keep_count = max(0, int(round(len(contours) * keep_ratio)))
    selected = contours[:keep_count]
    paths = []
    for contour in selected:
        path = []
        for xn, yn in contour:
            x_mm, y_mm = _map_norm_to_mm(xn, yn, film_w, film_h, margin)
            path.append((x_mm, y_mm))
        if len(path) >= config.min_points_per_contour:
            paths.append(path)
    return _nearest_order(paths), {"contours_selected": len(paths)}


def build_drawing_paths(image_analysis, visual, config):
    gray = image_analysis["gray"]
    edges = image_analysis["edges"]
    contours = image_analysis["contours"]

    scanline_points, scan_meta = _build_scanline_path(gray, edges, visual, config)
    contour_paths, contour_meta = _build_contour_paths(contours, visual, config)

    # Un solo recorrido continuo: primero raster, luego contornos relevantes.
    paths = [scanline_points] + contour_paths
    meta = {}
    meta.update(scan_meta)
    meta.update(contour_meta)
    meta["continuous_path"] = True
    return paths, meta


def flatten_paths(paths):
    out = []
    for p in paths:
        out.extend(p)
    return out


def make_svg_path_data(paths):
    pts = flatten_paths(paths)
    if not pts:
        return ""
    commands = [f"M {pts[0][0]:.4f} {pts[0][1]:.4f}"]
    for x, y in pts[1:]:
        commands.append(f"L {x:.4f} {y:.4f}")
    return " ".join(commands)


def write_svg(output_path, paths, config):
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    d = make_svg_path_data(paths)
    dwg = svgwrite.Drawing(str(output_path), size=(f"{film_w}mm", f"{film_h}mm"), viewBox=f"0 0 {film_w} {film_h}", profile="tiny")
    dwg.add(dwg.rect(insert=(0, 0), size=(film_w, film_h), fill="white"))
    dwg.add(dwg.path(d=d, fill="none", stroke="black", stroke_width=float(getattr(config, "stroke_width_mm", 0.1)), stroke_linecap="round", stroke_linejoin="round"))
    dwg.save()
    pts = flatten_paths(paths)
    return {
        "svg_path": str(output_path),
        "path_points": len(pts),
        "path_segments": max(0, len(pts) - 1),
        "continuous_path": True,
    }
