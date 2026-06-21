from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, ImageFilter

try:
    import cv2
except Exception:
    cv2 = None

from utils import natural_sort_key


def _read_gray(path):
    if cv2 is not None:
        arr = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if arr is None:
            raise ValueError(f"No se pudo leer imagen: {path}")
        return arr
    img = Image.open(path)
    return np.array(ImageOps.grayscale(img))


def _center_crop(gray, aspect):
    h, w = gray.shape[:2]
    current = w / float(h)
    if current > aspect:
        new_w = max(1, int(round(h * aspect)))
        x0 = (w - new_w) // 2
        return gray[:, x0:x0 + new_w]
    new_h = max(1, int(round(w / aspect)))
    y0 = (h - new_h) // 2
    return gray[y0:y0 + new_h, :]


def _resize(gray, target_w, target_h):
    if cv2 is not None:
        return cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(gray)
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return np.array(img)


def _autocontrast(gray):
    p1 = np.percentile(gray, 1)
    p99 = np.percentile(gray, 99)
    if p99 <= p1:
        return gray
    arr = (gray.astype(np.float32) - p1) * (255.0 / (p99 - p1))
    return np.clip(arr, 0, 255).astype(np.uint8)


def _smooth(gray, ksize):
    if ksize % 2 == 0:
        ksize += 1
    if cv2 is not None:
        return cv2.GaussianBlur(gray, (ksize, ksize), 0)
    img = Image.fromarray(gray)
    img = img.filter(ImageFilter.GaussianBlur(radius=max(1, ksize // 2)))
    return np.array(img)


def _quantize(gray, levels):
    levels = max(2, int(levels))
    bins = np.linspace(0, 256, levels + 1)
    inds = np.digitize(gray, bins) - 1
    inds = np.clip(inds, 0, levels - 1)
    vals = np.linspace(0, 255, levels)
    quant = vals[inds].astype(np.uint8)
    return quant, inds.astype(np.uint8)


def _compose_median(photo_paths, aspect, target_h):
    target_w = max(100, int(round(target_h * aspect)))
    stack = []
    for p in photo_paths:
        g = _read_gray(p)
        g = _center_crop(g, aspect)
        g = _resize(g, target_w, target_h)
        stack.append(g.astype(np.float32))
    composite = np.median(np.stack(stack, axis=0), axis=0).astype(np.uint8)
    composite = _autocontrast(composite)
    return composite


def _extract_contours(level_index_map, gray, config):
    h, w = gray.shape[:2]
    contours_out = []
    meta = {"contours_found": 0, "contours_used": 0}
    if cv2 is None:
        return contours_out, meta

    area_min = h * w * float(config.min_contour_area_ratio)

    # Tomar masas oscuras y medias oscuras.
    level_values = sorted(np.unique(level_index_map).tolist())
    target_levels = level_values[: max(1, min(3, len(level_values)))]

    for level in target_levels:
        mask = (level_index_map <= level).astype(np.uint8) * 255
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if len(found) == 2:
            contours, _ = found
        else:
            _img, contours, _ = found
        for c in contours:
            area = abs(cv2.contourArea(c))
            if area < area_min:
                continue
            length = cv2.arcLength(c, closed=True)
            if length < 20:
                continue
            eps = max(0.5, float(config.contour_simplify_ratio) * length)
            approx = cv2.approxPolyDP(c, eps, True)
            pts = approx.reshape(-1, 2)
            if len(pts) < int(config.min_points_per_contour):
                continue
            if len(pts) > int(config.max_points_per_contour):
                step = int(np.ceil(len(pts) / float(config.max_points_per_contour)))
                pts = pts[::step]
            norm = [(float(x) / max(1, w - 1), float(y) / max(1, h - 1)) for x, y in pts]
            score = area + length * 2.0
            contours_out.append({"score": score, "points": norm})

    contours_out.sort(key=lambda x: x["score"], reverse=True)
    meta["contours_found"] = len(contours_out)
    contours_out = contours_out[: int(config.max_contours)]
    meta["contours_used"] = len(contours_out)
    return [c["points"] for c in contours_out], meta


def analyze_photos(photo_paths, config):
    photo_paths = sorted([Path(p) for p in photo_paths], key=natural_sort_key)
    photo_paths = photo_paths[-int(config.max_photos):]

    aspect = float(config.film_width_mm) / float(config.film_height_mm)
    gray = _compose_median(photo_paths, aspect, int(config.image_process_height_px))
    if cv2 is not None:
        k = int(config.blur_size)
        if k % 2 == 0:
            k += 1
        smooth = cv2.GaussianBlur(gray, (k, k), 0)
    else:
        smooth = gray
    quantized, level_index = _quantize(smooth, int(config.quantization_levels))
    contours, contour_meta = _extract_contours(level_index, smooth, config)

    meta = {
        "photos_used": len(photo_paths),
        "photo_files": [str(p) for p in photo_paths],
        "composite_width": int(gray.shape[1]),
        "composite_height": int(gray.shape[0]),
        "quantization_levels": int(config.quantization_levels),
        **contour_meta,
    }
    return {
        "gray": gray,
        "smooth": smooth,
        "quantized": quantized,
        "level_index": level_index,
        "contours": contours,
        "meta": meta,
    }
