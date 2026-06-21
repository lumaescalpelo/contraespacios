"""
Generación SVG.

Se genera un trazo continuo para anticipar que la máquina no tendrá eje Z.
Los saltos entre contornos son líneas reales de conexión.
"""

import math
from pathlib import Path

import svgwrite

from utils import clamp, ensure_dir


def _map_point_to_mm(point, film_w, film_h, margin):
    x, y = point
    draw_w = max(0.1, film_w - margin * 2)
    draw_h = max(0.1, film_h - margin * 2)
    return (
        margin + clamp(x, 0, 1) * draw_w,
        margin + clamp(y, 0, 1) * draw_h
    )


def _warp_point(x, y, visual, film_w, film_h):
    noise = float(visual.get("noise_mm", 0.08))
    freq = float(visual.get("wave_frequency", 2.0))
    phase = float(visual.get("phase", 0.0))

    nx = math.sin((y / max(0.1, film_h)) * math.tau * freq + phase) * noise
    ny = math.sin((x / max(0.1, film_w)) * math.tau * (freq * 0.67) + phase * 1.7) * noise * 0.45

    return (
        clamp(x + nx, 0, film_w),
        clamp(y + ny, 0, film_h)
    )


def _generate_atmosphere_path(visual, film_w, film_h, margin):
    lines = int(visual.get("atmosphere_lines", 10))
    lines = max(4, min(24, lines))

    amp = float(visual.get("noise_mm", 0.12)) * 2.0
    freq = float(visual.get("wave_frequency", 2.0))
    phase = float(visual.get("phase", 0.0))

    left = margin
    right = film_w - margin
    top = margin
    bottom = film_h - margin

    points = []
    samples = 32

    for i in range(lines):
        t = i / max(1, lines - 1)
        y_base = top + t * (bottom - top)

        row = []
        for s in range(samples):
            u = s / max(1, samples - 1)

            if i % 2 == 0:
                x = left + u * (right - left)
            else:
                x = right - u * (right - left)

            y = y_base + math.sin(u * math.tau * freq + phase + i * 0.35) * amp
            row.append((clamp(x, left, right), clamp(y, top, bottom)))

        points.extend(row)

    return points


def _nearest_order(paths):
    if not paths:
        return []

    remaining = [list(path) for path in paths if len(path) > 1]
    ordered = [remaining.pop(0)]

    while remaining:
        last = ordered[-1][-1]

        best_index = 0
        best_reverse = False
        best_dist = None

        for i, path in enumerate(remaining):
            d_start = (path[0][0] - last[0]) ** 2 + (path[0][1] - last[1]) ** 2
            d_end = (path[-1][0] - last[0]) ** 2 + (path[-1][1] - last[1]) ** 2

            if best_dist is None or d_start < best_dist:
                best_dist = d_start
                best_index = i
                best_reverse = False

            if d_end < best_dist:
                best_dist = d_end
                best_index = i
                best_reverse = True

        chosen = remaining.pop(best_index)
        if best_reverse:
            chosen = list(reversed(chosen))

        ordered.append(chosen)

    return ordered


def build_drawing_paths(image_paths_norm, visual, config):
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    margin = float(config.margin_mm)

    density = float(visual.get("density", 0.55))
    max_paths = int(config.max_paths)
    keep_count = max(1, min(max_paths, int(round(max_paths * density))))

    selected = image_paths_norm[:keep_count]

    mm_paths = []

    atmosphere = _generate_atmosphere_path(visual, film_w, film_h, margin)
    mm_paths.append(atmosphere)

    for path in selected:
        mapped = []
        for point in path:
            x, y = _map_point_to_mm(point, film_w, film_h, margin)
            x, y = _warp_point(x, y, visual, film_w, film_h)
            mapped.append((x, y))

        if len(mapped) >= config.min_points_per_path:
            mm_paths.append(mapped)

    mm_paths = _nearest_order(mm_paths)

    return mm_paths


def flatten_paths(paths):
    result = []
    for path in paths:
        for point in path:
            result.append(point)
    return result


def make_svg_path_data(paths):
    points = flatten_paths(paths)
    if not points:
        return ""

    commands = []
    first = points[0]
    commands.append(f"M {first[0]:.4f} {first[1]:.4f}")

    for x, y in points[1:]:
        commands.append(f"L {x:.4f} {y:.4f}")

    return " ".join(commands)


def write_svg(output_path, paths, config, metadata=None):
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)

    d = make_svg_path_data(paths)

    dwg = svgwrite.Drawing(
        str(output_path),
        size=(f"{film_w}mm", f"{film_h}mm"),
        viewBox=f"0 0 {film_w} {film_h}",
        profile="tiny"
    )

    dwg.add(dwg.rect(
        insert=(0, 0),
        size=(film_w, film_h),
        fill="white"
    ))

    dwg.add(dwg.rect(
        insert=(0, 0),
        size=(film_w, film_h),
        fill="none",
        stroke="black",
        stroke_width=0.03,
        opacity=0.25
    ))

    dwg.add(dwg.path(
        d=d,
        fill="none",
        stroke="black",
        stroke_width=float(getattr(config, "stroke_width_mm", 0.1)),
        stroke_linecap="round",
        stroke_linejoin="round"
    ))

    dwg.save()

    return {
        "svg_path": str(output_path),
        "path_points": len(flatten_paths(paths)),
        "path_segments": max(0, len(flatten_paths(paths)) - 1),
        "continuous_path": True,
    }
