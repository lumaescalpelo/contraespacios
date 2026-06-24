from pathlib import Path

import numpy as np
import svgwrite

from utils import clamp, ensure_dir


def _map_norm_to_mm(xn, yn, film_w, film_h, margin):
    draw_w = max(0.1, film_w - margin * 2)
    draw_h = max(0.1, film_h - margin * 2)
    return margin + xn * draw_w, margin + yn * draw_h


def flatten_paths(paths):
    out = []
    for p in paths:
        out.extend(p)
    return out


def _nearest_order(paths):
    if not paths:
        return []
    remaining = [list(p) for p in paths if len(p) > 1]
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1][-1]
        best_idx = 0
        best_rev = False
        best_d = None
        for i, path in enumerate(remaining):
            d0 = (path[0][0] - last[0])**2 + (path[0][1] - last[1])**2
            d1 = (path[-1][0] - last[0])**2 + (path[-1][1] - last[1])**2
            if best_d is None or d0 < best_d:
                best_d = d0
                best_idx = i
                best_rev = False
            if d1 < best_d:
                best_d = d1
                best_idx = i
                best_rev = True
        picked = remaining.pop(best_idx)
        if best_rev:
            picked = list(reversed(picked))
        ordered.append(picked)
    return ordered


def _merge_segments_to_paths(seg_points):
    paths = []
    for seg in seg_points:
        if len(seg) >= 2:
            paths.append(seg)
    return paths


def _partial_landscape_bands(image_analysis, visual, config):
    gray = image_analysis['smooth'].astype(np.float32) / 255.0
    h, w = gray.shape[:2]
    density = float(visual.get('band_density', 0.9))
    amp_factor = float(visual.get('band_amplitude_factor', 1.0))

    # Escalado más suave: valores grandes siguen siendo utilizables.
    requested = max(1.0, float(config.landscape_bands))
    num_bands = max(3, int(round(1.0 + (requested - 1.0) * density * 0.55)))
    num_bands = min(num_bands, 8)
    samples = int(config.band_samples)
    thresh = float(config.band_dark_threshold)
    amp_mm = float(config.band_amplitude_mm) * (0.88 + 0.12 * amp_factor)

    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    margin = float(config.margin_mm)
    draw_w = film_w - margin * 2
    draw_h = film_h - margin * 2
    min_seg_len = max(3, int(round(samples * float(config.band_min_length_ratio))))

    paths = []
    band_meta = {"bands_used": num_bands, "band_segments": 0, "band_amplitude_mm": round(amp_mm, 4)}

    # Más concentrado al centro para una lectura tipo paisaje.
    base_ys = np.linspace(0.24, 0.76, num_bands)

    for bi, y_norm in enumerate(base_ys):
        y_idx = int(round(y_norm * (h - 1)))
        xs = np.linspace(0, w - 1, samples)
        darkness = []
        for x in xs:
            xi = int(round(x))
            y0 = max(0, y_idx - 2)
            y1 = min(h, y_idx + 3)
            v = 1.0 - float(np.mean(gray[y0:y1, xi]))
            darkness.append(v)
        darkness = np.array(darkness, dtype=np.float32)
        active = darkness >= thresh

        seg = []
        seg_len = 0
        current = []
        for j, x in enumerate(xs):
            xn = float(x) / max(1.0, w - 1)
            x_mm = margin + xn * draw_w
            base_y_mm = margin + y_norm * draw_h
            offset = (darkness[j] - thresh) / max(1e-5, (1.0 - thresh))
            offset = clamp(offset, 0.0, 1.0)
            direction = -1.0 if bi % 2 == 0 else 1.0
            y_mm = base_y_mm + direction * offset * amp_mm
            y_mm = clamp(y_mm, margin, film_h - margin)

            if active[j]:
                current.append((x_mm, y_mm))
                seg_len += 1
            else:
                if seg_len >= min_seg_len:
                    seg.append(current)
                current = []
                seg_len = 0
        if seg_len >= min_seg_len:
            seg.append(current)

        if bi % 2 == 1:
            seg = [list(reversed(s)) for s in seg]
            seg.reverse()
        paths.extend(_merge_segments_to_paths(seg))

    band_meta['band_segments'] = len(paths)
    return paths, band_meta


