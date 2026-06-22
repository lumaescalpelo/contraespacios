from dataclasses import dataclass


@dataclass
class DrawingConfig:
    # Area de dibujo calibrada para la maquina actual.
    film_width_mm: float = 30.0
    film_height_mm: float = 32.0
    margin_mm: float = 0.8

    image_process_height_px: int = 420
    max_photos: int = 12

    # Cuantización / masas.
    quantization_levels: int = 5
    blur_size: int = 7

    # Contornos grandes.
    max_contours: int = 8
    max_points_per_contour: int = 100
    min_points_per_contour: int = 10
    contour_simplify_ratio: float = 0.012
    min_contour_area_ratio: float = 0.0025

    # Bandas parciales tipo paisaje.
    landscape_bands: int = 5
    band_samples: int = 90
    band_dark_threshold: float = 0.55
    band_amplitude_mm: float = 0.75
    band_min_length_ratio: float = 0.08

    # Líneas internas suaves.
    internal_lines: int = 3
    internal_samples: int = 80
    internal_dark_threshold: float = 0.46
    internal_amplitude_mm: float = 0.42

    # Salidas.
    stroke_width_mm: float = 0.11
    preview_height_px: int = 700
    preview_line_width_px: int = 2
    gcode_feed_mm_min: float = 300.0
    gcode_seek_mm_min: float = 600.0

    algorithm_name: str = "contraespacios_svg_v4_30x32_legible"


DEFAULT_CONFIG = DrawingConfig()
