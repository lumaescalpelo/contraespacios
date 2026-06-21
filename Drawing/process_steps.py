from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from preview_generator import write_preview
from svg_generator import (
    _partial_landscape_bands,
    _internal_feature_lines,
    _contours_to_paths,
    _nearest_order,
)
from utils import ensure_dir, save_json


def _save_gray_like(array, path):
    path = Path(path)
    ensure_dir(path.parent)

    arr = np.asarray(array)

    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    Image.fromarray(arr, mode="L").save(path)

    return str(path)


def _save_contact_sheet(photo_paths, output_path, thumb_h=120, cols=3):
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    photos = [Path(p) for p in photo_paths]
    imgs = []

    for p in photos:
        try:
            img = Image.open(p).convert("L")
            w, h = img.size
            thumb_w = max(1, int(round(thumb_h * w / max(1, h))))
            img = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            img = ImageOps.expand(img, border=1, fill=180)
            imgs.append((p.name, img))
        except Exception:
            continue

    if not imgs:
        return None

    font_space = 14
    pad = 6
    max_w = max(img.width for _, img in imgs)
    rows = int(np.ceil(len(imgs) / float(cols)))
    cell_w = max_w + pad * 2
    cell_h = thumb_h + font_space + pad * 2

    sheet = Image.new("L", (cols * cell_w, rows * cell_h), 255)
    draw = ImageDraw.Draw(sheet)

    for i, (name, img) in enumerate(imgs):
        r = i // cols
        c = i % cols
        x = c * cell_w + pad
        y = r * cell_h + pad + font_space
        sheet.paste(img, (x, y))
        draw.text((x, r * cell_h + 2), name, fill=0)

    sheet.save(output_path)

    return str(output_path)


def _save_contours_overlay(image_analysis, output_path):
    gray = image_analysis["gray"]
    h, w = gray.shape[:2]

    img = Image.fromarray(gray, mode="L").convert("RGB")
    draw = ImageDraw.Draw(img)

    for contour in image_analysis["contours"]:
        pts = [(xn * (w - 1), yn * (h - 1)) for xn, yn in contour]

        if len(pts) >= 2:
            draw.line(pts + [pts[0]], fill=(255, 0, 0), width=1)

    ensure_dir(Path(output_path).parent)
    img.save(output_path)

    return str(output_path)


def save_process_steps(session, image_analysis, env_stats, visual, config, output_dir):
    output_dir = Path(output_dir)
    steps_dir = ensure_dir(output_dir / "process_steps")

    manifest = []

    def add_step(num, filename, description):
        manifest.append(
            {
                "step": num,
                "file": filename,
                "description": description,
            }
        )

    # 01. Fotos fuente
    contact_name = "01_source_photos_contact_sheet.png"
    _save_contact_sheet(image_analysis["meta"]["photo_files"], steps_dir / contact_name)
    add_step(
        1,
        contact_name,
        "Hoja de contacto de las fotos válidas utilizadas en la sesión.",
    )

    # 02. Resumen de sesión
    session_summary_name = "02_session_summary.json"
    save_json(
        steps_dir / session_summary_name,
        {
            "session_id": session["session_id"],
            "photos_used": image_analysis["meta"]["photos_used"],
            "photo_files": image_analysis["meta"]["photo_files"],
            "environment_files": [str(x["path"]) for x in session["environment"]],
        },
    )
    add_step(
        2,
        session_summary_name,
        "Resumen de archivos de entrada usados para esta generación.",
    )

    # 03. Ambiente
    env_summary_name = "03_environment_summary.json"
    save_json(
        steps_dir / env_summary_name,
        {
            "environment_stats": env_stats,
            "visual_parameters": visual,
        },
    )
    add_step(
        3,
        env_summary_name,
        "Estadísticas ambientales y parámetros visuales derivados de las lecturas.",
    )

    # 04-07. Raster e imagen
    name = "04_composite_gray.png"
    _save_gray_like(image_analysis["gray"], steps_dir / name)
    add_step(
        4,
        name,
        "Composición en gris creada a partir de varias fotos de la sesión.",
    )

    name = "05_smoothed.png"
    _save_gray_like(image_analysis["smooth"], steps_dir / name)
    add_step(
        5,
        name,
        "Imagen suavizada para reducir ruido y preparar extracción de formas.",
    )

    name = "06_quantized.png"
    _save_gray_like(image_analysis["quantized"], steps_dir / name)
    add_step(
        6,
        name,
        "Imagen cuantizada en niveles tonales para simplificar las masas visuales.",
    )

    name = "07_contours_overlay.png"
    _save_contours_overlay(image_analysis, steps_dir / name)
    add_step(
        7,
        name,
        "Contornos detectados superpuestos sobre la composición en gris.",
    )

    # 08-10. Familias de trayectorias
    band_paths, band_meta = _partial_landscape_bands(image_analysis, visual, config)
    internal_paths, internal_meta = _internal_feature_lines(image_analysis, visual, config)
    contour_paths, contour_meta = _contours_to_paths(
        image_analysis["contours"],
        visual,
        config,
    )

    name = "08_landscape_bands_preview.png"
    write_preview(steps_dir / name, band_paths, config)
    add_step(
        8,
        name,
        "Bandas de paisaje parciales generadas a partir de la lectura tonal horizontal.",
    )

    name = "09_internal_lines_preview.png"
    write_preview(steps_dir / name, internal_paths, config)
    add_step(
        9,
        name,
        "Líneas internas suaves que sugieren estructura y variación local.",
    )

    name = "10_contour_paths_preview.png"
    write_preview(steps_dir / name, contour_paths, config)
    add_step(
        10,
        name,
        "Trayectorias derivadas de los contornos principales detectados en la imagen.",
    )

    # 11. Resultado ordenado
    ordered = _nearest_order(band_paths + internal_paths + contour_paths)

    name = "11_final_ordered_paths_preview.png"
    write_preview(steps_dir / name, ordered, config)
    add_step(
        11,
        name,
        "Vista previa del recorrido final continuo, ya ordenado para dibujo sin eje Z.",
    )

    # 12. Metadatos
    meta_name = "12_path_groups_metadata.json"
    save_json(
        steps_dir / meta_name,
        {
            "band_meta": band_meta,
            "internal_meta": internal_meta,
            "contour_meta": contour_meta,
            "final_paths_count": len(ordered),
            "style": "landscape_legible_debug",
        },
    )
    add_step(
        12,
        meta_name,
        "Metadatos de las familias de trayectorias y del ordenamiento final.",
    )

    # Manifest
    manifest_name = "00_manifest.json"
    save_json(steps_dir / manifest_name, {"steps": manifest})

    # README humano
    readme_name = "README_steps.txt"
    lines = [
        "Proceso de transformación de imagen para Contra Espacios:",
        "",
    ]

    for item in manifest:
        lines.append(
            f"{item['step']:02d}. {item['file']} - {item['description']}"
        )

    (steps_dir / readme_name).write_text("\n".join(lines), encoding="utf-8")

    return {
        "steps_dir": str(steps_dir),
        "manifest": str(steps_dir / manifest_name),
        "steps_count": len(manifest),
    }
