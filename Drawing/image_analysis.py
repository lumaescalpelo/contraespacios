"""
Análisis de imagen.

Lee fotos de la sesión y extrae contornos ligeros. OpenCV es preferido, pero se
incluye una ruta de emergencia con Pillow si cv2 no está disponible.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

try:
    import cv2
except Exception:
    cv2 = None

from utils import natural_sort_key


def _center_crop_to_aspect_array(gray, target_aspect):
    h, w = gray.shape[:2]
    current_aspect = w / float(h)

    if current_aspect > target_aspect:
        new_w = max(1, int(h * target_aspect))
        x0 = (w - new_w) // 2
        return gray[:, x0:x0 + new_w]

    new_h = max(1, int(w / target_aspect))
    y0 = (h - new_h) // 2
    return gray[y0:y0 + new_h, :]


def _load_gray_cv2(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"No se pudo abrir imagen: {path}")
    return img


def _load_gray_pillow(path):
    img = Image.open(path)
    img = ImageOps.grayscale(img)
    return np.array(img)


def _resize_array(gray, target_w, target_h):
    if cv2 is not None:
        return cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)

    img = Image.fromarray(gray)
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return np.array(img)


def _composite_photos(photo_paths, film_aspect, target_h):
    target_w = max(32, int(round(target_h * film_aspect)))
    processed = []

    for path in photo_paths:
        gray = _load_gray_cv2(path) if cv2 is not None else _load_gray_pillow(path)
        gray = _center_crop_to_aspect_array(gray, film_aspect)
        gray = _resize_array(gray, target_w, target_h)
        processed.append(gray.astype(np.float32))

    composite = np.mean(processed, axis=0).astype(np.uint8)

    return composite


def _extract_contours_cv2(composite, config):
    blur_size = int(config.blur_size)
    if blur_size % 2 == 0:
        blur_size += 1

    blurred = cv2.GaussianBlur(composite, (blur_size, blur_size), 0)
    edges = cv2.Canny(blurred, int(config.canny_low), int(config.canny_high))

    found = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if len(found) == 2:
        contours, _hierarchy = found
    else:
        _image, contours, _hierarchy = found

    h, w = composite.shape[:2]

    scored = []
    for contour in contours:
        if contour is None or len(contour) < config.min_points_per_path:
            continue

        length = cv2.arcLength(contour, closed=False)
        if length < 8:
            continue

        epsilon = max(0.5, config.contour_simplify_ratio * length)
        approx = cv2.approxPolyDP(contour, epsilon, closed=False)

        pts = approx.reshape(-1, 2)
        if len(pts) < config.min_points_per_path:
            continue

        if len(pts) > config.max_points_per_path:
            step = int(np.ceil(len(pts) / float(config.max_points_per_path)))
            pts = pts[::step]

        area = abs(cv2.contourArea(contour))
        score = length + area * 0.02

        norm_pts = [
            (float(x) / max(1, w - 1), float(y) / max(1, h - 1))
            for x, y in pts
        ]

        scored.append({
            "score": score,
            "points": norm_pts
        })

    scored.sort(key=lambda item: item["score"], reverse=True)

    return [item["points"] for item in scored[:config.max_paths]], {
        "edge_method": "opencv_canny",
        "composite_width": int(w),
        "composite_height": int(h),
        "contours_found": len(scored),
        "contours_used": min(len(scored), config.max_paths),
    }


def _extract_contours_pillow(composite, config):
    img = Image.fromarray(composite)
    img = img.filter(ImageFilter.FIND_EDGES)
    arr = np.array(img)

    h, w = arr.shape[:2]
    threshold = int(np.percentile(arr, 88))

    paths = []
    row_step = max(4, h // 60)

    for y in range(0, h, row_step):
        row = arr[y]
        xs = np.where(row > threshold)[0]
        if len(xs) < 4:
            continue

        run = []
        last = None
        for x in xs:
            if last is None or x <= last + 2:
                run.append(x)
            else:
                if len(run) >= 4:
                    points = [(float(px) / max(1, w - 1), float(y) / max(1, h - 1)) for px in run]
                    paths.append(points)
                run = [x]
            last = x

        if len(run) >= 4:
            points = [(float(px) / max(1, w - 1), float(y) / max(1, h - 1)) for px in run]
            paths.append(points)

    return paths[:config.max_paths], {
        "edge_method": "pillow_find_edges",
        "composite_width": int(w),
        "composite_height": int(h),
        "contours_found": len(paths),
        "contours_used": min(len(paths), config.max_paths),
    }


def analyze_photos(photo_paths, config):
    if not photo_paths:
        raise ValueError("No hay fotos para analizar.")

    photo_paths = sorted([Path(p) for p in photo_paths], key=natural_sort_key)
    photo_paths = photo_paths[-int(config.max_photos):]

    film_aspect = float(config.film_width_mm) / float(config.film_height_mm)
    composite = _composite_photos(photo_paths, film_aspect, int(config.image_process_height_px))

    if cv2 is not None:
        paths, meta = _extract_contours_cv2(composite, config)
    else:
        paths, meta = _extract_contours_pillow(composite, config)

    meta.update({
        "photos_used": len(photo_paths),
        "photo_files": [str(p) for p in photo_paths],
    })

    return paths, meta