def _internal_feature_lines(image_analysis, visual, config):
    gray = image_analysis['smooth'].astype(np.float32) / 255.0
    h, w = gray.shape[:2]
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    margin = float(config.margin_mm)
    draw_w = film_w - margin * 2
    draw_h = film_h - margin * 2

    requested = max(1.0, float(config.internal_lines))
    num_lines = max(1, int(round(1.0 + (requested - 1.0) * float(visual.get('internal_weight', 0.8)) * 0.50)))
    num_lines = min(num_lines, 5)
    samples = int(config.internal_samples)
    thresh = float(config.internal_dark_threshold)
    amp_mm = float(config.internal_amplitude_mm)

    y_positions = np.linspace(0.32, 0.68, num_lines)
    paths = []
    for li, y_norm in enumerate(y_positions):
        y_idx = int(round(y_norm * (h - 1)))
        xs = np.linspace(0, w - 1, samples)
        pts = []
        for x in xs:
            xi = int(round(x))
            window = gray[max(0, y_idx-5):min(h, y_idx+6), xi]
            dark = 1.0 - window
            best_k = int(np.argmax(dark))
            best_dark = float(np.max(dark))
            if best_dark < thresh:
                continue
            local_y = max(0, y_idx-5) + best_k
            xn = float(x) / max(1.0, w - 1)
            yn = (0.75 * (float(local_y) / max(1.0, h - 1))) + (0.25 * y_norm)
            x_mm = margin + xn * draw_w
            y_mm = margin + yn * draw_h
            y_mm += (best_dark - thresh) * amp_mm * (1 if li % 2 else -1)
            y_mm = clamp(y_mm, margin, film_h - margin)
            pts.append((x_mm, y_mm))
        if len(pts) >= max(10, samples // 4):
            if li % 2 == 1:
                pts.reverse()
            paths.append(pts)
    return paths, {"internal_lines_used": len(paths)}


def _contours_to_paths(contours, visual, config):
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    margin = float(config.margin_mm)

    # Escalado suave: aunque haya muchos contornos disponibles, no satura la escena.
    available = len(contours)
    requested = max(1, int(config.max_contours))
    base_keep = min(available, requested)
    weight = float(visual.get('contour_weight', 0.8))
    keep = max(1, int(round(1 + max(0, base_keep - 1) * weight * 0.45)))
    keep = min(keep, available)
    selected = contours[:keep]

    paths = []
    for c in selected:
        pts = []
        for xn, yn in c:
            x_mm, y_mm = _map_norm_to_mm(xn, yn, film_w, film_h, margin)
            pts.append((x_mm, y_mm))
        if len(pts) >= int(config.min_points_per_contour):
            paths.append(pts)
    return paths, {"contours_selected": len(paths)}


def build_drawing_paths(image_analysis, visual, config):
    band_paths, band_meta = _partial_landscape_bands(image_analysis, visual, config)
    internal_paths, internal_meta = _internal_feature_lines(image_analysis, visual, config)
    contour_paths, contour_meta = _contours_to_paths(image_analysis['contours'], visual, config)

    # Pocas trayectorias, ordenadas por vecindad.
    grouped = band_paths + internal_paths + contour_paths
    ordered = _nearest_order(grouped)
    meta = {
        **band_meta,
        **internal_meta,
        **contour_meta,
        "continuous_path": True,
        "style": "landscape_legible",
    }
    return ordered, meta


def make_svg_path_data(paths):
    flat_commands = []
    if not paths:
        return ""
    first = True
    prev_last = None
    for path in paths:
        if not path:
            continue
        if first:
            flat_commands.append(f"M {path[0][0]:.4f} {path[0][1]:.4f}")
            for x, y in path[1:]:
                flat_commands.append(f"L {x:.4f} {y:.4f}")
            first = False
        else:
            # conectar continuo al inicio del nuevo path.
            flat_commands.append(f"L {path[0][0]:.4f} {path[0][1]:.4f}")
            for x, y in path[1:]:
                flat_commands.append(f"L {x:.4f} {y:.4f}")
        prev_last = path[-1]
    return " ".join(flat_commands)


def write_svg(output_path, paths, config):
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    film_w = float(config.film_width_mm)
    film_h = float(config.film_height_mm)
    d = make_svg_path_data(paths)
    dwg = svgwrite.Drawing(str(output_path), size=(f"{film_w}mm", f"{film_h}mm"), viewBox=f"0 0 {film_w} {film_h}", profile="tiny")
    dwg.add(dwg.rect(insert=(0,0), size=(film_w, film_h), fill="white"))
    dwg.add(dwg.path(d=d, fill="none", stroke="black", stroke_width=float(config.stroke_width_mm), stroke_linecap="round", stroke_linejoin="round"))
    dwg.save()
    pts = flatten_paths(paths)
    return {"svg_path": str(output_path), "path_points": len(pts), "path_segments": max(0, len(pts) - 1), "continuous_path": True}
