"""Análisis de imagen orientado a mayor semejanza con las fotos."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, ImageFilter

try:
    import cv2
except Exception:
    cv2 = None

from utils import natural_sort_key


def _load_gray_cv2(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"No se pudo abrir imagen: {path}")
    return img


def _load_gray_pillow(path):
    img = Image.open(path)
    img = ImageOps.grayscale(img)
    return np.array(img)


def _center_crop_to_aspect(gray, target_aspect):
    h, w = gray.shape[:2]
    current_aspect = w / float(h)
    if current_aspect > target_aspect:
        new_w = max(1, int(round(h * target_aspect)))
        x0 = (w - new_w) // 2
        return gray[:, x0:x0 + new_w]
    new_h = max(1, int(round(w / target_aspect)))
    y0 = (h - new_h) // 2
    return gray[y0:y0 + new_h, :]


def _resize(gray, target_w, target_h):
    if cv2 is not None:
        return cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(gray)
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return np.array(img)


def _normalize_contrast(gray):
    # Autocontraste ligero para que la escena tenga más presencia.
    p_low = np.percentile(gray, 2)
    p_high = np.percentile(gray, 98)
    if p_high <= p_low:
        return gray
    arr = (gray.astype(np.float32) - p_low) * (255.0 / (p_high - p_low))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return arr


def _composite_photos(photo_paths, film_aspect, target_h):
    target_w = max(64, int(round(target_h * film_aspect)))
    processed = []
    for path in photo_paths:
        gray = _load_gray_cv2(path) if cv2 is not None else _load_gray_pillow(path)
        gray = _center_crop_to_aspect(gray, film_aspect)
        gray = _resize(gray, target_w, target_h)
        processed.append(gray.astype(np.float32))
    # Mediana para conservar estructura y reducir ruido.
    composite = np.median(np.stack(processed, axis=0), axis=0).astype(np.uint8)
    composite = _normalize_contrast(composite)
    return composite


def _smooth(gray, blur_size):
    blur_size = int(blur_size)
    if blur_size % 2 == 0:
        blur_size += 1
    if cv2 is not None:
        return cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    img = Image.fromarray(gray).filter(ImageFilter.GaussianBlur(radius=max(1, blur_size // 2)))
    return np.array(img)


def _extract_edges_and_contours(gray, config):
    if cv2 is None:
        # Fallback muy básico si no está OpenCV.
        h, w = gray.shape[:2]
        gx = np.zeros_like(gray, dtype=np.float32)
        gx[:, 1:] = np.abs(gray[:, 1:].astype(np.float32) - gray[:, :-1].astype(np.float32))
        edges = np.clip(gx * 2, 0, 255).astype(np.uint8)
        return edges, [], {
            "edge_method": "fallback_gradient",
            "contours_found": 0,
            "contours_used": 0,
        }

    blur_size = int(config.blur_size)
    if blur_size % 2 == 0:
        blur_size += 1
    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    edges = cv2.Canny(blurred, int(config.canny_low), int(config.canny_high))

    found = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    if len(found) == 2:
        contours, _ = found
    else:
        _img, contours, _ = found

    h, w = gray.shape[:2]
    scored = []
    for contour in contours:
        if contour is None or len(contour) < config.min_points_per_contour:
            continue
        length = cv2.arcLength(contour, closed=False)
        if length < 10:
            continue
        epsilon = max(0.4, config.contour_simplify_ratio * length)
        approx = cv2.approxPolyDP(contour, epsilon, closed=False)
        pts = approx.reshape(-1, 2)
        if len(pts) < config.min_points_per_contour:
            continue
        if len(pts) > config.max_points_per_contour:
            step = int(np.ceil(len(pts) / float(config.max_points_per_contour)))
            pts = pts[::step]
        area = abs(cv2.contourArea(contour))
        score = length + area * 0.015
        norm_pts = [(float(x) / max(1, w - 1), float(y) / max(1, h - 1)) for x, y in pts]
        scored.append({"score": score, "points": norm_pts})

    scored.sort(key=lambda item: item["score"], reverse=True)
    used = scored[: int(config.max_contours)]
    return edges, [item["points"] for item in used], {
        "edge_method": "opencv_canny",
        "contours_found": len(scored),
        "contours_used": len(used),
    }


def analyze_photos(photo_paths, config):
    if not photo_paths:
        raise ValueError("No hay fotos para analizar.")
    photo_paths = sorted([Path(p) for p in photo_paths], key=natural_sort_key)
    photo_paths = photo_paths[-int(config.max_photos):]

    film_aspect = float(config.film_width_mm) / float(config.film_height_mm)
    composite = _composite_photos(photo_paths, film_aspect, int(config.image_process_height_px))
    edges, contours, meta = _extract_edges_and_contours(composite, config)

    meta.update({
        "photos_used": len(photo_paths),
        "photo_files": [str(p) for p in photo_paths],
        "composite_width": int(composite.shape[1]),
        "composite_height": int(composite.shape[0]),
    })

    return {
        "gray": composite,
        "edges": edges,
        "contours": contours,
        "meta": meta,
    }
