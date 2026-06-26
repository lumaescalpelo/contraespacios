from pathlib import Path

from utils import ensure_dir


def _fmt(value):
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def _path_bounds(paths):
    pts = [pt for path in paths for pt in path]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
    }


def _transform_point(x, y, config):
    """Convierte coordenadas del dibujo a coordenadas de máquina."""
    mode = getattr(config, "gcode_y_mode", "flip")
    if mode == "direct":
        return x, y
    if mode == "flip":
        return x, float(config.film_height_mm) - y
    raise ValueError(f"Modo de Y para G-code no soportado: {mode}")


def make_gcode(paths, config, feed_mm_min=300.0, seek_mm_min=600.0):
    """Convierte las trayectorias continuas en G-code compatible con GRBL."""
    lines = [
        "(Contraespacios drawing)",
        f"(area_mm: {_fmt(config.film_width_mm)} x {_fmt(config.film_height_mm)})",
        "(requires_homing_before_execution: true)",
        f"(gcode_y_mode: {getattr(config, 'gcode_y_mode', 'flip')})",
        "G21",
        "G90",
        "G17",
        "G94",
        "G54",
        f"F{_fmt(feed_mm_min)}",
    ]

    move_count = 0
    first_point = True

    for path in paths:
        if len(path) < 2:
            continue

        x0, y0 = path[0]
        x0, y0 = _transform_point(x0, y0, config)
        if first_point:
            lines.append(f"G0 X{_fmt(x0)} Y{_fmt(y0)} F{_fmt(seek_mm_min)}")
            first_point = False
        else:
            # Sin eje Z: el recorrido conecta un tramo con el siguiente.
            lines.append(f"G1 X{_fmt(x0)} Y{_fmt(y0)} F{_fmt(feed_mm_min)}")
            move_count += 1

        for x, y in path[1:]:
            x, y = _transform_point(x, y, config)
            lines.append(f"G1 X{_fmt(x)} Y{_fmt(y)}")
            move_count += 1

    lines.extend([
        "",
    ])

    bounds = _path_bounds(paths)
    return "\n".join(lines), {
        "feed_mm_min": float(feed_mm_min),
        "seek_mm_min": float(seek_mm_min),
        "move_count": move_count,
        "path_count": len([p for p in paths if len(p) >= 2]),
        "bounds": bounds,
        "units": "mm",
        "absolute_coordinates": True,
        "gcode_y_mode": getattr(config, "gcode_y_mode", "flip"),
        "requires_homing_before_execution": True,
        "work_area_mm": {
            "width": float(config.film_width_mm),
            "height": float(config.film_height_mm),
        },
    }


def write_gcode(output_path, paths, config, feed_mm_min=300.0, seek_mm_min=600.0):
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    gcode, info = make_gcode(paths, config, feed_mm_min, seek_mm_min)
    output_path.write_text(gcode, encoding="utf-8")
    info["gcode_path"] = str(output_path)
    return info
